"""E-Waste Value Appraiser - FastAPI backend + PWA host."""
import os
import io
import json
import time

from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from engine import knowledge as K, vision as V, appraisal as A, store as S
from engine.appraisal import IMPACT
from engine import overrides as OV

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

app = FastAPI(title="E-Waste Value Appraiser", version="1.0")
S.init()

MAX_BYTES = 8 * 1024 * 1024


# ------------------------------------------------------------------ helpers
def _read(upload: UploadFile) -> bytes:
    data = upload.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 8 MB)")
    if not data:
        raise HTTPException(400, "Empty upload")
    # reject non-images up front so a stray PDF/HEIC never reaches the engine
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
    except Exception:                                            # noqa: BLE001
        raise HTTPException(400, "That file is not a readable image (use JPEG or PNG).")
    return data


def _reverse_geocode(lat, lng):
    try:
        import requests
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 17},
            headers={"User-Agent": "EWASTE-Value-Appraiser/1.0 (hackathon demo)"},
            timeout=6)
        if r.ok:
            return r.json().get("display_name", "")[:160]
    except Exception:                                            # noqa: BLE001
        pass
    return f"{lat:.4f}, {lng:.4f}"


# --------------------------------------------------------------- catalogue
@app.get("/api/health")
def health():
    return dict(ok=True, ai=V.AI_PROVIDER or "heuristic",
                model=V.current_model() if V.AI_PROVIDER else "",
                key_loaded=bool(V.AI_KEY),
                price_date=K.PRICE_DATE,
                devices=len(K.DEVICES), items=len(K.ITEMS))


@app.get("/api/catalog")
def catalog():
    return dict(items=K.catalog(), costs=K.DEFAULT_COSTS, price_date=K.PRICE_DATE)


@app.get("/api/prices")
def prices():
    return dict(price_date=K.PRICE_DATE, costs=K.DEFAULT_COSTS,
                metals={k: dict(name=v["name"], symbol=v["symbol"],
                                price_inr_per_kg=v["price_inr_per_kg"],
                                recovery=v["recovery"], precious=v["precious"],
                                source=v["source"])
                        for k, v in K.METALS.items()})


# ----------------------------------------------------------------- analyse
@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), record: int = 1):
    data = _read(file)
    t0 = time.time()
    try:
        result = V.analyze(data)
    except HTTPException:
        raise
    except Exception as exc:                                      # noqa: BLE001
        raise HTTPException(400, f"Could not analyse that image: {exc}")

    # auto-appraise the top guess so the result sheet is populated immediately
    cands = result["candidates"]
    if cands:
        top = cands[0]
        item = K.get(top["key"])
        # dispatch on the table the key lives in, not on `kind`: copper cable is
        # general waste but is valued through the mineral-recovery engine
        if top["key"] in K.DEVICES:
            ap = A.electronic_appraisal(top["key"], quantity=1)
        else:
            ap = A.waste_appraisal(top["key"], item["avg_weight_g"])
        # carry the model's own wording onto the first price screen, otherwise
        # the heading shows the generic catalogue name instead of what it saw
        ai_name = (top.get("display") or "").strip()
        if ai_name:
            ap["display_label"] = ai_name[:80]
        result["appraisal"] = ap
        result["guess"] = dict(key=top["key"], label=item["label"], score=top["score"],
                               why=top["why"], kind=item["kind"])
        if record:
            S.add_scan(top["key"], ap.get("display_label") or ap["label"], ap["is_electronic"],
                       result["verdict"]["confidence"], result["verdict"].get("engine"),
                       ap["total_kg"] * 1000, ap.get("gross", 0), ap.get("net", 0),
                       ap["kind"], ap.get("co2_saved_kg", 0.0), ap.get("quantity", 1.0))
    result["elapsed_ms"] = int((time.time() - t0) * 1000)
    return JSONResponse(result)


