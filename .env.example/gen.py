import random, string, aiohttp

GRANT = "https://100067.connect.garena.com/oauth/guest/token/grant"
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1d7b4b8b4d5f4"
UA = "GarenaMSDK/4.0.19P_GMA"

def _uid(): return "".join(random.choices(string.digits, k=9))
def _pw():  return "".join(random.choices(string.ascii_letters + string.digits, k=12))

async def create_guest():
    """Ek fresh guest account. Returns token + credentials."""
    uid, pw = _uid(), _pw()
    body = {
        "uid": uid, "password": pw, "response_type": "token",
        "client_type": "2", "client_secret": CLIENT_SECRET, "client_id": "100067",
    }
    h = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(GRANT, data=body, headers=h, timeout=25) as r:
                if r.status != 200:
                    return {"ok": False, "err": f"HTTP {r.status}"}
                j = await r.json()
    except Exception as e:
        return {"ok": False, "err": type(e).__name__}
    if not j.get("access_token"):
        return {"ok": False, "err": str(j)[:100]}
    return {"ok": True, "uid": uid, "password": pw,
            "token": j["access_token"], "open_id": j.get("open_id")}
