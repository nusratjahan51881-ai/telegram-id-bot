import os
import time
import html
import logging
import requests

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify

# ==================================================
# TEAM SHADOW STRIKER | TG INFO BOT V5
# ==================================================

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

CHANNEL = "@team_shadow_striker"
CHANNEL_LINK = "https://t.me/team_shadow_striker"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "TeamShadowStriker/5.0"})


# ==================================================
# TELEGRAM API
# ==================================================

def api(method, data=None):
    try:
        response = SESSION.post(
            f"{API}/{method}",
            json=data or {},
            timeout=20
        )
        return response.json()
    except Exception as error:
        logger.error("%s: %s", method, error)
        return {"ok": False, "description": str(error)}


def safe(value):
    if value is None or value == "":
        value = "Not available"
    return html.escape(str(value))


def send(chat_id, text, **kwargs):
    data = {"chat_id": chat_id, "text": text}
    data.update(kwargs)
    return api("sendMessage", data)


def send_report(chat_id, sections):
    """Send a report in safe, separate HTML messages."""
    for section in sections:
        if section:
            result = send(
                chat_id,
                section,
                parse_mode="HTML"
            )
            if not result.get("ok"):
                logger.error("Report failed: %s", result)


def line(label, value):
    return f"<b>{safe(label)}:</b> {safe(value)}\n"


def now():
    return datetime.now(
        ZoneInfo("Asia/Dhaka")
    ).strftime("%d %B %Y | %I:%M:%S %p")


def header(title):
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{safe(title)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )


# ==================================================
# VERIFICATION
# ==================================================

