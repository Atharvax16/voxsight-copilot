"""Phase 1 companion tests — all offline (mock providers), zero API credits.

Covers the JSON parser's robustness and end-to-end intent routing through the
real WebSocket, with STT/vision/TTS all on mock.
"""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import companion  # noqa: E402


def test_parse_clean_json():
    r = companion.parse('{"intent": "read", "spoken": "It says Exit.", "memory_add": null, "reminder": null}')
    assert r.intent == "read" and r.spoken == "It says Exit."


def test_parse_fenced_and_noisy():
    raw = 'Sure!\n```json\n{"intent":"find","spoken":"On your left.","memory_add":null,"reminder":null}\n```'
    r = companion.parse(raw)
    assert r.intent == "find" and r.spoken == "On your left."


def test_parse_prose_fallback():
    # Model ignored the JSON instruction — we still speak whatever it said.
    r = companion.parse("There is a red door ahead of you.")
    assert r.intent == "describe" and "red door" in r.spoken


def test_parse_unknown_intent_defaults():
    r = companion.parse('{"intent": "teleport", "spoken": "ok"}')
    assert r.intent == "describe" and r.spoken == "ok"


def test_parse_extracts_sideeffects():
    r = companion.parse(
        '{"intent":"remind","spoken":"Will do.","memory_add":null,'
        '"reminder":{"text":"pills","when":"20:00"}}'
    )
    assert r.reminder == {"text": "pills", "when": "20:00"}


def _run_intent(transcript: str) -> dict:
    """Drive one WS turn fully offline and return the last two messages."""
    import importlib
    import tempfile

    import app.config as cfg

    cfg.settings.demo_mode = "off"
    cfg.settings.stt_provider = "mock"
    cfg.settings.vision_provider = "mock"
    cfg.settings.tts_provider = "mock"

    # Isolate memory so a leftover demo fact can't reroute intents (a fact makes
    # "what..." questions look like recall). Point the store at a fresh temp file.
    import app.memory_store as mem

    mem.MEMORY_PATH = Path(tempfile.mkdtemp()) / "mem.json"

    from starlette.testclient import TestClient

    import app.orchestrator as orch

    importlib.reload(orch)
    from app.main import app

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "query", "image": "", "audio": "", "transcript": transcript})
            msgs = [ws.receive_json() for _ in range(3)]
    return {m["type"]: m for m in msgs}


def test_ws_intent_routing_offline():
    """The same button routes to different intents by what the user says."""
    for transcript, expected_word in [
        ("read this label for me", "milk"),
        ("where is my mug", "mug"),
        ("what is in front of me", "table"),
    ]:
        msgs = _run_intent(transcript)
        answer = msgs["answer"]["text"].lower()
        audio = base64.b64decode(msgs["audio"]["data"])
        assert expected_word in answer, f"{transcript!r} -> {answer!r}"
        assert len(audio) > 100  # mock TTS emits a real WAV tone
        print(f"OK  {transcript!r:34} -> {msgs['answer']['text']}")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL PHASE 1 TESTS PASS")
