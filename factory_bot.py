#!/usr/bin/env python3
# مصنع بوتات التمويل - يصنع بوت تمويل كامل لكل مستخدم عبر Railway API

import os
import telebot
import requests
import json
import time
import sqlite3
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
#   إعدادات المصنع
# ==========================================
FACTORY_TOKEN   = os.environ.get("FACTORY_TOKEN", "ضع_توكن_المصنع_هنا")
RAILWAY_TOKEN   = os.environ.get("RAILWAY_TOKEN", "ضع_railway_token_هنا")
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "ضع_github_token_هنا")
GITHUB_REPO     = os.environ.get("GITHUB_REPO", "nemo40/bot-factory")
RAILWAY_PROJECT = os.environ.get("RAILWAY_PROJECT", "")  # Project ID من Railway
ADMIN_ID        = int(os.environ.get("ADMIN_ID", "0"))

DB_PATH = "factory.db"

bot = telebot.TeleBot(FACTORY_TOKEN, parse_mode="HTML")

# ==========================================
#   قاعدة البيانات
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            bot_token TEXT NOT NULL,
            service_id TEXT,
            status TEXT DEFAULT 'deploying',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_bot(user_id, username, bot_token, service_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO bots (user_id, username, bot_token, service_id) VALUES (?,?,?,?)",
        (user_id, username, bot_token, service_id)
    )
    conn.commit()
    conn.close()

def get_user_bots(user_id):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT bot_token, service_id, status, created_at FROM bots WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows

# ==========================================
#   Railway GraphQL API
# ==========================================
RAILWAY_GQL = "https://backboard.railway.com/graphql/v2"

def railway_headers():
    return {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json",
    }

def get_railway_project_id():
    """جيب Project ID من Railway"""
    query = """
    query {
      me {
        projects {
          edges {
            node { id name }
          }
        }
      }
    }
    """
    r = requests.post(RAILWAY_GQL, json={"query": query}, headers=railway_headers(), timeout=15)
    data = r.json()
    projects = data.get("data", {}).get("me", {}).get("projects", {}).get("edges", [])
    for p in projects:
        if "factory" in p["node"]["name"].lower() or "bot" in p["node"]["name"].lower():
            return p["node"]["id"]
    if projects:
        return projects[0]["node"]["id"]
    return None

def deploy_bot_on_railway(bot_token: str, user_id: int) -> dict:
    """ينشئ service جديد على Railway لكل بوت"""
    project_id = RAILWAY_PROJECT or get_railway_project_id()
    if not project_id:
        return {"ok": False, "error": "لم يتم العثور على مشروع Railway"}

    # إنشاء service جديد من GitHub repo
    mutation = """
    mutation serviceCreate($input: ServiceCreateInput!) {
      serviceCreate(input: $input) {
        id
        name
      }
    }
    """
    service_name = f"bot-{user_id}-{int(time.time())}"
    variables = {
        "input": {
            "projectId": project_id,
            "name": service_name,
            "source": {
                "repo": f"https://github.com/{GITHUB_REPO}"
            }
        }
    }
    r = requests.post(
        RAILWAY_GQL,
        json={"query": mutation, "variables": variables},
        headers=railway_headers(),
        timeout=30
    )
    data = r.json()
    if "errors" in data:
        return {"ok": False, "error": str(data["errors"])}

    service_id = data["data"]["serviceCreate"]["id"]

    # إضافة Environment Variables (BOT_TOKEN)
    env_mutation = """
    mutation variableUpsert($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }
    """
    env_vars = {
        "BOT_TOKEN": bot_token,
        "PYTHONUNBUFFERED": "1"
    }
    for key, value in env_vars.items():
        requests.post(
            RAILWAY_GQL,
            json={
                "query": env_mutation,
                "variables": {
                    "input": {
                        "projectId": project_id,
                        "serviceId": service_id,
                        "name": key,
                        "value": value
                    }
                }
            },
            headers=railway_headers(),
            timeout=15
        )

    # Deploy
    deploy_mutation = """
    mutation serviceInstanceDeploy($serviceId: String!, $projectId: String!) {
      serviceInstanceDeploy(serviceId: $serviceId, projectId: $projectId)
    }
    """
    requests.post(
        RAILWAY_GQL,
        json={
            "query": deploy_mutation,
            "variables": {"serviceId": service_id, "projectId": project_id}
        },
        headers=railway_headers(),
        timeout=15
    )

    return {"ok": True, "service_id": service_id, "service_name": service_name}


# ==========================================
#   حالات المحادثة
# ==========================================
WAITING_TOKEN = {}  # user_id: True

