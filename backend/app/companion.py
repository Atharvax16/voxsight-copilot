"""Companion brain: turn one spoken request + camera frame into a structured turn.

Instead of a fixed "describe the scene" prompt, VoxSight decides *what the user
needs* (read text, find an object, remember a fact, set a reminder, ...) and
returns both the words to speak and any side-effects to apply. It all happens in
the single vision call, so there's no extra latency or credit cost.

`build_prompt` produces the instruction sent to the vision model; `parse` turns
the model's reply into a `CompanionResult`, degrading gracefully to plain speech
if the model didn't return clean JSON.
"""

import json
from dataclasses import dataclass

# Recognized intents. `other` is the catch-all.
INTENTS = (
    "describe",       # describe the scene / answer about what's visible
    "read",           # read text in view (mail, labels, menus, signs)
    "find",           # locate a specific object and say where it is
    "remember",       # store a fact the user tells us (person, place, preference, allergy)
    "recall",         # answer from what we remember
    "remind",         # create a reminder
    "list_reminders", # read back reminders
    "other",
)

# Marker the mock provider uses to recover the transcript from the prompt.
_SAID_PREFIX = "The user just said:"


@dataclass
class CompanionResult:
    intent: str
    spoken: str
    memory_add: str | None = None       # Phase 2: a fact to persist
    reminder: dict | None = None        # Phase 3: {"text": ..., "when": ...}


def build_prompt(transcript: str, facts: list[str], reminders: list[dict]) -> str:
    if facts or reminders:
        mem_lines = []
        if facts:
            mem_lines.append("Facts you remember about the user:")
            mem_lines += [f"- {f}" for f in facts]
        if reminders:
            mem_lines.append("Their reminders:")
            mem_lines += [f"- {r.get('text','')} ({r.get('when','')})" for r in reminders]
        memory_block = "\n".join(mem_lines)
    else:
        memory_block = "You don't remember anything about the user yet."

    return f"""You are VoxSight, a calm, concise companion for a person who is blind or has low vision. You see through their phone camera and hear what they say. Decide what they need, then reply in 1-3 short spoken sentences, leading with what matters for safety and orientation (obstacles, distances, left/right).

{_SAID_PREFIX} "{transcript}"

{memory_block}

Choose exactly ONE intent and act on it:
- describe: describe the scene or answer a question about what is visible.
- read: read the text visible in the image (mail, label, menu, sign) clearly and in order.
- find: locate the object they're looking for; say where it is relative to them.
- remember: they are telling you something to remember (a person, place, preference, or allergy). Acknowledge briefly, and put the fact in "memory_add" as a short third-person statement.
- recall: they're asking about something they told you before; answer from what you remember.
- remind: they want a reminder. Put it in "reminder" as {{"text": "...", "when": "..."}} and acknowledge.
- list_reminders: read back their reminders.
- other: anything else; help as best you can.

Use what you remember when relevant (for example, warn about allergens when reading a menu).

Reply with ONLY a JSON object, no markdown fences, exactly:
{{"intent": "<one of the above>", "spoken": "<what to say>", "memory_add": null, "reminder": null}}"""


def parse(raw: str, transcript: str = "") -> CompanionResult:
    """Parse the model reply into a CompanionResult, degrading to plain speech."""
    text = (raw or "").strip()

    # Pull the JSON object out of any surrounding prose / code fences.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            intent = data.get("intent", "describe")
            if intent not in INTENTS:
                intent = "describe"
            spoken = (data.get("spoken") or "").strip()
            if spoken:
                reminder = data.get("reminder")
                if not isinstance(reminder, dict):
                    reminder = None
                mem = data.get("memory_add")
                mem = mem.strip() if isinstance(mem, str) and mem.strip() else None
                return CompanionResult(intent, spoken, mem, reminder)
        except (ValueError, AttributeError):
            pass

    # Fallback: the model answered in prose — just speak it (or a safe default).
    spoken = text or "Sorry, I didn't catch that. Could you ask again?"
    return CompanionResult("describe", spoken)


def transcript_from_prompt(prompt: str) -> str:
    """Recover the user's words from a companion prompt (used by the mock provider)."""
    if _SAID_PREFIX in prompt:
        after = prompt.split(_SAID_PREFIX, 1)[1].lstrip()
        if after.startswith('"'):
            return after[1:].split('"', 1)[0]
    return ""
