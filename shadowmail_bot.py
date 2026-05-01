import telebot
import requests
import random
import string
import time
import os
import threading
import json
import re
from flask import Flask, request
from telebot import types

TOKEN = os.environ.get("TOKEN", "8445270867:AAF6H50J64se-KW3z00sa8DYsQlPoiMJmj0")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "user_data.json"
seen_messages = {}
available_domains = []

# ======= TRANSLATIONS =======
TEXTS = {
    "ar": {
        "welcome": "👤 أهلاً بك في ShadowMail!\n\n🌑 مساعدك للإيميلات المجهولة\n\n📋 الأوامر:\n📬 /generate — إيميل عشوائي جديد\n🪪 /id — عرض إيميلاتك\n✏️ /set اسم — إيميل مخصص\n⏰ /temp 1h — إيميل مؤقت\n📊 /stats — إحصائياتك\n📱 /phone — رقم الاسترداد\n🌐 /domain — الدومينات\n🚫 /block — قائمة الحظر\n\n⚡ الرسايل بتوصلك فوراً!\n\n🚀 جرب /generate دلوقتي!",
        "generating": "⏳ جاري الإنشاء...",
        "new_email": "✅ إيميلك الجديد:\n\n{email}\n\n(اضغط للنسخ)\n\n⚡ الرسايل هتوصلك تلقائياً!\n📋 استخدم /id لعرض كل إيميلاتك",
        "failed": "❌ فشل. حاول تاني!",
        "no_emails": "⚠️ مفيش إيميلات!\nاستخدم /generate الأول.",
        "email_list": "📋 إيميلاتك:\n\n",
        "deleted": "🗑️ تم الحذف!",
        "not_found": "⚠️ مش موجود.",
        "new_mail_notif": "📩 إيميل جديد!\n\n📬 إلى: {to}\n👤 من: {from_}\n📌 الموضوع: {subject}\n\n💬 الرسالة:\n{body}",
        "stats": "📊 إحصائياتك:\n\n📬 عدد الإيميلات: {emails}\n📩 رسايل استُقبلت: {received}\n⏰ إيميلات مؤقتة: {temp}",
        "temp_set": "⏰ إيميل مؤقت!\n\n{email}\n\nهيتحذف بعد {duration}",
        "temp_usage": "⚠️ الاستخدام: /temp 1h أو /temp 30m",
        "copy_btn": "📋 نسخ",
        "delete_btn": "🗑️ حذف",
        "setting_up": "⏳ جاري الإعداد...",
        "temp_deleted": "🗑️ تم حذف الإيميل المؤقت: {email}",
    },
    "en": {
        "welcome": "👤 Welcome to ShadowMail!\n\n🌑 Your anonymous email assistant\n\n📋 Commands:\n📬 /generate — Random email\n🪪 /id — Show your emails\n✏️ /set name — Custom email\n⏰ /temp 1h — Temporary email\n📊 /stats — Your stats\n📱 /phone — Recovery phone\n🌐 /domain — Manage domains\n🚫 /block — Manage blocklist\n\n⚡ Emails arrive instantly!\n\n🚀 Try /generate now!",
        "generating": "⏳ Generating...",
        "new_email": "✅ Your new email:\n\n{email}\n\n(tap to copy)\n\n⚡ New emails will appear here automatically!\n📋 Use /id to see all your emails",
        "failed": "❌ Failed. Try again!",
        "no_emails": "⚠️ No emails yet!\nUse /generate first.",
        "email_list": "📋 Your emails:\n\n",
        "deleted": "🗑️ Email deleted!",
        "not_found": "⚠️ Not found.",
        "new_mail_notif": "📩 New Email!\n\n📬 To: {to}\n👤 From: {from_}\n📌 Subject: {subject}\n\n💬 Message:\n{body}",
        "stats": "📊 Your Stats:\n\n📬 Total emails: {emails}\n📩 Emails received: {received}\n⏰ Temp emails: {temp}",
        "temp_set": "⏰ Temporary Email!\n\n{email}\n\nWill be deleted after {duration}",
        "temp_usage": "⚠️ Usage: /temp 1h or /temp 30m",
        "copy_btn": "📋 Copy",
        "delete_btn": "🗑️ Delete",
        "setting_up": "⏳ Setting up...",
        "temp_deleted": "🗑️ Temp email deleted: {email}",
    }
}

