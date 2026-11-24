import asyncio, io, time
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile

import db, ui, scheduler
from config import BOT_TOKEN, ADMIN_IDS, DEFAULT_TARGET, DEFAULT_MIN

router = Router()
is_admin = lambda uid: uid in ADMIN_IDS

class F_Add(StatesGroup): ign = State(); uid = State()
class F_Sub(StatesGroup): amount = State(); proof = State()
class F_Set(StatesGroup): value = State()
class F_BC(StatesGroup): text = State()

# ---------- home ----------
@router.message(CommandStart())
async def start(m: Message):
    if not await db.get_member(m.from_user.id):
        await db.add_member(m.from_user.id, m.from_user.full_name)
    name = await db.get_setting("guild_name", "Guild")
    await ui.banner(m, "home", f"🏰 <b>{name}</b> — Glory Control\n\nNeeche se option chuno:",
                    ui.kb_main())
    if is_admin(m.from_user.id):
        await m.answer("🛠 <b>Admin panel</b>", reply_markup=ui.kb_admin())

@router.callback_query(F.data == "home")
async def home(c: CallbackQuery):
    name = await db.get_setting("guild_name", "Guild")
    await c.message.edit_text(f"🏰 <b>{name}</b> — Glory Control\n\nNeeche se option chuno:",
                              reply_markup=ui.kb_main())
    await c.answer()

# ---------- public ----------
@router.callback_query(F.data == "board")
async def board(c: CallbackQuery):
    rows = await db.board()
    target = int(await db.get_setting("target", DEFAULT_TARGET))
    await c.answer("Loading…")
    await c.message.edit_text("⏳")
    frames = []
    for i in range(1, 4):
        chunk = []
        for idx, r in enumerate(rows[:15]):
            g = r["glory_week"] * i // 3
            chunk.append(f"{ui.MEDALS[idx]} <b>{r['ign']}</b> — {g}/{target}\n{ui.bar(g, target)}")
        frames.append(f"📊 <b>WEEKLY GLORY BOARD</b>\nTarget: {target}\n\n" + ("\n\n".join(chunk) or "Koi member nahi."))
    await ui.animate(c.message, frames, ui.kb_back())

@router.callback_query(F.data == "me")
async def me(c: CallbackQuery):
    m = await db.get_member(c.from_user.id)
    target = int(await db.get_setting("target", DEFAULT_TARGET))
    if not m:
        return await c.answer("Pehle /start karo", show_alert=True)
    left = max(0, target - m["glory_week"])
    pct = min(100, round(m["glory_week"] / target * 100)) if target else 0
    txt = (f"🎯 <b>{m['ign']}</b>\n\n{ui.bar(m['glory_week'], target)}  {pct}%\n"
           f"Is week: <b>{m['glory_week']}</b> / {target}\n"
           f"Baaki: <b>{left}</b>\nTotal: {m['glory_total']}\nStrikes: {'⚠️' * m['strikes'] or '—'}")
    await c.message.edit_text(txt, reply_markup=ui.kb_back())
    await c.answer()

@router.callback_query(F.data == "rules")
async def rules(c: CallbackQuery):
    target = int(await db.get_setting("target", DEFAULT_TARGET))
    minimum = int(await db.get_setting("min", DEFAULT_MIN))
    maxs = int(await db.get_setting("max_strikes", 3))
    txt = (f"📜 <b>RULES</b>\n\n"
           f"1. Weekly target: <b>{target}</b> glory\n"
           f"2. Minimum: <b>{minimum}</b> — isse kam = 1 strike\n"
           f"3. <b>{maxs}</b> strike = kick list\n"
           f"4. Glory proof ke bina submit = reject\n"
           f"5. Reset har Somwar 04:00 IST")
    await c.message.edit_text(txt, reply_markup=ui.kb_back())
    await c.answer()

# ---------- submit ----------
@router.callback_query(F.data == "submit")
async def sub_start(c: CallbackQuery, state: FSMContext):
    today = await db.today_subs(c.from_user.id)
    if len(today) >= 5:
        return await c.answer("Aaj 5 submission ho gaye, kal try karo.", show_alert=True)
    await state.set_state(F_Sub.amount)
    await c.message.edit_text("🔢 Kitni glory add karni hai? (sirf number)", reply_markup=ui.kb_back())
    await c.answer()

@router.message(F_Sub.amount)
async def sub_amount(m: Message, state: FSMContext):
    if not m.text.isdigit():
        return await m.answer("Sirf number bhejo.")
    await state.update_data(amount=int(m.text))
    await state.set_state(F_Sub.proof)
    await m.answer("📸 Proof screenshot bhejo, ya `-` likh ke skip karo.")

@router.message(F_Sub.proof)
async def sub_proof(m: Message, state: FSMContext):
    d = await state.get_data()
    proof = m.photo[-1].file_id if m.photo else None
    sid = await db.add_sub(m.from_user.id, d["amount"], proof)
    await state.clear()
    await m.answer(f"✅ Submission #{sid} bheja gaya — admin approve karega.")
    mem = await db.get_member(m.from_user.id)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as B
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        B(text="✅ Approve", callback_data=f"ap:{sid}"),
        B(text="❌ Reject", callback_data=f"rj:{sid}")]])
    for a in ADMIN_IDS:
        try:
            cap = f"🕓 <b>New submission #{sid}</b>\n{mem['ign']} — <b>{d['amount']}</b> glory"
            if proof:
                await m.bot.send_photo(a, proof, caption=cap, reply_markup=kb)
            else:
                await m.bot.send_message(a, cap, reply_markup=kb)
        except Exception:
            pass

