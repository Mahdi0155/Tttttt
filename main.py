from flask import Flask, request
import requests
import threading
import time
from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_TAG, PING_INTERVAL
from database import save_file, get_file
from utils import gen_code

app = Flask(__name__)
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
users = {}
pinging = True

def send(method, data):
    response = requests.post(f"{URL}/{method}", json=data).json()
    print(f"Response from {method}: {response}")
    return response

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

@app.route("/")
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    # ابتدا بررسی کنیم اگر پیام start با کد بود
    if "message" in update and "text" in update["message"] and update["message"]["text"].startswith("/start "):
        msg = update["message"]
        cid = msg["chat"]["id"]
        code = msg["text"].split("/start ")[1]
        print(f"Received /start with code: {code}")
        file_id = get_file(code)
        print(f"File_id retrieved from database: {file_id}")
        if file_id:
            sent = send("sendVideo", {"chat_id": cid, "video": file_id})
            print(f"Sent video response: {sent}")
            if "result" in sent:
                mid = sent["result"]["message_id"]
                send("sendMessage", {"chat_id": cid, "text": "⚠️این محتوا تا ۲۰ ثانیه دیگر پاک میشود "})
                threading.Timer(20, delete, args=(cid, mid)).start()
        return "ok"

    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        state = users.get(uid, {})

        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "سلام خوش اومدی عزیزم واسه دریافت فایل مد نظرت از کانال @hottof روی دکمه مشاهده بزن ♥️"})

        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "🔞سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_video"}
            send("sendMessage", {"chat_id": cid, "text": "ای جان یه سوپر ناب برام بفرست 🍌"})

        elif text == "🖼پست" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_forward"}
            send("sendMessage", {"chat_id": cid, "text": "محتوا رو برا فوروارد کن یادت نره تگ بزنی روش ✅️"})

        elif state.get("step") == "awaiting_video" and "video" in msg:
            users[uid]["step"] = "awaiting_caption"
            users[uid]["file_id"] = msg["video"]["file_id"]
            print(f"Received video file_id: {users[uid]['file_id']}")
            send("sendMessage", {"chat_id": cid, "text": "منتظر کپشن خوشکلت هستم 💫"})

        elif state.get("step") == "awaiting_caption":
            users[uid]["step"] = "awaiting_cover"
            users[uid]["caption"] = text
            send("sendMessage", {"chat_id": cid, "text": "یه عکس برای پیش نمایش بهم بده 📸"})

        elif state.get("step") == "awaiting_cover" and "photo" in msg:
            file_id = users[uid]["file_id"]
            caption = users[uid]["caption"]
            cover_id = msg["photo"][-1]["file_id"]
            code = gen_code()
            print(f"Saving file with code: {code} and file_id: {file_id}")
            save_file(file_id, code)
            text = f"<a href='https://t.me/HotTofBot?start={code}'>مشاهده</a>\n\n{CHANNEL_TAG}"
            send("sendPhoto", {
                "chat_id": cid,
                "photo": cover_id,
                "caption": caption + "\n\n" + text,
                "parse_mode": "HTML"
            })
            users.pop(uid)
            send("sendMessage", {
                "chat_id": cid,
                "text": "درخواست شما تایید شد✅️",
                "reply_markup": {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}]], "resize_keyboard": True}
            })

        elif state.get("step") == "awaiting_forward" and ("video" in msg or "photo" in msg):
    users[uid]["step"] = "awaiting_post_caption"
    users[uid]["post_msg"] = msg
    send("sendMessage", {"chat_id": cid, "text": "یه کپشن خوشکل بزن حال کنم 😁"})

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
            send("sendMessage", {"chat_id": cid, "text": "بفرما اینم درخواستت ✅️ آماده ام پست بعدی رو بفرستی ارباب🔥"})

    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
