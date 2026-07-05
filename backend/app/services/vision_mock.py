"""Mock Vision — returns a structured companion reply as JSON, no API needed.

It recovers the user's words from the companion prompt and keyword-routes to an
intent, so `VISION_PROVIDER=mock` gives a full offline walkthrough of the product
(and lets tests exercise the companion pipeline for free). Swap
VISION_PROVIDER=gemini for real image understanding.
"""

import asyncio
import json

from app.companion import transcript_from_prompt


class MockVision:
    async def describe(self, image_b64: str, question: str) -> str:
        await asyncio.sleep(0.15)  # pretend we called a vision model
        said = transcript_from_prompt(question).lower()

        intent, spoken, memory_add, reminder = "describe", "", None, None

        if any(w in said for w in ("read", "label", "menu", "sign", "mail")):
            intent = "read"
            spoken = "[mock] The label reads: Whole Milk, best before June 5th."
        elif any(w in said for w in ("find", "where", "locate")):
            intent = "find"
            spoken = "[mock] Your mug is on the table, just to your right."
        elif said.startswith("remember") or "this is" in said or "allergic" in said:
            intent = "remember"
            spoken = "[mock] Got it — I'll remember that."
            memory_add = transcript_from_prompt(question) or "a fact about the user"
        elif "remind" in said:
            intent = "remind"
            spoken = "[mock] Okay, I'll remind you."
            reminder = {"text": said, "when": "later"}
        elif any(w in said for w in ("reminder", "schedule", "what's on", "today")):
            intent = "list_reminders"
            spoken = "[mock] You have no reminders set yet."
        else:
            intent = "describe"
            spoken = (
                "[mock] A wooden table is ahead of you with a mug to the right, "
                "a doorway on your left, and the path is clear."
            )

        return json.dumps(
            {"intent": intent, "spoken": spoken, "memory_add": memory_add, "reminder": reminder}
        )
