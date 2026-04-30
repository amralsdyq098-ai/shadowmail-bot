import telebot
import requests
import json
import time

TOKEN = "8445270867:AAFDcQs3VrCr5TklIoShCagQgmDJ8PZEQIc"
bot = telebot.TeleBot(TOKEN)

# تخزين الإيميلات الخاصة بكل يوزر
user_emails = {}

# ==================== مساعد ====================

def generate_email():
    """توليد إيميل جديد من 1secmail"""
    try:
        res = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1")
        email = res.json()[0]
        return email
    except:
        return None

def get_inbox(email):
    """جلب الرسائل من الصندوق"""
    try:
        login, domain = email.split("@")
        res = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}")
        return res.json()
    except:
        return []

def get_message(email, msg_id):
    """جلب رسالة محددة"""
    try:
        login, domain = email.split("@")
        res = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}")
        return res.json()
    except:
        return None

# ==================== الأوامر ====================

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

@bot.message_handler(commands=['generate'])
def generate(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Generating your email address...")
    
    email = generate_email()
    if email:
        user_emails[chat_id] = email
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

@bot.message_handler(commands=['refresh'])
def refresh(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔄 Generating new email address...")
    
    email = generate_email()
    if email:
        user_emails[chat_id] = email
        text = (
            f"✅ *Your new ShadowMail address:*\n\n"
            f"`{email}`\n\n"
            f"_(tap to copy)_\n\n"
            f"📥 Use /inbox to check for new messages"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ Failed. Try again!")

@bot.message_handler(commands=['inbox'])
def inbox(message):
    chat_id = message.chat.id
    
    if chat_id not in user_emails:
        bot.send_message(chat_id, "⚠️ You don't have an email yet!\nUse /generate first.")
        return
    
    email = user_emails[chat_id]
    bot.send_message(chat_id, f"📥 Checking inbox for:\n`{email}`", parse_mode="Markdown")
    
    messages = get_inbox(email)
    
    if not messages:
        bot.send_message(chat_id, "📭 Your inbox is empty!\nWait for emails to arrive.")
        return
    
    bot.send_message(chat_id, f"📬 *You have {len(messages)} message(s):*", parse_mode="Markdown")
    
    for msg in messages[:5]:  # أول 5 رسائل بس
        msg_detail = get_message(email, msg['id'])
        if msg_detail:
            body = msg_detail.get('body', msg_detail.get('textBody', 'No content'))[:500]
            text = (
                f"📩 *New Message*\n\n"
                f"👤 *From:* {msg.get('from', 'Unknown')}\n"
                f"📌 *Subject:* {msg.get('subject', 'No subject')}\n"
                f"📅 *Date:* {msg.get('date', 'Unknown')}\n\n"
                f"💬 *Message:*\n{body}"
            )
            bot.send_message(chat_id, text, parse_mode="Markdown")
            time.sleep(0.5)

# ==================== تشغيل البوت ====================

print("🚀 ShadowMail Bot is running...")
bot.polling(none_stop=True)
