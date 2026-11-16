import os
import json
import time
import logging
import requests
import html

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
            timeout=20
        )
        return response.json()
    except Exception as error:
        logger.error("Telegram API Error: %s", error)
        return {"ok": False, "description": str(error)}


def send(chat_id, text, **kwargs):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    data.update(kwargs)
    return api("sendMessage", data)


def answer_callback(callback_id, text=""):
    return api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })


def safe(value):
    return html.escape(str(value if value is not None else "Unavailable"))


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


# ================= VERIFICATION =================

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

    return (
        status in ("member", "administrator", "creator")
        or (
            status == "restricted"
            and member.get("is_member")
        )
    )


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
            [
                {"text": "👤 My Information"},
                {
                    "text": "🔎 Select User",
                    "request_users": {
                        "request_id": 1001,
                        "user_is_bot": False,
                        "max_quantity": 1,
                        "request_name": True,
                        "request_username": True,
                        "request_photo": True
                    }
                }
            ],
            [
                {"text": "👥 Group Information"},
                {"text": "📢 Channel Information"}
            ],
            [
                {"text": "🤖 Bot Information"},
                {"text": "🧾 JSON Formatter"}
            ],
            [
                {"text": "📊 Server Status"}
            ],
            [
                {"text": "📖 Help Menu"}
            ]
        ],
        "resize_keyboard": True
    }

    send(
        chat_id,
        "⚡ TEAM SHADOW STRIKER\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome to TG Info Bot V3!\n\n"
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
        f"📝 Last Name: {user.get('last_name', 'Not set')}\n"
        f"📛 Username: @{username if username else 'Not set'}\n"
        f"🆔 User ID: {user.get('id')}\n"
        f"🌐 Language: {user.get('language_code', 'Unknown')}\n"
        f"🤖 Is Bot: {user.get('is_bot', False)}\n"
        f"📱 Premium: {user.get('is_premium', 'Unknown')}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )

    send(chat_id, text)


def selected_user(chat_id, shared):
    users = shared.get("users", [])

    if not users:
        send(chat_id, "❌ User Information পাওয়া যায়নি।")
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


# ================= CHAT SELECTION =================

def chat_selection(chat_id, mode="all"):

    buttons = []

    if mode in ("all", "group"):
        buttons.append({
            "text": "👥 Select Group",
            "request_chat": {
                "request_id": 2001,
                "chat_is_channel": False,
                "bot_is_member": True
            }
        })

    if mode in ("all", "channel"):
        buttons.append({
            "text": "📢 Select Channel",
            "request_chat": {
                "request_id": 2002,
                "chat_is_channel": True,
                "bot_is_member": True
            }
        })

    keyboard = {
        "keyboard": [
            buttons,
            [{"text": "⬅️ Main Menu"}]
        ],
        "resize_keyboard": True
    }

    send(
        chat_id,
        "🔎 CHAT SELECTION\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "তুমি কোন Chat-এর Information দেখতে চাও?\n\n"
        "👥 Group অথবা 📢 Channel নির্বাচন করো।\n\n"
        "⚠️ নির্বাচিত Chat-এ Bot যুক্ত থাকতে হবে।",
        reply_markup=keyboard
    )


# ================= CHAT ANALYZER =================

def chat_info(chat_id, selected_chat_id):

    result = api("getChat", {
        "chat_id": selected_chat_id
    })

    if not result.get("ok"):
        send(
            chat_id,
            "❌ Chat Information পাওয়া যায়নি।\n\n"
            "নিশ্চিত করো যে Bot নির্বাচিত Chat-এ যুক্ত আছে।"
        )
        return

    chat = result.get("result", {})
    actual_id = chat.get("id")

    count_result = api("getChatMemberCount", {
        "chat_id": actual_id
    })

    member_count = (
        count_result.get("result")
        if count_result.get("ok")
        else "Unavailable"
    )

    chat_type = chat.get("type", "Unknown")

    # Admin Information
    admin_result = api("getChatAdministrators", {
        "chat_id": actual_id
    })

    admins = []
    admin_status = admin_result.get("ok", False)

    if admin_status:
        admins = admin_result.get("result", [])

    total_admins = len(admins)

    bot_admins = []
    human_admins = []

    for admin in admins:
        user = admin.get("user", {})

        item = {
            "name": " ".join(filter(None, [
                user.get("first_name", ""),
                user.get("last_name", "")
            ])) or "Unknown",
            "username": user.get("username"),
            "id": user.get("id"),
            "status": admin.get("status", "Unknown"),
            "is_bot": user.get("is_bot", False)
        }

        if item["is_bot"]:
            bot_admins.append(item)
        else:
            human_admins.append(item)

    username = chat.get("username")
    description = chat.get("description", "Not available")
    invite_link = chat.get("invite_link", "Not available")

    # Basic Information
    text = (
        "🔎 ADVANCED CHAT ANALYZER\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📌 BASIC INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📝 Name: {safe(chat.get('title'))}\n"
        f"📛 Username: @{safe(username) if username else 'Not available'}\n"
        f"🆔 Chat ID: <code>{actual_id}</code>\n"
        f"📂 Type: {safe(chat_type)}\n"
        f"👥 Total Members: {member_count}\n"
        f"📝 Description: {safe(description)}\n"
        f"🔗 Invite Link: {safe(invite_link)}\n"
        f"🕒 Time: {current_time()}\n\n"
    )

    # Admin Information
    text += (
        "👑 ADMIN INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    if admin_status:
        text += (
            f"👑 Total Admins: {total_admins}\n"
            f"👤 Human Admins: {len(human_admins)}\n"
            f"🤖 Bot Admins: {len(bot_admins)}\n\n"
        )

        text += "📋 ADMIN LIST\n\n"

        for index, admin in enumerate(admins[:15], 1):
            role = (
                "Creator"
                if admin["status"] == "creator"
                else "Administrator"
            )

            text += (
                f"{index}. {safe(admin['name'])}\n"
                f"   🆔 ID: <code>{admin['id']}</code>\n"
                f"   📛 Username: @{safe(admin['username']) if admin['username'] else 'Not set'}\n"
                f"   👑 Role: {role}\n"
                f"   🤖 Bot: {'Yes' if admin['is_bot'] else 'No'}\n\n"
            )

        if total_admins > 15:
            text += f"... এবং আরও {total_admins - 15} জন Admin\n\n"

    else:
        text += (
            "⚠️ Admin List পাওয়া যায়নি।\n"
            "Bot-কে Group/Channel Admin করতে হতে পারে।\n\n"
        )

    # Bot Information
    text += (
        "🤖 BOT ADMIN ANALYZER\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    if admin_status:
        if bot_admins:
            for index, bot in enumerate(bot_admins, 1):
                text += (
                    f"{index}. {safe(bot['name'])}\n"
                    f"   🆔 ID: <code>{bot['id']}</code>\n"
                    f"   📛 Username: @{safe(bot['username']) if bot['username'] else 'Not set'}\n\n"
                )
        else:
            text += "❌ কোনো Bot Admin পাওয়া যায়নি।\n\n"
    else:
        text += "⚠️ Bot Admin List Unavailable\n\n"

    text += "⚡ TEAM SHADOW STRIKER"

    # Telegram message length protection
    if len(text) > 3900:
        text = text[:3800] + "\n\n⚠️ List shortened."

    send(
        chat_id,
        text,
        parse_mode="HTML"
    )


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
            '🧾 JSON FORMATTER\n\n'
            'উদাহরণ:\n'
            '/json {"name":"Miraz","age":18}'
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
            send(chat_id, "⚠️ JSON অনেক বড়।")
            return

        send(
            chat_id,
            "✅ JSON FORMATTED\n\n"
            f"<pre>{safe(formatted)}</pre>",
            parse_mode="HTML"
        )

    except json.JSONDecodeError:
        send(chat_id, "❌ Invalid JSON!")


# ================= SERVER STATUS =================

def server_status(chat_id):

    start = time.time()
    result = api("getMe")

    elapsed = round(
        (time.time() - start) * 1000,
        2
    )

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
        "📖 TG INFO BOT V3\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👤 My Information\n"
        "নিজের Telegram Information।\n\n"
        "🔎 Select User\n"
        "User Picker দিয়ে তথ্য।\n\n"
        "👥 Group Information\n"
        "Group অথবা Channel নির্বাচন করে Analyzer।\n\n"
        "📢 Channel Information\n"
        "Channel Information Analyzer।\n\n"
        "🤖 Bot Information\n"
        "Bot Details।\n\n"
        "🧾 JSON Formatter\n"
        "/json এর পরে JSON পাঠাও।\n\n"
        "📊 Server Status\n"
        "Bot ও API Status।\n\n"
        "⚠️ Telegram API-এর সীমাবদ্ধতার কারণে "
        "সব সদস্যের পূর্ণ তালিকা পাওয়া যায় না।"
    )


# ================= FORWARD LOOKUP =================

def forwarded_user(chat_id, message):

    origin = message.get("forward_origin", {})

    if origin.get("type") != "user":
        send(
            chat_id,
            "ℹ️ Telegram এই Forward-এর প্রেরকের "
            "পরিচয় প্রকাশ করেনি।"
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
            "TG Info Bot V3-তে স্বাগতম।"
        )

        main_menu(chat_id)
        return

    if not is_member(user_id):
        join_page(chat_id)
        return

    # User Selection
    if message.get("users_shared"):
        selected_user(chat_id, message["users_shared"])
        return

    # Group / Channel Selection
    if message.get("chat_shared"):
        shared = message["chat_shared"]
        selected_chat_id = shared.get("chat_id")

        if selected_chat_id:
            chat_info(chat_id, selected_chat_id)
        else:
            send(chat_id, "❌ Chat ID পাওয়া যায়নি।")

        return

    # Commands
    if text == "/help":
        help_menu(chat_id)
        return

    if text == "/menu":
        main_menu(chat_id)
        return

    if text == "⬅️ Main Menu":
        main_menu(chat_id)
        return

    # Features
    if text == "👤 My Information":
        my_info(chat_id, user)

    elif text == "👥 Group Information":
        chat_selection(chat_id, "all")

    elif text == "📢 Channel Information":
        chat_selection(chat_id, "channel")

    elif text == "🤖 Bot Information":
        bot_info(chat_id)

    elif text == "🧾 JSON Formatter":
        send(
            chat_id,
            '🧾 JSON FORMATTER\n\n'
            'উদাহরণ:\n'
            '/json {"name":"Miraz"}'
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


# ================= CALLBACK HANDLER =================

def handle_callback(callback):

    callback_id = callback.get("id")
    data = callback.get("data")

    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    if data == "verify" and chat_id:

        if is_member(user_id):

            answer_callback(
                callback_id,
                "Verification Successful!"
            )

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
        "version": "3.0"
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
        "url": render_url.rstrip("/") + "/webhook",
        "allowed_updates": [
            "message",
            "callback_query"
        ]
    })

    logger.info("Webhook setup: %s", result)


# ================= RUN =================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