# ==========================================
#   القائمة الرئيسية
# ==========================================
def main_kb():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🛒 صنع بوت تمويل", callback_data="make_bot"))
    kb.row(InlineKeyboardButton("📋 بوتاتي", callback_data="my_bots"))
    kb.row(InlineKeyboardButton("📩 قناة التحديثات", url="https://t.me/your_channel"))
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    WAITING_TOKEN.pop(msg.from_user.id, None)
    text = (
        f"👋 أهلاً <b>{msg.from_user.first_name}</b> في مصنع بوتات التمويل!\n\n"
        "اختر من القائمة أدناه ✨"
    )
    bot.send_message(msg.chat.id, text, reply_markup=main_kb())

@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id

    if call.data == "make_bot":
        WAITING_TOKEN[uid] = True
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("❌ إلغاء", callback_data="cancel"))
        bot.edit_message_text(
            "🤖 <b>صنع بوت تمويل جديد</b>\n\n"
            "أرسل <b>توكن البوت</b> الذي حصلت عليه من @BotFather\n\n"
            "<i>مثال: 123456789:AAExxxxxxxxxxxxxxx</i>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )

    elif call.data == "my_bots":
        rows = get_user_bots(uid)
        if not rows:
            text = "📋 <b>بوتاتي:</b>\n\nلا يوجد بوتات مصنوعة بعد.\nاضغط «صنع بوت» للبدء!"
        else:
            text = "📋 <b>بوتاتك المصنوعة:</b>\n\n"
            for i, (token, sid, status, created) in enumerate(rows, 1):
                token_short = token[:20] + "..."
                status_emoji = "✅" if status == "running" else "⏳"
                text += f"{i}. {status_emoji} <code>{token_short}</code>\n📅 {created[:10]}\n\n"
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("🔙 رجوع", callback_data="back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data in ("back", "cancel"):
        WAITING_TOKEN.pop(uid, None)
        text = f"👋 أهلاً <b>{call.from_user.first_name}</b> في مصنع بوتات التمويل!\n\nاختر من القائمة أدناه ✨"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.from_user.id in WAITING_TOKEN)
def handle_token(msg):
    uid = msg.from_user.id
    token = msg.text.strip()

    if len(token) < 30 or ":" not in token:
        bot.reply_to(msg, "❌ التوكن غير صحيح، أرسله مرة أخرى.\n<i>مثال: 123456789:AAExxxxxxx</i>")
        return

    WAITING_TOKEN.pop(uid, None)

    # رسالة انتظار
    wait_msg = bot.send_message(
        msg.chat.id,
        "⏳ <b>جاري إنشاء وتشغيل بوتك...</b>\n\nقد يستغرق هذا دقيقة واحدة ☕"
    )

    # Deploy على Railway
    result = deploy_bot_on_railway(token, uid)

    if result["ok"]:
        save_bot(uid, msg.from_user.username or "", token, result["service_id"])

        # استخراج يوزرنيم البوت من التوكن
        try:
            r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            bot_info = r.json()
            bot_username = "@" + bot_info["result"]["username"] if bot_info.get("ok") else "البوت"
        except:
            bot_username = "البوت"

        bot.delete_message(msg.chat.id, wait_msg.message_id)

        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton(f"🚀 دخول للبوت مباشر", url=f"https://t.me/{bot_username.lstrip('@')}"))
        kb.row(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back"))

        bot.send_message(
            msg.chat.id,
            f"✅ <b>تم إنشاء بوتك بنجاح!</b>\n\n"
            f"🤖 البوت: <b>{bot_username}</b>\n"
            f"🔄 جاري التشغيل... قد يأخذ دقيقتين للبدء\n\n"
            f"• ملاحظة: فعّل الاشتراك التلقائي عشان بوتك ميقفش من لوحة الأدمن",
            reply_markup=kb
        )

        # إشعار الأدمن
        if ADMIN_ID:
            bot.send_message(
                ADMIN_ID,
                f"🆕 بوت جديد تم صنعه!\n"
                f"👤 المستخدم: {msg.from_user.first_name} ({uid})\n"
                f"🤖 البوت: {bot_username}\n"
                f"🔑 Service ID: {result['service_id']}"
            )
    else:
        bot.delete_message(msg.chat.id, wait_msg.message_id)
        bot.send_message(
            msg.chat.id,
            f"❌ <b>حدث خطأ أثناء الإنشاء</b>\n\n{result.get('error', 'خطأ غير معروف')}\n\nحاول مرة أخرى.",
            reply_markup=main_kb()
        )


@bot.message_handler(func=lambda m: True)
def fallback(msg):
    bot.reply_to(msg, "استخدم /start لفتح القائمة 🏠")


# ==========================================
#   تشغيل المصنع
# ==========================================
if __name__ == "__main__":
    init_db()
    print("✅ مصنع البوتات شغّال!")
    bot.infinity_polling()
