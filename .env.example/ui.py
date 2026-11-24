import asyncio
from pathlib import Path
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

ASSETS = Path("assets")
FULL, EMPTY = "▰", "▱"
MEDALS = ["🥇", "🥈", "🥉"] + ["▫️"] * 50

async def banner(msg, name: str, caption: str, kb: InlineKeyboardMarkup | None = None):
    """assets/<name>.mp4 ho to animation, warna text card."""
    f = ASSETS / f"{name}.mp4"
    if f.exists():
        await msg.answer_animation(FSInputFile(f), caption=caption, reply_markup=kb)
    else:
        await msg.answer(caption, reply_markup=kb)

def bar(value: int, target: int, width: int = 10) -> str:
    if target <= 0:
        return EMPTY * width
    filled = max(0, min(width, round(value / target * width)))
    return FULL * filled + EMPTY * (width - filled)

def bar_frames(value: int, target: int, width: int = 10, steps: int = 3) -> list[str]:
    frames, final = [], bar(value, target, width)
    for i in range(1, steps + 1):
        frames.append(bar(int(value * i / steps), target, width))
    frames.append(final)
    return frames

async def animate(msg, frames: list[str], kb: InlineKeyboardMarkup | None = None):
    for fr in frames[:-1]:
        try:
            await msg.edit_text(fr, reply_markup=kb)
            await asyncio.sleep(0.28)
        except Exception:
            pass
    await msg.edit_text(frames[-1], reply_markup=kb)

def btn(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)

def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("📊 Guild Board", "board"), btn("🎯 My Target", "me")],
        [btn("✅ Submit Glory", "submit"), btn("📜 Rules", "rules")],
    ])

def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("« Back", "home")]])

def kb_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("🕓 Approval Queue", "aq"), btn("👥 Members", "mm")],
        [btn("🎯 Set Target", "st"), btn("📤 Export CSV", "csv")],
        [btn("📣 Broadcast", "bc"), btn("⚠️ Kick List", "kick")],
        [btn("🔄 Force Weekly Reset", "reset")],
    ])
