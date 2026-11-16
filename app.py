import os
import time
import logging
import requests

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify

# ==================================================
# TEAM SHADOW STRIKER | TG INFO BOT V6
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

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Team-Shadow-Striker-TGInfoBot/6.0"
})


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
        logger.error("%s error: %s", method, error)
        return {"ok": False, "description": str(error)}


def send(chat_id, text, **kwargs):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    data.update(kwargs)
    return api("sendMessage", data)


def safe(value):
    if value is None or value == "":
        value = "Not available"

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def line(label, value):
    return f"<b>{safe(label)}:</b> {safe(value)}\n"


# ==================================================
# TIME
# ==================================================

def now():
    return datetime.now(
        ZoneInfo("Asia/Dhaka")
    ).strftime("%d-%m-%Y | %I:%M:%S %p")


def greeting():
    hour = datetime.now(
        ZoneInfo("Asia/Dhaka")
    ).hour

    if 5 <= hour < 12:
        return "শুভ সকাল"

    if 12 <= hour < 17:
        return "শুভ দুপুর"

    if 17 <= hour < 20:
        return "শুভ সন্ধ্যা"

    return "শুভ রাত্রি"


# ==================================================
# DESIGN
# ==================================================

def header(title):
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{safe(title)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )


def footer():
    return (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "<b>⚡ TEAM SHADOW STRIKER</b>\n"
        f"<b>🕒 {now()}</b>"
    )


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

    if status in ("member", "administrator", "creator"):
        return True

    if status == "restricted" and member.get("is_member"):
        return True

    return False


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
        header("🔐 TEAM SHADOW STRIKER")
        + "<b>Bot ব্যবহার করতে প্রথমে আমাদের Channel-এ Join করো।</b>\n\n"
        "① Join Channel চাপ দাও\n"
        "② Channel-এ Join করো\n"
        "③ Verify Now চাপ দাও\n\n"
        + footer(),
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
                {"text": "📖 HELP MENU"}
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

    send(
        chat_id,
        header("⚡ TEAM SHADOW STRIKER")
        + "<b>WELCOME TO TG INFO BOT V6</b>\n\n"
        "✨ Premium Telegram Information System\n\n"
        "<b>👤 User Information</b>\n"
        "<b>👥 Group Analyzer</b>\n"
        "<b>📢 Channel Analyzer</b>\n"
        "<b>🤖 Bot Information</b>\n"
        "<b>📊 Server Status</b>\n\n"
        + footer(),
        parse_mode="HTML",
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
        uid = user.get("user_id")

        name = " ".join(filter(None, [
            user.get("first_name", ""),
            user.get("last_name", "")
        ]))

        username = user.get("username")
        shared_photos = user.get("photo", [])

        # Try to retrieve profile photos
        photo_result = api("getUserProfilePhotos", {
            "user_id": uid,
            "limit": 5
        })

        photos = []
        total_photos = "Unavailable"

        if photo_result.get("ok"):
            photo_data = photo_result.get("result", {})
            photos = photo_data.get("photos", [])
            total_photos = photo_data.get("total_count", 0)

        report = (
            header("👤 USER PROFILE INFORMATION")
            + line("Full Name", name)
            + line("Username", "@" + username if username else "Not set")
            + line("User ID", uid)
            + line("Account Type", "Telegram User")
            + line("Profile Photos", total_photos)
            + line(
                "Shared Photo",
                "Available" if shared_photos else "Not shared"
            )
            + line("Selection", "Telegram User Picker")
            + footer()
        )

        send(chat_id, report, parse_mode="HTML")

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

        send(
            chat_id,
            "ℹ️ Telegram Bot API দিয়ে User-এর ব্যক্তিগত Story বা গোপন Bio দেখা যায় না।"
        )


# ==================================================
# GROUP / CHANNEL SELECTOR
# ==================================================

def chat_selection(chat_id, mode):
    if mode == "group":
        button = {
            "text": "👥 SELECT GROUP",
            "request_chat": {
                "request_id": 2001,
                "chat_is_channel": False,
                "request_title": True,
                "request_username": True,
                "request_photo": True
            }
        }

        title = "👥 GROUP SELECTOR"

    else:
        button = {
            "text": "📢 SELECT CHANNEL",
            "request_chat": {
                "request_id": 2002,
                "chat_is_channel": True,
                "request_title": True,
                "request_username": True,
                "request_photo": True
            }
        }

        title = "📢 CHANNEL SELECTOR"

    keyboard = {
        "keyboard": [
            [button],
            [{"text": "⬅️ MAIN MENU"}]
        ],
        "resize_keyboard": True
    }

    send(
        chat_id,
        header(title)
        + "<b>যে Chat-এর তথ্য দেখতে চাও সেটি Select করো।</b>\n\n"
        "🔎 Chat নির্বাচন করলেই Analyzer শুরু হবে।\n\n"
        "✅ Public Chat-এর তথ্য Bot যুক্ত না থাকলেও "
        "যতটুকু পাওয়া সম্ভব দেখানো হবে।\n\n"
        "⚠️ Private Chat-এর বিস্তারিত তথ্যের জন্য "
        "Bot-এর Access প্রয়োজন হতে পারে।"
        + footer(),
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ==================================================
# GET CHAT INFORMATION
# ==================================================

def get_chat_details(shared):
    chat_id = shared.get("chat_id")
    username = shared.get("username")

    result = {"ok": False}

    # Public username lookup
    if username:
        result = api("getChat", {
            "chat_id": "@" + username.lstrip("@")
        })

    # Try selected numeric ID if needed
    if not result.get("ok") and chat_id:
        result = api("getChat", {
            "chat_id": chat_id
        })

    chat = result.get("result", {})

    return {
        "id": chat.get("id") or chat_id,
        "title": chat.get("title") or shared.get("title"),
        "username": chat.get("username") or username,
        "type": chat.get("type") or (
            "channel" if shared.get("request_id") == 2002
            else "supergroup"
        ),
        "description": chat.get("description"),
        "invite_link": chat.get("invite_link"),
        "photo": chat.get("photo"),
        "shared_photo": shared.get("photo", []),
        "accessible": result.get("ok", False)
    }


# ==================================================
# CHAT PROFILE PHOTO
# ==================================================

def send_chat_photo(chat_id, chat):
    photo = chat.get("photo") or {}

    photo_id = (
        photo.get("big_file_id")
        or photo.get("small_file_id")
    )

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
            "caption": "🖼️ <b>CHAT PROFILE PHOTO</b>",
            "parse_mode": "HTML"
        })

        if not result.get("ok"):
            logger.warning("Photo error: %s", result)

    else:
        send(chat_id, "🖼️ Profile Picture পাওয়া যায়নি।")


