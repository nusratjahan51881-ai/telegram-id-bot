import os
import json
import time
import logging
import html
import requests

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify

# ==================================================
# TEAM SHADOW STRIKER - TG INFO BOT V4
# ==================================================

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

CHANNEL = "@team_shadow_striker"
CHANNEL_LINK = "https://t.me/team_shadow_striker"

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================================================
# TELEGRAM API
# ==================================================

def api(method, data=None):
    try:
        response = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=20
        )
        return response.json()
    except Exception as error:
        logger.error("API Error: %s", error)
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
    if value is None or value == "":
        value = "Unavailable"
    return html.escape(str(value))


def send_long(chat_id, text, parse_mode="HTML"):
    """Send long reports in multiple messages."""
    limit = 3800

    while text:
        if len(text) <= limit:
            part = text
            text = ""
        else:
            split_at = text.rfind("\n", 0, limit)

            if split_at < 100:
                split_at = limit

            part = text[:split_at]
            text = text[split_at:].lstrip("\n")

        result = send(
            chat_id,
            part,
            parse_mode=parse_mode
        )

        if not result.get("ok"):
            logger.error("Report sending failed: %s", result)
            break


# ==================================================
# TIME
# ==================================================

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


# ==================================================
# CHANNEL VERIFICATION
# ==================================================

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
            and member.get("is_member", False)
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
        "🔐 TEAM SHADOW STRIKER\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "বট ব্যবহার করতে প্রথমে আমাদের Channel-এ Join করো।\n\n"
        "1️⃣ Join Channel চাপ দাও\n"
        "2️⃣ Channel-এ Join করো\n"
        "3️⃣ Verify চাপ দাও\n\n"
        "⚡ Verification ছাড়া কোনো Feature ব্যবহার করা যাবে না।",
        reply_markup=keyboard
    )


# ==================================================
# MAIN MENU
# ==================================================

