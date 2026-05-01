import telebot
import requests
import random
import string
import time
import os
import threading
import json
from flask import Flask, request

TOKEN = os.environ.get("TOKEN", "8445270867:AAF6H50J64se-KW3z00sa8DYsQlPoiMJmj0")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "user_data.json"
seen_messages = {}
available_domains = []

# ===== حفظ وتحميل البيانات =====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump({str(k): v for k, v in data.items()}, f)

user_data = load_data()

# ===== Domains =====
def fetch_domains():
    global available_domains
    try:
        res = requests.get("https://api.mail.tm/domains", timeout=10)
        domains = res.json().get("hydra:member", [])
        available_domains = [d["domain"] for d in domains]
        print(f"Available domains: {available_domains}")
    except Exception as e:
        print(f"Error fetching domains: {e}")
        available_domains = []

def create_account(username, domain=None):
    try:
        if not available_domains:
            fetch_domains()
        if not available_domains:
            return None, None

        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        domains_to_try = [domain] if domain else available_domains

        for d in domains_to_try:
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

def generate_email(domain=None):
    username = ''.join(random.choices(string.ascii_lowercase, k=5))
    return create_account(username, domain)

def set_email(username, domain=None):
    return create_account(username[:10].lower(), domain)

def init_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "emails": [],
            "phone": None,
            "custom_domains": [],
            "blocklist": []
        }

# ===== Inbox =====
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
    while True:
        for chat_id, data in list(user_data.items()):
            try:
                blocklist = data.get("blocklist", [])
                emails = data.get("emails", [])
                for entry in emails:
                    token = entry.get("token")
                    email = entry.get("email")
                    email_id = entry.get("id")
                    if not token:
                        continue
                    messages = get_inbox(token)
                    key = f"{chat_id}_{email_id}"
                    if key not in seen_messages:
                        seen_messages[key] = set()
                    for msg in messages:
                        msg_id = msg.get("id")
                        sender = msg.get('from', {}).get('address', '')
                        if any(b in sender for b in blocklist):
                            continue
                        if msg_id and msg_id not in seen_messages[key]:
                            seen_messages[key].add(msg_id)
                            msg_detail = get_message(token, msg_id)
                            if msg_detail:
                                body = msg_detail.get('text', msg_detail.get('html', 'No content'))
                                if body:
                                    body = body[:500]
                                text = (
                                    f"📩 *New Email!*\n\n"
                                    f"📬 *To:* `{email}`\n"
                                    f"👤 *From:* {sender}\n"
                                    f"📌 *Subject:* {msg.get('subject', 'No subject')}\n\n"
                                    f"💬 *Message:*\n{body}"
                                )
                                bot.send_message(chat_id, text, parse_mode="Markdown")
            except Exception as e:
                print(f"Error checking emails for {chat_id}: {e}")
        time.sleep(10)