# ---------- admin approve ----------
@router.callback_query(F.data.startswith(("ap:", "rj:")))
async def approve(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Admin only", show_alert=True)
    act, sid = c.data.split(":")
    s = await db.get_sub(int(sid))
    if not s or s["status"] != "pending":
        return await c.answer("Already processed", show_alert=True)
    mem = await db.get_member(s["user_id"])
    if act == "ap":
        await db.set_sub(s["id"], "approved")
        await db.add_glory(s["user_id"], s["amount"])
        await c.message.edit_caption(caption=f"✅ Approved — {mem['ign']} +{s['amount']} glory")
        try:
            await c.bot.send_message(s["user_id"], f"✅ +{s['amount']} glory approved. Shukriya!")
        except Exception:
            pass
    else:
        await db.set_sub(s["id"], "rejected")
        await c.message.edit_caption(caption=f"❌ Rejected — {mem['ign']}")
        try:
            await c.bot.send_message(s["user_id"], "❌ Submission reject hui. Proof check karo.")
        except Exception:
            pass
    await c.answer("Done")

# ---------- admin panel ----------
@router.message(Command("panel"))
async def panel(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("Admin only.")
    await m.answer("🛠 <b>Admin panel</b>", reply_markup=ui.kb_admin())

@router.callback_query(F.data == "aq")
async def aq(c: CallbackQuery):
    rows = await db.pending()
    if not rows:
        return await c.answer("Queue khaali hai.", show_alert=True)
    for s in rows[:10]:
        mem = await db.get_member(s["user_id"])
        cap = f"#{s['id']} — {mem['ign']} — {s['amount']} glory"
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as B
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            B(text="✅", callback_data=f"ap:{s['id']}"), B(text="❌", callback_data=f"rj:{s['id']}")]])
        if s["proof"]:
            await c.bot.send_photo(c.from_user.id, s["proof"], caption=cap, reply_markup=kb)
        else:
            await c.bot.send_message(c.from_user.id, cap, reply_markup=kb)
    await c.answer()

@router.callback_query(F.data == "mm")
async def mm(c: CallbackQuery):
    rows = await db.board()
    txt = "👥 <b>MEMBERS</b>\n\n" + "\n".join(
        f"• {r['ign']} — {r['glory_week']} — ⚠️{r['strikes']} — <code>{r['user_id']}</code>"
        for r in rows[:40])
    await c.message.edit_text(txt or "Koi nahi.", reply_markup=ui.kb_back())
    await c.answer()

@router.callback_query(F.data == "st")
async def st(c: CallbackQuery, state: FSMContext):
    await state.set_state(F_Set.value)
    await c.message.edit_text("🎯 Naya weekly target bhejo:", reply_markup=ui.kb_back())
    await c.answer()

@router.message(F_Set.value)
async def st_set(m: Message, state: FSMContext):
    if not m.text.isdigit():
        return await m.answer("Number bhejo.")
    await db.set_setting("target", m.text)
    await state.clear()
    await m.answer(f"✅ Target = {m.text}")

@router.callback_query(F.data == "kick")
async def kick(c: CallbackQuery):
    minimum = int(await db.get_setting("min", DEFAULT_MIN))
    rows = [r for r in await db.board() if r["glory_week"] < minimum]
    txt = f"⚠️ <b>KICK LIST</b> (min {minimum})\n\n" + "\n".join(
        f"• {r['ign']} — {r['glory_week']} — strikes {r['strikes']}" for r in rows)
    await c.message.edit_text(txt if rows else "✅ Sab safe.", reply_markup=ui.kb_back())
    await c.answer()

@router.callback_query(F.data == "csv")
async def csv(c: CallbackQuery):
    rows = await db.board()
    buf = io.StringIO()
    buf.write("ign,user_id,glory_week,glory_total,strikes\n")
    for r in rows:
        buf.write(f"{r['ign']},{r['user_id']},{r['glory_week']},{r['glory_total']},{r['strikes']}\n")
    f = BufferedInputFile(buf.getvalue().encode(), filename=f"glory_{int(time.time())}.csv")
    await c.message.answer_document(f)
    await c.answer()

@router.callback_query(F.data == "bc")
async def bc(c: CallbackQuery, state: FSMContext):
    await state.set_state(F_BC.text)
    await c.message.edit_text("📣 Broadcast message bhejo:", reply_markup=ui.kb_back())
    await c.answer()

@router.message(F_BC.text)
async def bc_send(m: Message, state: FSMContext):
    await state.clear()
    ok = 0
    for r in await db.board():
        try:
            await m.bot.send_message(r["user_id"], f"📣 {m.text}")
            ok += 1
        except Exception:
            pass
    await m.answer(f"✅ {ok} members ko bheja.")

@router.callback_query(F.data == "reset")
async def reset(c: CallbackQuery):
    week, rows = await db.weekly_reset()
    await c.answer("Reset ho gaya", show_alert=True)
    await c.message.answer(f"🔁 Manual reset {week} — {len(rows)} members archived.")

# ---------- boot ----------
async def main():
    await db.init()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)
    scheduler.build(bot).start()
    print("Bot live.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
