import os
import html
import sqlite3
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
BASE = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "@team_shadow_striker"
CHANNEL_LINK = "https://t.me/team_shadow_striker"
DB = "users.db"
TZ = ZoneInfo("Asia/Dhaka")

def api(method, data=None):
    r = requests.post(
        f"{BASE}/{method}",
        json=data or {},
        timeout=20
    )
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise Exception(result.get("description"))
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

def now_info():
    now = datetime.now(TZ)
    hour = now.hour

    if 5 <= hour < 12:
        greeting = "শুভ সকাল"
    elif 12 <= hour < 17:
        greeting = "শুভ দুপুর"
    elif 17 <= hour < 20:
        greeting = "শুভ সন্ধ্যা"
    else:
        greeting = "শুভ রাত্রি"

    return greeting, now.strftime("%I:%M %p")

def send(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        data["reply_markup"] = keyboard
    return api("sendMessage", data)

def save_user(user):
    uid = user.get("id")
    if not uid:
        return

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

def is_member(uid):
    member = api("getChatMember", {
        "chat_id": CHANNEL,
        "user_id": uid
    })
    status = member.get("status")
    return (
        status in ("creator", "administrator", "member")
        or (
            status == "restricted"
            and member.get("is_member", False)
        )
    )

def identity(user):
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    username = user.get("username", "")
    uid = user.get("id")

    return (
        f"👤 নাম: <b>{esc(first)} {esc(last)}</b>\n"
        f"📛 Username: "
        f"{('@' + esc(username)) if username else 'নেই'}\n"
        f"🆔 Chat ID: <code>{uid}</code>"
    )

def join_page(chat_id, user):
    greeting, clock = now_info()

    text = (
        f"⚡ <b>TEAM SHADOW STRIKER</b>\n\n"
        f"{greeting}, <b>{esc(user.get('first_name'))}</b>! ❤️\n\n"
        f"{identity(user)}\n"
        f"🕒 সময়: <b>{clock}</b>\n\n"
        "বটটি ব্যবহার করতে হলে নিচের লিংকে চাপ দিয়ে "
        "আমাদের Telegram Channel-এ Join করুন।\n\n"
        "Join করার পর Verify বাটনে চাপ দিন।"
    )

    keyboard = {
        "inline_keyboard": [
            [{
                "text": "📢 JOIN OUR CHANNEL",
                "url": CHANNEL_LINK
            }],
            [{
                "text": "✅ VERIFY",
                "callback_data": "verify"
            }]
        ]
    }

    send(chat_id, text, keyboard)

def main_menu(chat_id, user):
    greeting, clock = now_info()

    text = (
        f"⚡ <b>TEAM SHADOW STRIKER</b>\n\n"
        f"{greeting}, <b>{esc(user.get('first_name'))}</b>! ❤️\n\n"
        f"{identity(user)}\n"
        f"🕒 বাংলাদেশ সময়: <b>{clock}</b>\n\n"
        "স্বাগতম! বট ব্যবহার করতে নিচের মেনু থেকে অপশন বেছে নিন।"
    )

    keyboard = {
        "keyboard": [
            [{"text": "👤 Select User"}],
            [{"text": "🆔 My Information"}],
            [{"text": "ℹ️ How To Use"}]
        ],
        "resize_keyboard": True
    }

    send(chat_id, text, keyboard)

def user_list(chat_id):
    with sqlite3.connect(DB) as con:
        rows = con.execute("""
            SELECT user_id, first_name, last_name, username
            FROM profiles
            ORDER BY first_name COLLATE NOCASE
            LIMIT 30
        """).fetchall()

    if not rows:
        send(
            chat_id,
            "এখনো কোনো User পাওয়া যায়নি।\n"
            "প্রথমে কোনো ব্যক্তির Forward করা Message পাঠান।"
        )
        return

    buttons = []

    for uid, first, last, username in rows:
        name = (first + " " + last).strip() or str(uid)
        if username:
            name += " (@" + username + ")"

        buttons.append([{
            "text": "👤 " + name[:45],
            "callback_data": "user:" + str(uid)
        }])

    send(
        chat_id,
        "⚡ <b>SELECT USER</b>\n\n"
        "যার তথ্য দেখতে চান তাকে নির্বাচন করুন:",
        {"inline_keyboard": buttons}
    )

def user_report(chat_id, uid):
    with sqlite3.connect(DB) as con:
        row = con.execute("""
            SELECT user_id, first_name, last_name, username
            FROM profiles WHERE user_id=?
        """, (uid,)).fetchone()

    if not row:
        send(chat_id, "এই User-এর তথ্য পাওয়া যায়নি।")
        return

    uid, first, last, username = row
    name = (first + " " + last).strip() or "Unknown"

    try:
        photos = api("getUserProfilePhotos", {
            "user_id": uid,
            "offset": 0,
            "limit": 1
        })

        count = photos.get("total_count", 0)
        photo_id = None

        if photos.get("photos"):
            photo_id = photos["photos"][0][-1]["file_id"]

    except Exception:
        count = None
        photo_id = None

    report = (
        "⚡ <b>USER INFORMATION</b>\n\n"
        f"👤 Name: <b>{esc(name)}</b>\n\n"
        f"📛 Username: "
        f"{('@' + esc(username)) if username else 'পাওয়া যায়নি'}\n"
        f"🆔 Chat ID: <code>{uid}</code>\n"
        f"🖼️ Profile Photos: "
        f"<b>{count if count is not None else 'পাওয়া যায়নি'}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>Bot From Team Shadow Striker ⚡</b>"
    )

    if photo_id:
        api("sendPhoto", {
            "chat_id": chat_id,
            "photo": photo_id,
            "caption": report,
            "parse_mode": "HTML"
        })
    else:
        send(chat_id, report)

def handle_message(message):
    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    uid = user.get("id")
    text = message.get("text", "")

    if not uid:
        return

    if text.startswith("/start"):
        save_user(user)

        try:
            if is_member(uid):
                main_menu(chat_id, user)
            else:
                join_page(chat_id, user)
        except Exception:
            send(
                chat_id,
                "⚠️ Channel verification করা যাচ্ছে না। "
                "Bot-কে Channel Admin করুন।"
            )
        return

    try:
        if not is_member(uid):
            join_page(chat_id, user)
            return
    except Exception:
        send(chat_id, "Channel verification ব্যর্থ হয়েছে।")
        return

    if text == "👤 Select User":
        user_list(chat_id)
        return

    if text == "🆔 My Information":
        save_user(user)
        user_report(chat_id, uid)
        return

    if text == "ℹ️ How To Use":
        send(
            chat_id,
            "কোনো User-এর Forward করা Message পাঠান।\n"
            "তারপর Select User থেকে তাকে নির্বাচন করুন।\n\n"
            "শুধু Telegram API-তে উপলব্ধ তথ্য দেখানো হবে।"
        )
        return

    origin = message.get("forward_origin", {})

    if origin.get("type") == "user":
        forwarded_user = origin.get("sender_user", {})
        if forwarded_user.get("id"):
            save_user(forwarded_user)
            send(
                chat_id,
                "✅ User তালিকায় যোগ হয়েছে!\n\n"
                "এখন 👤 Select User চাপুন।"
            )
            return

    send(
        chat_id,
        "কোনো User-এর Forward করা Message পাঠান "
        "অথবা নিচের Menu ব্যবহার করুন।"
    )

@app.route("/")
def home():
    return "Team Shadow Striker Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    callback = data.get("callback_query")

    if callback:
        try:
            uid = callback["from"]["id"]
            chat_id = callback["message"]["chat"]["id"]
            action = callback.get("data", "")

            api("answerCallbackQuery", {
                "callback_query_id": callback["id"]
            })

            if not is_member(uid):
                user = callback["from"]
                join_page(chat_id, user)

            elif action == "verify":
                main_menu(chat_id, callback["from"])

            elif action.startswith("user:"):
                selected_id = int(action.split(":", 1)[1])
                user_report(chat_id, selected_id)

        except Exception:
            return jsonify({"ok": False}), 500

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