@app.post("/api/appraise")
async def appraise(payload: dict):
    key = payload.get("key")
    if key not in K.DEVICES and key not in K.ITEMS:
        raise HTTPException(404, f"Unknown item '{key}'")
    ap = A.appraise(key,
                    weight_g=payload.get("weight_g"),
                    quantity=payload.get("quantity", 1),
                    costs=payload.get("costs"),
                    prices=payload.get("prices"),
                    rate=payload.get("rate"))
    # let the caller keep the model's own wording on screen (e.g. "Banana peel")
    # even when the maths runs off a generic profile
    if payload.get("ai_label"):
        ap["display_label"] = str(payload["ai_label"])[:80]
    if payload.get("record"):
        S.add_scan(key, ap["label"], ap["is_electronic"],
                   payload.get("confidence", 0.0), payload.get("engine", "manual"),
                   ap["total_kg"] * 1000, ap.get("gross", 0), ap.get("net", 0),
                   ap["kind"], ap.get("co2_saved_kg", 0.0), ap.get("quantity", 1.0))
    return JSONResponse(ap)


@app.get("/api/history")
def history(limit: int = 30):
    return dict(history=S.history(limit))


# ---------------------------------------------------------------- settings
@app.get("/api/settings")
def get_settings():
    """Everything numeric, with its current effective value."""
    ov = OV.all_overrides()
    # report EFFECTIVE values (defaults already layered with saved overrides) so
    # the settings screen shows what the engine will actually use
    return dict(
        overrides=ov,
        costs=OV.costs(dict(K.DEFAULT_COSTS)),
        processing={k: OV.processing(k, K.PROCESSING.get(k, K.DEFAULT_PROCESSING))
                    for k in K.DEVICES},
        default_processing=K.DEFAULT_PROCESSING,
        metals={k: dict(name=v["name"], symbol=v["symbol"],
                        price=OV.metal_price(k, v["price_inr_per_kg"]),
                        recovery=OV.metal_recovery(k, v["recovery"]),
                        precious=v["precious"],
                        impact=OV.impact(k, IMPACT.get(k, 0.0)),
                        unit=("Rs/g" if v["precious"] else "Rs/kg"))
                for k, v in K.METALS.items()},
        devices={k: dict(label=v["label"],
                         weight_g=OV.device_weight(k, v["avg_weight_g"]),
                         yields=OV.device_yields(k, dict(v["yields"])),
                         is_electronic=v.get("is_electronic", True))
                 for k, v in K.DEVICES.items()},
        items={k: dict(label=v["label"],
                       weight_g=OV.item_weight(k, v["avg_weight_g"]),
                       rate=OV.item_rate(k, v["rate_inr_per_kg"]), bin=v["bin"])
               for k, v in K.ITEMS.items()},
        price_date=K.PRICE_DATE)


@app.post("/api/settings")
async def save_settings(payload: dict):
    return dict(ok=True, overrides=OV.save(payload))


@app.post("/api/settings/reset")
def reset_settings():
    return dict(ok=True, overrides=OV.reset())


# ----------------------------------------------------------------- history
@app.delete("/api/history")
def delete_history():
    return dict(ok=True, removed=S.clear_history())


@app.get("/api/stats")
def stats():
    return S.stats()


# --------------------------------------------------------------------- map
@app.get("/api/map")
def map_data(lat: float = 13.0827, lng: float = 80.2707, radius: float = 30):
    return dict(reports=S.reports(), listings=S.listings(),
                recyclers=S.nearby(lat, lng, radius))


@app.post("/api/report")
async def report(payload: dict):
    try:
        lat = float(payload["lat"]); lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "lat/lng required")
    rid = S.add_report(lat, lng, _reverse_geocode(lat, lng),
                       payload.get("category", "e-waste"), payload.get("note", ""),
                       payload.get("severity", "medium"))
    return dict(id=rid, ok=True)


@app.post("/api/report/{rid}/upvote")
def upvote(rid: int):
    S.upvote_report(rid)
    return dict(ok=True)


