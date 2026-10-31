import os
import threading
from flask import Flask
import telebot

# --- Твой код бота (токен, логика, парсинг) ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бот работает!")

# --- Flask для Render ---
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    bot.polling(none_stop=True)

# Запускаем бота в отдельном потоке
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    # Render передает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)