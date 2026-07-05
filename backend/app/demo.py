"""Demo capture/replay store — present and record without burning API credits.

Three modes (env `DEMO_MODE`):
  off     — normal live pipeline (default)
  capture — live pipeline, but every turn is saved to `recordings/`
  replay  — serve saved turns, NO API calls (free, instant, can't fail live)

Replay picks the saved clip whose transcript best overlaps the asked question,
falling back to sequential playback. This makes a scripted demo reliable: say the
question you captured and you get that exact real answer + audio back.
"""

import json
from dataclasses import dataclass
from pathlib import Path

RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "recordings"


@dataclass
class Recording:
    transcript: str
    answer: str
    audio: bytes
    mime: str


def _tokens(s: str) -> set[str]:
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if w}


class RecordingStore:
    def __init__(self, directory: Path = RECORDINGS_DIR) -> None:
        self.dir = directory
        self.dir.mkdir(exist_ok=True)
        self.manifest = self.dir / "manifest.json"
        self._seq = 0  # round-robin cursor for replay fallback

    def _load(self) -> list[dict]:
        if not self.manifest.exists():
            return []
        return json.loads(self.manifest.read_text(encoding="utf-8")).get("clips", [])

    def save(self, transcript: str, answer: str, audio: bytes, mime: str) -> None:
        clips = self._load()
        ext = "wav" if "wav" in mime else "mp3"
        name = f"clip_{len(clips) + 1:03d}.{ext}"
        (self.dir / name).write_bytes(audio)
        clips.append(
            {"transcript": transcript, "answer": answer, "audio": name, "mime": mime}
        )
        self.manifest.write_text(
            json.dumps({"clips": clips}, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def count(self) -> int:
        return len(self._load())

    def match(self, transcript: str) -> Recording | None:
        clips = self._load()
        if not clips:
            return None

        # Best transcript overlap; fall back to round-robin if nothing matches.
        q = _tokens(transcript)
        best, best_score = None, 0
        for clip in clips:
            score = len(q & _tokens(clip["transcript"])) if q else 0
            if score > best_score:
                best, best_score = clip, score
        if best is None:
            best = clips[self._seq % len(clips)]
            self._seq += 1

        audio = (self.dir / best["audio"]).read_bytes()
        return Recording(best["transcript"], best["answer"], audio, best["mime"])