# ===== Commands =====
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    text = (
        "👤 *Welcome to ShadowMail!*\n\n"
        "🌑 Your anonymous email assistant\n\n"
        "📋 *Commands:*\n"
        "📬 /generate — Get a new fake mail id\n"
        "🪪 /id — To know your current fake mail id\n"
        "✏️ /set name — To setup a custom fake mail id\n"
        "📱 /phone — Add/update recovery phone number\n"
        "🌐 /domain — Manage custom domains\n"
        "🚫 /block — Manage Blocklist\n\n"
        "⚡ Emails arrive automatically in chat!\n\n"
        "🚀 Try /generate now!"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

# ===== /id =====
@bot.message_handler(commands=['id'])
def show_ids(message):
    chat_id = message.chat.id
    if chat_id not in user_data or not user_data[chat_id].get("emails"):
        bot.send_message(chat_id, "⚠️ No emails yet!\nUse /generate first.")
        return
    emails = user_data[chat_id]["emails"]
    text = "📋 *here are the list of fake mail ids you have*\n\n"
    for i, entry in enumerate(emails, 1):
        text += f"{i}. `{entry['email']}` | /delete\\_{entry['id']}\n"
    bot.send_message(chat_id, text, parse_mode="MarkdownV2")

# ===== /generate =====
@bot.message_handler(commands=['generate'])
def generate(message):
    chat_id = message.chat.id
    init_user(chat_id)
    custom_domains = user_data[chat_id].get("custom_domains", [])
    domain = random.choice(custom_domains) if custom_domains else None
    bot.send_message(chat_id, "⏳ Generating...")
    email, token = generate_email(domain)
    if email and token:
        email_id = str(int(time.time()))
        user_data[chat_id]["emails"].append({"id": email_id, "email": email, "token": token})
        save_data(user_data)
        text = (
            f"✅ *Your new email:*\n\n"
            f"`{email}`\n\n_(tap to copy)_\n\n"
            f"⚡ New emails will appear here automatically!\n"
            f"📋 Use /id to see all your emails"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed. Try again!")

# ===== /set =====
@bot.message_handler(commands=['set'])
def set_custom(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ Usage: /set yourname\nExample: /set shadow")
        return
    username = parts[1].lower().strip()[:10]
    custom_domains = user_data[chat_id].get("custom_domains", [])
    domain = random.choice(custom_domains) if custom_domains else None
    bot.send_message(chat_id, f"⏳ Setting up `{username}`...", parse_mode="Markdown")
    email, token = set_email(username, domain)
    if email and token:
        email_id = str(int(time.time()))
        user_data[chat_id]["emails"].append({"id": email_id, "email": email, "token": token})
        save_data(user_data)
        text = (
            f"✅ *Your email:*\n\n"
            f"`{email}`\n\n_(tap to copy)_\n\n"
            f"⚡ New emails will appear here automatically!\n"
            f"📋 Use /id to see all your emails"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed. Try another name!")

# ===== /delete =====
@bot.message_handler(func=lambda m: m.text and m.text.startswith('/delete_'))
def delete_email(message):
    chat_id = message.chat.id
    email_id = message.text.replace('/delete_', '').strip()
    if chat_id not in user_data:
        bot.send_message(chat_id, "⚠️ No emails found.")
        return
    emails = user_data[chat_id].get("emails", [])
    new_emails = [e for e in emails if e["id"] != email_id]
    if len(new_emails) == len(emails):
        bot.send_message(chat_id, "⚠️ Email not found.")
        return
    user_data[chat_id]["emails"] = new_emails
    save_data(user_data)
    bot.send_message(chat_id, "🗑️ Email deleted successfully!")

# ===== /phone =====
@bot.message_handler(commands=['phone'])
def phone(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    current = user_data[chat_id].get("phone")

    if len(parts) < 2:
        if current:
            bot.send_message(chat_id,
                f"📱 *Your recovery phone:*\n`{current}`\n\n"
                "To update: /phone +201234567890\n"
                "To remove: /phone remove",
                parse_mode="Markdown")
        else:
            bot.send_message(chat_id,
                "📱 *No phone number set.*\n\n"
                "To add: /phone +201234567890",
                parse_mode="Markdown")
        return

    if parts[1].lower() == "remove":
        user_data[chat_id]["phone"] = None
        save_data(user_data)
        bot.send_message(chat_id, "✅ Phone number removed.")
        return

    phone_num = parts[1]
    user_data[chat_id]["phone"] = phone_num
    save_data(user_data)
    bot.send_message(chat_id, f"✅ Phone number saved: `{phone_num}`", parse_mode="Markdown")

# ===== /domain =====
@bot.message_handler(commands=['domain'])
def domain_cmd(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    custom_domains = user_data[chat_id].get("custom_domains", [])

    if len(parts) < 2:
        if custom_domains:
            d_list = "\n".join([f"{i+1}. `{d}` | /removedomain_{d}" for i, d in enumerate(custom_domains)])
            bot.send_message(chat_id,
                f"🌐 *Your custom domains:*\n\n{d_list}\n\n"
                "To add: /domain add yourdomain.com\n"
                "To clear all: /domain clear",
                parse_mode="Markdown")
        else:
            bot.send_message(chat_id,
                "🌐 *No custom domains set.*\n\n"
                "To add a domain: /domain add yourdomain.com\n\n"
                "⚠️ Note: The domain must be supported by mail.tm",
                parse_mode="Markdown")
        return

    if parts[1].lower() == "add" and len(parts) >= 3:
        new_domain = parts[2].lower().strip()
        if new_domain in custom_domains:
            bot.send_message(chat_id, "⚠️ Domain already added.")
            return
        user_data[chat_id]["custom_domains"].append(new_domain)
        save_data(user_data)
        bot.send_message(chat_id, f"✅ Domain added: `{new_domain}`\nNew emails will use this domain.", parse_mode="Markdown")

    elif parts[1].lower() == "clear":
        user_data[chat_id]["custom_domains"] = []
        save_data(user_data)
        bot.send_message(chat_id, "✅ All custom domains cleared.")
    else:
        bot.send_message(chat_id, "⚠️ Usage:\n/domain add yourdomain.com\n/domain clear")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/removedomain_'))
def remove_domain(message):
    chat_id = message.chat.id
    domain_to_remove = message.text.replace('/removedomain_', '').strip()
    if chat_id not in user_data:
        return
    domains = user_data[chat_id].get("custom_domains", [])
    if domain_to_remove in domains:
        domains.remove(domain_to_remove)
        user_data[chat_id]["custom_domains"] = domains
        save_data(user_data)
        bot.send_message(chat_id, f"✅ Domain `{domain_to_remove}` removed.", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠️ Domain not found.")

# ===== /block =====
@bot.message_handler(commands=['block'])
def block_cmd(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    blocklist = user_data[chat_id].get("blocklist", [])

    if len(parts) < 2:
        if blocklist:
            b_list = "\n".join([f"{i+1}. `{b}` | /unblock_{b}" for i, b in enumerate(blocklist)])
            bot.send_message(chat_id,
                f"🚫 *Your blocklist:*\n\n{b_list}\n\n"
                "To add: /block sender@example.com\n"
                "To clear all: /block clear",
                parse_mode="Markdown")
        else:
            bot.send_message(chat_id,
                "🚫 *Blocklist is empty.*\n\n"
                "To block a sender: /block sender@example.com\n"
                "Or block a domain: /block @spam.com",
                parse_mode="Markdown")
        return

    if parts[1].lower() == "clear":
        user_data[chat_id]["blocklist"] = []
        save_data(user_data)
        bot.send_message(chat_id, "✅ Blocklist cleared.")
        return

    to_block = parts[1].lower().strip()
    if to_block in blocklist:
        bot.send_message(chat_id, "⚠️ Already in blocklist.")
        return
    user_data[chat_id]["blocklist"].append(to_block)
    save_data(user_data)
    bot.send_message(chat_id, f"✅ Blocked: `{to_block}`\nEmails from this sender will be ignored.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/unblock_'))
def unblock(message):
    chat_id = message.chat.id
    to_unblock = message.text.replace('/unblock_', '').strip()
    if chat_id not in user_data:
        return
    blocklist = user_data[chat_id].get("blocklist", [])
    if to_unblock in blocklist:
        blocklist.remove(to_unblock)
        user_data[chat_id]["blocklist"] = blocklist
        save_data(user_data)
        bot.send_message(chat_id, f"✅ Unblocked: `{to_unblock}`", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠️ Not found in blocklist.")

# ===== Webhook =====
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
    fetch_domains()

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
