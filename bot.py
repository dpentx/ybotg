from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import json
import os
from upstash_redis import Redis

# Upstash Redis bağlantısı
redis = Redis(
    url=os.getenv('UPSTASH_REDIS_REST_URL'),
    token=os.getenv('UPSTASH_REDIS_REST_TOKEN')
)

DERSLER = {
    'mat': 'Matematik',
    'geo': 'Geometri',
    'fiz': 'Fizik',
    'kim': 'Kimya',
    'bio': 'Biyoloji',
    'tar': 'Tarih',
    'cog': 'Coğrafya',
    'fel': 'Felsefe',
    'din': 'Din Kültürü',
    'tur': 'Türkçe',
    'sos': 'Sosyal Bilimler',
    'ing': 'İngilizce'
}

def get_user_data(user_id):
    """Kullanıcı verisini Redis'ten al"""
    data = redis.get(f"user:{user_id}")
    if data:
        return json.loads(data)
    return {
        'gunluk': {},
        'denemeler': [],
        'current_deneme': None
    }

def save_user_data(user_id, data):
    """Kullanıcı verisini Redis'e kaydet"""
    redis.set(f"user:{user_id}", json.dumps(data))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 YKS Takip Botuna Hoş Geldin!\n\n"
        "📚 Komutlar:\n"
        "/gunluk - Günlük ders çalışma kaydet\n"
        "/deneme - Deneme sınavı sonucu gir\n"
        "/durum - Ay sonu özet rapor\n"
        "/clear - Tüm verileri temizle\n\n"
        "Başlamak için /gunluk veya /deneme komutunu kullan!"
    )

