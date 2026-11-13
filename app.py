import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = "@team_shadow_striker"
CHANNEL_LINK = "https://t.me/team_shadow_striker"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def api(method, data=None):
    try:
        r = requests.post(f"{API}/{method}", json=data or {}, timeout=20)
        return r.json()
    except Exception:
        return {}

def send(chat_id, text, **kwargs):
    data = {"chat_id": chat_id, "text": text}
    data.update(kwargs)
    return api("sendMessage", data)

def current_time():
    return datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%d-%m-%Y  %I:%M:%S %p")

def greeting():
    hour = datetime.now(ZoneInfo("Asia/Dhaka")).hour
    if 5 <= hour < 12:
        return "শুভ সকাল"
    if 12 <= hour < 17:
        return "শুভ দুপুর"
    if 17 <= hour < 20:
        return "শুভ সন্ধ্যা"
    return "শুভ রাত্রি"

def is_member(user_id):
    result = api("getChatMember", {
        "chat_id": CHANNEL,
        "user_id": user_id
    })
    status = result.get("result", {}).get("status")
    return status in ("member", "administrator", "creator")

def join_page(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📢 Join Channel", "url": CHANNEL_LINK}],
            [{"text": "✅ Verify", "callback_data": "verify"}]
        ]
    }
    send(
        chat_id,
        "🔐 বট ব্যবহার করতে আমাদের Channel-এ Join করো।\n\nJoin করার পর Verify চাপ দাও।",
        reply_markup=keyboard
    )

def main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{
                "text": "👤 Select User",
                "request_users": {
                    "request_id": 1001,
                    "user_is_bot": False,
                    "max_quantity": 1,
                    "request_name": True,
                    "request_username": True,
                    "request_photo": True
                }
            }],
            [{"text": "📩 Forward Message"}, {"text": "ℹ️ My Information"}],
            [{"text": "📖 How To Use"}]
        ],
        "resize_keyboard": True
    }
    send(
        chat_id,
        "⚡ Team Shadow Striker Main Menu\n\nনিচের অপশন থেকে বেছে নাও।",
        reply_markup=keyboard
    )

def my_info(chat_id, user):
    name = user.get("first_name", "Unknown")
    username = user.get("username")
    text = (
        f"👤 Name: {name}\n"
        f"📛 Username: @{username if username else 'Not set'}\n"
        f"🆔 Chat ID: {user.get('id')}\n"
        f"🕒 Current Time: {current_time()}\n\n"
        "⚡ Bot From Team Shadow Striker"
    )
    send(chat_id, text)

def selected_user(chat_id, shared):
    users = shared.get("users", [])
    if not users:
        send(chat_id, "কোনো User পাওয়া যায়নি।")
        return

    for user in users:
        uid = user.get("user_id", "Unavailable")
        name = " ".join(filter(None, [
            user.get("first_name", ""),
            user.get("last_name", "")
        ])) or "Unavailable"
        username = user.get("username")
        photos = user.get("photo", [])

        text = (
            "🔎 Selected User Information\n\n"
            f"👤 Name: {name}\n"
            f"📛 Username: @{username if username else 'Not set'}\n"
            f"🆔 Chat ID: {uid}\n"
            f"🖼️ Shared Profile Photo: {'Available' if photos else 'Not shared'}\n"
            f"🕒 Current Time: {current_time()}\n\n"
            "ℹ️ তথ্যগুলো Telegram User Picker থেকে পাওয়া।\n"
            "⚡ Bot From Team Shadow Striker"
        )

        if photos:
            largest = max(photos, key=lambda p: p.get("file_size", 0))
            api("sendPhoto", {
                "chat_id": chat_id,
                "photo": largest.get("file_id"),
                "caption": text
            })
        else:
            send(chat_id, text)

def forwarded_user(chat_id, message):
    origin = message.get("forward_origin", {})
    if origin.get("type") != "user":
        send(
            chat_id,
            "এই Forward করা মেসেজে Telegram প্রেরকের পরিচয় প্রকাশ করেনি। তাই User ID দেখানো যাচ্ছে না।"
        )
        return

    user = origin.get("sender_user", {})
    name = " ".join(filter(None, [
        user.get("first_name", ""),
        user.get("last_name", "")
    ])) or "Unavailable"
    username = user.get("username")

    text = (
        "🔎 Forward Lookup Result\n\n"
        f"👤 Name: {name}\n"
        f"📛 Username: @{username if username else 'Not set'}\n"
        f"🆔 Chat ID: {user.get('id', 'Unavailable')}\n"
        "🖼️ Profile Photo: Not provided in this forward\n"
        f"🕒 Current Time: {current_time()}\n\n"
        "ℹ️ শুধু Forward-এর সঙ্গে Telegram যে তথ্য দিয়েছে সেটিই দেখানো হয়েছে.\n"
        "⚡ Bot From Team Shadow Striker"
    )
    send(chat_id, text)

def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    user = message.get("from", {})

    if not chat_id:
        return

    text = message.get("text", "")

    if text.startswith("/start"):
        if is_member(user.get("id")):
            send(
                chat_id,
                f"{greeting()}, {user.get('first_name', 'বন্ধু')}!\n\n"
                "⚡ Welcome to Team Shadow Striker\n\n"
                f"👤 Name: {user.get('first_name', 'Unknown')}\n"
                f"📛 Username: @{user.get('username', 'Not set')}\n"
                f"🆔 Chat ID: {user.get('id')}\n"
                f"🕒 Current Time: {current_time()}\n\n"
                "নিচের Menu ব্যবহার করো।"
            )
            main_menu(chat_id)
        else:
            join_page(chat_id)
        return

    if text == "ℹ️ My Information":
        my_info(chat_id, user)
        return

    if text == "📩 Forward Message":
        send(
            chat_id,
            "যে মেসেজটি দেখতে চাও সেটি এই বটে Forward করো।\n\n"
            "Telegram প্রেরকের পরিচয় প্রকাশ করলে শুধু সেই তথ্য দেখানো হবে।"
        )
        return

    if text == "📖 How To Use":
        send(
            chat_id,
            "📖 How To Use\n\n"
            "1. Select User চাপ দিয়ে Telegram থেকে একজন User বেছে নাও।\n"
            "2. Forward Message চাপ দিয়ে একটি মেসেজ Forward করো।\n"
            "3. My Information দিয়ে নিজের তথ্য দেখো।\n\n"
            "⚠️ গোপন ফোন নম্বর, Last Seen বা ব্যক্তিগত তথ্য এই বট দিতে পারে না।"
        )
        return

    if message.get("users_shared"):
        selected_user(chat_id, message["users_shared"])
        return

    if message.get("forward_origin"):
        forwarded_user(chat_id, message)
        return

def handle_callback(callback):
    data = callback.get("data")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    api("answerCallbackQuery", {
        "callback_query_id": callback.get("id")
    })

    if data == "verify" and chat_id:
        if is_member(user_id):
            send(chat_id, "✅ Verification Successful!")
            main_menu(chat_id)
        else:
            join_page(chat_id)

@app.route("/", methods=["GET"])
def home():
    return "Team Shadow Striker Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])

    return "OK", 200

if __name__ == "__main__":
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        api("setWebhook", {
            "url": render_url.rstrip("/") + "/webhook"
        })

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
            )
