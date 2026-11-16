import os
import json
import time
import logging
import requests

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify

# ================= CONFIG =================

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

CHANNEL = "@team_shadow_striker"
CHANNEL_LINK = "https://t.me/team_shadow_striker"

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= TELEGRAM API =================

def api(method, data=None):
    try:
        response = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=15
        )
        return response.json()
    except Exception as error:
        logger.error("Telegram API error: %s", error)
        return {"ok": False}


def send(chat_id, text, **kwargs):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    data.update(kwargs)
    return api("sendMessage", data)


def answer_callback(callback_id, text=""):
    api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })


# ================= TIME =================

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


# ================= CHANNEL VERIFICATION =================

def is_member(user_id):
    if not user_id:
        return False

    result = api("getChatMember", {
        "chat_id": CHANNEL,
        "user_id": user_id
    })

    if not result.get("ok"):
        return False

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
        "⚡ Verification ছাড়া কোনো Feature ব্যবহার করা যাবে না।",
        reply_markup=keyboard
    )


# ================= MAIN MENU =================

def main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{
                "text": "👤 My Information"
            }, {
                "text": "🔎 Select User",
                "request_users": {
                    "request_id": 1001,
                    "user_is_bot": False,
                    "max_quantity": 1,
                    "request_name": True,
                    "request_username": True,
                    "request_photo": True
                }
            }],
            [{
                "text": "👥 Group Information"
            }, {
                "text": "📢 Channel Information"
            }],
            [{
                "text": "🤖 Bot Information"
            }, {
                "text": "🧾 JSON Formatter"
            }],
            [{
                "text": "📊 Server Status"
            }],
            [{
                "text": "📖 Help Menu"
            }]
        ],
        "resize_keyboard": True
    }

    send(
        chat_id,
        "⚡ TEAM SHADOW STRIKER\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome to TG Info Bot V2!\n\n"
        "নিচের Menu থেকে একটি Feature নির্বাচন করো।\n\n"
        f"🕒 {current_time()}",
        reply_markup=keyboard
    )


# ================= USER INFORMATION =================

