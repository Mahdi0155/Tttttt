import json
import uuid
import time
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler, ContextTypes
)
from flask import Flask
import threading

ADMIN_ID = 6387942633
DATA_FILE = "files.json"
STATES = {
    "CHOOSING_MODE": 0,
    "WAIT_FILE": 1,
    "WAIT_COVER": 2,
    "WAIT_CAPTION": 3,
    "WAIT_CAPTION_SIMPLE": 4,
}

user_sessions = {}
app = Flask(__name__)

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("ساخت لینک با مشاهده", callback_data="mode_link")],
        [InlineKeyboardButton("ساخت پست با تگ", callback_data="mode_simple")]
    ]
    await update.message.reply_text("یکی از حالت‌ها رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATES["CHOOSING_MODE"]

async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    user_sessions[uid] = {"mode": query.data}
    await query.message.reply_text("لطفاً عکس یا ویدیو رو ارسال کن.")
    return STATES["WAIT_FILE"]

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return ConversationHandler.END
    msg = update.message
    file_data = {}
    if msg.video:
        file_data["file_id"] = msg.video.file_id
        file_data["file_type"] = "video"
    elif msg.photo:
        file_data["file_id"] = msg.photo[-1].file_id
        file_data["file_type"] = "photo"
    else:
        await update.message.reply_text("فقط عکس یا ویدیو بفرست.")
        return STATES["WAIT_FILE"]
    user_sessions[uid].update(file_data)
    if user_sessions[uid]["mode"] == "mode_link" and file_data["file_type"] == "video":
        await update.message.reply_text("ویدیو دریافت شد. لطفاً کاور ارسال کن.")
        return STATES["WAIT_COVER"]
    else:
        await update.message.reply_text("لطفاً کپشن رو ارسال کن.")
        return STATES["WAIT_CAPTION"] if user_sessions[uid]["mode"] == "mode_link" else STATES["WAIT_CAPTION_SIMPLE"]

async def handle_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID or not update.message.photo:
        return ConversationHandler.END
    user_sessions[uid]["thumb_id"] = update.message.photo[-1].file_id
    await update.message.reply_text("کاور دریافت شد. لطفاً کپشن رو ارسال کن.")
    return STATES["WAIT_CAPTION"]

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return ConversationHandler.END
    caption = update.message.text
    session = user_sessions[uid]
    session["caption"] = caption
    token = str(uuid.uuid4())[:8]
    session["token"] = token
    data = load_data()
    data[token] = {
        "file_id": session["file_id"],
        "file_type": session["file_type"],
        "thumb_id": session.get("thumb_id"),
        "caption": caption,
        "timestamp": time.time()
    }
    save_data(data)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={token}"
    final_caption = f"{caption}\n\nمشاهده: [کلیک کنید]({link})\n\n🔥@hottof | تُفِ داغ"
    await context.bot.send_photo(
        chat_id=uid,
        photo=session.get("thumb_id") if session["file_type"] == "video" else session["file_id"],
        caption=final_caption,
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text("پیش‌نمایش ساخته شد. پیام رو کپی کن و توی کانال ارسال کن.")
    return ConversationHandler.END

async def handle_caption_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return ConversationHandler.END
    caption = update.message.text
    session = user_sessions[uid]
    final_caption = f"{caption}\n\n🔥@hottof | تُفِ داغ"
    if session["file_type"] == "video":
        await update.message.reply_video(video=session["file_id"], caption=final_caption)
    else:
        await update.message.reply_photo(photo=session["file_id"], caption=final_caption)
    await update.message.reply_text("پیش‌نمایش ساخته شد. پیام رو کپی کن و توی کانال ارسال کن.")
    return ConversationHandler.END

async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    msg = context.job.data.get("message")
    try:
        await msg.delete()
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("برای دریافت فایل، از لینکی که دریافت کردید وارد شوید.")
        return
    token = args[0]
    data = load_data()
    if token not in data:
        await update.message.reply_text("فایل مورد نظر یافت نشد یا منقضی شده.")
        return
    item = data[token]
    file_type = item["file_type"]
    file_id = item["file_id"]
    caption = item["caption"]
    warning = await update.message.reply_text("توجه: این فایل پس از ۲۰ ثانیه حذف خواهد شد.")
    if file_type == "photo":
        sent = await update.message.reply_photo(photo=file_id, caption=caption)
    else:
        thumb = item.get("thumb_id")
        sent = await update.message.reply_video(video=file_id, thumbnail=thumb, caption=caption)

    context.application.job_queue.run_once(delete_message, 20, data={"message": sent})
    context.application.job_queue.run_once(delete_message, 20, data={"message": warning})

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

async def main():
    TOKEN = os.environ.get("BOT_TOKEN", "توکن_تست_اینجا")  # برای تست دستی توکن رو بنویس
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("panel", panel)],
        states={
            STATES["CHOOSING_MODE"]: [CallbackQueryHandler(choose_mode)],
            STATES["WAIT_FILE"]: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_file)],
            STATES["WAIT_COVER"]: [MessageHandler(filters.PHOTO, handle_cover)],
            STATES["WAIT_CAPTION"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            STATES["WAIT_CAPTION_SIMPLE"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption_simple)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))

    threading.Thread(target=run_flask).start()
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
