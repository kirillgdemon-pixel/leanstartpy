import os
import threading
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice

# ---------- КОНФИГ ----------
BOT_TOKEN = os.environ.get("8710607522:AAH0Mg7UOADPsB7tcqAxuXXP0B5Q-SYsYZQ")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")

# URL вашего HTML-сайта (должен быть HTTPS, например, https://leanstart.netlify.app)
# Если сайт статический, укажите его полный адрес
SITE_URL = os.environ.get("SITE_URL", "https://leanstart.netlify.app")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

# ---------- ФУНКЦИЯ СОЗДАНИЯ ИНВОЙСА ----------
def create_stars_invoice_link(amount: int) -> str:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
    payload = {
        "title": "Поддержка LeanStart",
        "description": f"Вы отправляете {amount} Telegram Stars в благодарность за бесплатные курсы.",
        "payload": f"donation_{amount}",
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": f"LeanStart donation ({amount} ⭐)", "amount": amount}]
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get("ok"):
        return data["result"]
    else:
        raise Exception(f"Telegram API error: {data.get('description')}")

# ---------- ЭНДПОИНТ ДЛЯ ВАШЕГО САЙТА (MINI APP) ----------
@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({"ok": False, "error": "Missing amount"}), 400
    try:
        stars = int(data['amount'])
        if stars < 1:
            raise ValueError
    except:
        return jsonify({"ok": False, "error": "Amount must be a positive integer"}), 400

    try:
        invoice_link = create_stars_invoice_link(stars)
        return jsonify({"ok": True, "invoice_link": invoice_link})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/health')
def health():
    return "OK"

# ---------- КОМАНДА /start С КНОПКОЙ MINI APP ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаём клавиатуру с кнопкой, открывающей ваш сайт как Mini App
    markup = InlineKeyboardMarkup()
    web_app_btn = InlineKeyboardButton(
        text="🌟 Открыть LeanStart",
        web_app=WebAppInfo(url=SITE_URL)
    )
    markup.add(web_app_btn)
    bot.send_message(
        message.chat.id,
        "Добро пожаловать в LeanStart!\nНажмите кнопку ниже, чтобы открыть приложение и поддержать проект Telegram Stars ⭐",
        reply_markup=markup
    )

# ---------- ОБРАБОТКА ПЛАТЕЖЕЙ ----------
@bot.pre_checkout_query_handler(func=lambda query: True)
def on_pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def on_successful_payment(message):
    stars = message.successful_payment.total_amount
    bot.send_message(
        message.chat.id,
        f"🎉 Спасибо за вашу поддержку! Вы отправили {stars} Telegram Stars.\nВаши средства уже зачислены на счёт проекта LeanStart. ❤️"
    )

# ---------- ЗАПУСК БОТА В ПОТОКЕ И FLASK ----------
def run_bot():
    bot.infinity_polling(skip_pending=True)

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