# ==================================================
# GROUP / CHANNEL ANALYZER
# ==================================================

def chat_analyzer(chat_id, shared, mode):
    chat = get_chat_details(shared)

    target = chat.get("id")
    username = chat.get("username")

    lookup = (
        "@" + username.lstrip("@")
        if username else target
    )

    if username:
        full_link = "https://t.me/" + username.lstrip("@")
    else:
        full_link = chat.get("invite_link") or "Not available"

    # Member count
    count_result = api("getChatMemberCount", {
        "chat_id": lookup
    })

    member_count = (
        count_result.get("result")
        if count_result.get("ok")
        else "Unavailable"
    )

    # Administrator list
    admin_result = api("getChatAdministrators", {
        "chat_id": lookup
    })

    admins = (
        admin_result.get("result", [])
        if admin_result.get("ok")
        else []
    )

    humans = []
    bots = []
    owner = None

    for item in admins:
        user = item.get("user", {})

        entry = {
            "name": " ".join(filter(None, [
                user.get("first_name", ""),
                user.get("last_name", "")
            ])) or "Unknown",
            "username": user.get("username"),
            "id": user.get("id"),
            "is_bot": user.get("is_bot", False),
            "role": item.get("status", "administrator")
        }

        if entry["role"] == "creator":
            owner = entry

        if entry["is_bot"]:
            bots.append(entry)
        else:
            humans.append(entry)

    # Build report
    report = header("✨ PREMIUM CHAT ANALYZER")

    report += (
        "<b>━━━ BASIC INFORMATION ━━━</b>\n"
        + line("Name", chat.get("title"))
        + line(
            "Username",
            "@" + username if username else "Not available"
        )
        + line("Chat ID", target)
        + line("Chat Type", chat.get("type"))
        + line("Full Link", full_link)
        + line("Total Members", member_count)
        + line("Description", chat.get("description"))
        + line(
            "Bot Chat Access",
            "Available" if chat["accessible"] else "Limited"
        )
    )

    # Admin information
    report += "\n<b>━━━ ADMIN STATISTICS ━━━</b>\n"

    if admin_result.get("ok"):
        report += (
            line("Total Admins", len(admins))
            + line("Human Admins", len(humans))
            + line("Bot Admins", len(bots))
        )

        if owner:
            report += (
                "\n<b>👑 CHAT OWNER</b>\n"
                + line("Name", owner["name"])
                + line(
                    "Username",
                    "@" + owner["username"]
                    if owner["username"] else "Not available"
                )
                + line("User ID", owner["id"])
            )

        report += "\n<b>━━━ ADMIN LIST ━━━</b>\n"

        for index, admin in enumerate(admins[:15], 1):
            report += (
                f"\n<b>{index}. {safe(admin['name'])}</b>\n"
                + line(
                    "Username",
                    "@" + admin["username"]
                    if admin["username"] else "Not available"
                )
                + line("User ID", admin["id"])
                + line("Role", admin["role"])
                + line("Bot Account", "Yes" if admin["is_bot"] else "No")
            )

        if len(admins) > 15:
            report += (
                f"\n<i>আরও {len(admins) - 15} জন Admin রয়েছে।</i>\n"
            )

        report += "\n<b>━━━ BOT ADMIN LIST ━━━</b>\n"

        if bots:
            for index, bot in enumerate(bots, 1):
                report += (
                    f"\n<b>🤖 BOT {index}</b>\n"
                    + line("Name", bot["name"])
                    + line(
                        "Username",
                        "@" + bot["username"]
                        if bot["username"] else "Not available"
                    )
                    + line("Bot ID", bot["id"])
                )
        else:
            report += "❌ কোনো Bot Admin পাওয়া যায়নি।\n"

    else:
        report += (
            "⚠️ Admin List পাওয়া যায়নি।\n"
            "Telegram API এই Chat-এর Admin তথ্য দেয়নি।\n"
        )

    report += footer()

    # Send report
    if len(report) <= 4000:
        send(
            chat_id,
            report,
            parse_mode="HTML"
        )
    else:
        # Split long report without losing HTML validity
        sections = [
            report[i:i + 3500]
            for i in range(0, len(report), 3500)
        ]

        for section in sections:
            send(
                chat_id,
                section,
                parse_mode="HTML"
            )

    # Send profile photo
    send_chat_photo(chat_id, chat)


