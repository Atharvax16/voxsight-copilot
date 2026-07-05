# VoxSight

Real-time accessibility co-pilot for visually impaired users. Point a camera, hold a button, ask a
question by voice → get a spoken answer describing your surroundings.

Pipeline: **audio + camera frame → STT → Qwen Vision → ElevenLabs TTS → audio back**, over WebSocket.

Full spec: [`voxsight_technical_blueprint.md`](./voxsight_technical_blueprint.md).

---

## Status: pre-hackathon skeleton (mock mode)

The whole app runs **end-to-end tonight with zero API keys.** Every AI service has a swappable
provider selected by an env flag; tonight they're all `mock`. Tomorrow you paste keys and flip flags —
no code changes needed in the pipeline.

```
Browser (Next.js)            FastAPI backend
 camera ─ frame ─┐
 mic ─ audio ────┼─ WS /ws ─► Orchestrator ─► STT ─► Vision ─► TTS ─► audio back
 audio playback ◄┘                          (mock|wispr)(mock|qwen)(mock|elevenlabs)
```

---

## Run locally (mock mode — works right now)

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
cp .env.example .env                                        # all providers = mock
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload
```

Check: `curl http://localhost:8000/health` → `{"providers":{"stt":"mock","vision":"mock","tts":"mock"}}`

**Frontend** (Node 20+):

```bash
cd frontend
cp .env.local.example .env.local        # NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
npm install
npm run dev
```

Open http://localhost:3000, allow camera + mic, hold **"Hold to Ask"**, release. You should see a
mock transcript + answer and hear a short tone (mock TTS). That proves the full round-trip.

> Camera/mic need a secure context. `localhost` is fine. To test from a phone, use HTTPS or an
> `ngrok`/`cloudflared` tunnel to both servers.

---

## Tomorrow: go live (key-swap checklist)

Bring each service online **one at a time** and re-test between each — easier to debug.

1. **Vision (Qwen)** — the core. In `backend/.env`:
   ```
   VISION_PROVIDER=qwen
   QWEN_API_KEY=<your DashScope key>
   QWEN_MODEL=qwen-vl-max
   ```
   Restart backend, verify `/health`, ask a question. See `app/services/vision_qwen.py`
   (`# TODO verify` notes: confirm intl vs. cn endpoint + model name).

2. **TTS (ElevenLabs)**:
   ```
   TTS_PROVIDER=elevenlabs
   ELEVENLABS_API_KEY=<key>
   ELEVENLABS_VOICE_ID=<voice id>   # optional
   ```
   See `app/services/tts_elevenlabs.py`.

3. **STT (Wispr / fallback)**:
   ```
   STT_PROVIDER=wispr
   WISPR_API_KEY=<key>
   ```
   ⚠️ Wispr Flow may not expose a usable public transcription API. If not, edit
   `app/services/stt_wispr.py` to call **OpenAI Whisper** instead
   (`POST https://api.openai.com/v1/audio/transcriptions`, `model=whisper-1`) — the orchestrator
   doesn't change.

Then: tune the Qwen prompt in `app/orchestrator.py` (`PROMPT_TEMPLATE`) and practice the demo.

### Adding a provider

Write `app/services/<svc>_<name>.py` implementing the protocol in `app/services/base.py`, then add one
branch in `app/services/factory.py`. That's it.

---

## Deploy (stretch, tomorrow if time)

- **Frontend** → Netlify/Vercel. Set `NEXT_PUBLIC_WS_URL` to the deployed backend's `wss://` URL.
- **Backend** → Render/Railway. Set env vars (providers + keys). Add the frontend origin to
  `ALLOWED_ORIGINS`.

---

## Layout

```
backend/app/
  main.py          FastAPI: /health + WebSocket /ws
  orchestrator.py  STT → Vision → TTS pipeline + prompt template
  config.py        env settings (*_PROVIDER flags, keys)
  services/
    base.py        STT/Vision/TTS protocols
    factory.py     picks impl from *_PROVIDER
    *_mock.py      canned responses (mock TTS emits a real WAV tone)
    stt_wispr.py / vision_qwen.py / tts_elevenlabs.py   live stubs (# TODO verify)
frontend/src/
  app/page.tsx        main demo UI
  components/Camera.tsx  getUserMedia + frame capture
  components/Mic.tsx     push-to-talk recorder
  lib/useSocket.ts       WS client + audio playback
```
