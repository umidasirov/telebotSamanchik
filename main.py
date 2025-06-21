import asyncio, aiosqlite, json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

TOKEN = "7278033640:AAE-5yMcWeoDxkAFn6fiq9hPg_DhgL6C9qw"
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

DB_PATH = "data/database.db"
ADMIN_FILE = "data/admin_ids.json"
CHANNEL_FILE = "data/channel.json"
pending_add = {}

# ----------- SQLITE INIT -----------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                code TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                desk TEXT
            )
        """)
        await db.commit()

# ----------- JSON LOAD/SAVE ----------
def load_admins():
    try:
        with open(ADMIN_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_admins(admins):
    with open(ADMIN_FILE, "w") as f:
        json.dump(admins, f)

def load_channel():
    try:
        with open(CHANNEL_FILE, "r") as f:
            return json.load(f).get("channel")
    except:
        return None

def save_channel(username):
    with open(CHANNEL_FILE, "w") as f:
        json.dump({"channel": username}, f)

ADMIN_IDS = load_admins()

# --------- SUBSCRIPTION CHECK --------
async def is_user_subscribed(user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

# --------- BOT HANDLERS --------------
@router.message(F.text == "/start")
async def start_cmd(msg: Message):
    channel = load_channel()
    if channel:
        subscribed = await is_user_subscribed(msg.from_user.id, channel)
        if not subscribed:
            return await msg.answer(
                f"📛 Botdan foydalanish uchun {channel} kanaliga obuna bo‘ling!\n\n"
                f"➡️ <a href='https://t.me/{channel[1:]}'>Kanalga o‘tish</a>\n"
                f"✅ Obuna bo‘lgach, /start ni qayta yuboring.",
                disable_web_page_preview=True
            )
    await msg.answer("👋 Salom! Kod yuboring yoki /add orqali video qo‘shing (faqat admin).")

@router.message(F.text.startswith("/setchannel"))
async def set_channel(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ Siz admin emassiz.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].startswith("@"):
        return await msg.answer("❗ Format: /setchannel @kanal")
    save_channel(parts[1])
    await msg.answer(f"✅ Kanal saqlandi: {parts[1]}")

@router.message(F.text.startswith("/add"))
async def add_video_step1(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ Sizda ruxsat yo‘q.")
    parts = msg.text.split()
    if len(parts) != 2:
        return await msg.answer("❗ Format: /add <kod>")
    pending_add[msg.from_user.id] = parts[1].lower()
    await msg.answer(f"✅ Endi shu kodga video yuboring: {parts[1]}")

@router.message(lambda m: m.video and m.from_user.id in pending_add)
async def add_video_step2(msg: Message):
    code = pending_add.pop(msg.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("REPLACE INTO videos (code, file_id, desk) VALUES (?, ?, ?)",
                         (code, msg.video.file_id, ""))
        await db.commit()
    await msg.answer(f"✅ Video saqlandi! Kod: <b>{code}</b>")

@router.message(F.text.startswith("/desk"))
async def set_description(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ Sizda ruxsat yo‘q.")
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return await msg.answer("❗ Format: /desk <kod> <tavsif>")
    code, desk = parts[1].lower(), parts[2]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("UPDATE videos SET desk = ? WHERE code = ?", (desk, code))
        if cur.rowcount == 0:
            return await msg.answer("❌ Bunday kod yo‘q.")
        await db.commit()
    await msg.answer(f"📝 Tavsif yangilandi: {code} → {desk}")

@router.message()
async def search_video(msg: Message):
    code = msg.text.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT file_id, desk FROM videos WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()
    if row:
        file_id, desk = row
        caption = f"📽 Kod: {code}"
        if desk:
            caption += f"\n📝 {desk}"
        await msg.answer_video(video=file_id, caption=caption)
    else:
        await msg.answer("❌ Bunday kodga video topilmadi.")

# -------------- ADMIN ----------------
@router.message(F.text.startswith("/addadmin"))
async def add_admin(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ Sizda ruxsat yo‘q.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await msg.answer("❗ Format: /addadmin <user_id>")
    new_id = int(parts[1])
    if new_id in ADMIN_IDS:
        return await msg.answer("✅ Allaqachon admin.")
    ADMIN_IDS.append(new_id)
    save_admins(ADMIN_IDS)
    await msg.answer(f"✅ Admin qo‘shildi: {new_id}")

@router.message(F.text == "/adminlist")
async def admin_list(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ Ruxsat yo‘q.")
    admins = "\n".join([f"<a href='tg://user?id={i}'>{i}</a>" for i in ADMIN_IDS])
    await msg.answer(f"👤 Adminlar:\n{admins}")

# --------- START ---------------------
dp.include_router(router)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
