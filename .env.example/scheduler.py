from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import db, ui
from config import ADMIN_IDS, TZ

def build(bot):
    sch = AsyncIOScheduler(timezone=TZ)

    async def reset_job():
        week, rows = await db.weekly_reset()
        total = sum(g for _, g in rows)
        kick = [u for u, g in rows if g < int(await db.get_setting("min", 200))]
        lines = [f"🔁 <b>Weekly reset</b> ({week})", f"Guild total: <b>{total}</b>", ""]
        if kick:
            lines.append(f"⚠️ Kick list ({len(kick)}):")
            for u in kick[:40]:
                m = await db.get_member(u)
                if m:
                    lines.append(f"• {m['ign']} — strikes {m['strikes']}")
        else:
            lines.append("✅ Sab members target ke andar.")
        for a in ADMIN_IDS:
            try:
                await bot.send_message(a, "\n".join(lines))
            except Exception:
                pass

    sch.add_job(reset_job, CronTrigger(day_of_week="mon", hour=4, minute=0, timezone=TZ))
    return sch
