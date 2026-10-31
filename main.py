import os
import threading
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from flask import Flask

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ЗАГЛУШКА ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ПОЛНЫЙ СЛОВАРЬ СОКРАЩЕНИЙ (ИЗ PDF) ---
ABBR_MAP = {
    # 09.02.07
    "архитектура аппаратных средств": "ААС",
    "безопасность жизнедеятельности": "БЖД",
    "внедрение и поддержка компьютерных систем": "ВиПКС",
    "графический дизайн и мультимедиа": "ГДиМ",
    "дискретная математика с элементами математической логики": "ДМЭМЛ",
    "инструментальные средства разработки программного обеспечения": "ИСРПО",
    "информационные технологии": "ИТ",
    "иностранный язык в профессиональной деятельности": "ИЯПД",
    "компьютерные сети": "КС",
    "математическое моделирование": "ММ",
    "основы алгоритмизации и программирования": "ОАиП",
    "основы бережливого производства": "ОБП",
    "обеспечение качества функционирования компьютерных систем": "ОКФКС",
    "основы проектирования баз данных": "ОПБД",
    "операционные системы и среды": "ОСиС",
    "основы философии": "ОснФилософ",
    "основы web-технологий": "ОТ",
    "проектирование и разработка веб-приложений": "ПиРП",
    "правовое обеспечение профессиональной деятельности": "ПОПД",
    "прикладное программирование": "ПП",
    "психология общения": "ПсихОбщения",
    "разработка мобильных приложений": "РМП",
    "разработка программных модулей": "РПМ",
    "системное программирование": "СП",
    "стандартизация, сертификация и техническое документоведение": "ССиТД",
    "теория вероятностей и математическая статистика": "ТВиМС",
    "технология разработки и защиты баз данных": "ТРиЗБД",
    "технология разработки программного обеспечения": "ТРПО",
    "учебная практика": "УП",
    "физическая культура": "ФизКультура",
    "численные методы": "ЧМ",
    "элементы высшей математики": "ЭВМ",
    "экономика отрасли": "ЭконОтрасли",
    
    # 09.02.11
    "иностранный язык": "ИнЯзык",
    "основы безопасности и защиты родины": "ОБиЗР",
    
    # 13.02.03
    "основы управления персоналом производственного подразделения": "ОУППП",
    "релейная защита электрооборудования электрических станций, сетей и систем": "РЗСиС",
    "техническая диагностика и ремонт электрооборудования": "ТДиРЭ",
    "техническая эксплуатация электрооборудования электрических станций, сетей и систем": "ТЭСиС",
    
    # 13.02.12
    "автоматизированные системы управления в электроэнергетических системах": "АСУЭС",
    "инженерная графика": "ИнжГраф",
    "измерительная техника": "ИТ",
    "материаловедение": "Материаловед",
    "математические методы решения прикладных профессиональных задач": "ММРППЗ",
    "метрология, стандартизация и сертификация": "МСиС",
    "наладка электрооборудования подстанций электрических сетей": "НЭЭС",
    "общая энергетика": "ОбщЭнергет",
    "основы применения искусственного интеллекта и нейронных сетей в профессиональной деятельности": "ОПИИ",
    "основы релейной защиты и автоматики": "ОРЗиА",
    "основы экономики": "ОснЭконом",
    "основы финансовой грамотности": "ОФГ",
    "прикладные компьютерные программы в профессиональной деятельности": "ПКППД",
    "техническая механика": "ТехМех",
    "техническое обслуживание электрооборудования подстанций электрических сетей": "ТОЭПЭС",
    "электротехника и электроника": "ЭиЭ",
    "эксплуатация электротехнического оборудования и трансформаторов": "ЭЭОиТ",
    
    # 14.02.01
    "атомные электростанции": "АЭС",
    "информационные технологии в профессиональной деятельности": "ИТПД",
    "контроль и защита теплоэнергетического оборудования и технических систем атомных электростанций": "КиЗТОиТСАЭ",
    "обеспечение безопасности атомных станций": "ОБАС",
    "основы обеспечения безопасного ведения и контроля технологических процессов хранения отработанного ядерного топлива": "ОБВиКТПХОЯТ",
    "основы эксплуатации теплоэнергетического оборудования и технических систем атомных электростанций": "ОЭТОиТСАЭ",
    "основы технического обслуживания основного и вспомогательного теплоэнергетического оборудования и систем атомных электростанций": "ТООиВТОиСАЭ",
    "управление персоналом": "УпрПерсонал",
    "электрические и гидравлические машины": "ЭиГМ",
    "экологические основы природопользования": "ЭОП",
    "ядерные установки атомных станций": "ЯУАС",
    
    # 15.02.14
    "моделирование технологических процессов": "МТП",
    "организация работ по устранению неполадок и отказов автоматизированного оборудования": "ОРУНиОАО",
    "осуществление текущего мониторинга состояния систем автоматизации": "ОТМССА",
    "программирование чпу для автоматизированного оборудования": "ПАО",
    "разработка, организация и контроль качества работ по монтажу, наладке и техническому обслуживанию систем и средств автоматизации": "РОиККРМНиТОС",
    "экономика организации": "ЭконОрганиз",
    
    # 15.02.18
    "автоматизация проектирования технологических процессов": "АПТП",
    "атомные электрические станции и их технологическое оборудование": "АЭСиТО",
    "выполнение работ по настройке и конфигурированию программируемых логических контроллеров": "ВРНиКПЛК",
    "гидравлические и пневматические системы": "ГиПС",
    "информационные и цифровые технологии в профессиональной деятельности, с применением нейронных сетей и искусственного интеллекта": "ИЦТПД НСиИИ",
    "математические методы моделирования производственных процессов": "МММПП",
    "осуществление анализа структуры технологического процесса и характеристик его элементов для разработки маршрутного технологического процесса на робототехнологическом комплексе": "ОАСТП",
    "осуществление комплекса пусконаладочных работ и технического обслуживания робототехнологических комплексов с формированием пакета технической документации": "ОКПРиТО",
    "организация работ по монтажу и наладке средства автоматизации и механизации, текущему мониторингу состояния системы": "ОРМНСА",
    "охрана труда и бережливое производство": "ОТиБП",
    "основы ядерной физики и дозиметрических измерений": "ОЯФиДИ",
    "планирование материально-технического обеспечения эксплуатации робототехнических комплексов": "ПМТОЭРК",
    "проектирование приспособлений и технологической оснастки": "ППиТО",
    "программирование систем с числовым программным управлением": "ПСЧПС",
    "процессы формообразования и инструменты": "ПФиИ",
    "разработка и тестирование модели системы автоматизации и механизации с формированием пакета технической документации": "РТСА",
    "технологическое оборудование и приспособления": "ТОиП",
    "классный час": "Кл. час"
}