def get_lang(chat_id):
    if chat_id in user_data:
        return user_data[chat_id].get("lang", "en")
    return "en"

def t(chat_id, key, **kwargs):
    lang = get_lang(chat_id)
    text = TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text

def detect_lang(message):
    try:
        lang_code = message.from_user.language_code or "en"
        return "ar" if lang_code.startswith("ar") else "en"
    except:
        return "en"

# ======= DATA =======
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

def init_user(chat_id, lang="en"):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "emails": [], "phone": None,
            "custom_domains": [], "blocklist": [],
            "received_count": 0, "lang": lang
        }
    elif "received_count" not in user_data[chat_id]:
        user_data[chat_id]["received_count"] = 0

# ======= EMAIL PROVIDERS =======
def fetch_mailtm_domains():
    global available_domains
    try:
        res = requests.get("https://api.mail.tm/domains", timeout=10)
        domains = res.json().get("hydra:member", [])
        available_domains = [d["domain"] for d in domains]
        print(f"mail.tm domains: {available_domains}")
    except Exception as e:
        print(f"Error fetching domains: {e}")
        available_domains = []

GUERRILLA_DOMAINS = ["sharklasers.com", "guerrillamail.com", "grr.la", "guerrillamail.org"]

def create_mailtm(username, domain=None):
    try:
        if not available_domains:
            fetch_mailtm_domains()
        if not available_domains:
            return None, None, None
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
                return email, token, "mailtm"
        return None, None, None
    except Exception as e:
        print(f"mail.tm Error: {e}")
        return None, None, None

def create_guerrilla(username):
    try:
        domain = random.choice(GUERRILLA_DOMAINS)
        email = f"{username}@{domain}"
        res = requests.get(f"https://api.guerrillamail.com/ajax.php?f=get_email_address&email_user={username}&domain={domain}", timeout=10)
        if res.status_code == 200:
            return email, None, "guerrilla"
        return None, None, None
    except Exception as e:
        print(f"guerrilla Error: {e}")
        return None, None, None

def get_guerrilla_inbox(email):
    try:
        username = email.split("@")[0]
        domain = email.split("@")[1]
        res = requests.get(f"https://api.guerrillamail.com/ajax.php?f=get_email_list&offset=0&email_user={username}&domain={domain}", timeout=10)
        data = res.json()
        return data.get("list", [])
    except:
        return []

def create_email(username=None, domain=None, provider="auto"):
    if not username:
        username = ''.join(random.choices(string.ascii_lowercase, k=5))
    username = username[:10].lower()

    if provider == "guerrilla":
        return create_guerrilla(username)
    elif provider == "mailtm":
        return create_mailtm(username, domain)
    else:
        # auto: جرب mailtm الأول، لو فشل جرب guerrilla
        email, token, prov = create_mailtm(username, domain)
        if email:
            return email, token, prov
        return create_guerrilla(username)

