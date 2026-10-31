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

# --- СЛОВАРЬ СОКРАЩЕНИЙ (согласно вашему PDF) ---
ABBR_MAP = {
    "Автоматизация проектирования технологических процессов": "АПТП",
    "Атомные электрические станции и их технологическое оборудование": "АЭСиТО",
    "Безопасность жизнедеятельности": "БЖД",
    "Выполнение работ по настройке и конфигурированию программируемых логических контроллеров": "ВРНиКПЛК",
    "Гидравлические и пневматические системы": "ГиПС",
    "Инженерная графика": "ИнжГраф",
    "Иностранный язык": "ИнЯзык",
    "Информационные и цифровые технологии в профессиональной деятельности, с применением нейронных сетей и искусственного интеллекта": "ИЦТПД НСиИИ",
    "Иностранный язык в профессиональной деятельности": "ИЯПД",
    "Классный час": "Кл. час",
    "Математические методы моделирования производственных процессов": "МММПП",
    "Метрология, стандартизация и сертификация": "МСиС",
    "Осуществление анализа структуры технологического процесса и характеристик его элементов для разработки маршрутного технологического процесса на робототехнологическом комплексе": "ОАСТП",
    "Основы безопасности и защиты Родины": "ОБиЗР",
    "Осуществление комплекса пусконаладочных работ и технического обслуживания робототехнологических комплексов с формированием пакета технической документации": "ОКПРиТО",
    "Организация работ по монтажу и наладке средства автоматизации и механизации, текущему мониторингу состояния системы": "ОРМНСА",
    "Охрана труда и бережливое производство": "ОТиБП",
    "Основы финансовой грамотности": "ОФГ",
    "Основы ядерной физики и дозиметрических измерений": "ОЯФиДИ",
    "Планирование материально-технического обеспечения эксплуатации робототехнических комплексов": "ПМТОЭРК",
    "Правовое обеспечение профессиональной деятельности": "ПОПД",
    "Проектирование приспособлений и технологической оснастки": "ППиТО",
    "Программирование систем с числовым программным управлением": "ПСЧПС",
    "Процессы формообразования и инструменты": "ПФиИ",
    "Разработка и тестирование модели системы автоматизации и механизации с формированием пакета технической документации": "РТСА",
    "Техническая механика": "ТехМех",
    "Технологическое оборудование и приспособления": "ТОиП",
    "Учебная практика": "УП",
    "Физическая культура": "ФизКультура",
    "Электротехника и электроника": "ЭиЭ",
    "Экологические основы природопользования": "ЭОП"
}

def get_abbr(name):
    """Возвращает сокращение, если есть, иначе обрезает длинное название."""
    if name in ABBR_MAP:
        return ABBR_MAP[name]
    
    name_lower = name.lower()
    for k, v in ABBR_MAP.items():
        if k.lower() in name_lower or name_lower in k.lower():
            return v
            
    return name[:30] + "..." if len(name) > 30 else name

# --- БАЗОВЫЕ ФУНКЦИИ ---

def login_to_urtk(login, password):
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
        
        check = session.get("https://marks-urtk.mephi.ru/student/schedule")
        if "Электронный дневник" in check.text:
            return session
        return None
    except:
        return None

def get_current_term_id(session):
    """Автоматически определяет ID текущего (выбранного по умолчанию) семестра."""
    res = session.get("https://marks-urtk.mephi.ru/student/schedule")
    soup = BeautifulSoup(res.text, 'html.parser')
    
    selected_span = soup.find('span', class_='custom-select__selected')
    if selected_span:
        selected_text = selected_span.text.strip()
        for li in soup.find_all('li', attrs={'data-action': 'click->dropdown#select_term'}):
            if li.text.strip() == selected_text:
                return li.get('data-value')
                
    first_li = soup.find('li', attrs={'data-action': 'click->dropdown#select_term'})
    return first_li.get('data-value') if first_li else "5"

def get_disciplines(session, term_id):
    res = session.get(f"https://marks-urtk.mephi.ru/student/disciplines?term_id={term_id}")
    soup = BeautifulSoup(res.text, 'html.parser')
    
    disciplines = []
    for div in soup.find_all('div', class_='discipline__container'):
        title_div = div.find('div', class_='subtitle')
        link_a = div.find('a', class_='link')
        if title_div and link_a:
            name = title_div.text.strip()
            href = link_a['href']
            disc_id = href.split('/')[3]
            disciplines.append({'id': disc_id, 'name': name})
    return disciplines