@app.post("/api/listing")
async def listing(payload: dict):
    try:
        lat = float(payload["lat"]); lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "lat/lng required")
    key = payload.get("item_key", "smartphone")
    item = K.get(key) or K.get("smartphone")
    qty = float(payload.get("qty", 1))
    ap = A.appraise(key, quantity=qty)
    fair = ap.get("net") or ap.get("gross", 0)
    asking = payload.get("asking")
    lid = S.add_listing(lat, lng, _reverse_geocode(lat, lng), key, item["label"],
                        qty, float(asking) if asking else fair,
                        payload.get("note", ""))
    return dict(id=lid, ok=True, suggested_price=round(fair, 2))


# ------------------------------------------------------------------- tiles
# OpenStreetMap serves a REAL tile to browser User-Agents but a 103-byte blank
# 1-bit placeholder to anything else. Fetching tiles server-side with a browser
# UA and caching them means the browser never depends on that policy, and the
# map renders over a plain same-origin URL.
TILE_CACHE = os.path.join(BASE, "tilecache")
os.makedirs(TILE_CACHE, exist_ok=True)
TILE_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TILE_MAX_FILES = 4000
TILE_SUBDOMAINS = ("a", "b", "c")
# OpenTopoMap serves real tiles to this host; plain OSM hands back a uniform
# placeholder. OSM is kept as a fallback if OpenTopoMap is ever unavailable.
TILE_PROVIDERS = (
    "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)
_BLANK = {}


def _is_real_tile(data):
    """True when the bytes are map imagery, not a provider stub/placeholder."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        try:
            px = im.get_flattened_data()
        except AttributeError:                    # older Pillow
            px = list(im.getdata())
        return len(set(px)) >= 60
    except Exception:                                            # noqa: BLE001
        return False


def _empty_tile():
    """Transparent 256x256 for genuinely empty areas (open water)."""
    if "empty" not in _BLANK:
        import io as _io
        from PIL import Image as _Image
        im = _Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        buf = _io.BytesIO()
        im.save(buf, "PNG")
        _BLANK["empty"] = buf.getvalue()
    return _BLANK["empty"]


def _blank_tile():
    """Dark 256x256 placeholder so a failed tile looks intentional, not broken."""
    if "png" not in _BLANK:
        import io as _io
        from PIL import Image as _Image
        im = _Image.new("RGB", (256, 256), (14, 21, 18))
        buf = _io.BytesIO()
        im.save(buf, "PNG")
        _BLANK["png"] = buf.getvalue()
    return _BLANK["png"]


@app.get("/tiles/{z}/{x}/{y}.png")
def tiles(z: int, x: int, y: int):
    if not (0 <= z <= 19):
        raise HTTPException(400, "bad zoom")
    n = 1 << z
    if not (0 <= x < n and 0 <= y < n):
        raise HTTPException(400, "bad tile coordinate")
    fp = os.path.join(TILE_CACHE, f"{z}_{x}_{y}.png")
    if os.path.isfile(fp):
        return FileResponse(fp, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
    sub = TILE_SUBDOMAINS[(z + x + y) % len(TILE_SUBDOMAINS)]
    for tpl in TILE_PROVIDERS:
        try:
            import requests
            r = requests.get(
                tpl.format(s=sub, z=z, x=x, y=y),
                headers={"User-Agent": TILE_UA,
                         "Referer": "https://www.openstreetmap.org/"},
                timeout=10)
            if r.status_code != 200:
                continue
            data = r.content
            # Tile servers hand datacenter IPs a uniform placeholder. Real map
            # imagery has 250+ distinct colours; the OSM stub has 23.
            if not _is_real_tile(data):
                # genuinely empty tile (open water) - transparent so the grid
                # underneath shows through instead of a jarring grey square
                if len(data) < 1500:
                    return Response(_empty_tile(), media_type="image/png",
                                    headers={"Cache-Control": "public, max-age=604800"})
                continue                      # a stub - try the next provider
            try:
                if len(os.listdir(TILE_CACHE)) < TILE_MAX_FILES:
                    with open(fp, "wb") as fh:
                        fh.write(data)
            except OSError:
                pass
            return Response(data, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
        except Exception:                                        # noqa: BLE001
            continue
    return Response(_empty_tile(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------------ static
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(STATIC, "manifest.json"),
                        media_type="application/manifest+json")
