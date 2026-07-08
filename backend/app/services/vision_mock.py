"""Mock Vision — returns a structured companion reply as JSON, no API needed.

It recovers the user's words from the companion prompt and keyword-routes to an
intent, so `VISION_PROVIDER=mock` gives a full offline walkthrough of the product
(and lets tests exercise the companion pipeline for free). Swap
VISION_PROVIDER=gemini for real image understanding.
"""

import asyncio
import json

from app.companion import facts_from_prompt, transcript_from_prompt

# Recall must be memory-referential, not any question: "what am I allergic to"
# is recall, but "what is in front of me" is a scene question (describe). Keying
# on bare "what"/"who" swallowed scene questions, so require specific phrasing.
_QUESTION_STARTS = (
    "do you remember",
    "did i",
    "recall",
    "what did i",
    "what do you remember",
    "what am i",
    "who am i",
    "who is",
    "am i",
)


class MockVision:
    async def describe(self, image_b64: str, question: str) -> str:
        await asyncio.sleep(0.15)  # pretend we called a vision model
        said = transcript_from_prompt(question).lower()

        intent, spoken, memory_add, reminder, navigation = "describe", "", None, None, None

        if any(w in said for w in ("take me", "walk me", "navigate", "directions to")):
            intent = "navigate"
            dest = said.split(" to ", 1)[1].strip() if " to " in said else "your destination"
            spoken = f"[mock] Okay, taking you to {dest}."
            navigation = {"action": "start", "destination": dest}
        elif "where am i" in said or "where are we" in said:
            intent = "where_am_i"
            spoken = "[mock] The footpath ahead is clear; a doorway is on your left."
        elif "stop" in said and ("navigat" in said or "direction" in said or "route" in said):
            intent = "stop_navigation"
            spoken = "[mock] Navigation stopped."
            navigation = {"action": "stop"}
        elif any(w in said for w in ("read", "label", "menu", "sign", "mail")):
            intent = "read"
            spoken = "[mock] The label reads: Whole Milk, best before June 5th."
        elif any(w in said for w in ("find", "where", "locate")):
            intent = "find"
            spoken = "[mock] Your mug is on the table, just to your right."
        elif said.startswith(_QUESTION_STARTS):
            # Recall: answer from the facts injected into the prompt.
            intent = "recall"
            facts = facts_from_prompt(question)
            spoken = (
                "[mock] Here's what you told me: " + "; ".join(facts) + "."
                if facts
                else "[mock] I don't have anything remembered about that yet."
            )
        elif said.startswith("remember") or "this is" in said or "allergic" in said:
            intent = "remember"
            spoken = "[mock] Got it — I'll remember that."
            memory_add = transcript_from_prompt(question) or "a fact about the user"
        elif "remind" in said:
            intent = "remind"
            spoken = "[mock] Okay, I'll remind you."
            reminder = {"text": said, "when": "later"}
        elif any(w in said for w in ("reminder", "schedule", "today")):
            intent = "list_reminders"
            spoken = "[mock] You have no reminders set yet."
        else:
            intent = "describe"
            spoken = (
                "[mock] A wooden table is ahead of you with a mug to the right, "
                "a doorway on your left, and the path is clear."
            )

        return json.dumps(
            {
                "intent": intent,
                "spoken": spoken,
                "memory_add": memory_add,
                "reminder": reminder,
                "navigation": navigation,
            }
        )