async def gunluk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for i, (kod, ders) in enumerate(DERSLER.items()):
        row.append(InlineKeyboardButton(ders, callback_data=f"ders_{kod}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📖 Hangi dersi çalıştın?",
        reply_markup=reply_markup
    )

async def ders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ders_kod = query.data.split('_')[1]
    user_id = query.from_user.id
    
    context.user_data['selected_ders'] = ders_kod
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Doğru +", callback_data=f"dogru_add_{ders_kod}"),
            InlineKeyboardButton("❌ Yanlış +", callback_data=f"yanlis_add_{ders_kod}"),
            InlineKeyboardButton("⭕ Boş +", callback_data=f"bos_add_{ders_kod}")
        ],
        [
            InlineKeyboardButton("📊 Kaydet & Bitir", callback_data=f"save_{ders_kod}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    data = get_user_data(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if today not in data['gunluk']:
        data['gunluk'][today] = {}
    if ders_kod not in data['gunluk'][today]:
        data['gunluk'][today][ders_kod] = {'d': 0, 'y': 0, 'b': 0}
    
    save_user_data(user_id, data)
    stats = data['gunluk'][today][ders_kod]
    
    await query.edit_message_text(
        f"📚 {DERSLER[ders_kod]}\n\n"
        f"✅ Doğru: {stats['d']}\n"
        f"❌ Yanlış: {stats['y']}\n"
        f"⭕ Boş: {stats['b']}\n",
        reply_markup=reply_markup
    )

async def soru_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action = parts[0]
    ders_kod = parts[2]
    user_id = query.from_user.id
    
    data = get_user_data(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if action == 'dogru':
        data['gunluk'][today][ders_kod]['d'] += 1
    elif action == 'yanlis':
        data['gunluk'][today][ders_kod]['y'] += 1
    elif action == 'bos':
        data['gunluk'][today][ders_kod]['b'] += 1
    
    save_user_data(user_id, data)
    stats = data['gunluk'][today][ders_kod]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Doğru +", callback_data=f"dogru_add_{ders_kod}"),
            InlineKeyboardButton("❌ Yanlış +", callback_data=f"yanlis_add_{ders_kod}"),
            InlineKeyboardButton("⭕ Boş +", callback_data=f"bos_add_{ders_kod}")
        ],
        [
            InlineKeyboardButton("📊 Kaydet & Bitir", callback_data=f"save_{ders_kod}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📚 {DERSLER[ders_kod]}\n\n"
        f"✅ Doğru: {stats['d']}\n"
        f"❌ Yanlış: {stats['y']}\n"
        f"⭕ Boş: {stats['b']}\n",
        reply_markup=reply_markup
    )

async def save_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Kaydedildi!")
    
    ders_kod = query.data.split('_')[1]
    user_id = query.from_user.id
    data = get_user_data(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    stats = data['gunluk'][today][ders_kod]
    
    await query.edit_message_text(
        f"✅ {DERSLER[ders_kod]} kaydedildi!\n\n"
        f"✅ Doğru: {stats['d']}\n"
        f"❌ Yanlış: {stats['y']}\n"
        f"⭕ Boş: {stats['b']}\n\n"
        f"Başka ders eklemek için /gunluk yazabilirsin."
    )

async def deneme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for i, (kod, ders) in enumerate(DERSLER.items()):
        row.append(InlineKeyboardButton(ders, callback_data=f"deneme_{kod}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("📊 Denemeyi Bitir", callback_data="deneme_finish")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_id = update.message.user.id
    data = get_user_data(user_id)
    data['current_deneme'] = {
        'tarih': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'sonuclar': {}
    }
    save_user_data(user_id, data)
    
    await update.message.reply_text(
        "📝 Deneme Sınavı Girişi\n\n"
        "Dersleri seçerek sonuçları gir:",
        reply_markup=reply_markup
    )

async def deneme_ders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ders_kod = query.data.split('_')[1]
    user_id = query.from_user.id
    data = get_user_data(user_id)
    
    if ders_kod not in data['current_deneme']['sonuclar']:
        data['current_deneme']['sonuclar'][ders_kod] = {'d': 0, 'y': 0, 'b': 0}
    
    save_user_data(user_id, data)
    context.user_data['deneme_ders'] = ders_kod
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Doğru +", callback_data=f"ddeneme_dogru_{ders_kod}"),
            InlineKeyboardButton("❌ Yanlış +", callback_data=f"ddeneme_yanlis_{ders_kod}"),
            InlineKeyboardButton("⭕ Boş +", callback_data=f"ddeneme_bos_{ders_kod}")
        ],
        [
            InlineKeyboardButton("🔙 Geri Dön", callback_data="deneme_back")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    stats = data['current_deneme']['sonuclar'][ders_kod]
    
    await query.edit_message_text(
        f"📚 {DERSLER[ders_kod]} - Deneme\n\n"
        f"✅ Doğru: {stats['d']}\n"
        f"❌ Yanlış: {stats['y']}\n"
        f"⭕ Boş: {stats['b']}\n",
        reply_markup=reply_markup
    )

async def deneme_soru_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action = parts[1]
    ders_kod = parts[2]
    user_id = query.from_user.id
    
    data = get_user_data(user_id)
    
    if action == 'dogru':
        data['current_deneme']['sonuclar'][ders_kod]['d'] += 1
    elif action == 'yanlis':
        data['current_deneme']['sonuclar'][ders_kod]['y'] += 1
    elif action == 'bos':
        data['current_deneme']['sonuclar'][ders_kod]['b'] += 1
    
    save_user_data(user_id, data)
    stats = data['current_deneme']['sonuclar'][ders_kod]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Doğru +", callback_data=f"ddeneme_dogru_{ders_kod}"),
            InlineKeyboardButton("❌ Yanlış +", callback_data=f"ddeneme_yanlis_{ders_kod}"),
            InlineKeyboardButton("⭕ Boş +", callback_data=f"ddeneme_bos_{ders_kod}")
        ],
        [
            InlineKeyboardButton("🔙 Geri Dön", callback_data="deneme_back")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📚 {DERSLER[ders_kod]} - Deneme\n\n"
        f"✅ Doğru: {stats['d']}\n"
        f"❌ Yanlış: {stats['y']}\n"
        f"⭕ Boş: {stats['b']}\n",
        reply_markup=reply_markup
    )

async def deneme_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    row = []
    for i, (kod, ders) in enumerate(DERSLER.items()):
        row.append(InlineKeyboardButton(ders, callback_data=f"deneme_{kod}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("📊 Denemeyi Bitir", callback_data="deneme_finish")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 Deneme Sınavı Girişi\n\n"
        "Dersleri seçerek sonuçları gir:",
        reply_markup=reply_markup
    )

async def deneme_finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Deneme kaydedildi!")
    
    user_id = query.from_user.id
    data = get_user_data(user_id)
    
    deneme = data['current_deneme']
    data['denemeler'].append(deneme)
    data['current_deneme'] = None
    save_user_data(user_id, data)
    
    mesaj = f"✅ Deneme Kaydedildi!\n📅 {deneme['tarih']}\n\n"
    
    toplam_d = toplam_y = toplam_b = 0
    for ders_kod, stats in deneme['sonuclar'].items():
        mesaj += f"📚 {DERSLER[ders_kod]}: {stats['d']}D / {stats['y']}Y / {stats['b']}B\n"
        toplam_d += stats['d']
        toplam_y += stats['y']
        toplam_b += stats['b']
    
    net = toplam_d - (toplam_y * 0.25)
    mesaj += f"\n🎯 Toplam Net: {net:.2f}"
    
    await query.edit_message_text(mesaj)

async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.user.id
    data = get_user_data(user_id)
    
    mesaj = "📊 AY SONU ÖZET RAPOR\n\n"
    
    mesaj += "📖 GÜNLÜK ÇALIŞMALAR\n"
    if data['gunluk']:
        toplam_ders = {}
        for tarih, dersler in data['gunluk'].items():
            for ders_kod, stats in dersler.items():
                if ders_kod not in toplam_ders:
                    toplam_ders[ders_kod] = {'d': 0, 'y': 0, 'b': 0}
                toplam_ders[ders_kod]['d'] += stats['d']
                toplam_ders[ders_kod]['y'] += stats['y']
                toplam_ders[ders_kod]['b'] += stats['b']
        
        for ders_kod, stats in toplam_ders.items():
            net = stats['d'] - (stats['y'] * 0.25)
            mesaj += f"{DERSLER[ders_kod]}: {stats['d']}D/{stats['y']}Y/{stats['b']}B (Net: {net:.1f})\n"
    else:
        mesaj += "Henüz günlük çalışma kaydı yok.\n"
    
    mesaj += "\n📝 DENEMELER\n"
    if data['denemeler']:
        mesaj += f"Toplam {len(data['denemeler'])} deneme çözüldü.\n\n"
        for i, deneme in enumerate(data['denemeler'][-3:], 1):
            toplam_d = sum(s['d'] for s in deneme['sonuclar'].values())
            toplam_y = sum(s['y'] for s in deneme['sonuclar'].values())
            net = toplam_d - (toplam_y * 0.25)
            mesaj += f"{i}. Deneme ({deneme['tarih']}): {net:.2f} Net\n"
    else:
        mesaj += "Henüz deneme kaydı yok.\n"
    
    await update.message.reply_text(mesaj)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.user.id
    redis.delete(f"user:{user_id}")
    await update.message.reply_text("🗑️ Tüm veriler temizlendi!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data.startswith('ders_'):
        await ders_callback(update, context)
    elif query.data.startswith('dogru_') or query.data.startswith('yanlis_') or query.data.startswith('bos_'):
        await soru_callback(update, context)
    elif query.data.startswith('save_'):
        await save_callback(update, context)
    elif query.data.startswith('deneme_') and not query.data.startswith('ddeneme_'):
        if query.data == 'deneme_finish':
            await deneme_finish_callback(update, context)
        elif query.data == 'deneme_back':
            await deneme_back_callback(update, context)
        else:
            await deneme_ders_callback(update, context)
    elif query.data.startswith('ddeneme_'):
        await deneme_soru_callback(update, context)

async def setup_webhook(application: Application):
    """Webhook kurulumu"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        await application.bot.set_webhook(url=webhook_url)

def create_application():
    """Application oluştur"""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gunluk", gunluk))
    application.add_handler(CommandHandler("deneme", deneme))
    application.add_handler(CommandHandler("durum", durum))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    return application

# Vercel için handler
from telegram import Update
import asyncio

application = create_application()

async def handler(request):
    """Vercel serverless function handler"""
    if request.method == "POST":
        update = Update.de_json(await request.json(), application.bot)
        await application.process_update(update)
        return {"statusCode": 200}
    return {"statusCode": 200, "body": "Bot is running"}

# Flask wrapper for Vercel
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Bot is running!"})

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return jsonify({"status": "ok"})

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        asyncio.run(application.bot.set_webhook(url=webhook_url))
        return jsonify({"status": "Webhook set!", "url": webhook_url})
    return jsonify({"error": "WEBHOOK_URL not set"})
