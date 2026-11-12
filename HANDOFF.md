# Handoff Brief — E-Waste Value Appraiser

**Paste this into a new chat that has the GitHub connector enabled.**
Everything referenced lives in the repo, so the agent can read the code directly.
Last updated: 2026-11-12.

---

## 1. What this is

A mobile web app (PWA) that photographs an item of e-waste or rubbish, identifies
it with Gemini vision, and tells the user what it is worth in recovered minerals
— gold, copper, aluminium, lithium and so on — plus the CO2 avoided by recycling
rather than mining virgin metal.

Built for a user in **Chennai, Tamil Nadu, India**. Currency is INR (Rs).

Stack: **FastAPI (Python) + vanilla JS. No framework, no build step.**
The frontend is deliberately plain JS so the app stays a single small repo with
no npm toolchain.

## 2. How to run it

```bash
pip install -r requirements.txt
AI_PROVIDER=gemini python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 \
  --app-dir <repo>
```

The Gemini key is read from the `AI_API_KEY` env var, falling back to a `.aikey`
file in the repo root. **Without a key the app still runs** — it degrades to an
offline colour/texture heuristic and shows an "AI unavailable" notice. This was
verified.

## 3. File map

| File | What it does |
|---|---|
| `server.py` | FastAPI routes. `/api/analyze`, `/api/appraise`, `/api/settings`, `/api/catalog`, `/api/stats`, `/api/map`, `/api/history`, `/api/health` |
| `engine/knowledge.py` | The catalogue: 14 devices, 21 waste items, 13 metals, processing costs. Plus two hidden generic fallback profiles |
| `engine/vision.py` | Offline heuristic classifier + Gemini vision hook, model fallback ladder, fuzzy catalogue matcher |
| `engine/appraisal.py` | Value maths: mineral yields → recovery → gross → processing cost → net. CO2 avoided |
| `engine/overrides.py` | JSON user overrides with deep merge, so every number is editable |
| `engine/store.py` | SQLite: scan history, stats |
| `static/index.html` | Single-page shell, four screens |
| `static/app.js` | All UI logic, camera, rendering, settings editor |
| `static/styles.css` | Dark green theme |
| `static/sw.js` | Service worker — **network-first** for app code (see gotchas) |
| `Procfile` / `render.yaml` / `requirements.txt` / `runtime.txt` | Deployment, ready to go |
| `DEPLOY.md` | Deployment walkthrough |
| `check_link.sh` | Health-checks the public URL; `--refish` rebuilds the tunnel |
| `watchdog.sh` | Self-healing loop, rebuilds the tunnel when it drops |

## 4. Standing requirements from the user

These were stated explicitly and are not negotiable:

1. **Actual weight must drive the appraisal**, never the catalogue default.
   (Complaint: *"my lap is 1000g it showing 2200g"*.)
2. **Every numeric value must be user-editable** — costs, processing, metal
   prices, recovery rates, yields, weights, CO2 factors. 178 values are
   editable through the Settings screen.
3. **No seeded or demo statistics.** Stats must derive from real scans only.
4. **CO2 must be explained in plain language**, not shown as a bare number.
5. **Scans must be accurate.** (*"the scans r not right"*.)
6. **It must open on the user's phone**, over the real internet, camera working.
7. **The AI's identification must always be a selectable option**, even when it
   matches nothing in the catalogue.

## 5. Current state

- **Working.** All seven requirements above are met and verified.
- Accuracy verified on real photographs: banana peel → `fruit_peel`, RAM sticks
  → `ram`, smartphone → `smartphone`.
- Gemini live via `gemini-flash-lite-latest`.
- Deployment files written and tested to boot with `PORT` set and no API key.
- Git repo initialised and committed; 24 files tracked; `.aikey` confirmed
  untracked.

## 6. Gotchas — read before changing anything

- **The sandbox kills background processes.** Any long-lived server can vanish
  between messages. Always probe (`curl /api/health`) before assuming uptime.
