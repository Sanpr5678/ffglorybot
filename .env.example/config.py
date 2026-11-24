import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
TZ = os.getenv("TZ", "Asia/Kolkata")
DB_PATH = "guild.db"

# Defaults (admin panel se badal sakte ho)
DEFAULT_TARGET = 2000        # weekly guild glory target
DEFAULT_MIN = 200            # isse kam = strike
DEFAULT_MAX_STRIKES = 3      # 3 strike = kick-list me