def my_info(chat_id, user):
    username = user.get("username")

    text = (
        "👤 MY INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 Name: {user.get('first_name', 'Unknown')}\n"
        f"📛 Username: @{username if username else 'Not set'}\n"
        f"🆔 User ID: {user.get('id')}\n"
        f"🌐 Language: {user.get('language_code', 'Unknown')}\n"
        f"🤖 Is Bot: {user.get('is_bot', False)}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )

    send(chat_id, text)


def selected_user(chat_id, shared):
    users = shared.get("users", [])

    if not users:
        send(chat_id, "❌ কোনো User Information পাওয়া যায়নি।")
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
            "🔎 SELECTED USER INFORMATION\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Name: {name}\n"
            f"📛 Username: @{username if username else 'Not shared'}\n"
            f"🆔 User ID: {uid}\n"
            f"🖼️ Profile Photo: {'Available' if photos else 'Not shared'}\n"
            f"🕒 Time: {current_time()}\n\n"
            "⚡ TEAM SHADOW STRIKER"
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


# ================= GROUP / CHANNEL INFORMATION =================

def chat_info(chat_id, username):
    username = username.strip()

    if not username.startswith("@"):
        username = "@" + username

    result = api("getChat", {
        "chat_id": username
    })

    if not result.get("ok"):
        send(
            chat_id,
            "❌ Chat Information পাওয়া যায়নি।\n\n"
            "Public Group অথবা Channel-এর সঠিক Username দাও।"
        )
        return

    chat = result.get("result", {})

    count_result = api("getChatMemberCount", {
        "chat_id": username
    })

    count = (
        count_result.get("result")
        if count_result.get("ok")
        else "Unavailable"
    )

    chat_type = chat.get("type", "Unknown")

    text = (
        "🔎 CHAT INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 Name: {chat.get('title', 'Unavailable')}\n"
        f"📛 Username: @{chat.get('username', 'Not available')}\n"
        f"🆔 Chat ID: {chat.get('id', 'Unavailable')}\n"
        f"📂 Type: {chat_type}\n"
        f"👥 Members: {count}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )

    send(chat_id, text)


# ================= BOT INFORMATION =================

def bot_info(chat_id):
    result = api("getMe")

    if not result.get("ok"):
        send(chat_id, "❌ Bot Information পাওয়া যায়নি।")
        return

    bot = result.get("result", {})

    send(
        chat_id,
        "🤖 BOT INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 Name: {bot.get('first_name')}\n"
        f"📛 Username: @{bot.get('username')}\n"
        f"🆔 Bot ID: {bot.get('id')}\n"
        f"🤖 Can Join Groups: {bot.get('can_join_groups')}\n"
        f"🔗 Inline Mode: {bot.get('supports_inline_queries')}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )


# ================= JSON FORMATTER =================

def json_formatter(chat_id, raw_text):
    raw_text = raw_text.strip()

    if raw_text.startswith("/json"):
        raw_text = raw_text[5:].strip()

    if not raw_text:
        send(
            chat_id,
            "🧾 JSON FORMATTER\n\n"
            "JSON পাঠাও এভাবে:\n\n"
            "/json {\"name\":\"Miraz\",\"age\":18}"
        )
        return

    try:
        parsed = json.loads(raw_text)

        formatted = json.dumps(
            parsed,
            indent=4,
            ensure_ascii=False
        )

        if len(formatted) > 3500:
            send(chat_id, "⚠️ JSON অনেক বড়। ছোট JSON পাঠাও।")
            return

        send(
            chat_id,
            "✅ JSON FORMATTED\n\n"
            f"<pre>{formatted}</pre>",
            parse_mode="HTML"
        )

    except json.JSONDecodeError:
        send(
            chat_id,
            "❌ Invalid JSON!\n\n"
            "সঠিক JSON Format দিয়ে আবার চেষ্টা করো।"
        )


# ================= SERVER STATUS =================

def server_status(chat_id):
    start = time.time()

    result = api("getMe")

    elapsed = round((time.time() - start) * 1000, 2)

    if result.get("ok"):
        status = "🟢 Online"
        api_status = "Connected"
    else:
        status = "🔴 API Error"
        api_status = "Disconnected"

    send(
        chat_id,
        "📊 SERVER STATUS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🖥️ Bot Status: {status}\n"
        f"🌐 Telegram API: {api_status}\n"
        f"⚡ API Response: {elapsed} ms\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )


# ================= HELP MENU =================

def help_menu(chat_id):
    send(
        chat_id,
        "📖 TG INFO BOT V2 - HELP\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👤 My Information\n"
        "নিজের Telegram Information দেখো।\n\n"
        "🔎 Select User\n"
        "Telegram-এর User Picker ব্যবহার করো।\n\n"
        "👥 Group Information\n"
        "Public Group-এর Username দিয়ে তথ্য দেখো।\n\n"
        "📢 Channel Information\n"
        "Public Channel-এর Username দিয়ে তথ্য দেখো।\n\n"
        "🤖 Bot Information\n"
        "নিজের Bot-এর Information দেখো।\n\n"
        "🧾 JSON Formatter\n"
        " /json এর পরে JSON পাঠাও।\n\n"
        "📊 Server Status\n"
        "Bot ও API-এর Status দেখো।\n\n"
        "⚠️ Telegram-এর গোপন তথ্য এই Bot দিতে পারে না।"
    )


# ================= MESSAGE HANDLER =================

def handle_message(message):
    chat_id = message.get("chat", {}).get("id")
    user = message.get("from", {})

    if not chat_id:
        return

    user_id = user.get("id")
    text = message.get("text", "").strip()

    if text.startswith("/start"):
        if not is_member(user_id):
            join_page(chat_id)
            return

        send(
            chat_id,
            f"{greeting()}, {user.get('first_name', 'বন্ধু')}!\n\n"
            "⚡ Welcome to TEAM SHADOW STRIKER!\n"
            "TG Info Bot V2-তে স্বাগতম।"
        )

        main_menu(chat_id)
        return

    # Verification is required for all bot features.
    if not is_member(user_id):
        join_page(chat_id)
        return

    if message.get("users_shared"):
        selected_user(chat_id, message["users_shared"])
        return

    if text == "👤 My Information":
        my_info(chat_id, user)

    elif text == "👥 Group Information":
        send(
            chat_id,
            "👥 GROUP INFORMATION\n\n"
            "Public Group-এর Username পাঠাও।\n\n"
            "উদাহরণ: @example_group\n\n"
            "⚠️ শুধুমাত্র Bot-এর অ্যাক্সেসযোগ্য Chat-এর তথ্য পাওয়া যাবে।"
        )

    elif text == "📢 Channel Information":
        send(
            chat_id,
            "📢 CHANNEL INFORMATION\n\n"
            "Public Channel-এর Username পাঠাও।\n\n"
            "উদাহরণ: @example_channel"
        )

    elif text == "🤖 Bot Information":
        bot_info(chat_id)

    elif text == "🧾 JSON Formatter":
        send(
            chat_id,
            "🧾 JSON FORMATTER\n\n"
            "এভাবে JSON পাঠাও:\n"
            "/json {\"name\":\"Miraz\"}"
        )

    elif text == "📊 Server Status":
        server_status(chat_id)

    elif text == "📖 Help Menu":
        help_menu(chat_id)

    elif text.startswith("/json"):
        json_formatter(chat_id, text)

    elif text.startswith("/chat"):
        parts = text.split(maxsplit=1)

        if len(parts) == 2:
            chat_info(chat_id, parts[1])
        else:
            send(chat_id, "ব্যবহার: /chat @username")

    elif text.startswith("@") and len(text) > 1:
        chat_info(chat_id, text)

    elif message.get("forward_origin"):
        forwarded_user(chat_id, message)

    else:
        send(
            chat_id,
            "⚠️ Menu থেকে একটি Feature নির্বাচন করো।\n"
            "Help পেতে /help লিখো।"
        )


# ================= FORWARD LOOKUP =================

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
        "🔎 FORWARD INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Name: {name}\n"
        f"📛 Username: @{username if username else 'Not available'}\n"
        f"🆔 User ID: {user.get('id', 'Unavailable')}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )


# ================= CALLBACK HANDLER =================

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data")

    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    if data == "verify" and chat_id:
        if is_member(user_id):
            answer_callback(callback_id, "Verification Successful!")

            send(
                chat_id,
                "✅ Verification Successful!\n\n"
                "Welcome to TEAM SHADOW STRIKER!"
            )

            main_menu(chat_id)

        else:
            answer_callback(
                callback_id,
                "আগে Channel-এ Join করো!"
            )
            join_page(chat_id)


# ================= FLASK ROUTES =================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "bot": "TEAM SHADOW STRIKER",
        "status": "Running",
        "version": "2.0"
    })


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    try:
        if "message" in update:
            handle_message(update["message"])

        elif "callback_query" in update:
            handle_callback(update["callback_query"])

    except Exception:
        logger.exception("Update processing failed")

    return "OK", 200


# ================= WEBHOOK SETUP =================

render_url = os.environ.get("RENDER_EXTERNAL_URL")

if render_url:
    result = api("setWebhook", {
        "url": render_url.rstrip("/") + "/webhook"
    })

    logger.info("Webhook setup: %s", result)


# ================= RUN =================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
