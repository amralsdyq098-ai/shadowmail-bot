import telebot
import requests
import random
import string
import time
import os
from flask import Flask, request

TOKEN = os.environ.get("TOKEN", "8445270867:AAF6H50J64se-KW3z00sa8DYsQlPoiMJmj0")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_data = {}

# دومينات قصيرة
SHORT_DOMAINS = ["hi2.in", "nut.cc", "uk2.net", "got.sh"]

def generate_email():
    """توليد إيميل قصير"""
    try:
        username = ''.join(random.choices(string.ascii_lowercase, k=5))
        domain = random.choice(SHORT_DOMAINS)
        email = f"{username}@{domain}"
        res = requests.get(f"https://www.guerrillamail.com/ajax.php?f=set_email_user&email_user={username}&lang=en&sid=", timeout=10)
        data = res.json()
        sid = data.get("sid_token", "")
        real_email = data.get("email_addr", email)
        return real_email, sid
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def set_email(username):
    """تعيين إيميل مخصص قصير"""
    try:
        username = username[:8]  # 8 أحرف بس
        res = requests.get(f"https://www.guerrillamail.com/ajax.php?f=set_email_user&email_user={username}&lang=en&sid=", timeout=10)
        data = res.json()
        email = data.get("email_addr", "")
        sid = data.get("sid_token", "")
        if email:
            return email, sid
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def get_inbox(sid):
    try:
        res = requests.get(f"https://www.guerrillamail.com/ajax.php?f=get_email_list&offset=0&sid_token={sid}", timeout=10)
        return res.json().get("list", [])
    except:
        return []

def get_message(sid, msg_id):
    try:
        res = requests.get(f"https://www.guerrillamail.com/ajax.php?f=fetch_email&email_id={msg_id}&sid_token={sid}", timeout=10)
        return res.json()
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    text = (
        "👤 *Welcome to ShadowMail!*\n\n"
        "🌑 Your anonymous email assistant\n\n"
        "📋 *Commands:*\n"
        "📬 /generate — Random short email\n"
        "✏️ /set name — Custom email\n"
        "📥 /inbox — Check inbox\n"
        "🔄 /refresh — New email\n\n"
        "🚀 Try /generate now!"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    chat_id = message.chat.id
    text = (
        "📋 *Commands:*\n\n"
        "📬 /generate — Random email\n"
        "✏️ /set name — Custom email\n"
        "📥 /inbox — Check inbox\n"
        "🔄 /refresh — New email"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(commands=['generate', 'refresh'])
def generate(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Generating...")
    email, sid = generate_email()
    if email and sid:
        user_data[chat_id] = {"email": email, "sid": sid}
        text = (
            f"✅ *Your email:*\n\n"
            f"`{email}`\n\n"
            f"_(tap to copy)_\n\n"
            f"📥 /inbox — Check messages\n"
            f"✏️ /set name — Custom email"
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
    email, sid = set_email(username)
    if email and sid:
        user_data[chat_id] = {"email": email, "sid": sid}
        text = (
            f"✅ *Your email:*\n\n"
            f"`{email}`\n\n"
            f"_(tap to copy)_\n\n"
            f"📥 /inbox — Check messages"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed. Try another name!")

@bot.message_handler(commands=['inbox'])
def inbox(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "⚠️ No email yet!\nUse /generate first.")
        return
    email = user_data[chat_id]["email"]
    sid = user_data[chat_id]["sid"]
    bot.send_message(chat_id, f"📥 Checking:\n`{email}`", parse_mode="Markdown")
    messages = get_inbox(sid)
    if not messages:
        bot.send_message(chat_id, "📭 Inbox is empty!")
        return
    bot.send_message(chat_id, f"📬 *{len(messages)} message(s):*", parse_mode="Markdown")
    for msg in messages[:5]:
        msg_detail = get_message(sid, msg.get('mail_id'))
        if msg_detail:
            body = msg_detail.get('mail_body', 'No content')[:500]
            text = (
                f"📩 *From:* {msg.get('mail_from', 'Unknown')}\n"
                f"📌 *Subject:* {msg.get('mail_subject', 'No subject')}\n\n"
                f"💬 {body}"
            )
            bot.send_message(chat_id, text, parse_mode="Markdown")
            time.sleep(0.5)

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
