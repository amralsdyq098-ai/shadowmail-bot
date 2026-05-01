import telebot
import requests
import random
import string
import time
import os
import threading
from flask import Flask, request

TOKEN = os.environ.get("TOKEN", "8445270867:AAF6H50J64se-KW3z00sa8DYsQlPoiMJmj0")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_data = {}
seen_messages = {}  # لتتبع الرسايل اللي اتبعتت

DOMAINS = ["hi2.in", "nut.cc", "got.sh", "lol.ovh"]

def create_account(username):
    try:
        domain = random.choice(DOMAINS)
        email = f"{username}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        res = requests.post("https://api.mail.tm/accounts",
                          json={"address": email, "password": password}, timeout=10)
        if res.status_code == 201:
            res2 = requests.post("https://api.mail.tm/token",
                               json={"address": email, "password": password}, timeout=10)
            token = res2.json().get("token")
            return email, token
        else:
            for d in DOMAINS:
                if d != domain:
                    email = f"{username}@{d}"
                    res = requests.post("https://api.mail.tm/accounts",
                                      json={"address": email, "password": password}, timeout=10)
                    if res.status_code == 201:
                        res2 = requests.post("https://api.mail.tm/token",
                                           json={"address": email, "password": password}, timeout=10)
                        token = res2.json().get("token")
                        return email, token
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def generate_email():
    username = ''.join(random.choices(string.ascii_lowercase, k=5))
    return create_account(username)

def set_email(username):
    return create_account(username[:8].lower())

def get_inbox(token):
    try:
        res = requests.get("https://api.mail.tm/messages",
                          headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return res.json().get("hydra:member", [])
    except:
        return []

def get_message(token, msg_id):
    try:
        res = requests.get(f"https://api.mail.tm/messages/{msg_id}",
                          headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return res.json()
    except:
        return None

def check_new_emails():
    """فحص الرسايل الجديدة كل 10 ثواني"""
    while True:
        for chat_id, data in list(user_data.items()):
            try:
                token = data.get("token")
                email = data.get("email")
                if not token:
                    continue
                messages = get_inbox(token)
                if chat_id not in seen_messages:
                    seen_messages[chat_id] = set()
                for msg in messages:
                    msg_id = msg.get("id")
                    if msg_id and msg_id not in seen_messages[chat_id]:
                        seen_messages[chat_id].add(msg_id)
                        msg_detail = get_message(token, msg_id)
                        if msg_detail:
                            body = msg_detail.get('text', msg_detail.get('html', 'No content'))
                            if body:
                                body = body[:500]
                            text = (
                                f"📩 *New Email on* `{email}`\n\n"
                                f"👤 *From:* {msg.get('from', {}).get('address', 'Unknown')}\n"
                                f"📌 *Subject:* {msg.get('subject', 'No subject')}\n\n"
                                f"💬 *Message:*\n{body}"
                            )
                            bot.send_message(chat_id, text, parse_mode="Markdown")
            except Exception as e:
                print(f"Error checking emails: {e}")
        time.sleep(10)

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    text = (
        "👤 *Welcome to ShadowMail!*\n\n"
        "🌑 Your anonymous email assistant\n\n"
        "📋 *Commands:*\n"
        "📬 /generate — Random email\n"
        "✏️ /set name — Custom email\n"
        "🔄 /refresh — New email\n"
        "📧 /myemail — Show current email\n\n"
        "⚡ Emails arrive automatically in chat!\n\n"
        "🚀 Try /generate now!"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(commands=['myemail'])
def myemail(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "⚠️ No email yet!\nUse /generate first.")
        return
    email = user_data[chat_id]["email"]
    bot.send_message(chat_id, f"📬 *Your email:*\n\n`{email}`\n\n_(tap to copy)_", parse_mode="Markdown")

@bot.message_handler(commands=['generate', 'refresh'])
def generate(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Generating...")
    email, token = generate_email()
    if email and token:
        user_data[chat_id] = {"email": email, "token": token}
        seen_messages[chat_id] = set()
        text = (
            f"✅ *Your email:*\n\n"
            f"`{email}`\n\n"
            f"_(tap to copy)_\n\n"
            f"⚡ New emails will appear here automatically!"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed. Try again!")

@bot.message_handler(commands=['set'])
def set_custom(message):
    chat_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ Usage: /set yourname\nExample: /set shadow")
        return
    username = parts[1].lower().strip()[:8]
    bot.send_message(chat_id, f"⏳ Setting up `{username}`...", parse_mode="Markdown")
    email, token = set_email(username)
    if email and token:
        user_data[chat_id] = {"email": email, "token": token}
        seen_messages[chat_id] = set()
        text = (
            f"✅ *Your email:*\n\n"
            f"`{email}`\n\n"
            f"_(tap to copy)_\n\n"
            f"⚡ New emails will appear here automatically!"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed. Try another name!")

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data(as_text=True)
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def index():
    return 'ShadowMail Bot is running!', 200

if __name__ == "__main__":
    # تشغيل thread لفحص الرسايل
    email_thread = threading.Thread(target=check_new_emails, daemon=True)
    email_thread.start()

    if WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL + '/' + TOKEN)
        print("🚀 ShadowMail Bot running with Webhook!")
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        print("🚀 ShadowMail Bot running with Polling...")
        bot.remove_webhook()
        bot.polling(none_stop=True)
