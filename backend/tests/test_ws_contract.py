"""End-to-end WebSocket contract test.

Exercises the exact protocol the frontend (`src/lib/useSocket.ts`) speaks:
sends one `query` frame (JPEG data URL + a client transcript) and asserts the
backend streams back `transcript`, `answer`, and playable `audio`.

Runs the real app in-process via Starlette's TestClient, so it hits the live
providers configured in `.env` (Gemini vision + ElevenLabs TTS). That makes it a
true smoke test of the whole round-trip, not a mock.

Run:  cd backend && .venv/Scripts/python -m pytest tests/test_ws_contract.py -s
  or: cd backend && .venv/Scripts/python tests/test_ws_contract.py
"""

import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Allow running as a plain script (not just under pytest).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _scene_data_url() -> str:
    """A simple, recognizable scene so the vision answer is verifiable."""
    img = Image.new("RGB", (480, 480), "white")
    d = ImageDraw.Draw(img)
    d.ellipse([50, 50, 210, 210], fill="red")            # red circle, upper-left
    d.rectangle([280, 120, 430, 410], fill="royalblue")  # blue rectangle, right
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def test_ws_roundtrip():
    """Frontend-shaped query -> transcript + answer + audio."""
    question = "Briefly, what shapes and colors do you see?"
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "query",
                    "image": _scene_data_url(),
                    "audio": "",
                    "transcript": question,  # browser-mode: backend STT is skipped
                }
            )
            transcript = ws.receive_json()
            answer = ws.receive_json()
            audio = ws.receive_json()

    # Contract: three typed messages, in order.
    assert transcript["type"] == "transcript" and transcript["text"] == question
    assert answer["type"] == "answer" and answer["text"].strip()
    assert audio["type"] == "audio" and audio["mime"].startswith("audio/")
    audio_bytes = base64.b64decode(audio["data"])
    assert len(audio_bytes) > 1000  # real speech, not an empty blob

    print("\n--- WS round-trip OK ---")
    print("VISION ANSWER:", answer["text"])
    print(f"AUDIO: {len(audio_bytes)} bytes ({audio['mime']})")

    # Sanity: Gemini should mention at least one of the colors it was shown.
    low = answer["text"].lower()
    assert ("red" in low) or ("blue" in low), f"unexpected answer: {answer['text']}"
    return answer["text"], audio_bytes


if __name__ == "__main__":
    ans, audio = test_ws_roundtrip()
    out = Path(__file__).resolve().parents[1] / "_ws_test_output.mp3"
    out.write_bytes(audio)
    print("Saved audio ->", out.name)
    print("PASS")
