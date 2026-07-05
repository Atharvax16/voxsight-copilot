"""Phase 2 memory tests — offline (mock providers), zero API credits.

Verifies the facts store and the remember -> recall loop end to end: a fact the
user states is persisted, injected into later prompts, and can be recalled.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.memory_store import MemoryStore  # noqa: E402


def test_store_add_dedupe_clear():
    store = MemoryStore(Path(tempfile.mkdtemp()) / "mem.json")
    assert store.facts() == []
    store.add_fact("The user is allergic to peanuts")
    store.add_fact("the user is ALLERGIC to peanuts")  # dupe (case-insensitive)
    store.add_fact("")  # ignored
    assert store.facts() == ["The user is allergic to peanuts"]
    store.clear()
    assert store.facts() == []


def test_remember_then_recall_offline():
    """remember a fact -> it's stored -> a later turn recalls it. All mock."""
    import importlib

    import app.config as cfg

    cfg.settings.demo_mode = "off"
    cfg.settings.stt_provider = "mock"
    cfg.settings.vision_provider = "mock"
    cfg.settings.tts_provider = "mock"

    import app.orchestrator as orch_mod

    importlib.reload(orch_mod)

    import asyncio

    async def scenario():
        o = orch_mod.Orchestrator()
        o.memory = MemoryStore(Path(tempfile.mkdtemp()) / "mem.json")  # isolated

        # 1) State a fact.
        t1 = await o.run("", b"", "remember I am allergic to peanuts")
        assert t1.intent == "remember"
        facts = o.memory.facts()
        assert facts and "peanut" in facts[0].lower(), facts

        # 2) Ask about it later — recall reads the injected memory.
        t2 = await o.run("", b"", "what am I allergic to")
        assert t2.intent == "recall"
        assert "peanut" in t2.answer.lower(), t2.answer
        return t1, t2

    t1, t2 = asyncio.run(scenario())
    print("\nremember ->", t1.answer)
    print("recall   ->", t2.answer)


if __name__ == "__main__":
    test_store_add_dedupe_clear()
    test_remember_then_recall_offline()
    print("\nALL PHASE 2 TESTS PASS")