# ======= INBOX =======
def get_mailtm_inbox(token):
    try:
        res = requests.get("https://api.mail.tm/messages",
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return res.json().get("hydra:member", [])
    except:
        return []

def get_mailtm_message(token, msg_id):
    try:
        res = requests.get(f"https://api.mail.tm/messages/{msg_id}",
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return res.json()
    except:
        return None

def extract_body(msg_detail):
    """استخراج محتوى الإيميل بشكل صح سواء نص أو HTML"""
    # جرب النص الأول
    body = msg_detail.get('text', '') or ''
    body = body.strip()
    
    # لو مفيش نص جرب HTML
    if not body:
        html = msg_detail.get('html', '') or ''
        if html:
            # استخرج الروابط المهمة زي OTP
            links = re.findall(r'https?://[^\s"\'<>]+', html)
            # استخرج الأرقام اللي ممكن تكون OTP
            codes = re.findall(r'\b\d{4,8}\b', html)
            # نظف الـ HTML
            body = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
            body = re.sub(r'<[^>]+>', ' ', body)
            body = re.sub(r'\s+', ' ', body).strip()
            # أضف الروابط المهمة في الآخر
            if links:
                body += '\n\n🔗 Links:\n' + '\n'.join(links[:3])
            if codes:
                body += '\n\n🔢 Codes found: ' + ', '.join(set(codes[:5]))
    
    if not body:
        body = 'No content'
    
    # قصر على 2000 حرف
    if len(body) > 2000:
        body = body[:2000] + '...'
    
    return body

def send_long_message(chat_id, text):
    max_len = 4000
    for i in range(0, len(text), max_len):
        try:
            bot.send_message(chat_id, text[i:i+max_len])
            time.sleep(0.3)
        except:
            pass

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
                    provider = entry.get("provider", "mailtm")
                    key = f"{chat_id}_{email_id}"
                    if key not in seen_messages:
                        seen_messages[key] = set()

                    if provider == "guerrilla":
                        messages = get_guerrilla_inbox(email)
                        for msg in messages:
                            msg_id = str(msg.get("mail_id", ""))
                            sender = msg.get("mail_from", "")
                            if any(b in sender for b in blocklist):
                                continue
                            if msg_id and msg_id not in seen_messages[key]:
                                seen_messages[key].add(msg_id)
                                body = msg.get("mail_excerpt", "No content")[:1000]
                                subject = msg.get("mail_subject", "No subject")
                                notif = t(chat_id, "new_mail_notif",
                                          to=email, from_=sender,
                                          subject=subject, body=body)
                                send_long_message(chat_id, notif)
                                try:
                                    bot.send_sticker(chat_id, "CAACAgIAAxkBAAECqf1mZQABH1v4AAGRvQABLs1LRQABAAECAAL2BhtKAAFQAAFUGQAB3yQE")
                                except:
                                    pass
                                user_data[chat_id]["received_count"] = user_data[chat_id].get("received_count", 0) + 1
                                save_data(user_data)
                    else:
                        if not token:
                            continue
                        messages = get_mailtm_inbox(token)
                        for msg in messages:
                            msg_id = msg.get("id")
                            sender = msg.get('from', {}).get('address', '')
                            if any(b in sender for b in blocklist):
                                continue
                            if msg_id and msg_id not in seen_messages[key]:
                                seen_messages[key].add(msg_id)
                                msg_detail = get_mailtm_message(token, msg_id)
                                if msg_detail:
                                    body = extract_body(msg_detail)
                                    subject = msg.get('subject', 'No subject')
                                    notif = t(chat_id, "new_mail_notif",
                                              to=email, from_=sender,
                                              subject=subject, body=body)
                                    send_long_message(chat_id, notif)
                                    try:
                                        bot.send_sticker(chat_id, "CAACAgIAAxkBAAECqf1mZQABH1v4AAGRvQABLs1LRQABAAECAAL2BhtKAAFQAAFUGQAB3yQE")
                                    except:
                                        pass
                                    user_data[chat_id]["received_count"] = user_data[chat_id].get("received_count", 0) + 1
                                    save_data(user_data)
            except Exception as e:
                print(f"Error checking emails for {chat_id}: {e}")
        time.sleep(3)

# ======= TEMP EMAIL CLEANER =======
def check_temp_emails():
    while True:
        now = time.time()
        for chat_id, data in list(user_data.items()):
            emails = data.get("emails", [])
            to_delete = []
            for entry in emails:
                if entry.get("expires_at") and now > entry["expires_at"]:
                    to_delete.append(entry)
            for entry in to_delete:
                emails.remove(entry)
                try:
                    bot.send_message(chat_id, t(chat_id, "temp_deleted", email=entry["email"]))
                except:
                    pass
            if to_delete:
                user_data[chat_id]["emails"] = emails
                save_data(user_data)
        time.sleep(60)

# ======= INLINE KEYBOARD =======
def email_keyboard(chat_id, email, email_id):
    markup = types.InlineKeyboardMarkup()
    copy_btn = types.InlineKeyboardButton(t(chat_id, "copy_btn"), callback_data=f"copy_{email_id}")
    delete_btn = types.InlineKeyboardButton(t(chat_id, "delete_btn"), callback_data=f"del_{email_id}")
    markup.row(copy_btn, delete_btn)
    return markup

# ======= COMMANDS =======
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    lang = detect_lang(message)
    init_user(chat_id, lang)
    user_data[chat_id]["lang"] = lang
    save_data(user_data)
    bot.send_message(chat_id, t(chat_id, "welcome"))

@bot.message_handler(commands=['generate'])
def generate(message):
    chat_id = message.chat.id
    lang = detect_lang(message)
    init_user(chat_id, lang)
    custom_domains = user_data[chat_id].get("custom_domains", [])
    domain = random.choice(custom_domains) if custom_domains else None
    bot.send_message(chat_id, t(chat_id, "generating"))
    email, token, provider = create_email(domain=domain)
    if email:
        email_id = str(int(time.time()))
        user_data[chat_id]["emails"].append({
            "id": email_id, "email": email,
            "token": token, "provider": provider
        })
        save_data(user_data)
        markup = email_keyboard(chat_id, email, email_id)
        bot.send_message(chat_id, t(chat_id, "new_email", email=email), reply_markup=markup)
    else:
        bot.send_message(chat_id, t(chat_id, "failed"))

@bot.message_handler(commands=['temp'])
def temp_email(message):
    chat_id = message.chat.id
    lang = detect_lang(message)
    init_user(chat_id, lang)
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(chat_id, t(chat_id, "temp_usage"))
        return
    duration_str = parts[1].lower()
    seconds = 0
    if duration_str.endswith('h'):
        try: seconds = int(duration_str[:-1]) * 3600
        except: pass
    elif duration_str.endswith('m'):
        try: seconds = int(duration_str[:-1]) * 60
        except: pass
    if seconds == 0:
        bot.send_message(chat_id, t(chat_id, "temp_usage"))
        return
    bot.send_message(chat_id, t(chat_id, "generating"))
    email, token, provider = create_email()
    if email:
        email_id = str(int(time.time()))
        expires_at = time.time() + seconds
        user_data[chat_id]["emails"].append({
            "id": email_id, "email": email,
            "token": token, "provider": provider,
            "expires_at": expires_at
        })
        save_data(user_data)
        markup = email_keyboard(chat_id, email, email_id)
        bot.send_message(chat_id, t(chat_id, "temp_set", email=email, duration=duration_str), reply_markup=markup)
    else:
        bot.send_message(chat_id, t(chat_id, "failed"))

@bot.message_handler(commands=['id'])
def show_ids(message):
    chat_id = message.chat.id
    if chat_id not in user_data or not user_data[chat_id].get("emails"):
        bot.send_message(chat_id, t(chat_id, "no_emails"))
        return
    emails = user_data[chat_id]["emails"]
    text = t(chat_id, "email_list")
    for i, entry in enumerate(emails, 1):
        expires = ""
        if entry.get("expires_at"):
            remaining = int((entry["expires_at"] - time.time()) / 60)
            expires = f" ⏰ {remaining}m" if remaining > 0 else " ⏰ expired"
        text += f"{i}. {entry['email']}{expires}\n"
        markup = email_keyboard(chat_id, entry['email'], entry['id'])
        if i == len(emails):
            bot.send_message(chat_id, text, reply_markup=markup)
        else:
            bot.send_message(chat_id, f"{i}. {entry['email']}{expires}", reply_markup=markup)
            text = ""

@bot.message_handler(commands=['set'])
def set_custom(message):
    chat_id = message.chat.id
    lang = detect_lang(message)
    init_user(chat_id, lang)
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ /set yourname")
        return
    username = parts[1].lower().strip()[:10]
    custom_domains = user_data[chat_id].get("custom_domains", [])
    domain = random.choice(custom_domains) if custom_domains else None
    bot.send_message(chat_id, t(chat_id, "setting_up"))
    email, token, provider = create_email(username=username, domain=domain)
    if email:
        email_id = str(int(time.time()))
        user_data[chat_id]["emails"].append({
            "id": email_id, "email": email,
            "token": token, "provider": provider
        })
        save_data(user_data)
        markup = email_keyboard(chat_id, email, email_id)
        bot.send_message(chat_id, t(chat_id, "new_email", email=email), reply_markup=markup)
    else:
        bot.send_message(chat_id, t(chat_id, "failed"))

@bot.message_handler(commands=['stats'])
def stats(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, t(chat_id, "no_emails"))
        return
    data = user_data[chat_id]
    total_emails = len(data.get("emails", []))
    received = data.get("received_count", 0)
    temp_count = sum(1 for e in data.get("emails", []) if e.get("expires_at"))
    bot.send_message(chat_id, t(chat_id, "stats",
                                emails=total_emails,
                                received=received,
                                temp=temp_count))

@bot.message_handler(commands=['phone'])
def phone(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    current = user_data[chat_id].get("phone")
    if len(parts) < 2:
        msg = f"📱 {current}" if current else "📱 No phone set.\n/phone +201234567890"
        bot.send_message(chat_id, msg)
        return
    if parts[1].lower() == "remove":
        user_data[chat_id]["phone"] = None
        save_data(user_data)
        bot.send_message(chat_id, "✅ Removed.")
        return
    user_data[chat_id]["phone"] = parts[1]
    save_data(user_data)
    bot.send_message(chat_id, f"✅ Saved: {parts[1]}")

@bot.message_handler(commands=['domain'])
def domain_cmd(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    custom_domains = user_data[chat_id].get("custom_domains", [])
    if len(parts) < 2:
        if custom_domains:
            d_list = "\n".join([f"{i+1}. {d}" for i, d in enumerate(custom_domains)])
            bot.send_message(chat_id, f"🌐 Domains:\n{d_list}\n\n/domain add x.com\n/domain clear")
        else:
            bot.send_message(chat_id, "🌐 No domains.\n/domain add x.com")
        return
    if parts[1] == "add" and len(parts) >= 3:
        d = parts[2].lower()
        if d not in custom_domains:
            user_data[chat_id]["custom_domains"].append(d)
            save_data(user_data)
        bot.send_message(chat_id, f"✅ Added: {d}")
    elif parts[1] == "clear":
        user_data[chat_id]["custom_domains"] = []
        save_data(user_data)
        bot.send_message(chat_id, "✅ Cleared.")

@bot.message_handler(commands=['block'])
def block_cmd(message):
    chat_id = message.chat.id
    init_user(chat_id)
    parts = message.text.split()
    blocklist = user_data[chat_id].get("blocklist", [])
    if len(parts) < 2:
        if blocklist:
            b_list = "\n".join([f"{i+1}. {b}" for i, b in enumerate(blocklist)])
            bot.send_message(chat_id, f"🚫 Blocklist:\n{b_list}\n\n/block sender@x.com\n/block clear")
        else:
            bot.send_message(chat_id, "🚫 Empty.\n/block sender@x.com")
        return
    if parts[1] == "clear":
        user_data[chat_id]["blocklist"] = []
        save_data(user_data)
        bot.send_message(chat_id, "✅ Cleared.")
        return
    to_block = parts[1].lower()
    if to_block not in blocklist:
        user_data[chat_id]["blocklist"].append(to_block)
        save_data(user_data)
    bot.send_message(chat_id, f"✅ Blocked: {to_block}")

# ======= CALLBACKS =======
@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_"))
def copy_callback(call):
    chat_id = call.message.chat.id
    email_id = call.data.replace("copy_", "")
    if chat_id in user_data:
        for entry in user_data[chat_id].get("emails", []):
            if entry["id"] == email_id:
                bot.answer_callback_query(call.id, f"📋 {entry['email']}", show_alert=True)
                return
    bot.answer_callback_query(call.id, "⚠️ Not found")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_callback(call):
    chat_id = call.message.chat.id
    email_id = call.data.replace("del_", "")
    if chat_id in user_data:
        emails = user_data[chat_id].get("emails", [])
        user_data[chat_id]["emails"] = [e for e in emails if e["id"] != email_id]
        save_data(user_data)
        bot.answer_callback_query(call.id, "🗑️ Deleted!")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass

# ======= WEBHOOK =======
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
    fetch_mailtm_domains()
    threading.Thread(target=check_new_emails, daemon=True).start()
    threading.Thread(target=check_temp_emails, daemon=True).start()
    if WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL + '/' + TOKEN)
        print("🚀 ShadowMail Bot running with Webhook!")
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    else:
        print("🚀 ShadowMail Bot running with Polling...")
        bot.remove_webhook()
        bot.polling(none_stop=True)
