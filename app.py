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
        r = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=20
        )
        return r.json()
    except Exception:
        return {}

def send(chat_id, text, **kwargs):
    data = {"chat_id": chat_id, "text": text}
    data.update(kwargs)
    return api("sendMessage", data)

def current_time():
    return datetime.now(
        ZoneInfo("Asia/Dhaka")
    ).strftime("%d-%m-%Y %I:%M:%S %p")

def greeting():
    hour = datetime.now(ZoneInfo("Asia/Dhaka")).hour
    if 5 <= hour < 12:
        return "শুভ সকাল"
    elif 12 <= hour < 17:
        return "শুভ দুপুর"
    elif 17 <= hour < 20:
        return "শুভ সন্ধ্যা"
    return "শুভ রাত্রি"

def is_member(user_id):
    result = api("getChatMember", {
        "chat_id": CHANNEL,
        "user_id": user_id
    })

    member = result.get("result", {})
    status = member.get("status")

    if status in ("member", "administrator", "creator"):
        return True

    if status == "restricted" and member.get("is_member"):
        return True

    return False

def join_page(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{
                "text": "📢 Join Channel",
                "url": CHANNEL_LINK
            }],
            [{
                "text": "✅ Verify",
                "callback_data": "verify"
            }]
        ]
    }

    send(
        chat_id,
        "🔐 TEAM SHADOW STRIKER\n\n"
        "বট ব্যবহার করতে প্রথমে আমাদের Channel-এ Join করো।\n\n"
        "1️⃣ Join Channel চাপ দাও\n"
        "2️⃣ Channel-এ Join করো\n"
        "3️⃣ Verify চাপ দাও\n\n"
        "⚡ তারপর বটের সব ফিচার ব্যবহার করতে পারবে।",
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
            [
                {"text": "📩 Forward Message"},
                {"text": "ℹ️ My Information"}
            ],
            [{"text": "📖 How To Use"}]
        ],
        "resize_keyboard": True
    }

    send(
        chat_id,
        "⚡ TEAM SHADOW STRIKER\n\n"
        "Welcome to Main Menu!\n\n"
        "নিচের অপশন থেকে বেছে নাও।",
        reply_markup=keyboard
    )

def my_info(chat_id, user):
    username = user.get("username")

    send(
        chat_id,
        "👤 MY INFORMATION\n\n"
        f"Name: {user.get('first_name', 'Unknown')}\n"
        f"Username: @{username if username else 'Not set'}\n"
        f"Chat ID: {user.get('id')}\n"
        f"🕒 Current Time: {current_time()}\n\n"
        "⚡ Bot From Team Shadow Striker"
    )

def selected_user(chat_id, shared):
    users = shared.get("users", [])

    for user in users:
        uid = user.get("user_id", "Unavailable")

        name = " ".join(filter(None, [
            user.get("first_name", ""),
            user.get("last_name", "")
        ])) or "Unavailable"

        username = user.get("username")
        photos = user.get("photo", [])

        text = (
            "🔎 SELECTED USER INFORMATION\n\n"
            f"👤 Name: {name}\n"
            f"📛 Username: @{username if username else 'Not set'}\n"
            f"🆔 Chat ID: {uid}\n"
            f"🖼️ Profile Photo: {'Available' if photos else 'Not shared'}\n"
            f"🕒 Current Time: {current_time()}\n\n"
            "⚡ Bot From Team Shadow Striker"
        )

        if photos:
            largest = max(
                photos,
                key=lambda p: p.get("file_size", 0)
            )
            api("sendPhoto", {
                "chat_id": chat_id,
                "photo": largest["file_id"],
                "caption": text
            })
        else:
            send(chat_id, text)

def forwarded_user(chat_id, message):
    origin = message.get("forward_origin", {})

    if origin.get("type") != "user":
        send(
            chat_id,
            "ℹ️ Telegram এই Forward-এর প্রেরকের পরিচয় প্রকাশ করেনি।"
        )
        return

    user = origin.get("sender_user", {})
    username = user.get("username")

    name = " ".join(filter(None, [
        user.get("first_name", ""),
        user.get("last_name", "")
    ])) or "Unavailable"

    send(
        chat_id,
        "🔎 FORWARD LOOKUP RESULT\n\n"
        f"👤 Name: {name}\n"
        f"📛 Username: @{username if username else 'Not set'}\n"
        f"🆔 Chat ID: {user.get('id', 'Unavailable')}\n"
        f"🕒 Current Time: {current_time()}\n\n"
        "⚡ Bot From Team Shadow Striker"
    )

def handle_message(message):
    chat_id = message.get("chat", {}).get("id")
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
                "নিচের Menu থেকে বেছে নাও।"
            )
            main_menu(chat_id)
        else:
            join_page(chat_id)
        return

    # সব ফিচার ব্যবহারের আগে Channel Membership যাচাই
    if not is_member(user.get("id")):
        join_page(chat_id)
        return

    if text == "ℹ️ My Information":
        my_info(chat_id, user)

    elif text == "📩 Forward Message":
        send(
            chat_id,
            "📩 যে মেসেজটি দেখতে চাও সেটি এই বটে Forward করো।"
        )

    elif text == "📖 How To Use":
        send(
            chat_id,
            "📖 HOW TO USE\n\n"
            "1. Select User দিয়ে Telegram User Picker থেকে User বেছে নাও।\n"
            "2. Forward Message দিয়ে মেসেজ Forward করো।\n"
            "3. My Information দিয়ে নিজের তথ্য দেখো।\n\n"
            "⚠️ গোপন ফোন নম্বর বা Last Seen পাওয়া যায় না।"
        )

    elif message.get("users_shared"):
        selected_user(chat_id, message["users_shared"])

    elif message.get("forward_origin"):
        forwarded_user(chat_id, message)

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    api("answerCallbackQuery", {
        "callback_query_id": callback_id
    })

    if data == "verify" and chat_id:
        if is_member(user_id):
            send(chat_id, "✅ Verification Successful!\n\nWelcome!")
            main_menu(chat_id)
        else:
            join_page(chat_id)

@app.route("/", methods=["GET"])
def home():
    return "Team Shadow Striker Bot Running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    if "message" in update:
        handle_message(update["message"])

    elif "callback_query" in update:
        handle_callback(update["callback_query"])

    return "OK", 200

# Render Webhook Auto Setup
render_url = os.environ.get("RENDER_EXTERNAL_URL")

if render_url:
    api("setWebhook", {
        "url": render_url.rstrip("/") + "/webhook"
    })