def is_member(user_id):
    if not user_id:
        return False

    result = api("getChatMember", {
        "chat_id": CHANNEL,
        "user_id": user_id
    })

    if not result.get("ok"):
        logger.warning("Verification API failed: %s", result)
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
                "text": "📢 JOIN CHANNEL",
                "url": CHANNEL_LINK
            }],
            [{
                "text": "✅ VERIFY NOW",
                "callback_data": "verify"
            }]
        ]
    }

    send(
        chat_id,
        header("🔐 TEAM SHADOW STRIKER") +
        "<b>Bot ব্যবহার করার আগে আমাদের Channel-এ Join করো।</b>\n\n"
        "① Join Channel চাপ দাও\n"
        "② Channel-এ Join করো\n"
        "③ Verify Now চাপ দাও\n\n"
        f"<b>🕒 {now()}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ==================================================
# MAIN MENU
# ==================================================

def main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{
                "text": "👤 USER INFORMATION",
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
                {"text": "👥 GROUP INFORMATION"},
                {"text": "📢 CHANNEL INFORMATION"}
            ],
            [
                {"text": "🤖 BOT INFORMATION"},
                {"text": "📊 SERVER STATUS"}
            ],
            [
                {"text": "📖 HELP"}
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

    send(
        chat_id,
        header("⚡ TEAM SHADOW STRIKER") +
        "<b>WELCOME TO TG INFO BOT V5</b>\n\n"
        "✨ Premium Telegram Information System\n\n"
        f"<b>🕒 Bangladesh Time:</b> {now()}\n\n"
        "<i>Select a feature below.</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ==================================================
# USER INFORMATION
# ==================================================

def user_information(chat_id, shared):
    users = shared.get("users", [])

    if not users:
        send(chat_id, "❌ User information পাওয়া যায়নি।")
        return

    for user in users:
        uid = user.get("user_id")
        first = user.get("first_name", "")
        last = user.get("last_name", "")
        name = " ".join(filter(None, [first, last]))

        username = user.get("username")
        shared_photos = user.get("photo", [])

        photo_result = api("getUserProfilePhotos", {
            "user_id": uid,
            "limit": 5
        })

        photos = []
        total_photos = "Unavailable"

        if photo_result.get("ok"):
            result = photo_result.get("result", {})
            photos = result.get("photos", [])
            total_photos = result.get("total_count", 0)

        text = (
            header("👤 USER PROFILE REPORT")
            + line("Full Name", name)
            + line("Username", "@" + username if username else "Not set")
            + line("User ID", uid)
            + line("Account Type", "User")
            + line("Profile Photos", total_photos)
            + line("Shared Photo", "Available" if shared_photos else "Not shared")
            + line("Information Source", "Telegram User Picker")
            + f"\n<b>🕒 Bangladesh Time:</b> {now()}\n\n"
            "<i>Story and private Bio are not provided by Telegram Bot API.</i>\n\n"
            "<b>⚡ TEAM SHADOW STRIKER</b>"
        )

        send(chat_id, text, parse_mode="HTML")

        photo_id = None

        if photos and photos[0]:
            photo_id = photos[0][-1].get("file_id")
        elif shared_photos:
            photo_id = max(
                shared_photos,
                key=lambda p: p.get("file_size", 0)
            ).get("file_id")

        if photo_id:
            api("sendPhoto", {
                "chat_id": chat_id,
                "photo": photo_id,
                "caption": "🖼️ <b>USER PROFILE PHOTO</b>",
                "parse_mode": "HTML"
            })


# ==================================================
# GROUP / CHANNEL SELECTOR
# ==================================================

def chat_selection(chat_id, mode):
    buttons = []

    if mode == "group":
        buttons.append({
            "text": "👥 SELECT GROUP",
            "request_chat": {
                "request_id": 2001,
                "chat_is_channel": False,
                "request_title": True,
                "request_username": True,
                "request_photo": True
            }
        })

    elif mode == "channel":
        buttons.append({
            "text": "📢 SELECT CHANNEL",
            "request_chat": {
                "request_id": 2002,
                "chat_is_channel": True,
                "request_title": True,
                "request_username": True,
                "request_photo": True
            }
        })

    keyboard = {
        "keyboard": [
            buttons,
            [{"text": "⬅️ MAIN MENU"}]
        ],
        "resize_keyboard": True
    }

    send(
        chat_id,
        header("🔎 ADVANCED CHAT SELECTOR") +
        "<b>যে Group অথবা Channel-এর তথ্য দেখতে চাও সেটি Select করো।</b>\n\n"
        "👥 Group: Select Group\n"
        "📢 Channel: Select Channel\n\n"
        "<b>ℹ️ Bot আগে থেকে যুক্ত না থাকলেও Chat নির্বাচন করতে পারবে।</b>\n"
        "<i>তবে বিস্তারিত তথ্য Telegram-এর অনুমতির ওপর নির্ভর করবে।</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ==================================================
# CHAT INFORMATION
# ==================================================

def get_chat_details(shared, mode):
    chat_id = shared.get("chat_id")
    username = shared.get("username")

    # First try using selected chat ID.
    result = api("getChat", {"chat_id": chat_id})

    # Public chats may also be accessible through username.
    if not result.get("ok") and username:
        result = api("getChat", {"chat_id": "@" + username})

    chat = result.get("result", {}) if result.get("ok") else {}

    # Shared selection data is still useful if getChat fails.
    title = chat.get("title") or shared.get("title")
    actual_username = chat.get("username") or username
    description = chat.get("description")

    actual_id = chat.get("id") or chat_id
    chat_type = chat.get("type") or (
        "channel" if mode == "channel" else "group/supergroup"
    )

    return {
        "id": actual_id,
        "title": title,
        "username": actual_username,
        "description": description,
        "type": chat_type,
        "invite_link": chat.get("invite_link"),
        "photo": chat.get("photo"),
        "shared_photo": shared.get("photo", []),
        "get_chat_ok": result.get("ok", False)
    }


def send_chat_photo(chat_id, chat):
    photo = chat.get("photo") or {}

    photo_id = photo.get("big_file_id") or photo.get("small_file_id")

    if not photo_id:
        shared_photos = chat.get("shared_photo", [])

        if shared_photos:
            photo_id = max(
                shared_photos,
                key=lambda p: p.get("file_size", 0)
            ).get("file_id")

    if photo_id:
        result = api("sendPhoto", {
            "chat_id": chat_id,
            "photo": photo_id,
            "caption": "🖼️ <b>GROUP / CHANNEL PROFILE PHOTO</b>",
            "parse_mode": "HTML"
        })

        if not result.get("ok"):
            logger.warning("Photo sending failed: %s", result)
    else:
        send(chat_id, "🖼️ এই Chat-এর Profile Picture পাওয়া যায়নি।")


def chat_analyzer(chat_id, shared, mode):
    chat = get_chat_details(shared, mode)

    actual_id = chat["id"]
    username = chat["username"]

    if username:
        full_link = f"https://t.me/{username}"
    else:
        full_link = chat.get("invite_link") or "Public link unavailable"

    # Member count
    count_result = api("getChatMemberCount", {
        "chat_id": actual_id
    })

    member_count = (
        count_result.get("result")
        if count_result.get("ok")
        else "Unavailable (Bot access required)"
    )

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

    for item in admins:
        user = item.get("user", {})

        admin = {
            "id": user.get("id"),
            "name": " ".join(filter(None, [
                user.get("first_name", ""),
                user.get("last_name", "")
            ])) or "Unknown",
            "username": user.get("username"),
            "is_bot": user.get("is_bot", False),
            "status": item.get("status", "administrator"),
            "custom_title": item.get("custom_title")
        }

        if admin["status"] == "creator":
            creator = admin

        if admin["is_bot"]:
            bot_admins.append(admin)
        else:
            human_admins.append(admin)

    # Main report
    report = header("📊 ADVANCED CHAT REPORT V5")

    report += (
        "<b>━━━ BASIC INFORMATION ━━━</b>\n"
        + line("Name", chat["title"])
        + line("Username", "@" + username if username else "Not set")
        + line("Full Link", full_link)
        + line("Chat ID", actual_id)
        + line("Chat Type", chat["type"])
        + line("Total Members", member_count)
        + line("Description", chat["description"])
        + line("Bot Access", "Available" if chat["get_chat_ok"] else "Limited")
        + f"\n<b>🕒 Bangladesh Time:</b> {now()}\n\n"
    )

    report += "<b>━━━ ADMIN STATISTICS ━━━</b>\n"

    if admin_available:
        report += (
            line("Total Admins", len(admins))
            + line("Human Admins", len(human_admins))
            + line("Bot Admins", len(bot_admins))
        )

        if creator:
            report += (
                "\n<b>👑 CREATOR</b>\n"
                + line("Name", creator["name"])
                + line("Username", "@" + creator["username"] if creator["username"] else "Not set")
                + line("User ID", creator["id"])
            )

        report += "\n<b>━━━ ADMIN LIST ━━━</b>\n"

        for index, admin in enumerate(admins[:15], 1):
            report += (
                f"\n<b>{index}. {safe(admin['name'])}</b>\n"
                + line("ID", admin["id"])
                + line("Username", "@" + admin["username"] if admin["username"] else "Not set")
                + line("Role", admin["status"])
                + line("Bot Account", "Yes" if admin["is_bot"] else "No")
            )

            if admin["custom_title"]:
                report += line("Custom Title", admin["custom_title"])

        if len(admins) > 15:
            report += f"\n<i>আরও {len(admins) - 15} জন Admin আছে।</i>\n"

        report += "\n<b>━━━ BOT ADMIN LIST ━━━</b>\n"

        if bot_admins:
            for index, bot in enumerate(bot_admins, 1):
                report += (
                    f"\n<b>🤖 BOT {index}</b>\n"
                    + line("Name", bot["name"])
                    + line("Username", "@" + bot["username"] if bot["username"] else "Not set")
                    + line("Bot ID", bot["id"])
                )
        else:
            report += "❌ কোনো Bot Admin পাওয়া যায়নি।\n"

    else:
        report += (
            "⚠️ Admin List পাওয়া যায়নি।\n"
            "Bot-কে Chat-এ যুক্ত করে প্রয়োজনীয় অনুমতি দিলে "
            "আরও বিস্তারিত তথ্য পাওয়া যেতে পারে।\n"
        )
        report += (
            "\n<i>Bot সদস্য না হলে Telegram Admin List "
            "দিতে নাও পারে।</i>\n"
        )

    report += (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "<b>⚡ TEAM SHADOW STRIKER</b>"
    )

    send(chat_id, report, parse_mode="HTML")

    # Send photo separately
    send_chat_photo(chat_id, chat)


# ==================================================
# BOT INFORMATION
# ==================================================

def bot_information(chat_id):
    result = api("getMe")

    if not result.get("ok"):
        send(chat_id, "❌ Bot Information পাওয়া যায়নি।")
        return

    bot = result["result"]

    text = (
        header("🤖 BOT INFORMATION")
        + line("Name", bot.get("first_name"))
        + line("Username", "@" + bot.get("username", ""))
        + line("Bot ID", bot.get("id"))
        + line("Can Join Groups", bot.get("can_join_groups"))
        + line("Inline Mode", bot.get("supports_inline_queries"))
        + f"\n<b>🕒 Time:</b> {now()}\n\n"
        "<b>⚡ TEAM SHADOW STRIKER</b>"
    )

    send(chat_id, text, parse_mode="HTML")


# ==================================================
# SERVER STATUS
# ==================================================

def server_status(chat_id):
    start = time.monotonic()
    result = api("getMe")
    elapsed = round((time.monotonic() - start) * 1000, 2)

    status = "🟢 ONLINE" if result.get("ok") else "🔴 API ERROR"

    text = (
        header("📊 SERVER STATUS")
        + line("Bot Status", status)
        + line("Telegram API", "Connected" if result.get("ok") else "Disconnected")
        + line("API Response", f"{elapsed} ms")
        + line("Timezone", "Asia/Dhaka")
        + f"\n<b>🕒 Bangladesh Time:</b> {now()}\n\n"
        "<b>⚡ TEAM SHADOW STRIKER</b>"
    )

    send(chat_id, text, parse_mode="HTML")


# ==================================================
# HELP
# ==================================================

def help_menu(chat_id):
    send(
        chat_id,
        header("📖 HELP CENTER")
        + "<b>👤 USER INFORMATION</b>\n"
        "Telegram User Picker দিয়ে User নির্বাচন করো।\n\n"
        "<b>👥 GROUP INFORMATION</b>\n"
        "Group নির্বাচন করে তথ্য দেখো।\n\n"
        "<b>📢 CHANNEL INFORMATION</b>\n"
        "Channel নির্বাচন করে তথ্য দেখো।\n\n"
        "<b>🤖 BOT INFORMATION</b>\n"
        "নিজের Bot-এর তথ্য দেখো।\n\n"
        "<b>📊 SERVER STATUS</b>\n"
        "Bot API Status ও Response Time।\n\n"
        "<i>Telegram API-এর সীমাবদ্ধতার কারণে "
        "সব তথ্য সবসময় পাওয়া সম্ভব নয়।</i>",
        parse_mode="HTML"
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
    text = (message.get("text") or "").strip()

    if text.startswith("/start"):
        if not is_member(user_id):
            join_page(chat_id)
            return

        send(
            chat_id,
            f"<b>{safe('স্বাগতম')} {safe(user.get('first_name', 'বন্ধু'))}!</b>\n\n"
            "<b>⚡ TEAM SHADOW STRIKER V5</b>\n"
            "Premium TG Information System",
            parse_mode="HTML"
        )
        main_menu(chat_id)
        return

    # Require channel verification
    if not is_member(user_id):
        join_page(chat_id)
        return

    # User selection
    if message.get("users_shared"):
        user_information(chat_id, message["users_shared"])
        return

    # Group / Channel selection
    if message.get("chat_shared"):
        shared = message["chat_shared"]
        request_id = shared.get("request_id")

        mode = "channel" if request_id == 2002 else "group"

        chat_analyzer(chat_id, shared, mode)
        return

    if text in ("/menu", "⬅️ MAIN MENU"):
        main_menu(chat_id)

    elif text == "/help" or text == "📖 HELP":
        help_menu(chat_id)

    elif text == "👤 USER INFORMATION":
        send(
            chat_id,
            "<b>👤 USER SELECTOR</b>\n\n"
            "Menu-এর USER INFORMATION বাটনে আবার চাপ দিয়ে "
            "একজন User নির্বাচন করো।",
            parse_mode="HTML"
        )

    elif text == "👥 GROUP INFORMATION":
        chat_selection(chat_id, "group")

    elif text == "📢 CHANNEL INFORMATION":
        chat_selection(chat_id, "channel")

    elif text == "🤖 BOT INFORMATION":
        bot_information(chat_id)

    elif text == "📊 SERVER STATUS":
        server_status(chat_id)

    elif text.startswith("/chat"):
        parts = text.split(maxsplit=1)

        if len(parts) == 2:
            # Username lookup fallback
            username = parts[1].strip()
            if not username.startswith("@"):
                username = "@" + username

            result = api("getChat", {"chat_id": username})

            if result.get("ok"):
                found = result["result"]
                shared = {
                    "chat_id": found.get("id"),
                    "title": found.get("title"),
                    "username": found.get("username"),
                    "photo": []
                }
                mode = "channel" if found.get("type") == "channel" else "group"
                chat_analyzer(chat_id, shared, mode)
            else:
                send(chat_id, "❌ Chat পাওয়া যায়নি।")
        else:
            send(chat_id, "ব্যবহার: /chat @username")

    else:
        send(
            chat_id,
            "⚠️ Menu থেকে একটি Feature নির্বাচন করো।\n"
            "/menu লিখে Main Menu খোলো।"
        )


# ==================================================
# CALLBACK HANDLER
# ==================================================

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    if data == "verify" and chat_id:
        if is_member(user_id):
            api("answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Verification Successful!"
            })

            send(
                chat_id,
                "<b>✅ VERIFICATION SUCCESSFUL</b>\n"
                "Welcome to TEAM SHADOW STRIKER!",
                parse_mode="HTML"
            )
            main_menu(chat_id)
        else:
            api("answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "আগে Channel-এ Join করো!"
            })
            join_page(chat_id)


# ==================================================
# FLASK ROUTES
# ==================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "bot": "TEAM SHADOW STRIKER",
        "version": "5.0",
        "status": "Running",
        "timezone": "Asia/Dhaka"
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
        logger.exception("Webhook processing error")

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