# ==================================================
# BOT INFORMATION
# ==================================================

def bot_information(chat_id):
    result = api("getMe")

    if not result.get("ok"):
        send(chat_id, "❌ Bot Information পাওয়া যায়নি।")
        return

    bot = result.get("result", {})

    report = (
        header("🤖 BOT INFORMATION")
        + line("Name", bot.get("first_name"))
        + line("Username", "@" + bot.get("username", ""))
        + line("Bot ID", bot.get("id"))
        + line("Can Join Groups", bot.get("can_join_groups"))
        + line("Inline Mode", bot.get("supports_inline_queries"))
        + footer()
    )

    send(chat_id, report, parse_mode="HTML")


# ==================================================
# SERVER STATUS
# ==================================================

def server_status(chat_id):
    start = time.monotonic()

    result = api("getMe")

    elapsed = round(
        (time.monotonic() - start) * 1000,
        2
    )

    status = "🟢 ONLINE" if result.get("ok") else "🔴 API ERROR"

    report = (
        header("📊 SERVER STATUS")
        + line("Bot Status", status)
        + line(
            "Telegram API",
            "Connected" if result.get("ok") else "Disconnected"
        )
        + line("API Response", f"{elapsed} ms")
        + line("Timezone", "Asia/Dhaka")
        + footer()
    )

    send(chat_id, report, parse_mode="HTML")


