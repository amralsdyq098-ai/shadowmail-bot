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

def generate_email():
    try:
        res = requests.get("https://api.mail.tm/domains", timeout=10)
        domain = res.json()["hydra:member"][0]["domain"]
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{username}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        res = requests.post("https://api.mail.tm/accounts", json={"address": email, "password": password}, timeout=10)
        if res.status_code == 201:
            res = requests.post("https://api.mail.tm/token", json={"address": email, "password": password}, timeout=10)
            token = res.json().get("token")
            return email, token
        return None, None
    except Exception as e:
        print(f"Error generating email: {e}")
        return None, None

def get_inbox(token):
    try:
        res = requests.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return res.json().get("hydra:member", [])
    except:
        return []

def get_message(token, msg_id):
    try:
        res = requests.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return res.json()
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    text = (
        "👤 *Welcome to ShadowMail!*\n\n"
        "🌑 Your anonymous email assistant on Telegram\n\n"
        "📋 *Commands:*\n"
        "📬 /generate — Get a new email address\n"
        "📥 /inbox — Check your inbox\n"
        "🔄 /refresh — Get new email address\n"
        "❓ /help — Show all commands\n\n"
        "🚀 Start with /generate to get your email!"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    chat_id = message.chat.id
    text = (
        "📋 *ShadowMail Commands:*\n\n"
        "📬 /generate — Generate new email\n"
        "📥 /inbox — Check your inbox\n"
        "🔄 /refresh — Get a new email address\n"
        "❓ /help — Show this message"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(commands=['generate', 'refresh'])
def generate(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Generating your email address...")
    email, token = generate_email()
    if email and token:
        user_data[chat_id] = {"email": email, "token": token}
        text = (
            f"✅ *Your ShadowMail address:*\n\n"
            f"`{email}`\n\n"
            f"_(tap to copy)_\n\n"
            f"📥 Use /inbox to check for new messages\n"
            f"🔄 Use /refresh to get a new address"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed to generate email. Try again!")

@bot.message_handler(commands=['inbox'])
def inbox(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "⚠️ You don't have an email yet!\nUse /generate first.")
        return
    email = user_data[chat_id]["email"]
    token = user_data[chat_id]["token"]
    bot.send_message(chat_id, f"📥 Checking inbox for:\n`{email}`", parse_mode="Markdown")
    messages = get_inbox(token)
    if not messages:
        bot.send_message(chat_id, "📭 Your inbox is empty!\nWait for emails to arrive.")
        return
    bot.send_message(chat_id, f"📬 *You have {len(messages)} message(s):*", parse_mode="Markdown")
    for msg in messages[:5]:
        msg_detail = get_message(token, msg['id'])
        if msg_detail:
            body = msg_detail.get('text', msg_detail.get('html', 'No content'))
            if body:
                body = body[:500]
            text = (
                f"📩 *New Message*\n\n"
                f"👤 *From:* {msg.get('from', {}).get('address', 'Unknown')}\n"
                f"📌 *Subject:* {msg.get('subject', 'No subject')}\n\n"
                f"💬 *Message:*\n{body}"
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
        print(f"🚀 ShadowMail Bot running with Webhook!")
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        print("🚀 ShadowMail Bot running with Polling...")
        bot.remove_webhook()
        bot.polling(none_stop=True)
