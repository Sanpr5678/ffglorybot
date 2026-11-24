ACC = """
CREATE TABLE IF NOT EXISTS accs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  login_uid TEXT, password TEXT, token TEXT, open_id TEXT,
  active INTEGER DEFAULT 1, joins INTEGER DEFAULT 0, ts INTEGER
);
"""
# init() ke andar: await db.executescript(ACC)

async def add_acc(login_uid, pw, token, open_id):
    await q("INSERT INTO accs(login_uid,password,token,open_id,ts) VALUES(?,?,?,?,?)",
            (login_uid, pw, token, open_id, int(time.time())), write=True)

async def all_accs(active_only=False):
    sql = "SELECT * FROM accs" + (" WHERE active=1" if active_only else "")
    rows = await q(sql + " ORDER BY id")
    return [dict(zip([c[0] for c in ("id","login_uid","password","token","open_id","active","joins","ts")], r)) for r in rows]

async def bump_join(i):
    await q("UPDATE accs SET joins=joins+1 WHERE id=?", (i,), write=True)
