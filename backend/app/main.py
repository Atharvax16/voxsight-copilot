"""FastAPI entrypoint: REST /health + WebSocket /ws.

WS protocol (all JSON; binary is base64-encoded to keep framing simple):
  client -> {"type": "query", "image": "<b64 or data-url>", "audio": "<b64>",
             "transcript": "<optional; if set, backend STT is skipped>",
             "location": {"lat": .., "lng": ..}   # optional, for navigation}
  client -> {"type": "location", "location": {"lat": .., "lng": ..}}  # walk-mode tick
  server -> {"type": "transcript", "text": "..."}
  server -> {"type": "answer", "text": "..."}
  server -> {"type": "audio", "mime": "audio/wav", "data": "<b64>"}
  server -> {"type": "nav_step", "text": "..."}   # turn-by-turn announcement
  server -> {"type": "error", "message": "..."}
"""

import base64
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("voxsight")

app = FastAPI(title="VoxSight backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "providers": {
            "stt": settings.stt_provider,
            "vision": settings.vision_provider,
            "tts": settings.tts_provider,
        },
    }


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    orch = Orchestrator()
    log.info("client connected")
    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            # --- walk-mode location tick: turn-by-turn only, no model call ---
            if msg_type == "location":
                loc = msg.get("location") or {}
                if "lat" not in loc or "lng" not in loc:
                    continue
                try:
                    step = await orch.on_location(float(loc["lat"]), float(loc["lng"]))
                except Exception as exc:
                    log.exception("navigation tick error")
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                if step is not None:
                    await websocket.send_json({"type": "nav_step", "text": step.text})
                    if step.audio:
                        await websocket.send_json(
                            {
                                "type": "audio",
                                "mime": step.mime,
                                "data": base64.b64encode(step.audio).decode("ascii"),
                            }
                        )
                continue

            if msg_type != "query":
                continue

            image_b64 = msg.get("image", "")
            audio_b64 = msg.get("audio", "")
            transcript = msg.get("transcript", "")
            location = msg.get("location")
            try:
                audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
            except Exception:
                audio_bytes = b""

            try:
                turn = await orch.run(image_b64, audio_bytes, transcript, location)
            except Exception as exc:  # keep the socket alive on provider errors
                log.exception("pipeline error")
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            await websocket.send_json({"type": "transcript", "text": turn.transcript})
            await websocket.send_json({"type": "answer", "text": turn.answer})
            await websocket.send_json(
                {
                    "type": "audio",
                    "mime": turn.mime,
                    "data": base64.b64encode(turn.audio).decode("ascii"),
                }
            )
            # Surface the started route to the UI (the answer already spoke step 1).
            if turn.intent == "navigate":
                await websocket.send_json({"type": "nav_step", "text": turn.answer})
    except WebSocketDisconnect:
        log.info("client disconnected")


# Serve the exported frontend (frontend/out) on the same origin, so the whole app
# can run behind a single tunnel. Mounted last so /health and /ws win. Skipped if
# the static build doesn't exist (normal dev uses the Next dev server instead).
_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "out"
if _FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
    log.info("serving frontend from %s", _FRONTEND)
