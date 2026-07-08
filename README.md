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

## Demo mode — present & record video without burning credits

Live API calls cost credits (ElevenLabs' free tier is ~10 min of audio total),
so **don't demo off the real APIs** — you can hit a limit mid-presentation. Instead
capture a few real responses once, then replay them for free. Set `DEMO_MODE` in
`backend/.env`:

| Mode | What it does |
| :--- | :--- |
| `off` | Normal live pipeline (default). |
| `capture` | Live pipeline **and** saves every response to `backend/recordings/`. |
| `replay` | Serves saved responses — **zero API calls**, instant, can't fail live. |

**Workflow:**

1. `DEMO_MODE=capture`, restart backend. Open the app and ask your scripted
   questions while pointing the camera at real things. Each turn is saved
   (`recordings/manifest.json` + `clip_NNN.mp3`). This spends a little credit — once.
2. `DEMO_MODE=replay`, restart backend. Now rehearse, present, and record the
   promo video as many times as you like — **free**. Replay matches the saved clip
   whose question best overlaps what you ask, so say a captured question and you get
   that exact real answer + audio back.
3. `/health` shows the active `demo_mode` so you can confirm you're safe before
   going on camera.

> Deploying the demo? Commit `backend/recordings/` and run the server with
> `DEMO_MODE=replay` so random clicks on your live link never drain credits.

---

## Navigation & walk mode (Phase 1)

VoxSight can give **spoken walking directions**, not just describe what's in front of
you. It reuses the same voice button — the companion decides the intent — plus your
device location.

**What you can say:**

| Say… | Intent | What happens |
| :--- | :--- | :--- |
| "Take me to the pharmacy on Dawson Street" | `navigate` | Geocodes the place, routes on foot, speaks the first step. |
| "Where am I?" | `where_am_i` | Reverse-geocodes your location and describes the surroundings. |
| "Stop navigation" | `stop_navigation` | Clears the active route. |

Turn-by-turn is **deterministic** — a routing engine produces the steps, not the AI —
so it costs no model calls per step. Once a route is active, the browser streams your
position (`watchPosition`) as lightweight `location` messages; the backend announces the
next maneuver only when you come within `NAV_ANNOUNCE_M` of it, and arrival within
`NAV_ARRIVE_M`. Tap **Enable navigation** in the app to opt in (this triggers the
browser's location prompt). Location is used transiently and is **not** persisted.

**Config** (`backend/.env`): `NAV_PROVIDER=mock` runs fully offline (canned route — good
for the demo/replay). For live directions:

```
NAV_PROVIDER=openrouteservice
OPENROUTESERVICE_API_KEY=<free key from openrouteservice.org>
```

> ⚠️ **Safety:** walk-mode directions are *advisory* and can be wrong or delayed. VoxSight
> complements a white cane or guide dog — it does not replace them, and a phone can't watch
> the road for you. This is stated in-app and worth repeating in any demo.

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
