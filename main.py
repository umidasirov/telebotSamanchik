from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio, json

TOKEN = "7278033640:AAE-5yMcWeoDxkAFn6fiq9hPg_DhgL6C9qw"

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())
router = Router()

db_path = "data/video_ids.json"

def load_db():
    try:
        with open(db_path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

db = load_db()
pending_add = {}
ADMIN_IDS = [8020192658,]

@router.message(F.text == "/start")
async def start_cmd(msg: Message):
    await msg.answer("Salom! Kod yuboring yoki /add kod orqali video qo‘shing (faqat admin).")

@router.message(F.text.startswith("/add"))
async def add_video_step1(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ Sizda ruxsat yo‘q.")

    parts = msg.text.strip().split()
    if len(parts) != 2:
        return await msg.answer("❗ Format: /add <kod>")

    code = parts[1].lower()
    pending_add[msg.from_user.id] = code
    await msg.answer(f"✅ Endi shu kodga video yuboring: {code}")

@router.message(lambda m: m.video and m.from_user.id in pending_add)
async def add_video_step2(msg: Message):
    code = pending_add.pop(msg.from_user.id)
    db[code] = msg.video.file_id
    save_db(db)
    await msg.answer(f"✅ Video saqlandi! Kod: <b>{code}</b>")

@router.message()
async def search_video(msg: Message):
    code = msg.text.strip().lower()
    if code in db:
        await msg.answer_video(video=db[code], caption=f"📽 Kod: {code}")
    else:
        await msg.answer("❌ Bunday kodga video topilmadi.")

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
