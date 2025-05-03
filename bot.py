from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import sqlite3
import os
import threading
import time

BOT_TOKEN = "7413532622:AAEbrkn4dwfQpelxY1c3cb1Wzd2Tk7WzcaE"
WEBHOOK_URL = "https://tttttt-v1kw.onrender.com/webhook"
ADMIN_IDS = [5459406429, 6387942633]

app = Flask(__name__)
db_path = "videos.db"

def init_db():
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, file_id TEXT)")
        conn.commit()

init_db()

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("لطفا یک ویدیو ارسال کنید.")
        return

    file_id = video.file_id
    name = video.file_name or f"video_{int(time.time())}"

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO videos (filename, file_id) VALUES (?, ?)", (name, file_id))
        video_id = c.lastrowid
        conn.commit()

    link = f"https://t.me/{context.bot.username}?start=video{video_id}"
    await update.message.reply_text(f"لینک این ویدیو:\n{link}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].startswith("video"):
        video_id = int(args[0][5:])
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT file_id FROM videos WHERE id=?", (video_id,))
            row = c.fetchone()
            if row:
                file_id = row[0]
                msg = await update.message.reply_video(file_id)
                await update.message.reply_text("این ویدیو تا ۲۰ ثانیه دیگر حذف می‌شود، لطفا ذخیره کنید.")
                threading.Thread(target=delete_after_delay, args=(context.bot, update.effective_chat.id, msg.message_id)).start()
            else:
                await update.message.reply_text("ویدیو پیدا نشد.")
    else:
        await update.message.reply_text("سلام! برای دریافت ویدیو روی لینکی که بهت دادن کلیک کن.")

def delete_after_delay(bot, chat_id, message_id):
    time.sleep(20)
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

@app.route("/")
def index():
    return "Bot is running"

async def setup():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_handler))
    await app_bot.bot.set_webhook(WEBHOOK_URL)
    app_bot.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 10000)),
        webhook_url=WEBHOOK_URL,
        path="/webhook"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup())

