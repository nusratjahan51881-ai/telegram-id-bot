import os
import html
import sqlite3
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
BASE = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "@team_shadow_striker"
CHANNEL_LINK = "https://t.me/team_shadow_striker"
DB = "users.db"

def api(method, data=None):
    r = requests.post(
        f"{BASE}/{method}",
        json=data or {},
        timeout=15
    )
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise Exception(result.get("description", "Telegram API error"))
    return result["result"]

def db_init():
    with sqlite3.connect(DB) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS usernames (
            user_id INTEGER,
            username TEXT,
            UNIQUE(user_id, username)
        )
        """)

def esc(value):
    return html.escape(str(value or ""))

def send(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        data["reply_markup"] = keyboard
    api("sendMessage", data)

def is_member(user_id):
    try:
        member = api("getChatMember", {
            "chat_id": CHANNEL,
            "user_id": user_id
        })
        status = member.get("status")
        return (
            status in ("creator", "administrator", "member")
            or (
                status == "restricted"
                and member.get("is_member", False)
            )
        )
    except Exception:
        return False

def join_message(chat_id):
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
        "⚡ <b>TEAM SHADOW STRIKER</b>\n\n"
        "বট ব্যবহার করতে আমাদের Channel-এ Join করুন।\n"
        "Join করার পর Verify চাপুন।",
        keyboard
    )

def main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🆔 My Information"}],
            [{"text": "ℹ️ How To Use"}]
        ],
        "resize_keyboard": True
    }
    send(
        chat_id,
        "⚡ <b>TEAM SHADOW STRIKER</b>\n\n"
        "Welcome! Bot is ready.\n\n"
        "কোনো ব্যক্তির উপলব্ধ তথ্য দেখতে তার Forward করা "
        "মেসেজ পাঠান।",
        keyboard
    )

def photo_count(user_id):
    try:
        result = api("getUserProfilePhotos", {
            "user_id": user_id,
            "limit": 1
        })
        return str(result.get("total_count", 0))
    except Exception:
        return "পাওয়া যায়নি"

def save_profile(user):
    uid = user.get("id")
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    username = user.get("username", "")

    with sqlite3.connect(DB) as con:
        if username:
            con.execute(
                "INSERT OR IGNORE INTO usernames VALUES (?, ?)",
                (uid, username)
            )

        con.execute("""
        INSERT INTO profiles VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username
        """, (uid, first, last, username))

        history = con.execute(
            "SELECT username FROM usernames WHERE user_id=?",
            (uid,)
        ).fetchall()

    previous = [
        row[0] for row in history
        if row[0] and row[0] != username
    ]
    return first, last, username, previous

def unavailable():
    return "❌ এই তথ্য পাওয়া যায়নি। আবার চেষ্টা করুন।"

def make_report(user):
    uid = user.get("id")
    first, last, username, previous = save_profile(user)

    old_names = (
        ", ".join("@" + x for x in previous)
        if previous else unavailable()
    )

    photos = photo_count(uid)

    return (
        "⚡ <b>USER INFORMATION</b>\n\n"
        f"🆔 Chat ID: <code>{uid}</code>\n"
        f"👤 Name: {esc(first)} {esc(last)}\n"
        f"📛 Username: "
        f"{('@' + esc(username)) if username else unavailable()}\n"
        f"🟢 Last Seen: {unavailable()}\n"
        f"👥 Total Groups: {unavailable()}\n"
        f"📝 Bio: {unavailable()}\n"
        f"🖼️ Profile Photos: {esc(photos)}\n"
        f"🔄 Previously Observed Usernames: {esc(old_names)}\n"
        f"📅 Name Change Date: {unavailable()}\n"
        f"📱 Phone Number: {unavailable()}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>Bot From Team Shadow Striker</b> ⚡"
    )

def handle_message(message):
    chat_id = message["chat"]["id"]
    sender_id = message.get("from", {}).get("id")

    if not sender_id or not is_member(sender_id):
        join_message(chat_id)
        return

    text = message.get("text", "")

    if text.startswith("/start"):
        main_menu(chat_id)
        return

    if text == "🆔 My Information":
        user = message.get("from", {})
        send(chat_id, make_report(user))
        return

    if text == "ℹ️ How To Use":
        send(
            chat_id,
            "একটি Telegram Message Forward করে পাঠান। "
            "Telegram যে Sender Information প্রকাশ করে, "
            "শুধু সেটিই দেখানো হবে।"
        )
        return

    origin = message.get("forward_origin")

    if not origin or origin.get("type") != "user":
        send(
            chat_id,
            "কোনো User-এর Forward করা Message পাঠান।\n\n"
            "Hidden Forward-এর তথ্য পাওয়া সম্ভব নয়।"
        )
        return

    user = origin.get("sender_user", {})
    if not user.get("id"):
        send(chat_id, unavailable())
        return

    send(chat_id, make_report(user))

@app.route("/")
def home():
    return "Team Shadow Striker Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    callback = data.get("callback_query")
    if callback:
        try:
            user_id = callback["from"]["id"]
            chat_id = callback["message"]["chat"]["id"]

            api("answerCallbackQuery", {
                "callback_query_id": callback["id"]
            })

            if callback.get("data") == "verify":
                if is_member(user_id):
                    main_menu(chat_id)
                else:
                    join_message(chat_id)
        except Exception:
            pass

        return jsonify({"ok": True})

    message = data.get("message")
    if message:
        try:
            handle_message(message)
        except Exception:
            return jsonify({"ok": False}), 500

    return jsonify({"ok": True})

db_init()

if TOKEN and os.environ.get("RENDER_EXTERNAL_URL"):
    try:
        api("setWebhook", {
            "url": os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
                    + "/webhook"
        })
    except Exception:
        pass
