import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- БАЗОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДНЕВНИКОМ ---

def login_to_urtk(login, password):
    """Авторизуется и возвращает объект session, либо None при ошибке."""
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    try:
        res = session.get("https://auth.mephi.ru/login?service=https://marks-urtk.mephi.ru/")
        soup = BeautifulSoup(res.text, 'html.parser')
        token = soup.find('input', {'name': 'authenticity_token'})['value']
        lt = soup.find('input', {'name': 'lt'})['value']
        
        payload = {
            "utf8": "✓", "authenticity_token": token, "lt": lt,
            "service": "https://marks-urtk.mephi.ru/",
            "username": login, "password": password, "commit": "Войти"
        }
        session.post("https://auth.mephi.ru/login", data=payload)
        
        # Проверка успешного входа
        check = session.get("https://marks-urtk.mephi.ru/student/schedule")
        if "Электронный дневник" in check.text:
            return session
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def get_terms(session):
    """Парсит доступные семестры из выпадающего списка."""
    res = session.get("https://marks-urtk.mephi.ru/student/schedule")
    soup = BeautifulSoup(res.text, 'html.parser')
    
    terms = []
    # Ищем элементы выпадающего списка семестров
    for li in soup.find_all('li', attrs={'data-action': 'click->dropdown#select_term'}):
        term_id = li.get('data-value')
        term_name = li.text.strip()
        terms.append({'id': term_id, 'name': term_name})
    return terms

def get_disciplines(session, term_id):
    """Получает список предметов для выбранного семестра."""
    res = session.get(f"https://marks-urtk.mephi.ru/student/disciplines?term_id={term_id}")
    soup = BeautifulSoup(res.text, 'html.parser')
    
    disciplines = []
    for div in soup.find_all('div', class_='discipline__container'):
        title_div = div.find('div', class_='subtitle')
        link_a = div.find('a', class_='link')
        
        if title_div and link_a:
            name = title_div.text.strip()
            # Из ссылки /student/disciplines/532/visits достаем ID (532)
            href = link_a['href']
            disc_id = href.split('/')[3]
            disciplines.append({'id': disc_id, 'name': name})
    return disciplines

def get_grades(session, disc_id):
    """Парсит оценки по выбранному предмету."""
    res = session.get(f"https://marks-urtk.mephi.ru/student/disciplines/{disc_id}/visits")
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
    has_grades = False
    for d, g in zip(dates, grades):
        if g:
            msg += f"✅ {d} — <b>{g}</b>\n"
            has_grades = True
            
    if not has_grades:
        msg += "Оценок пока нет."
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
    
    # Удаляем сообщение с паролем ради безопасности
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    try:
        supabase.table('users').upsert({
            "telegram_id": tg_id, 
            "urtk_login": login, 
            "urtk_password": password
        }).execute()
        bot.send_message(message.chat.id, "✅ Аккаунт привязан! Теперь напиши /marks")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка сохранения: {e}")

@bot.message_handler(commands=['marks'])
def marks(message):
    tg_id = message.from_user.id
    
    # Достаем данные из БД
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        if not response.data:
            bot.send_message(message.chat.id, "Сначала привяжи аккаунт через /login")
            return
        user_data = response.data[0]
        login, password = user_data['urtk_login'], user_data['urtk_password']
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка БД: {e}")
        return

    msg = bot.send_message(message.chat.id, "⏳ Загружаю семестры...")
    session = login_to_urtk(login, password)
    
    if not session:
        bot.edit_message_text("❌ Ошибка входа. Возможно, пароль изменился. Попробуй /login заново.", message.chat.id, msg.message_id)
        return
        
    terms = get_terms(session)
    if not terms:
        bot.edit_message_text("Не удалось найти семестры.", message.chat.id, msg.message_id)
        return

    # Создаем кнопки семестров
    markup = InlineKeyboardMarkup()
    for term in terms:
        markup.add(InlineKeyboardButton(text=term['name'], callback_data=f"term_{term['id']}"))

    bot.edit_message_text("Выбери семестр:", message.chat.id, msg.message_id, reply_markup=markup)

# --- ОБРАБОТКА НАЖАТИЙ НА КНОПКИ ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    tg_id = call.from_user.id
    
    # Получаем логин/пароль
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        user_data = response.data[0]
        login, password = user_data['urtk_login'], user_data['urtk_password']
    except Exception:
        bot.answer_callback_query(call.id, "Ошибка данных. Напиши /login")
        return

    # 1. Пользователь выбрал семестр
    if call.data.startswith('term_'):
        term_id = call.data.split('_')[1]
        bot.edit_message_text("⏳ Загружаю предметы...", call.message.chat.id, call.message.message_id)
        
        session = login_to_urtk(login, password)
        disciplines = get_disciplines(session, term_id)
        
        markup = InlineKeyboardMarkup()
        # Группируем по 1 кнопке в ряд (названия длинные)
        for d in disciplines:
            # Обрезаем слишком длинные названия для кнопки
            btn_text = d['name'] if len(d['name']) < 40 else d['name'][:37] + "..."
            markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"disc_{d['id']}"))
            
        markup.add(InlineKeyboardButton(text="⬅️ Назад к семестрам", callback_data="back_terms"))
        bot.edit_message_text("Выбери предмет:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # 2. Пользователь выбрал предмет
    elif call.data.startswith('disc_'):
        disc_id = call.data.split('_')[1]
        bot.edit_message_text("⏳ Загружаю оценки...", call.message.chat.id, call.message.message_id)
        
        session = login_to_urtk(login, password)
        grades_text = get_grades(session, disc_id)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="⬅️ Назад к предметам", callback_data="back_terms"))
        
        bot.edit_message_text(grades_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)

    # 3. Кнопка "Назад"
    elif call.data == "back_terms":
        # Перерисовываем сообщение обратно в меню семестров
        bot.edit_message_text("⏳ Загружаю...", call.message.chat.id, call.message.message_id)
        session = login_to_urtk(login, password)
        terms = get_terms(session)
        
        markup = InlineKeyboardMarkup()
        for term in terms:
            markup.add(InlineKeyboardButton(text=term['name'], callback_data=f"term_{term['id']}"))
            
        bot.edit_message_text("Выбери семестр:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