- **Snapshot restores reset file modes.** `.aikey` must be 600; `cloudflared`
  and the shell scripts need `+x`. Re-chmod at the start of a session.
- **Cloudflare quick tunnels return 530 permanently** once a host has restarted
  them repeatedly. Do not keep retrying — switch provider. `localhost.run`
  (SSH, no account) currently works; cloudflared is the fallback.
- **Every tunnel provider rotates hostnames.** A permanent URL requires a real
  deployment. This is the single biggest outstanding item.
- **Gemini model names retire.** `gemini-2.0-flash` and `gemini-2.5-flash` are
  404. `gemini-flash-latest` hangs. `gemini-3.7/3.8-flash` return 503. The
  working ladder is in `GEMINI_MODELS` in `engine/vision.py`.
- **Gemini intermittently 503s.** A scan then silently falls back to the
  heuristic, which produces visibly wrong answers (a banana was identified as
  "newspaper"). There is currently **no retry** — see roadmap item 1.
- **The service worker used to be cache-first** and pinned stale JS on the
  phone, so fixes never reached the user. It is now network-first for app code.
  Do not make it cache-first again.
- **Do not force the vision model to choose a catalogue key.** A forced-choice
  prompt fabricates the nearest wrong thing (a banana became "Brass fitting").
  The key is nullable and fuzzy-matched afterwards instead.
- `copper_wire` is in `DEVICES`, not `ITEMS`. `cfl_bulb` is invalid — use
  `cfl_tubelight`. `hdpe_bottle` → `recyclable` is correct behaviour.

## 7. What could be done next — prioritised

**1. Retry Gemini on transient failure (small, high value).**
`engine/vision.py` has no retry. A 503 silently degrades to the offline
heuristic, which is much worse than a short delay. Add 2–3 retries with
backoff, and only then fall back. This is the most cost-effective fix left.

**2. Finish the deployment (the actual fix for the link problem).**
Repo is ready. Needs: create empty GitHub repo, push, point Render at it. Then
the URL stops changing. Everything else is downstream of this.

**3. Automatic weight estimation from the photo.**
The user must currently type a weight, which is the most friction in the flow.
Ask the model for an estimated mass and pre-fill it, clearly marked as an
estimate the user can correct.

**4. Condition grading.** Working / damaged / crushed currently makes no
difference to value. A simple multiplier would materially improve accuracy.

**5. Localisation.** User is in Tamil Nadu. Tamil labels, and recycler data for
Chennai rather than generic placeholders.

**6. Batch mode.** Scan several items in one session and get a running total —
matches how people actually clear out e-waste.

**7. Export.** PDF or CSV of an appraisal, for quoting to a dealer.

**8. Persistent storage on deploy.** SQLite on a free-tier ephemeral disk means
scan history resets on every redeploy. Move to Postgres (Render offers a free
Postgres) or accept the loss.

**9. Tests.** There is no test suite. Verification has been ad-hoc scripts.
The valuation maths and the fuzzy matcher especially deserve proper tests.

**10. Rate limiting and upload caps.** Nothing stops a user hammering the
Gemini endpoint. Given the key is billable, this matters before any public use.

**11. Catalogue expansion** — more devices, and regional scrap rates.

**12. Better recycler data.** Currently 8 static placeholders in the map.

## 8. Security

- The Gemini key has been **pasted into chat multiple times** and must be
  treated as compromised. Rotate it before any production use.
- It is stored only in `.aikey` (chmod 600) and in the `AI_API_KEY` env var.
  Never in the repo, never in the frontend.
- `.gitignore` covers `.aikey`, `.env`, `data.db`. Verified untracked.

## 9. Suggested opening instruction for the new chat

> Read this repo. It is a FastAPI + vanilla-JS PWA that identifies e-waste from a
> photo and values the recoverable minerals. Start with `HANDOFF.md` section 6
> (gotchas) before changing anything. My first priority is item 1 in section 7:
> add retry-with-backoff to the Gemini call in `engine/vision.py` so transient
> 503s stop silently degrading scans to the offline heuristic.
