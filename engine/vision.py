"""Image analysis and classification.

Two modes:
  * heuristic  - feature extraction from the pixels (works with no API key)
  * ai         - Gemini / OpenAI vision when an API key is configured

Both return the same shape so the app behaves identically.
"""
import io
import os
import json
import base64

import numpy as np
from PIL import Image

from . import knowledge as K

AI_PROVIDER = os.environ.get("AI_PROVIDER", "").lower()   # "gemini" | "openai"
AI_KEY = os.environ.get("AI_API_KEY", "")
# Prefer a file over an env var so the secret never shows up in `ps` output.
_KEY_FILE = os.environ.get("AI_API_KEY_FILE",
                           os.path.join(os.path.dirname(os.path.dirname(
                               os.path.abspath(__file__))), ".aikey"))
if not AI_KEY:
    try:
        with open(_KEY_FILE) as _fh:
            AI_KEY = _fh.read().strip()
    except OSError:
        pass

# Models get retired (gemini-2.0-flash is gone as of 2026). Try an alias that
# tracks the current release first, then concrete fallbacks, then allow override.
# Ordered by measured latency on a real image request (2026-11):
#   gemini-flash-lite-latest  0.9s  correct
#   gemini-3.5-flash-lite     1.2s  correct
#   gemini-3.5-flash          2.8s  correct
#   gemini-3.6-flash          3.2s  correct
# Retired / unreliable, kept out of the chain on purpose:
#   gemini-2.0-flash, gemini-2.5-flash  -> 404 no longer available
#   gemini-3.7-flash, gemini-3.8-flash  -> 503 high demand
#   gemini-flash-latest                 -> hangs (>90s)
GEMINI_MODELS = [
    m for m in [os.environ.get("GEMINI_MODEL", ""),
                "gemini-flash-lite-latest", "gemini-3.5-flash-lite",
                "gemini-3.5-flash", "gemini-3.6-flash"] if m
]
_working_model = None


def current_model():
    """Which model the AI path actually settled on (empty until one succeeds)."""
    return _working_model or (GEMINI_MODELS[0] if GEMINI_MODELS else "")


# ------------------------------------------------------------ feature math
def _hsv_stats(img):
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32)
    h = hsv[..., 0] * 360.0 / 255.0
    s = hsv[..., 1] / 255.0
    v = hsv[..., 2] / 255.0
    return h, s, v


def _mask_frac(mask):
    return float(mask.mean()) if mask.size else 0.0


def _edge_density(gray):
    gx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0.0
    gy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0.0
    return float((gx + gy) / 2.0 / 255.0)


