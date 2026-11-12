# E-Waste Value Appraiser

Mobile-first PWA that snaps a photo of any waste item, decides whether it is
**electronic waste or other waste**, then shows what it is made of, what the
recoverable minerals are worth, and where to take it.

## Run it

```bash
pip install fastapi "uvicorn[standard]" python-multipart pillow numpy
cd ewaste_app
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Open the port in a browser. Camera capture needs HTTPS or localhost — the
sandbox preview URL is already HTTPS, so the camera works there.

## What it does

1. **Scan** — camera or file upload.
2. **Classify** — the engine decides *electronic vs other waste first*, then
   identifies the specific item. If it is unsure you get a ranked candidate
   list plus a full catalogue picker to correct it.
3. **Appraise** — components are reduced to base minerals, priced against
   market rates, and recovery costs are subtracted to give profit per unit,
   per kg and per tonne.
4. **Route** — wet / dry / recyclable / hazardous bin advice, with hazard
   warnings for batteries, CRTs, CFLs and paint.
5. **Map** — nearby recyclers, community dumping reports, and listings for
   e-waste you want to sell.

## Layout

```
ewaste_app/
  server.py          FastAPI app, REST API, static host
  engine/
    knowledge.py     metals + prices, device profiles, waste catalogue, cost model
    vision.py        feature extraction -> heuristic classifier -> verdict
    appraisal.py     deterministic valuation maths
    store.py         SQLite: scans, reports, listings, recyclers
  static/
    index.html       single-page shell (5 screens)
    styles.css       dark mobile UI
    app.js           camera, API calls, rendering
    sw.js            offline service worker
    manifest.json    installable PWA
    vendor/          Leaflet js/css (vendored - no CDN needed)
```

## Two classification engines

**Heuristic (default, no API key, works offline).** Pulls colour-band and
texture features from the image (PCB green, copper, gold contacts, leaf green,
fruit yellow, cardboard brown, edge density, saturation, aspect) and scores
them against the catalogue. Fast (~10 ms) and fully offline.

**Vision AI (optional).** Set two environment variables to switch the whole
app over to a real vision model; valuation stays deterministic.

```bash
export AI_PROVIDER=gemini   # or openai
export AI_API_KEY=...
```

Both paths return the same JSON shape, so nothing else changes. If the AI call
fails the app silently falls back to the heuristic engine.

## Honest numbers

- Metal prices captured **2026-11-07** from published Indian market rates.
- Yields are published PCB / device assay ranges; recovery % is per metal.
- Processing cost is charged **per recovery route**, not a flat rate — refining
  a PCB costs far more per kg than shredding a steel appliance.
- Values are **estimates, not a payout guarantee**. Real aggregators typically
  realise 60–70% of gross metal value. The app says so on every result screen.
- Some streams are genuinely negative: CRT glass and TV remotes cost more to
  process than the material returns. Those show as "Net cost to recycle".
