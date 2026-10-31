import os
import telebot
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ЛОГИКА ПАРСИНГА (принимает логин и пароль) ---
def get_grades(login, password):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    try:
        # Авторизация
        res = session.get("https://auth.mephi.ru/login?service=https://marks-urtk.mephi.ru/")
        soup = BeautifulSoup(res.text, 'html.parser')
        token = soup.find('input', {'name': 'authenticity_token'})['value']
        lt = soup.find('input', {'name': 'lt'})['value']
        
        payload = {
            "utf8": "✓", "authenticity_token": token, "lt": lt,
            "service": "https://marks-urtk.mephi.ru/",
            "username": login, "password": password, "commit": "Войти"
        }
        post_res = session.post("https://auth.mephi.ru/login", data=payload)
        
        # Проверка, правильный ли пароль
        if "Электронный дневник" not in session.get("https://marks-urtk.mephi.ru/student/schedule").text:
            return "❌ Неверный логин или пароль от дневника."
            
    except Exception as e:
        return f"❌ Ошибка авторизации: {e}"

    # Парсинг (для примера берем предмет 532)
    url = "https://marks-urtk.mephi.ru/student/disciplines/532/visits"
    res = session.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    title_span = soup.find('span', class_='text-bold')
    subject_name = title_span.text.strip() if title_span else "Предмет"
    
    dates = [th.find('div', class_='date').text for th in soup.find_all('th', class_='table-date-ceil-header') if th.find('div', class_='date')]
    
    grades = []
    row = soup.find('tr', class_='table-body-row')
    if row:
        cells = row.find_all('td', class_='table-date-ceil')[1:]
        for cell in cells:
            grades.append(cell.text.strip())

    msg = f"📚 <b>{subject_name}</b>\n\n"
    for d, g in zip(dates, grades):
        if g:
            msg += f"✅ {d} — <b>{g}</b>\n"
    return msg

# --- КОМАНДЫ БОТА ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "Привет! Я бот дневника.\n\n"
        "1. Напиши /login, чтобы привязать свой аккаунт.\n"
        "2. Напиши /marks, чтобы посмотреть оценки."
    )

@bot.message_handler(commands=['login'])
def login_start(message):
    msg = bot.send_message(message.chat.id, "Введи свой логин от дневника (например, uva001 urtk):")
    bot.register_next_step_handler(msg, process_login)

def process_login(message):
    login = message.text.strip()
    msg = bot.send_message(message.chat.id, "Теперь введи пароль:")
    bot.register_next_step_handler(msg, process_password, login)

def process_password(message, login):
    password = message.text.strip()
    tg_id = message.from_user.id
    
    # Сохраняем в базу
    try:
        supabase.table('users').upsert({
            "telegram_id": tg_id, 
            "urtk_login": login, 
            "urtk_password": password
        }).execute()
        bot.send_message(message.chat.id, "Аккаунт привязан! Теперь напиши /marks")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка сохранения: {e}")

@bot.message_handler(commands=['marks'])
def marks(message):
    tg_id = message.from_user.id
    
    # Достаем данные из базы
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        if not response.data:
            bot.send_message(message.chat.id, "Сначала привяжи аккаунт через /login")
            return
            
        user_data = response.data[0]
        login = user_data['urtk_login']
        password = user_data['urtk_password']
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка БД: {e}")
        return

    bot.send_message(message.chat.id, "Загружаю оценки...")
    result = get_grades(login, password)
    bot.send_message(message.chat.id, result, parse_mode='HTML')

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
