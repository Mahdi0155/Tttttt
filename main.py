# main.py

from flask import Flask, request
import requests
import threading
import time
from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_TAG, PING_INTERVAL
from database import init_db, add_video_id, get_video_id
from utils import gen_code

app = Flask(__name__)
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
users = {}
pinging = True

def send(method, data):
    return requests.post(f"{URL}/{method}", json=data).json()

def delete(chat_id, message_id):
    send("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def ping():
    while pinging:
        try:
            requests.get(WEBHOOK_URL)
        except:
            pass
        time.sleep(PING_INTERVAL)

threading.Thread(target=ping, daemon=True).start()
init_db()

@app.route("/")
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        state = users.get(uid, {})

        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "سلام خوش اومدی!"})

        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {"keyboard": [[{"text": "سوپر"}], [{"text": "پست"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "پنل مدیریت", "reply_markup": kb})

        elif text == "سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_video"}
            send("sendMessage", {"chat_id": cid, "text": "ویدیو رو بفرست"})

        elif text == "پست" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_forward"}
            send("sendMessage", {"chat_id": cid, "text": "پیام فورواردشده رو بفرست"})

        elif state.get("step") == "awaiting_video" and "video" in msg:
            users[uid]["step"] = "awaiting_caption"
            users[uid]["file_id"] = msg["video"]["file_id"]
            send("sendMessage", {"chat_id": cid, "text": "کپشن رو بنویس"})

        elif state.get("step") == "awaiting_caption":
            users[uid]["step"] = "awaiting_cover"
            users[uid]["caption"] = text
            send("sendMessage", {"chat_id": cid, "text": "حالا کاور رو بفرست (کاور اجباریه)"})

        elif state.get("step") == "awaiting_cover" and "photo" in msg:
            file_id = users[uid]["file_id"]
            caption = users[uid]["caption"]
            cover_id = msg["photo"][-1]["file_id"]
            code = gen_code()
            add_video_id(code, file_id)
            text = f"<a href='https://t.me/{BOT_TOKEN.split(':')[0]}?start={code}'>مشاهده</a>\n\n{CHANNEL_TAG}"
            send("sendPhoto", {
                "chat_id": cid,
                "photo": cover_id,
                "caption": caption + "\n\n" + text,
                "parse_mode": "HTML"
            })
            users.pop(uid)
            send("sendMessage", {
                "chat_id": cid,
                "text": "پیش‌نمایش ساخته شد. می‌تونی فورواردش کنی.",
                "reply_markup": {"keyboard": [[{"text": "سوپر"}], [{"text": "پست"}]], "resize_keyboard": True}
            })

        elif state.get("step") == "awaiting_forward" and ("video" in msg or "photo" in msg) and "forward_from" in msg:
            users[uid]["step"] = "awaiting_post_caption"
            users[uid]["post_msg"] = msg
            send("sendMessage", {"chat_id": cid, "text": "کپشن پست رو بفرست"})

        elif state.get("step") == "awaiting_post_caption":
            post_msg = users[uid]["post_msg"]
            caption = text + "\n\n" + CHANNEL_TAG
            if "video" in post_msg:
                fid = post_msg["video"]["file_id"]
                send("sendVideo", {"chat_id": cid, "video": fid, "caption": caption})
            else:
                fid = post_msg["photo"][-1]["file_id"]
                send("sendPhoto", {"chat_id": cid, "photo": fid, "caption": caption})
            users[uid]["step"] = "awaiting_forward"
            send("sendMessage", {"chat_id": cid, "text": "پست بعدی رو بفرست"})

    elif "message" in update and "text" in update["message"] and update["message"]["text"].startswith("/start "):
        msg = update["message"]
        cid = msg["chat"]["id"]
        code = msg["text"].split("/start ")[1]
        file_id = get_video_id(code)
        if file_id:
            sent = send("sendVideo", {"chat_id": cid, "video": file_id})
            if "result" in sent:
                mid = sent["result"]["message_id"]
                send("sendMessage", {"chat_id": cid, "text": "این ویدیو بعد از ۲۰ ثانیه حذف می‌شود."})
                threading.Timer(20, delete, args=(cid, mid)).start()
    return "ok"
