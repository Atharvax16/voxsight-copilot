"""Mock TTS — synthesizes a short spoken-length beep tone as a real WAV.

We can't call ElevenLabs without a key, but we can still return valid, playable
audio bytes so the frontend's audio round-trip is genuinely exercised tonight.
"""

import asyncio
import io
import math
import struct
import wave


def _tone_wav(duration_s: float = 0.6, freq: float = 440.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(rate)
        frames = bytearray()
        n = int(duration_s * rate)
        for i in range(n):
            # simple sine with a quick fade in/out to avoid clicks
            env = min(1.0, i / (rate * 0.05), (n - i) / (rate * 0.05))
            sample = int(env * 0.3 * 32767 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", sample)
        w.writeframes(bytes(frames))
    return buf.getvalue()


class MockTTS:
    async def synthesize(self, text: str) -> bytes:
        await asyncio.sleep(0.1)  # pretend we called a TTS API
        return _tone_wav()
