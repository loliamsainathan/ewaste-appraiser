"""User-editable numeric overrides.

Every number the app displays has a default baked into knowledge.py. Anything the
user changes in Settings is stored here as JSON and layered on top at read time,
so edits survive restarts and the defaults are always one "reset" away.
"""
import json
import os
import threading

PATH = os.environ.get("EWASTE_OVERRIDES", "/home/user/ewaste_app/overrides.json")
_lock = threading.Lock()

# shape of the override document
BLANK = {"costs": {}, "processing": {}, "metals": {},
         "devices": {}, "items": {}, "impact": {}}
_cache = None


def _read():
    global _cache
    if _cache is not None:
        return _cache
    data = json.loads(json.dumps(BLANK))
    try:
        with open(PATH) as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            for k in BLANK:
                if isinstance(loaded.get(k), dict):
                    data[k] = loaded[k]
    except (OSError, ValueError):
        pass
    _cache = data
    return data


def all_overrides():
    with _lock:
        return json.loads(json.dumps(_read()))


def _deep_merge(dst, src):
    """Merge src into dst recursively.

    A shallow update() would drop sibling fields: saving gold's recovery would
    wipe gold's already-edited price, because the UI saves one field at a time.
    """
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def save(data):
    """Merge a partial override document and persist it."""
    global _cache
    with _lock:
        cur = _read()
        for section in BLANK:
            incoming = data.get(section)
            if isinstance(incoming, dict):
                _deep_merge(cur.setdefault(section, {}), incoming)
        with open(PATH, "w") as fh:
            json.dump(cur, fh, indent=2, sort_keys=True)
        _cache = cur
        return json.loads(json.dumps(cur))


def reset():
    """Drop every override and go back to the shipped defaults."""
    global _cache
    with _lock:
        _cache = json.loads(json.dumps(BLANK))
        try:
            os.remove(PATH)
        except OSError:
            pass
        return json.loads(json.dumps(_cache))


def _num(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------------ getters
def costs(default):
    o = _read()["costs"]
    return {k: _num(o.get(k, v), v) for k, v in default.items()}


def processing(key, default):
    return _num(_read()["processing"].get(key), default)


def metal_price(metal, default):
    return _num(_read()["metals"].get(metal, {}).get("price"), default)


def metal_recovery(metal, default):
    v = _num(_read()["metals"].get(metal, {}).get("recovery"), default)
    return min(max(v, 0.0), 1.0)


def impact(metal, default):
    return _num(_read()["impact"].get(metal), default)


def device_weight(key, default):
    return _num(_read()["devices"].get(key, {}).get("weight_g"), default)


def device_yields(key, default_yields):
    """Default yields overlaid with any per-metal overrides."""
    out = dict(default_yields)
    for metal, val in (_read()["devices"].get(key, {}).get("yields") or {}).items():
        out[metal] = _num(val, out.get(metal, 0.0))
    return out


def item_weight(key, default):
    return _num(_read()["items"].get(key, {}).get("weight_g"), default)


def item_rate(key, default):
    return _num(_read()["items"].get(key, {}).get("rate"), default)