def extract_features(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((320, 320))
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    h, s, v = _hsv_stats(img)

    def band(lo, hi, smin=0.0, smax=1.0, vmin=0.0, vmax=1.0):
        m = (h >= lo) & (h <= hi) & (s >= smin) & (s <= smax) & (v >= vmin) & (v <= vmax)
        return float(m.mean())

    f = dict(
        width=img.width, height=img.height,
        brightness=float(gray.mean()),
        contrast=float(gray.std()),
        saturation=float(s.mean()),
        edge=_edge_density(gray),
        # bands tuned against measured samples:
        #   PCB solder mask  hue 141, sat .78, val .35
        #   leaf green       hue 113, sat .62, val .51
        #   copper           hue  25, sat .84, val .72
        #   cardboard        hue  31, sat .60, val .69
        pcb_green=band(128, 178, 0.40, 1.0, 0.10, 0.62),
        copper=band(4, 36, 0.68, 1.0, 0.25, 1.0),
        gold_tan=band(36, 62, 0.30, 1.0, 0.25, 0.95),
        metal_gray=float(((s < 0.16) & (v > 0.22) & (v < 0.88)).mean()),
        white_pale=float(((v > 0.86) & (s < 0.14)).mean()),
        brown_organic=band(12, 52, 0.18, 0.68, 0.18, 0.88),
        yellow_fruit=band(45, 70, 0.35, 1.0, 0.45, 1.0),
        green_plant=band(58, 128, 0.22, 1.0, 0.12, 0.95),
        blue_cool=band(180, 250, 0.15, 1.0, 0.20, 1.0),
        dark=float((v < 0.25).mean()),
    )
    f["aspect"] = round(img.width / max(img.height, 1), 3)
    return f


# ------------------------------------------------------------- heuristic
def classify_heuristic(features):
    """Return ordered candidate list. Each: key, kind, is_electronic, score, why."""
    c = []

    def add(key, kind, is_el, score, why):
        if score > 0.02:
            c.append(dict(key=key, kind=kind, is_electronic=is_el,
                          score=round(min(score, 0.97), 3), why=why))

    f = features
    pcb, gray, edge = f["pcb_green"], f["metal_gray"], f["edge"]
    cu, tan = f["copper"], f["gold_tan"]
    brown, yel, plant = f["brown_organic"], f["yellow_fruit"], f["green_plant"]
    pale, dark, bright = f["white_pale"], f["dark"], f["brightness"]
    blue, sat, aspect = f["blue_cool"], f["saturation"], f["aspect"]
    detail = f["contrast"]          # robust proxy: 0.03 flat, 0.11 dense PCB

    # ---- electronic signals -------------------------------------------
    # calibrated on measured samples (see extract_features band comments)
    if pcb > 0.10:
        add("motherboard", "e-waste", True, 0.60 + pcb * 0.9 + detail * 1.5,
            f"Circuit-board green over {pcb*100:.0f}% of the frame with dense surface detail")
    elif pcb > 0.03:
        add("motherboard", "e-waste", True, 0.40 + pcb * 3.0,
            f"Some circuit-board green detected ({pcb*100:.0f}%)")

    if pcb > 0.05 and aspect < 0.70:
        add("ram", "e-waste", True, 0.34 + pcb * 1.8,
            "Narrow green board - consistent with a memory module")

    # dark body + glowing panel = screen device; aspect separates the two
    if dark > 0.35 and blue > 0.12:
        if aspect < 0.85:
            add("smartphone", "e-waste", True, 0.48 + dark * 0.5 + blue * 0.6,
                "Dark portrait slab with a lit display - a phone")
        else:
            add("laptop", "e-waste", True, 0.46 + dark * 0.5 + blue * 0.5,
                "Dark body with a wide lit display panel")
    elif dark > 0.30 and gray > 0.15:
        add("appliance", "e-waste", True, 0.30 + gray * 0.9 + dark * 0.4,
            "Large dark metallic body")

    # Dark + desaturated is ambiguous between a powered-off device and insulated
    # cable. Bias toward e-waste: misrouting a phone to general waste is worse
    # than the reverse, and the user can always correct from the candidate list.
    if dark > 0.55 and sat < 0.30 and blue < 0.12:
        if aspect >= 1.0:
            add("laptop", "e-waste", True, 0.38 + dark * 0.15,
                "Dark uniform body with no lit panel - a powered-off device")
        else:
            add("smartphone", "e-waste", True, 0.38 + dark * 0.15,
                "Dark portrait slab, screen off")
    # cable only when the form is genuinely elongated - a coil has no colour signal
    if dark > 0.72 and sat < 0.20 and blue < 0.10 and aspect >= 1.5:
        add("copper_wire", "waste", False, 0.34 + dark * 0.3,
            "Long dark insulated form - cable or wire")

    if cu > 0.20:
        add("copper_wire", "waste", False, 0.46 + cu * 1.2,
            f"Strong copper tone ({cu*100:.0f}% of pixels)")
    if tan > 0.15 and detail > 0.05:
        add("cpu", "e-waste", True, 0.34 + tan * 1.4,
            "Gold-plated contacts and chip package tones")
    if tan > 0.12 and cu > 0.08:
        add("brass", "waste", False, 0.30 + tan * 1.2, "Brass / copper alloy colour")

    if gray > 0.25 and bright > 0.45 and detail < 0.10:
        add("alu_can", "waste", False, 0.34 + gray * 0.9,
            "Smooth bright metal - aluminium or steel")

    # ---- non-electronic signals ---------------------------------------
    if yel > 0.22 and sat > 0.35:
        add("fruit_peel", "waste", False, 0.45 + yel * 1.1,
            "Dominant fruit-yellow tone, little structural detail")
    if plant > 0.25 and plant > pcb * 2:
        add("garden_waste", "waste", False, 0.44 + plant * 1.0,
            "Leaf-green plant matter")
    # cardboard is lighter (brightness ~.52) than cooked food (~.37) at similar hue
    if brown > 0.30 and sat < 0.68 and bright > 0.42:
        add("cardboard", "waste", False, 0.44 + brown * 0.8,
            "Brown fibrous surface - cardboard or paper")
    if brown > 0.25 and bright <= 0.45 and plant < 0.10:
        add("food_scraps", "waste", False, 0.30 + brown * 0.5, "Mixed organic tones")
    if pale > 0.40 and sat < 0.25:
        add("newspaper", "waste", False, 0.34 + pale * 0.6, "Light, low-saturation sheet")
    if pale > 0.55 and bright > 0.80:
        add("thermocol", "waste", False, 0.30 + pale * 0.5, "Very bright, textureless")
    if blue > 0.20 and bright > 0.45:
        add("pet_bottle", "waste", False, 0.28 + blue * 0.8,
            "Clear / blue-tinted plastic")
    if blue > 0.15 and pale > 0.20:
        add("glass_bottle", "waste", False, 0.24 + blue * 0.7,
            "Glassy transparent surface")

    c.sort(key=lambda x: -x["score"])
    return c[:4]


def verdict_from_candidates(cands):
    """Turn ranked candidates into an e-waste / non-e-waste verdict."""
    if not cands:
        return dict(is_electronic=None, confidence=0.0, stream="unknown",
                    message="Couldn't recognise this. Pick the item manually or retake with better light.")
    top = cands[0]
    el = sum(c["score"] for c in cands if c["is_electronic"])
    non = sum(c["score"] for c in cands if not c["is_electronic"])
    total = el + non or 1.0
    conf = float(el / total)
    gap = top["score"] - (cands[1]["score"] if len(cands) > 1 else 0.0)

    if top["is_electronic"] and conf > 0.5:
        stream, msg = "e-waste", "Electronic waste - deep mineral appraisal available."
    elif not top["is_electronic"] and conf < 0.5:
        stream, msg = "other", "Not electronic - general waste stream."
    elif top["is_electronic"]:
        stream, msg = "e-waste", "Probably electronic, but the signal is weak. Confirm below."
    else:
        stream, msg = "other", "Probably general waste. Confirm below."

    if top["score"] < 0.30 or gap < 0.05:
        msg += " Low confidence - please confirm the item."

    # conf is the share of evidence backing the *stream*, so it saturates at 0/1
    # on flat synthetic colours. Clamp so the UI never claims absolute certainty.
    conf = min(max(conf, 0.03), 0.97)
    return dict(is_electronic=bool(top["is_electronic"]), confidence=round(conf, 3),
                stream=stream, message=msg, top_key=top["key"])


# ------------------------------------------------------------------- AI
_STOP = {"a", "an", "the", "of", "with", "and", "or", "in", "on", "is", "this",
         "that", "it", "some", "image", "photo", "picture", "object", "item",
         "appears", "shows", "showing", "looks", "like", "very", "single"}


def _words(text):
    return {w for w in "".join(c if c.isalnum() else " "
                               for c in (text or "").lower()).split()
            if len(w) > 2 and w not in _STOP}


def fuzzy_key(label, description, allowed):
    """Best catalogue key for a free-text description, or None.

    The model often names things the catalogue spells differently ("banana peel"
    vs "Fruit / vegetable peel"). Token overlap recovers those instead of
    discarding a correct identification.
    """
    query = _words(f"{label} {description}")
    if not query:
        return None
    best, best_score = None, 0.0
    for key in allowed:
        item = K.get(key)
        if not item:
            continue
        target = _words(f"{item['label']} {key.replace('_', ' ')}")
        if not target:
            continue
        overlap = len(query & target)
        # normalise by the smaller side so "peel" vs "fruit vegetable peel" scores well
        score = overlap / min(len(query), len(target))
        if score > best_score:
            best, best_score = key, score
    return best if best_score >= 0.34 else None


def allowed_keys():
    """Catalogue keys offered to the model - generics are hidden on purpose."""
    return sorted(set(list(K.DEVICES) + list(K.ITEMS)) - set(K.GENERIC_KEYS))


def classify_with_ai(image_bytes, features):
    """Optional real vision call. Returns None if no key is configured."""
    if not AI_KEY or AI_PROVIDER not in ("gemini", "openai"):
        return None
    allowed = allowed_keys()
    # Send key WITH its human label - bare keys like "fruit_peel" invite bad guesses
    catalog = ", ".join(f"{k} ({K.get(k)['label']})" for k in allowed)
    prompt = (
        "You analyse waste for a recycling app. Study the image, then answer.\n\n"
        "1. What exactly is this object? Be specific and plain, max 12 words.\n"
        "2. What materials can you actually SEE? Max 8 words, comma separated.\n"
        "3. Is it ELECTRONIC WASTE? Answer true only if it contains a circuit board, "
        "battery, chip, motor, display, transformer or electrical wiring. Otherwise false.\n"
        "4. Pick the closest key from this catalogue. If nothing is a genuinely good "
        "match, use null - do NOT guess something unrelated.\n"
        "Catalogue: " + catalog + "\n\n"
        "Return ONLY JSON:\n"
        "{\"description\": \"what you see, max 12 words\",\n"
        " \"materials\": \"comma separated, max 8 words\",\n"
        " \"key\": \"best catalogue key or null\",\n"
        " \"is_electronic\": true/false,\n"
        " \"confidence\": 0-1,\n"
        " \"label\": \"short human name\",\n"
        " \"reason\": \"one short sentence\"}"
    )
    b64 = base64.b64encode(image_bytes).decode()
    try:
        import requests
        if AI_PROVIDER == "gemini":
            body = {"contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
                "generationConfig": {"responseMimeType": "application/json"}}
            # key in a header, not the URL, so it stays out of access logs
            head = {"x-goog-api-key": AI_KEY}
            if _working_model:
                models = [_working_model]
            else:
                models = GEMINI_MODELS
                      import time
            last, txt = "", None
            for model in models:
                url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{model}:generateContent")
                # Gemini hands out transient 503s and can be slow on a cold
                # start. Retry with backoff: falling straight through to the
                # offline heuristic yields confidently WRONG identifications
                # (a banana has come back as "newspaper"), which is far worse
                # than making the user wait a few extra seconds.
                for attempt in range(3):
                    try:
                        r = requests.post(url, json=body, headers=head,
                                          timeout=45)
                    except Exception as exc:
                        last = f"{model}: {type(exc).__name__}"
                        time.sleep(1.5 * (2 ** attempt))
                        continue
                    if r.ok:
                        globals()["_working_model"] = model
                        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                        break
                    last = f"{model}: HTTP {r.status_code} {r.text[:120]}"
                    if r.status_code in (429, 500, 502, 503, 504):
                        time.sleep(1.5 * (2 ** attempt))
                        continue
                    break          # 400/403/404 - this model is not usable
                if txt:
                    break
            if not txt:
                raise RuntimeError("no usable Gemini model - " + last)
        else:
            url = "https://api.openai.com/v1/chat/completions"
            head = {"Authorization": f"Bearer {AI_KEY}"}
            body = {"model": "gpt-4o-mini", "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]}
            r = requests.post(url, json=body, headers=head, timeout=45)
            txt = r.json()["choices"][0]["message"]["content"]
        data = json.loads(txt)
        # a null key is a valid, useful answer - it means "nothing in your list fits"
        data["_key_matched"] = data.get("key") in allowed
        return data
    except Exception as exc:                                   # noqa: BLE001
        return {"error": str(exc)[:200]}
    return None


def analyze(image_bytes):
    """Full first-pass analysis: features -> verdict -> candidates."""
    features = extract_features(image_bytes)
    cands = classify_heuristic(features)
    ai = classify_with_ai(image_bytes, features)

    ai_view = None      # what the model said, kept for display either way
    if ai and not ai.get("error") and (ai.get("key") or ai.get("description")):
        ai_view = dict(description=ai.get("description", ""),
                       materials=ai.get("materials", ""),
                       label=ai.get("label", ""),
                       reason=ai.get("reason", ""),
                       key=ai.get("key"),
                       matched=bool(ai.get("_key_matched")))
        # Resolve the model's answer to something the user can actually select:
        #   exact catalogue key -> fuzzy match on its wording -> generic profile
        key = ai.get("key") if ai.get("_key_matched") else None
        how = "exact"
        if not key:
            key = fuzzy_key(ai.get("label", ""), ai.get("description", ""),
                            allowed_keys())
            how = "fuzzy" if key else "generic"
        if not key:
            key = "ewaste_generic" if ai.get("is_electronic") else "waste_generic"
        item = K.get(key)
        # the model's own name for the object, so a generic profile still reads
        # "Banana peel" on screen instead of "Other general waste"
        ai_name = (ai.get("label") or ai.get("description")
                   or item.get("label", key)).strip()
        cands.insert(0, dict(
            key=key, kind=item["kind"], is_electronic=item["is_electronic"],
            score=float(ai.get("confidence", 0.9)),
            why=ai.get("reason", "Identified by vision model"),
            source="ai", display=ai_name, match=how))
        seen, ded = set(), []
        for c in cands:
            if c["key"] not in seen:
                seen.add(c["key"]); ded.append(c)
        cands = ded[:4]
        ai_view.update(chosen_key=key, match=how, name=ai_name)

        verdict = verdict_from_candidates(cands)
        verdict["engine"] = f"ai:{AI_PROVIDER}"
        if how == "exact":
            verdict["message"] = f"Identified by AI vision: {ai_name}."
        elif how == "fuzzy":
            verdict["message"] = (f"AI identified this as {ai_name} - matched to "
                                  f"{item['label']} for valuation.")
        else:
            verdict["message"] = (f"AI sees: {ai_name}. Not in the catalogue, so "
                                  "a generic profile is used - refine below.")
    else:
        verdict = verdict_from_candidates(cands)
        verdict["engine"] = "heuristic"

    for c in cands:
        c.setdefault("source", "heuristic")
        item = K.get(c["key"])
        c["label"] = item["label"] if item else c["key"]

    return dict(features=features, candidates=cands, verdict=verdict,
                ai_view=ai_view, ai_error=(ai or {}).get("error"))
