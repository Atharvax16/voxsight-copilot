# VoxSight

Real-time accessibility co-pilot for visually impaired users. Point a camera, hold a button, ask a
question by voice → get a spoken answer describing your surroundings, reading text aloud, finding
an object, or giving you walking directions.

Pipeline: **audio + camera frame → STT → Vision/companion brain → TTS → audio back**, over WebSocket.

Original concept doc: [`voxsight_technical_blueprint.md`](./voxsight_technical_blueprint.md) (the
initial hackathon plan — the architecture has since grown past it; treat it as historical context,
not the current spec).

---

## Status: active development

The core pipeline is real and working end-to-end, with live providers available for every stage
(not just mocks). It's still a single-user prototype: no auth, no deployment, no persistence beyond
a local JSON file. See [Roadmap](#roadmap--known-gaps) for what's solid vs. still in progress.

```
Browser (Next.js)            FastAPI backend
 camera ─ frame ─┐
 mic ─ audio ────┼─ WS /ws ─► Orchestrator ─► STT ─► Companion/Vision ─► TTS ─► audio back
 location ───────┤                          (mock|elevenlabs|wispr)  │      (mock|elevenlabs)
 audio playback ◄┘                                                    ├─► Memory (facts/reminders)
                                                                       └─► Navigation (route/geocode)
```

Every service is swappable behind an env flag (`*_PROVIDER`); mock providers make the whole app
runnable offline with zero API keys.

---

## What it can do

One vision call doubles as the "companion brain" — it decides intent from the spoken request and
image, then replies with speech plus any side effects. Recognized intents:

| Say… | Intent | What happens |
| :--- | :--- | :--- |
| "What's in front of me?" | `describe` | Describes the scene. |
| "Read this to me" | `read` | Reads visible text (mail, labels, menus, signs). |
| "Find my keys" | `find` | Locates an object in view and says where it is. |
| "Remember I'm allergic to peanuts" | `remember` | Persists a fact for future turns. |
| "What am I allergic to?" | `recall` | Answers from remembered facts. |
| "Take me to the pharmacy on Dawson Street" | `navigate` | Geocodes, routes on foot, speaks the first step. |
| "Where am I?" | `where_am_i` | Reverse-geocodes location and describes surroundings. |
| "Stop navigation" | `stop_navigation` | Clears the active route. |
| "Remind me to..." / "What are my reminders?" | `remind` / `list_reminders` | Recognized, not yet applied — see [Roadmap](#roadmap--known-gaps). |

Turn-by-turn navigation is **deterministic** once a route starts — a routing engine produces the
steps, not the AI, so it costs no model calls per step. The browser streams position
(`watchPosition`) as the user walks; the backend announces the next maneuver only when they come
within `NAV_ANNOUNCE_M` of it, and arrival within `NAV_ARRIVE_M`. Location is opt-in (tap **Enable
navigation**) and used transiently — it is **not** persisted.

> ⚠️ **Safety:** walk-mode directions are *advisory* and can be wrong or delayed. VoxSight
> complements a white cane or guide dog — it does not replace them, and a phone can't watch
> the road for you. This is stated in-app and worth repeating in any demo.

---

## Run locally

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

**Backend tests** (offline, zero API cost, mock providers only):

```bash
cd backend
.venv/Scripts/python -m pytest
```

---

## Demo mode — record or present without burning API credits

Live API calls cost credits, so don't rehearse or demo off the real APIs — you can hit a rate
limit mid-presentation. Instead, capture a few real responses once, then replay them for free. Set
`DEMO_MODE` in `backend/.env`:

| Mode | What it does |
| :--- | :--- |
| `off` | Normal live pipeline (default). |
| `capture` | Live pipeline **and** saves every response to `backend/recordings/`. |
| `replay` | Serves saved responses — **zero API calls**, instant, can't fail live. |

**Workflow:**

1. `DEMO_MODE=capture`, restart backend. Open the app and ask your scripted
   questions while pointing the camera at real things. Each turn is saved
   (`recordings/manifest.json` + `clip_NNN.mp3`). This spends a little credit — once.
2. `DEMO_MODE=replay`, restart backend. Now rehearse, present, and record
   video as many times as you like — **free**. Replay matches the saved clip
   whose question best overlaps what you ask, so say a captured question and you get
   that exact real answer + audio back.
3. `/health` shows the active `demo_mode` so you can confirm you're safe before
   going on camera.

> If you ever deploy this somewhere public, commit `backend/recordings/` and run with
> `DEMO_MODE=replay` so random visitors never drain your API credits.

---

## Configuration (`backend/.env`)

Bring each service online independently and re-test after each change — easier to debug.

**Vision** (the core — describes, reads, finds, and decides intent):

```
VISION_PROVIDER=gemini        # or: fal, qwen, mock
GEMINI_API_KEY=<key>          # gemini_model defaults to gemini-2.5-flash
```
`fal` proxies a VLM (default Gemini 2.5 Flash Lite) through fal.ai; `qwen` uses DashScope's
`qwen-vl-max`. See `app/services/vision_*.py`.

**TTS:**

```
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=<key>
ELEVENLABS_VOICE_ID=<voice id>   # optional
```

**STT:**

```
STT_PROVIDER=elevenlabs       # Scribe model; or: wispr
ELEVENLABS_API_KEY=<key>
```
The frontend can also transcribe in-browser via the Web Speech API (`NEXT_PUBLIC_STT_MODE=browser`,
the default) and skip backend STT entirely.

**Navigation:**

```
NAV_PROVIDER=openrouteservice
OPENROUTESERVICE_API_KEY=<free key from openrouteservice.org>
```
`mock` (default) runs fully offline with a canned route — good for tests/demo/replay.

Then tune the companion prompt in `app/companion.py` (`build_prompt`) as needed.

### Adding a provider

Write `app/services/<svc>_<name>.py` implementing the protocol in `app/services/base.py`, then add one
branch in `app/services/factory.py`. That's it.

---

## Roadmap / known gaps

- **Reminders** — `remind` / `list_reminders` intents are recognized and the data model exists in
  `memory_store.py`, but the orchestrator doesn't act on them yet (see the `# Reminders are applied
  in Phase 3` note in `orchestrator.py`).
- **Deployment** — no Dockerfile, CI, or hosting config yet. Suggested path when ready: frontend to
  Netlify/Vercel (`NEXT_PUBLIC_WS_URL` → deployed backend's `wss://` URL), backend to
  Render/Railway (env vars for providers/keys, plus the frontend origin in `ALLOWED_ORIGINS`).
- **Persistence** — memory is a single-user local JSON file (`backend/memory_store.json`); no
  multi-user accounts or database yet.
- **Wispr STT** — `app/services/stt_wispr.py` is unverified against a real Wispr Flow endpoint;
  ElevenLabs Scribe (`STT_PROVIDER=elevenlabs`) is the tested live path.

---

## Layout

```
backend/app/
  main.py          FastAPI: /health + WebSocket /ws
  orchestrator.py  STT → Companion/Vision → TTS pipeline, navigation side effects
  companion.py     Intent routing: builds the prompt, parses model reply into intent + side effects
  memory_store.py  Persistent facts/reminders (JSON), injected into every companion prompt
  nav_state.py     Per-connection route state; pure geometry decides when to announce/arrive
  demo.py          Capture/replay recording store for demo mode
  config.py        env settings (*_PROVIDER flags, keys, nav/demo tuning)
  services/
    base.py        STT/Vision/TTS/Navigation protocols
    factory.py     picks impl from *_PROVIDER
    *_mock.py       canned responses (mock TTS emits a real WAV tone)
    stt_elevenlabs.py / stt_wispr.py
    vision_gemini.py / vision_fal.py / vision_qwen.py
    tts_elevenlabs.py
    navigation.py   OpenRouteService + mock navigation, haversine helpers
frontend/src/
  app/page.tsx           main UI: camera, status, navigation panel, transcript/answer, mic
  components/Camera.tsx  getUserMedia + frame capture
  components/Mic.tsx     push-to-talk recorder (browser or backend STT)
  lib/useSocket.ts       WS client + audio playback + navStep state
  lib/useGeolocation.ts  opt-in location sharing for navigation
```