def main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [
                {
                    "text": "👤 User Information",
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
        "Welcome to TG Info Bot V4!\n\n"
        "নিচের Menu থেকে একটি Feature নির্বাচন করো।\n\n"
        f"🕒 {current_time()}",
        reply_markup=keyboard
    )


# ==================================================
# USER INFORMATION
# ==================================================

def user_information(chat_id, shared):
    users = shared.get("users", [])

    if not users:
        send(chat_id, "❌ User Information পাওয়া যায়নি।")
        return

    for user in users:
        user_id = user.get("user_id")

        name = " ".join(filter(None, [
            user.get("first_name", ""),
            user.get("last_name", "")
        ])) or "Unavailable"

        username = user.get("username")
        shared_photos = user.get("photo", [])

        # Get profile photos through Telegram API
        photo_result = api("getUserProfilePhotos", {
            "user_id": user_id,
            "limit": 5
        })

        photos = []

        if photo_result.get("ok"):
            photos = photo_result.get(
                "result", {}
            ).get("photos", [])

        text = (
            "👤 USER INFORMATION V4\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 Full Name: {safe(name)}\n"
            f"📛 Username: @{safe(username) if username else 'Not set'}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"🌐 Source: Telegram User Picker\n"
            f"🖼️ Shared Photo: {'Available' if shared_photos else 'Not shared'}\n"
            f"📸 Profile Photo Count: "
            f"{photo_result.get('result', {}).get('total_count', 0) if photo_result.get('ok') else 'Unavailable'}\n"
            f"🕒 Time: {current_time()}\n\n"
            "⚠️ Personal Story access is not available through the Bot API.\n\n"
            "⚡ TEAM SHADOW STRIKER"
        )

        send(
            chat_id,
            text,
            parse_mode="HTML"
        )

        # Send latest available profile photo
        if photos and photos[0]:
            largest = photos[0][-1]

            api("sendPhoto", {
                "chat_id": chat_id,
                "photo": largest["file_id"],
                "caption": "🖼️ Selected User Profile Photo"
            })

        elif shared_photos:
            largest = max(
                shared_photos,
                key=lambda p: p.get("file_size", 0)
            )

            if largest.get("file_id"):
                api("sendPhoto", {
                    "chat_id": chat_id,
                    "photo": largest["file_id"],
                    "caption": "🖼️ Shared User Profile Photo"
                })


# ==================================================
# GROUP / CHANNEL SELECTOR
# ==================================================

def chat_selection(chat_id, mode):
    buttons = []

    if mode in ("group", "all"):
        buttons.append({
            "text": "👥 Select Group",
            "request_chat": {
                "request_id": 2001,
                "chat_is_channel": False,
                "bot_is_member": True,
                "request_title": True,
                "request_username": True,
                "request_photo": True
            }
        })

    if mode in ("channel", "all"):
        buttons.append({
            "text": "📢 Select Channel",
            "request_chat": {
                "request_id": 2002,
                "chat_is_channel": True,
                "bot_is_member": True,
                "request_title": True,
                "request_username": True,
                "request_photo": True
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
        "🔎 ADVANCED CHAT SELECTOR\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "তুমি কোন Chat-এর Information দেখতে চাও?\n\n"
        "👥 Group অথবা 📢 Channel নির্বাচন করো।\n\n"
        "⚠️ নির্বাচিত Chat-এ Bot যুক্ত থাকতে হবে।",
        reply_markup=keyboard
    )


# ==================================================
# CHAT PROFILE PHOTO
# ==================================================

def send_chat_photo(chat_id, chat):
    photo = chat.get("photo", {})

    file_id = photo.get("big_file_id")

    if not file_id:
        file_id = photo.get("small_file_id")

    if not file_id:
        send(chat_id, "🖼️ Profile Picture পাওয়া যায়নি।")
        return

    result = api("sendPhoto", {
        "chat_id": chat_id,
        "photo": file_id,
        "caption": "🖼️ Group / Channel Profile Picture"
    })

    if not result.get("ok"):
        send(chat_id, "⚠️ Profile Picture পাঠানো যায়নি।")


# ==================================================
# ADVANCED GROUP / CHANNEL ANALYZER
# ==================================================

def chat_info(chat_id, selected_chat_id):

    result = api("getChat", {
        "chat_id": selected_chat_id
    })

    if not result.get("ok"):
        send(
            chat_id,
            "❌ Chat Information পাওয়া যায়নি।\n\n"
            "Bot নির্বাচিত Chat-এ যুক্ত আছে কিনা দেখো।"
        )
        return

    chat = result.get("result", {})
    actual_id = chat.get("id")

    # Member Count
    count_result = api("getChatMemberCount", {
        "chat_id": actual_id
    })

    member_count = (
        count_result.get("result")
        if count_result.get("ok")
        else "Unavailable"
    )

    chat_type = chat.get("type", "Unknown")
    username = chat.get("username")

    if username:
        full_link = f"https://t.me/{username}"
    else:
        full_link = chat.get("invite_link", "Not available")

    # Admin list
    admin_result = api("getChatAdministrators", {
        "chat_id": actual_id
    })

    admins = (
        admin_result.get("result", [])
        if admin_result.get("ok")
        else []
    )

    admin_available = admin_result.get("ok", False)

    human_admins = []
    bot_admins = []
    creator = None

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
            "is_bot": user.get("is_bot", False),
            "custom_title": admin.get("custom_title")
        }

        if item["status"] == "creator":
            creator = item

        if item["is_bot"]:
            bot_admins.append(item)
        else:
            human_admins.append(item)

    # Basic information
    text = (
        "🔎 ADVANCED CHAT ANALYZER V4\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📌 BASIC INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📝 Name: {safe(chat.get('title'))}\n"
        f"📛 Username: @{safe(username) if username else 'Not available'}\n"
        f"🔗 Full Link: {safe(full_link)}\n"
        f"🆔 Chat ID: <code>{actual_id}</code>\n"
        f"📂 Type: {safe(chat_type)}\n"
        f"👥 Total Members: {member_count}\n"
        f"📝 Description: {safe(chat.get('description'))}\n"
        f"🕒 Time: {current_time()}\n\n"
    )

    # Creator
    text += (
        "👑 CREATOR INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    if creator:
        text += (
            f"👤 Name: {safe(creator['name'])}\n"
            f"📛 Username: @{safe(creator['username']) if creator['username'] else 'Not set'}\n"
            f"🆔 ID: <code>{creator['id']}</code>\n\n"
        )
    elif admin_available:
        text += "Creator Information Unavailable\n\n"
    else:
        text += "Admin permission unavailable\n\n"

    # Admin statistics
    text += (
        "👑 ADMIN STATISTICS\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    if admin_available:
        text += (
            f"👑 Total Admins: {len(admins)}\n"
            f"👤 Human Admins: {len(human_admins)}\n"
            f"🤖 Bot Admins: {len(bot_admins)}\n\n"
        )

        text += "📋 ADMIN LIST\n\n"

        for index, admin in enumerate(admins[:12], 1):
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
                f"   🤖 Bot: {'Yes' if admin['is_bot'] else 'No'}\n"
            )

            if admin["custom_title"]:
                text += (
                    f"   🏷️ Title: {safe(admin['custom_title'])}\n"
                )

            text += "\n"

        if len(admins) > 12:
            text += f"... আরও {len(admins) - 12} জন Admin রয়েছে।\n\n"

    else:
        text += (
            "⚠️ Admin Information পাওয়া যায়নি।\n"
            "Chat access ও Bot permissions পরীক্ষা করো।\n\n"
        )

    # Bot Admin Information
    text += (
        "🤖 BOT ADMIN INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    if admin_available and bot_admins:
        for index, bot in enumerate(bot_admins, 1):
            text += (
                f"{index}. {safe(bot['name'])}\n"
                f"   🆔 ID: <code>{bot['id']}</code>\n"
                f"   📛 Username: @{safe(bot['username']) if bot['username'] else 'Not set'}\n"
                f"   👑 Role: {safe(bot['status'])}\n\n"
            )

    elif admin_available:
        text += "❌ কোনো Bot Admin পাওয়া যায়নি।\n\n"

    else:
        text += "⚠️ Bot Admin Information Unavailable\n\n"

    text += (
        "⚠️ Note: Telegram API সব সদস্যের তালিকা বা "
        "সব সাধারণ সদস্যের Bot Status প্রকাশ করে না।\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )

    send_long(chat_id, text)

    # Send channel / group photo
    send_chat_photo(chat_id, chat)


# ==================================================
# BOT INFORMATION
# ==================================================

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
        f"📝 Name: {safe(bot.get('first_name'))}\n"
        f"📛 Username: @{safe(bot.get('username'))}\n"
        f"🆔 Bot ID: {bot.get('id')}\n"
        f"🤖 Can Join Groups: {bot.get('can_join_groups')}\n"
        f"🔗 Inline Mode: {bot.get('supports_inline_queries')}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )


# ==================================================
# JSON FORMATTER
# ==================================================

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
            f"✅ JSON FORMATTED\n\n<pre>{safe(formatted)}</pre>",
            parse_mode="HTML"
        )

    except json.JSONDecodeError:
        send(chat_id, "❌ Invalid JSON!")


# ==================================================
# SERVER STATUS
# ==================================================

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


# ==================================================
# HELP MENU
# ==================================================

def help_menu(chat_id):

    send(
        chat_id,
        "📖 TEAM SHADOW STRIKER V4\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👤 User Information\n"
        "User Picker দিয়ে তথ্য ও Profile Photo।\n\n"
        "👥 Group Information\n"
        "Group নির্বাচন করে Advanced Analyzer।\n\n"
        "📢 Channel Information\n"
        "Channel নির্বাচন করে Full Information।\n\n"
        "🤖 Bot Information\n"
        "Bot Details।\n\n"
        "🧾 JSON Formatter\n"
        "/json এর পরে JSON পাঠাও।\n\n"
        "📊 Server Status\n"
        "Bot ও API Status।\n\n"
        "⚠️ Telegram API-এর সীমাবদ্ধতার কারণে "
        "Story বা সব সদস্যের তথ্য পাওয়া যায় না।"
    )


# ==================================================
# FORWARD INFORMATION
# ==================================================

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
        f"👤 Name: {safe(name)}\n"
        f"📛 Username: @{safe(username) if username else 'Not available'}\n"
        f"🆔 User ID: {user.get('id', 'Unavailable')}\n"
        f"🕒 Time: {current_time()}\n\n"
        "⚡ TEAM SHADOW STRIKER"
    )


# ==================================================
# MESSAGE HANDLER
# ==================================================

def handle_message(message):

    chat_id = message.get("chat", {}).get("id")
    user = message.get("from", {})

    if not chat_id:
        return

    user_id = user.get("id")
    text = message.get("text", "").strip()

    # Start
    if text.startswith("/start"):

        if not is_member(user_id):
            join_page(chat_id)
            return

        send(
            chat_id,
            f"{greeting()}, {user.get('first_name', 'বন্ধু')}!\n\n"
            "⚡ Welcome to TEAM SHADOW STRIKER!\n"
            "TG Info Bot V4-তে স্বাগতম।"
        )

        main_menu(chat_id)
        return

    # Verification
    if not is_member(user_id):
        join_page(chat_id)
        return

    # User Selector Response
    if message.get("users_shared"):
        user_information(
            chat_id,
            message["users_shared"]
        )
        return

    # Group / Channel Selector Response
    if message.get("chat_shared"):
        shared = message["chat_shared"]

        selected_chat_id = shared.get("chat_id")

        if selected_chat_id:
            chat_info(chat_id, selected_chat_id)
        else:
            send(chat_id, "❌ Chat ID পাওয়া যায়নি।")

        return

    # Main Menu
    if text in ("/menu", "⬅️ Main Menu"):
        main_menu(chat_id)
        return

    if text == "/help":
        help_menu(chat_id)
        return

    # User Information
    if text == "👤 User Information":
        send(
            chat_id,
            "👤 উপরের User Information বাটনে চাপ দিয়ে "
            "একজন Telegram User নির্বাচন করো।"
        )

    # Group Information
    elif text == "👥 Group Information":
        chat_selection(chat_id, "group")

    # Channel Information
    elif text == "📢 Channel Information":
        chat_selection(chat_id, "channel")

    # Bot Information
    elif text == "🤖 Bot Information":
        bot_info(chat_id)

    # JSON Formatter
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


# ==================================================
# CALLBACK HANDLER
# ==================================================

def handle_callback(callback):

    callback_id = callback.get("id")
    data = callback.get("data")

    chat_id = callback.get(
        "message", {}
    ).get("chat", {}).get("id")

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


# ==================================================
# FLASK ROUTES
# ==================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "bot": "TEAM SHADOW STRIKER",
        "status": "Running",
        "version": "4.0"
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


# ==================================================
# WEBHOOK SETUP
# ==================================================

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


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
        )