def normalize_text(text):
    """Убирает лишние символы и приводит к нижнему регистру для поиска"""
    return text.lower().replace('ё', 'е').strip().rstrip('.')

def get_abbr(name):
    clean_name = normalize_text(name)
    
    # 1. Поиск точного совпадения
    if clean_name in ABBR_MAP:
        return ABBR_MAP[clean_name]
    
    # 2. Поиск по вхождению (если API добавил лишние слова)
    for full_name, abbr in ABBR_MAP.items():
        if full_name in clean_name or clean_name in full_name:
            return abbr
            
    # 3. Если не нашли, просто обрезаем
    return name[:30] + "..." if len(name) > 30 else name


# --- БАЗОВЫЕ ФУНКЦИИ ---

def login_to_urtk(login, password):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        res = session.get("https://auth.mephi.ru/login?service=https://marks-urtk.mephi.ru/", timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        token = soup.find('input', {'name': 'authenticity_token'})['value']
        lt = soup.find('input', {'name': 'lt'})['value']
        
        payload = {
            "utf8": "✓", "authenticity_token": token, "lt": lt,
            "service": "https://marks-urtk.mephi.ru/",
            "username": login, "password": password, "commit": "Войти"
        }
        session.post("https://auth.mephi.ru/login", data=payload, timeout=15)
        
        check = session.get("https://marks-urtk.mephi.ru/student/schedule", timeout=15)
        if "Электронный дневник" in check.text:
            return session
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def get_current_term_id(session):
    try:
        res = session.get("https://marks-urtk.mephi.ru/student/schedule", timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        selected_span = soup.find('span', class_='custom-select__selected')
        if selected_span:
            selected_text = selected_span.text.strip()
            for li in soup.find_all('li', attrs={'data-action': 'click->dropdown#select_term'}):
                if li.text.strip() == selected_text:
                    return li.get('data-value')
        first_li = soup.find('li', attrs={'data-action': 'click->dropdown#select_term'})
        return first_li.get('data-value') if first_li else "5"
    except:
        return "5"

def get_disciplines(session, term_id):
    try:
        res = session.get(f"https://marks-urtk.mephi.ru/student/disciplines?term_id={term_id}", timeout=15)
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
    except Exception as e:
        print(f"Disc error: {e}")
        return []

def get_grades(session, disc_id):
    try:
        res = session.get(f"https://marks-urtk.mephi.ru/student/disciplines/{disc_id}/visits", timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        title_span = soup.find('span', class_='text-bold')
        subject_name = title_span.text.strip() if title_span else "Предмет"
        
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
    except Exception as e:
        return f"❌ Ошибка при получении оценок: {e}"

# --- КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "Приветствую! Я бот электронного дневника.\n\n"
        "1. Отправьте /login, чтобы авторизоваться.\n"
        "2. Отправьте /marks, чтобы просмотреть оценки."
    )

@bot.message_handler(commands=['login'])
def login_start(message):
    msg = bot.send_message(message.chat.id, "Введите ваш логин от дневника:")
    bot.register_next_step_handler(msg, process_login)

def process_login(message):
    login = message.text.strip()
    msg = bot.send_message(message.chat.id, "Введите ваш пароль:")
    bot.register_next_step_handler(msg, process_password, login)

def process_password(message, login):
    password = message.text.strip()
    tg_id = message.from_user.id
    
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
        bot.send_message(message.chat.id, "✅ Аккаунт успешно привязан! Отправьте /marks для просмотра оценок.")
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

    msg = bot.send_message(message.chat.id, "⏳ Загружаю список предметов...")
    
    try:
        session = login_to_urtk(login, password)
        if not session:
            bot.edit_message_text("❌ Ошибка входа. Возможно, пароль изменился. Авторизуйтесь заново через /login.", message.chat.id, msg.message_id)
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
    except Exception as e:
        bot.edit_message_text(f"❌ Произошла ошибка: {e}", message.chat.id, msg.message_id)

# --- ОБРАБОТКА КНОПОК ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    tg_id = call.from_user.id
    
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        user_data = response.data[0]
        login, password = user_data['urtk_login'], user_data['urtk_password']
    except Exception:
        bot.answer_callback_query(call.id, "Ошибка данных. Авторизуйтесь через /login.")
        return

    if call.data.startswith('disc_'):
        disc_id = call.data.split('_')[1]
        bot.edit_message_text("⏳ Загружаю оценки...", call.message.chat.id, call.message.message_id)
        
        try:
            session = login_to_urtk(login, password)
            grades_text = get_grades(session, disc_id)
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="⬅️ Назад к предметам", callback_data="back_to_disciplines"))
            
            bot.edit_message_text(grades_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, call.message.message_id)

    elif call.data == "back_to_disciplines":
        bot.edit_message_text("⏳ Загружаю...", call.message.chat.id, call.message.message_id)
        
        try:
            session = login_to_urtk(login, password)
            term_id = get_current_term_id(session)
            disciplines = get_disciplines(session, term_id)
            
            markup = InlineKeyboardMarkup()
            for d in disciplines:
                btn_text = get_abbr(d['name'])
                markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"disc_{d['id']}"))
                
            bot.edit_message_text("Выберите предмет из списка ниже:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, call.message.message_id)

    bot.answer_callback_query(call.id)

# --- ЗАПУСК ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Бот запущен...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            if "409" in str(e):
                print("Ошибка 409: запущено два экземпляра. Ждем...")
                time.sleep(5)
            else:
                print(f"Неизвестная ошибка: {e}")
                time.sleep(5)