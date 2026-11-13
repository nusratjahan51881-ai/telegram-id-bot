
import os
import html
import sqlite3
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
BASE = f"https://api.telegram.org/bot{TOKEN}"
DB = "users.db"

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

def send(chat_id, text):
    requests.post(
        f"{BASE}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        },
        timeout=15
    )

def esc(value):
    return html.escape(str(value or ""))

def handle_message(message):
    chat_id = message["chat"]["id"]
    origin = message.get("forward_origin")

    if not origin:
        send(chat_id,
             "কোনো মেসেজ Forward করে পাঠাও। "
             "Sender তথ্য Telegram প্রকাশ করলেই দেখাতে পারব।")
        return

    if origin.get("type") != "user":
        send(chat_id,
             "এই Forward-এর মূল প্রেরকের ব্যক্তিগত Chat ID "
             "Telegram প্রকাশ করেনি।")
        return

    user = origin.get("sender_user", {})
    user_id = user.get("id")

    if not user_id:
        send(chat_id, "Sender ID পাওয়া যায়নি।")
        return

    first = user.get("first_name", "")
    last = user.get("last_name", "")
    username = user.get("username", "")

    with sqlite3.connect(DB) as con:
        old = con.execute(
            "SELECT username FROM profiles WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if username:
            con.execute(
                "INSERT OR IGNORE INTO usernames VALUES (?, ?)",
                (user_id, username)
            )

        con.execute("""
        INSERT INTO profiles VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username
        """, (user_id, first, last, username))

        history = con.execute(
            "SELECT username FROM usernames WHERE user_id=?",
            (user_id,)
        ).fetchall()

    previous = [
        row[0] for row in history
        if row[0] and row[0] != username
    ]

    old_text = ", ".join("@" + x for x in previous) or "পাওয়া যায়নি"

    result = (
        "🔎 <b>Forward Lookup Result</b>\n\n"
        f"🆔 Chat ID: <code>{user_id}</code>\n"
        f"👤 Name: {esc(first)} {esc(last)}\n"
        f"📛 Username: {('@' + esc(username)) if username else 'No Username'}\n"
        f"🕘 Previously observed usernames: {esc(old_text)}\n\n"
        "ℹ️ Account creation date ও ফোন নম্বর "
        "Telegram এই Forward থেকে দেয় না।"
    )

    send(chat_id, result)

@app.route("/")
def home():
    return "Telegram Forward Lookup Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    message = data.get("message")

    if message:
        try:
            handle_message(message)
        except Exception:
            return jsonify({"ok": False}), 500

    return jsonify({"ok": True})

db_init()

# Automatically register the Telegram webhook on Render.
if TOKEN and os.environ.get("RENDER_EXTERNAL_URL"):
    try:
        requests.post(
            f"{BASE}/setWebhook",
            json={
                "url": os.environ["RENDER_EXTERNAL_URL"].rstrip("/") + "/webhook"
            },
            timeout=15
        )
    except requests.RequestException:
        pass
