import time
import aiosqlite
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS members(
  user_id INTEGER PRIMARY KEY,
  ign TEXT NOT NULL,
  uid TEXT,
  role TEXT DEFAULT 'member',
  glory_week INTEGER DEFAULT 0,
  glory_total INTEGER DEFAULT 0,
  strikes INTEGER DEFAULT 0,
  joined INTEGER
);
CREATE TABLE IF NOT EXISTS subs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  amount INTEGER,
  proof TEXT,
  status TEXT DEFAULT 'pending',
  ts INTEGER
);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS history(week TEXT, user_id INTEGER, glory INTEGER);
"""

async def init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def q(sql, args=(), one=False, write=False):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, args)
        if write:
            await db.commit()
            return cur.lastrowid
        rows = await cur.fetchall()
        return (rows[0] if rows else None) if one else rows

# members
async def add_member(uid, ign, ffuid=None, role="member"):
    await q(
        "INSERT INTO members(user_id,ign,uid,role,joined) VALUES(?,?,?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET ign=excluded.ign, uid=excluded.uid, role=excluded.role",
        (uid, ign, ffuid, role, int(time.time())), write=True)

async def get_member(uid):
    return await q("SELECT * FROM members WHERE user_id=?", (uid,), one=True)

async def del_member(uid):
    await q("DELETE FROM members WHERE user_id=?", (uid,), write=True)

async def board():
    return await q("SELECT * FROM members ORDER BY glory_week DESC, ign ASC")

async def add_glory(uid, n):
    await q("UPDATE members SET glory_week=glory_week+?, glory_total=glory_total+? WHERE user_id=?",
            (n, n, uid), write=True)

async def set_strikes(uid, n):
    await q("UPDATE members SET strikes=? WHERE user_id=?", (n, uid), write=True)

# submissions
async def add_sub(uid, amount, proof=None):
    return await q("INSERT INTO subs(user_id,amount,proof,ts) VALUES(?,?,?,?)",
                   (uid, amount, proof, int(time.time())), write=True)

async def get_sub(sid):
    return await q("SELECT * FROM subs WHERE id=?", (sid,), one=True)

async def set_sub(sid, status):
    await q("UPDATE subs SET status=? WHERE id=?", (status, sid), write=True)

async def pending():
    return await q("SELECT * FROM subs WHERE status='pending' ORDER BY ts ASC")

async def today_subs(uid):
    start = int(time.time()) - 86400
    return await q("SELECT * FROM subs WHERE user_id=? AND ts>?", (uid, start))

# settings
async def set_setting(k, v):
    await q("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (k, str(v)), write=True)

async def get_setting(k, default=None):
    r = await q("SELECT v FROM settings WHERE k=?", (k,), one=True)
    return r[0] if r else default

# weekly reset (Monday 04:00 IST)
async def weekly_reset():
    week = time.strftime("%Y-W%V")
    rows = await q("SELECT user_id, glory_week FROM members")
    minimum = int(await get_setting("min", 200))
    for uid, g in rows:
        await q("INSERT INTO history(week,user_id,glory) VALUES(?,?,?)", (week, uid, g), write=True)
        strikes = 0 if g >= minimum else 1
        await q("UPDATE members SET glory_week=0, strikes=strikes+? WHERE user_id=?", (strikes, uid), write=True)
    return week, rows
