import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Configure these as hosting Environment Variables. Never commit your token to GitHub.
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8678341659
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@CODER_LEGEND").lstrip("@")
JOIN_LINK = os.getenv("JOIN_LINK", "https://t.me/+5XzK2EVfgY1iZDg1")

PAGE_SIZE = 10
DATABASE = "videos.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing!")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect(DATABASE, check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
db.execute("""CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT UNIQUE NOT NULL,
    caption TEXT DEFAULT 'Free Video',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
db.commit()


def is_admin(user_id):
    return user_id == ADMIN_ID


def save_user(user):
    db.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user.id, user.username, user.first_name)
    )
    db.commit()


def save_video(file_id, caption):
    cur = db.execute(
        "INSERT OR IGNORE INTO videos (file_id, caption) VALUES (?, ?)",
        (file_id, caption or "🎬 Free Video")
    )
    db.commit()
    return cur.lastrowid if cur.rowcount else None


def video_count():
    return db.execute("SELECT COUNT(*) FROM videos").fetchone()[0]


def user_count():
    return db.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def get_videos(page):
    return db.execute(
        "SELECT id, file_id, caption FROM videos ORDER BY id DESC LIMIT ? OFFSET ?",
        (PAGE_SIZE, page * PAGE_SIZE)
    ).fetchall()


def delete_video(video_id):
    cur = db.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    db.commit()
    return cur.rowcount > 0


def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Get Free Videos", callback_data="get_videos")],
        [InlineKeyboardButton(text="💎 Buy Paid Groups", callback_data="buy_paid_groups")]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Upload Videos", callback_data="upload")],
        [InlineKeyboardButton(text="🗑 Remove Videos", callback_data="remove:0")],
        [InlineKeyboardButton(text="📚 All Videos", callback_data="all")],
        [InlineKeyboardButton(text="📊 Statistics", callback_data="stats")]
    ])


def page_keyboard(page, total, prefix):
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️ Previous", callback_data=f"{prefix}:{page - 1}")
    if (page + 1) * PAGE_SIZE < total:
        builder.button(text="Next ➡️", callback_data=f"{prefix}:{page + 1}")
    builder.adjust(2)
    return builder.as_markup()


@dp.message(CommandStart())
async def start(message: Message):
    save_user(message.from_user)
    await message.answer(
        "👋 WELCOME TO FREE VIDEO BOT!\n\n"
        "🎬 Watch Free Videos\n💎 Explore Paid Groups\n\n👇 Select an option:",
        reply_markup=main_keyboard()
    )


@dp.callback_query(F.data == "buy_paid_groups")
async def buy_paid_groups(callback: CallbackQuery):
    if ADMIN_USERNAME == "yourusername":
        await callback.message.answer("💎 PAID GROUPS\n\nAdmin username hosting settings में configure नहीं है।")
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👨‍💻 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")
        ]])
        await callback.message.answer(
            "💎 PAID GROUPS\n\nPaid Groups की जानकारी और खरीदने के लिए Admin से संपर्क करें।",
            reply_markup=keyboard
        )
    await callback.answer()


@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Access Denied!")
        return
    await message.answer(
        f"⚙️ ADMIN PANEL\n\n🎬 Total Videos: {video_count()}\n👥 Total Users: {user_count()}",
        reply_markup=admin_keyboard()
    )


@dp.callback_query(F.data == "upload")
async def upload_info(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied!", show_alert=True)
        return
    await callback.message.answer(
        "📤 अपने Telegram Channel से वीडियो इस Bot की Private Chat में Forward करें।\n"
        "Video या video file के रूप में भेजे गए वीडियो सेव होंगे।"
    )
    await callback.answer()


@dp.message(F.video)
async def receive_video(message: Message):
    if not is_admin(message.from_user.id):
        return
    saved_id = save_video(message.video.file_id, message.caption or "🎬 Free Video")
    if saved_id:
        await message.answer(f"✅ VIDEO UPLOADED!\n🆔 Video ID: {saved_id}\n📚 Total Videos: {video_count()}")
    else:
        await message.answer("⚠️ यह Video पहले से Upload है।")


@dp.message(F.document)
async def receive_video_document(message: Message):
    if not is_admin(message.from_user.id):
        return
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        return
    saved_id = save_video(doc.file_id, message.caption or "🎬 Free Video")
    if saved_id:
        await message.answer(f"✅ VIDEO UPLOADED!\n🆔 Video ID: {saved_id}\n📚 Total Videos: {video_count()}")
    else:
        await message.answer("⚠️ यह Video पहले से Upload है।")


async def send_video_page(chat_id, page):
    total = video_count()
    videos = get_videos(page)
    if not videos:
        text = "😔 अभी कोई वीडियो उपलब्ध नहीं है।" if total == 0 else "इस Page पर कोई Video नहीं है।"
        await bot.send_message(chat_id, text)
        return

    await bot.send_message(chat_id, f"🎬 FREE VIDEO COLLECTION\n📚 Total Videos: {total}\n📄 Page: {page + 1}")

    for video_id, file_id, caption in videos:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="➕ Join Channel", url=JOIN_LINK)
        ]])
        try:
            await bot.send_video(chat_id=chat_id, video=file_id, caption=caption or "🎬 Free Video", reply_markup=keyboard)
        except Exception:
            logging.exception("Could not send video ID %s", video_id)

    await bot.send_message(chat_id, "👇 More Videos:", reply_markup=page_keyboard(page, total, "videos"))


@dp.callback_query(F.data == "get_videos")
async def show_videos(callback: CallbackQuery):
    await callback.answer()
    await send_video_page(callback.message.chat.id, 0)


@dp.callback_query(F.data.startswith("videos:"))
async def user_pagination(callback: CallbackQuery):
    try:
        page = int(callback.data.split(":")[1])
        if page < 0:
            raise ValueError
    except (ValueError, IndexError):
        await callback.answer("Invalid page!", show_alert=True)
        return
    await callback.answer()
    await send_video_page(callback.message.chat.id, page)


@dp.callback_query(F.data.startswith("remove:"))
async def remove_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied!", show_alert=True)
        return
    try:
        page = int(callback.data.split(":")[1])
        if page < 0:
            raise ValueError
    except (ValueError, IndexError):
        await callback.answer("Invalid page!")
        return

    total = video_count()
    rows = get_videos(page)
    if not rows:
        await callback.message.answer("❌ कोई Video मौजूद नहीं है।")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for video_id, _file_id, caption in rows:
        title = (caption or "Video").replace("\n", " ")[:22]
        builder.button(text=f"🗑 #{video_id} {title}", callback_data=f"delete:{video_id}")
    builder.adjust(1)

    await callback.message.answer(
        f"🗑 REMOVE VIDEO PANEL\n📚 Total Videos: {total}\n📄 Page: {page + 1}",
        reply_markup=builder.as_markup()
    )
    await callback.message.answer("👇 Change Page:", reply_markup=page_keyboard(page, total, "remove"))
    await callback.answer()


@dp.callback_query(F.data.startswith("delete:"))
async def delete_video_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied!", show_alert=True)
        return
    try:
        video_id = int(callback.data.split(":")[1])
        if video_id <= 0:
            raise ValueError
    except (ValueError, IndexError):
        await callback.answer("Invalid ID!")
        return

    if delete_video(video_id):
        await callback.message.answer(f"✅ Video #{video_id} Deleted Successfully!")
    else:
        await callback.message.answer("❌ Video Not Found!")
    await callback.answer()


@dp.callback_query(F.data == "all")
async def all_videos(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied!", show_alert=True)
        return
    await callback.message.answer(f"📚 Total Uploaded Videos: {video_count()}")
    await callback.answer()


@dp.callback_query(F.data == "stats")
async def statistics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied!", show_alert=True)
        return
    await callback.message.answer(
        f"📊 BOT STATISTICS\n\n👥 Total Users: {user_count()}\n🎬 Total Videos: {video_count()}\n🟢 Bot Status: Running"
    )
    await callback.answer()


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer("/start - Main Menu\n/admin - Admin Panel (Admin only)\n/help - Help")


async def main():
    print("BOT STARTING...", flush=True)
    await bot.delete_webhook(drop_pending_updates=True)
    print("BOT IS ONLINE ✅", flush=True)
    try:
        await dp.start_polling(bot)
    finally:
        db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("BOT STOPPED")
    except Exception:
        logging.exception("BOT CRASHED")
