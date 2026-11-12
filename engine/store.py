"""SQLite persistence for scans, map reports, listings and recyclers."""
import os
import sqlite3
import time
import math

DB = os.environ.get("EWASTE_DB", "/home/user/ewaste_app/data.db")

# Chennai-area seed recyclers / authorised e-waste collection points
SEED_RECYCLERS = [
    ("Chennai E-Waste Recyclers", 13.0827, 80.2707, "authorized",
     "Computers, Phones, Batteries", "+91-44-2621-0001"),
    ("Kabadiwala - T. Nagar", 13.0418, 80.2341, "dealer",
     "Paper, Plastic, Metal, E-waste", "+91-98400-11223"),
    ("Adyar Scrap Mart", 13.0067, 80.2570, "dealer",
     "Metal, Appliances, Cables", "+91-98400-33445"),
    ("Anna Nagar E-Waste Point", 13.0850, 80.2100, "authorized",
     "Phones, Laptops, PCBs", "+91-44-2616-7788"),
    ("Velachery Metal & Cable Co.", 12.9815, 80.2180, "dealer",
     "Copper, Aluminium, Brass", "+91-98400-55667"),
    ("Guindy Industrial Recyclers", 13.0100, 80.2120, "recycler",
     "Appliances, Motors, Steel", "+91-44-2235-9900"),
    ("Tambaram E-Waste Drive", 12.9249, 80.1000, "authorized",
     "All electronics", "+91-98400-77889"),
    ("Porur Battery & Metal Recovery", 13.0380, 80.1560, "authorized",
     "Batteries, Inverters", "+91-44-2476-1234"),
]


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS scans(
          id INTEGER PRIMARY KEY, ts REAL, key TEXT, label TEXT,
          is_electronic INTEGER, confidence REAL, engine TEXT,
          weight_g REAL, value REAL, net REAL, verdict TEXT, co2 REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reports(
          id INTEGER PRIMARY KEY, ts REAL, lat REAL, lng REAL, address TEXT,
          category TEXT, note TEXT, severity TEXT, upvotes INTEGER DEFAULT 0,
          status TEXT DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS listings(
          id INTEGER PRIMARY KEY, ts REAL, lat REAL, lng REAL, address TEXT,
          item_key TEXT, label TEXT, qty REAL, asking REAL, note TEXT,
          status TEXT DEFAULT 'available');
        CREATE TABLE IF NOT EXISTS recyclers(
          id INTEGER PRIMARY KEY, name TEXT, lat REAL, lng REAL, type TEXT,
          accepts TEXT, phone TEXT, verified INTEGER DEFAULT 1);
        """)
        cols = [r[1] for r in c.execute("PRAGMA table_info(scans)")]
        if cols and "co2" not in cols:
            c.execute("ALTER TABLE scans ADD COLUMN co2 REAL DEFAULT 0")
        cols = [r[1] for r in c.execute("PRAGMA table_info(scans)")]
        if cols and "quantity" not in cols:
            c.execute("ALTER TABLE scans ADD COLUMN quantity REAL DEFAULT 1")
        if c.execute("SELECT COUNT(*) FROM recyclers").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO recyclers(name,lat,lng,type,accepts,phone) VALUES(?,?,?,?,?,?)",
                SEED_RECYCLERS)


def add_scan(key, label, is_el, conf, engine, weight_g, value, net, verdict,
             co2=0.0, quantity=1.0):
    with conn() as c:
        cur = c.execute("INSERT INTO scans(ts,key,label,is_electronic,confidence,engine,"
                        "weight_g,value,net,verdict,co2,quantity)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (time.time(), key, label, int(bool(is_el)), conf, engine,
                         float(weight_g or 0), value, net, verdict,
                         float(co2 or 0), float(quantity or 1)))
        return cur.lastrowid


def clear_history():
    """Wipe saved scans (used by the Settings reset - demo data is not real usage)."""
    with conn() as c:
        n = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        c.execute("DELETE FROM scans")
        return n


def stats():
    """Aggregate totals straight from the rows the user actually scanned."""
    with conn() as c:
        r = c.execute("SELECT COUNT(*) n, COALESCE(SUM(weight_g),0) g, "
                      "COALESCE(SUM(value),0) v, COALESCE(SUM(net),0) net, "
                      "COALESCE(SUM(co2),0) co2 FROM scans").fetchone()
        return dict(scans=r["n"], kg=round(r["g"] / 1000.0, 3), value=round(r["v"], 2),
                    net=round(r["net"], 2), co2=round(r["co2"], 2))


def history(limit=30):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM scans ORDER BY ts DESC LIMIT ?", (limit,))]


def add_report(lat, lng, address, category, note, severity):
    with conn() as c:
        cur = c.execute("INSERT INTO reports(ts,lat,lng,address,category,note,severity)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (time.time(), lat, lng, address, category, note, severity))
        return cur.lastrowid


def reports():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM reports ORDER BY ts DESC")]


def upvote_report(rid):
    with conn() as c:
        c.execute("UPDATE reports SET upvotes = upvotes + 1 WHERE id=?", (rid,))


def add_listing(lat, lng, address, item_key, label, qty, asking, note):
    with conn() as c:
        cur = c.execute("INSERT INTO listings(ts,lat,lng,address,item_key,label,qty,"
                        "asking,note) VALUES(?,?,?,?,?,?,?,?,?)",
                        (time.time(), lat, lng, address, item_key, label, qty, asking, note))
        return cur.lastrowid


def listings():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM listings WHERE status='available' ORDER BY ts DESC")]


def recyclers():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM recyclers")]


def nearby(lat, lng, radius_km=25):
    out = []
    for r in recyclers():
        d = _haversine(lat, lng, r["lat"], r["lng"])
        if d <= radius_km:
            r = dict(r); r["distance_km"] = round(d, 2); out.append(r)
    return sorted(out, key=lambda x: x["distance_km"])


def _haversine(a1, o1, a2, o2):
    R = 6371.0
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = math.radians(a2 - a1), math.radians(o2 - o1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))
