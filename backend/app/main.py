"""FastAPI entrypoint: REST /health + WebSocket /ws.

WS protocol (all JSON; binary is base64-encoded to keep framing simple):
  client -> {"type": "query", "image": "<b64 or data-url>", "audio": "<b64>",
             "transcript": "<optional; if set, backend STT is skipped>"}
  server -> {"type": "transcript", "text": "..."}
  server -> {"type": "answer", "text": "..."}
  server -> {"type": "audio", "mime": "audio/wav", "data": "<b64>"}
  server -> {"type": "error", "message": "..."}
"""

import base64
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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
            if msg.get("type") != "query":
                continue

            image_b64 = msg.get("image", "")
            audio_b64 = msg.get("audio", "")
            transcript = msg.get("transcript", "")
            try:
                audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
            except Exception:
                audio_bytes = b""

            try:
                turn = await orch.run(image_b64, audio_bytes, transcript)
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
    except WebSocketDisconnect:
        log.info("client disconnected")