# ==================================================
# HELP MENU
# ==================================================

def help_menu(chat_id):
    report = (
        header("📖 HELP CENTER")
        + "<b>👤 USER INFORMATION</b>\n"
        "Telegram User Picker দিয়ে User নির্বাচন করো।\n\n"
        "<b>👥 GROUP INFORMATION</b>\n"
        "Group Select করে Analyzer ব্যবহার করো।\n\n"
        "<b>📢 CHANNEL INFORMATION</b>\n"
        "Channel Select করে তথ্য দেখো।\n\n"
        "<b>🤖 BOT INFORMATION</b>\n"
        "নিজের Bot-এর তথ্য দেখো।\n\n"
        "<b>📊 SERVER STATUS</b>\n"
        "Bot ও API Status দেখো।\n\n"
        "<i>সাধারণ সদস্যদের পূর্ণ তালিকা Telegram Bot API দেয় না। "
        "Story ও ব্যক্তিগত তথ্যও পাওয়া যায় না।</i>"
        + footer()
    )

    send(chat_id, report, parse_mode="HTML")


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

    # START
    if text.startswith("/start"):
        if not is_member(user_id):
            join_page(chat_id)
            return

        send(
            chat_id,
            f"<b>{greeting()}, {safe(user.get('first_name', 'বন্ধু'))}!</b>\n\n"
            "<b>⚡ TEAM SHADOW STRIKER V6</b>\n"
            "Premium TG Information System",
            parse_mode="HTML"
        )

        main_menu(chat_id)
        return

    # Verification
    if not is_member(user_id):
        join_page(chat_id)
        return

    # User selected
    if message.get("users_shared"):
        user_information(
            chat_id,
            message["users_shared"]
        )
        return

    # Group / Channel selected
    if message.get("chat_shared"):
        shared = message["chat_shared"]
        request_id = shared.get("request_id")

        if request_id == 2002:
            mode = "channel"
        elif request_id == 2001:
            mode = "group"
        else:
            send(chat_id, "❌ Unknown Chat Selection.")
            return

        chat_analyzer(chat_id, shared, mode)
        return

    # Menu
    if text in ("/menu", "⬅️ MAIN MENU"):
        main_menu(chat_id)

    elif text in ("/help", "📖 HELP MENU"):
        help_menu(chat_id)

    elif text == "👤 USER INFORMATION":
        send(
            chat_id,
            "<b>👤 USER SELECTOR</b>\n\n"
            "USER INFORMATION বাটনে চাপ দিয়ে একজন User নির্বাচন করো।",
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

        if len(parts) != 2:
            send(
                chat_id,
                "ব্যবহার: /chat @username"
            )
            return

        username = parts[1].strip().lstrip("@")

        result = api("getChat", {
            "chat_id": "@" + username
        })

        if not result.get("ok"):
            send(
                chat_id,
                "❌ Public Chat পাওয়া যায়নি।\n"
                "Username সঠিক কিনা পরীক্ষা করো।"
            )
            return

        found = result["result"]

        shared = {
            "chat_id": found.get("id"),
            "title": found.get("title"),
            "username": found.get("username"),
            "photo": [],
            "request_id": (
                2002 if found.get("type") == "channel"
                else 2001
            )
        }

        mode = (
            "channel" if found.get("type") == "channel"
            else "group"
        )

        chat_analyzer(chat_id, shared, mode)

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

    chat_id = callback.get(
        "message", {}
    ).get("chat", {}).get("id")

    user_id = callback.get("from", {}).get("id")

    if data == "verify" and chat_id:

        if is_member(user_id):

            api("answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": "Verification Successful!"
            })

            send(
                chat_id,
                "<b>✅ VERIFICATION SUCCESSFUL!</b>\n\n"
                "Welcome to TEAM SHADOW STRIKER.",
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
        "version": "6.0",
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
        logger.exception("Webhook processing failed")

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
