import json
import uuid
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.parsemode import ParseMode
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
)
from flask import Flask
import threading
import os

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

def panel(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("ساخت لینک با مشاهده", callback_data="mode_link")],
        [InlineKeyboardButton("ساخت پست با تگ", callback_data="mode_simple")]
    ]
    update.message.reply_text("یکی از حالت‌ها رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATES["CHOOSING_MODE"]

def choose_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    query.answer()
    user_sessions[uid] = {"mode": query.data}
    query.message.reply_text("لطفاً عکس یا ویدیو رو ارسال کن.")
    return STATES["WAIT_FILE"]

def handle_file(update: Update, context: CallbackContext):
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
        update.message.reply_text("فقط عکس یا ویدیو بفرست.")
        return STATES["WAIT_FILE"]
    user_sessions[uid].update(file_data)
    if user_sessions[uid]["mode"] == "mode_link" and file_data["file_type"] == "video":
        update.message.reply_text("ویدیو دریافت شد. لطفاً کاور ارسال کن.")
        return STATES["WAIT_COVER"]
    else:
        update.message.reply_text("لطفاً کپشن رو ارسال کن.")
        if user_sessions[uid]["mode"] == "mode_link":
            return STATES["WAIT_CAPTION"]
        else:
            return STATES["WAIT_CAPTION_SIMPLE"]

def handle_cover(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid != ADMIN_ID or not update.message.photo:
        return ConversationHandler.END
    user_sessions[uid]["thumb_id"] = update.message.photo[-1].file_id
    update.message.reply_text("کاور دریافت شد. لطفاً کپشن رو ارسال کن.")
    return STATES["WAIT_CAPTION"]

def handle_caption(update: Update, context: CallbackContext):
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
    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start={token}"
    final_caption = f"{caption}\n\nمشاهده: [کلیک کنید]({link})\n\n🔥@hottof | تُفِ داغ"
    context.bot.send_photo(
        chat_id=uid,
        photo=session.get("thumb_id") if session["file_type"] == "video" else session["file_id"],
        caption=final_caption,
        parse_mode=ParseMode.MARKDOWN
    )
    update.message.reply_text("پیش‌نمایش ساخته شد. پیام رو کپی کن و توی کانال ارسال کن.")
    return ConversationHandler.END

def handle_caption_simple(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return ConversationHandler.END
    caption = update.message.text
    session = user_sessions[uid]
    final_caption = f"{caption}\n\n🔥@hottof | تُفِ داغ"
    if session["file_type"] == "video":
        update.message.reply_video(video=session["file_id"], caption=final_caption)
    else:
        update.message.reply_photo(photo=session["file_id"], caption=final_caption)
    update.message.reply_text("پیش‌نمایش ساخته شد. پیام رو کپی کن و توی کانال ارسال کن.")
    return ConversationHandler.END

def start(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("برای دریافت فایل، از لینکی که دریافت کردید وارد شوید.")
        return
    token = args[0]
    data = load_data()
    if token not in data:
        update.message.reply_text("فایل مورد نظر یافت نشد یا منقضی شده.")
        return
    item = data[token]
    file_type = item["file_type"]
    file_id = item["file_id"]
    caption = item["caption"]
    warning = update.message.reply_text("توجه: این فایل پس از ۲۰ ثانیه حذف خواهد شد.")
    if file_type == "photo":
        sent = update.message.reply_photo(photo=file_id, caption=caption)
    else:
        thumb = item.get("thumb_id")
        sent = update.message.reply_video(video=file_id, thumb=thumb, caption=caption)
    context.job_queue.run_once(lambda c: sent.delete(), 20)
    context.job_queue.run_once(lambda c: warning.delete(), 20)

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

@app.route("/")
def home():
    return "OK"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def main():
    TOKEN = "7413532622:AAGUIJIR9fYe3SSi7CMqTQ5biBs63Bgfxn4"
    PORT = int(os.environ.get("PORT", 5000))
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.set_webhook(url=f"https://tttttt-v1kw.onrender.com/{TOKEN}")
    conv = ConversationHandler(
        entry_points=[CommandHandler("panel", panel)],
        states={
            STATES["CHOOSING_MODE"]: [CallbackQueryHandler(choose_mode)],
            STATES["WAIT_FILE"]: [MessageHandler(Filters.photo | Filters.video, handle_file)],
            STATES["WAIT_COVER"]: [MessageHandler(Filters.photo, handle_cover)],
            STATES["WAIT_CAPTION"]: [MessageHandler(Filters.text, handle_caption)],
            STATES["WAIT_CAPTION_SIMPLE"]: [MessageHandler(Filters.text, handle_caption_simple)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    dp.add_handler(conv)
    dp.add_handler(CommandHandler("start", start))
    threading.Thread(target=run_flask).start()  # Start Flask server in a separate thread
    updater.idle()

if __name__ == "__main__":
    main()
