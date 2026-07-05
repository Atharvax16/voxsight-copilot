"""Persistent memory for the companion: facts it should remember about the user.

A tiny JSON store (single-user for the demo). Facts are injected into every
companion prompt so VoxSight can use them — e.g. warn about allergens when
reading a menu, or greet a person it was introduced to. Reminders live here too
and are wired up in Phase 3.
"""

import json
from pathlib import Path

MEMORY_PATH = Path(__file__).resolve().parent.parent / "memory_store.json"


class MemoryStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else MEMORY_PATH

    def _load(self) -> dict:
        if not self.path.exists():
            return {"facts": [], "reminders": []}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("facts", [])
        data.setdefault("reminders", [])
        return data

    def _save(self, data: dict) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def facts(self) -> list[str]:
        return self._load()["facts"]

    def add_fact(self, fact: str) -> None:
        fact = (fact or "").strip()
        if not fact:
            return
        data = self._load()
        if fact.lower() not in (f.lower() for f in data["facts"]):
            data["facts"].append(fact)
            self._save(data)

    def reminders(self) -> list[dict]:
        return self._load()["reminders"]

    def add_reminder(self, reminder: dict) -> None:
        data = self._load()
        data["reminders"].append(reminder)
        self._save(data)

    def clear(self) -> None:
        self._save({"facts": [], "reminders": []})