def get_grades(session, disc_id):
    res = session.get(f"https://marks-urtk.mephi.ru/student/disciplines/{disc_id}/visits")
    soup = BeautifulSoup(res.text, 'html.parser')
    
    title_span = soup.find('span', class_='text-bold')
    subject_name = title_span.text.strip() if title_span else "Предмет"
    
    # Парсим даты и учитываем "пс"
    dates = []
    for th in soup.find_all('th', class_='table-date-ceil-header'):
        date_div = th.find('div', class_='date')
        week_div = th.find('div', class_='week')
        if date_div:
            d = date_div.text.strip()
            w = week_div.text.strip() if week_div else ""
            if w == "пс":
                dates.append(f"{d} (пс)")
            else:
                dates.append(d)
    
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
        "Приветствую! Я бот электронного дневника.\n\n"
        "1. Отправьте /login, чтобы авторизоваться.\n"
        "2. Отправьте /marks, чтобы просмотреть оценки."
    )

@bot.message_handler(commands=['login'])
def login_start(message):
    msg = bot.send_message(message.chat.id, "Пожалуйста, введите ваш логин от дневника:")
    bot.register_next_step_handler(msg, process_login)

def process_login(message):
    login = message.text.strip()
    msg = bot.send_message(message.chat.id, "Теперь введите ваш пароль:")
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
        bot.send_message(message.chat.id, "✅ Аккаунт успешно привязан! Теперь вы можете просмотреть оценки, отправив команду /marks.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка сохранения: {e}")

@bot.message_handler(commands=['marks'])
def marks(message):
    tg_id = message.from_user.id
    
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        if not response.data:
            bot.send_message(message.chat.id, "Сначала авторизуйтесь с помощью команды /login")
            return
        user_data = response.data[0]
        login, password = user_data['urtk_login'], user_data['urtk_password']
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка базы данных: {e}")
        return

    msg = bot.send_message(message.chat.id, "⏳ Загружаю список предметов для текущего семестра...")
    session = login_to_urtk(login, password)
    
    if not session:
        bot.edit_message_text("❌ Ошибка входа. Возможно, пароль изменился. Пожалуйста, авторизуйтесь заново через /login.", message.chat.id, msg.message_id)
        return
        
    term_id = get_current_term_id(session)
    disciplines = get_disciplines(session, term_id)
    
    if not disciplines:
        bot.edit_message_text("Не удалось загрузить список предметов.", message.chat.id, msg.message_id)
        return

    markup = InlineKeyboardMarkup()
    for d in disciplines:
        btn_text = get_abbr(d['name'])
        markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"disc_{d['id']}"))

    bot.edit_message_text("Выберите предмет из списка ниже:", message.chat.id, msg.message_id, reply_markup=markup)

# --- ОБРАБОТКА КНОПОК ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    tg_id = call.from_user.id
    
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        user_data = response.data[0]
        login, password = user_data['urtk_login'], user_data['urtk_password']
    except Exception:
        bot.answer_callback_query(call.id, "Ошибка данных. Пожалуйста, авторизуйтесь через /login.")
        return

    if call.data.startswith('disc_'):
        disc_id = call.data.split('_')[1]
        bot.edit_message_text("⏳ Загружаю оценки...", call.message.chat.id, call.message.message_id)
        
        session = login_to_urtk(login, password)
        grades_text = get_grades(session, disc_id)
        
        # Кнопка "Назад к предметам"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="⬅️ Назад к предметам", callback_data="back_to_disciplines"))
        
        bot.edit_message_text(grades_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)

    elif call.data == "back_to_disciplines":
        bot.edit_message_text("⏳ Загружаю...", call.message.chat.id, call.message.message_id)
        session = login_to_urtk(login, password)
        term_id = get_current_term_id(session)
        disciplines = get_disciplines(session, term_id)
        
        markup = InlineKeyboardMarkup()
        for d in disciplines:
            btn_text = get_abbr(d['name'])
            markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"disc_{d['id']}"))
            
        bot.edit_message_text("Выберите предмет из списка ниже:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
