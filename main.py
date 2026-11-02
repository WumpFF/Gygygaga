import os
import time
import re
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from flask import Flask

# ============================================================
# 🔐 WHITELIST — добавляйте сюда ID через запятую
# ============================================================
ALLOWED_IDS = {
    1807940916,   # ты
    # 123456789,  # пример: друг
    # 987654321,  # пример: второй друг
}

def is_allowed(tg_id):
    return tg_id in ALLOWED_IDS

def owner_only(func):
    """Декоратор для message_handler: пропускает только ALLOWED_IDS"""
    def wrapper(message, *args, **kwargs):
        if not message.from_user or not is_allowed(message.from_user.id):
            return  # молча игнорируем
        return func(message, *args, **kwargs)
    return wrapper

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

# --- СЛОВАРЬ СОКРАЩЕНИЙ ---
ABBR_MAP = {
    "архитектура аппаратных средств": "ААС", "безопасность жизнедеятельности": "БЖД", "внедрение и поддержка компьютерных систем": "ВиПКС", "графический дизайн и мультимедиа": "ГДиМ", "дискретная математика с элементами математической логики": "ДМЭМЛ", "инструментальные средства разработки программного обеспечения": "ИСРПО", "информационные технологии": "ИТ", "иностранный язык в профессиональной деятельности": "ИЯПД", "компьютерные сети": "КС", "математическое моделирование": "ММ", "основы алгоритмизации и программирования": "ОАиП", "основы бережливого производства": "ОБП", "обеспечение качества функционирования компьютерных систем": "ОКФКС", "основы проектирования баз данных": "ОПБД", "операционные системы и среды": "ОСиС", "основы философии": "ОснФилософ", "основы web-технологий": "ОТ", "проектирование и разработка веб-приложений": "ПиРП", "правовое обеспечение профессиональной деятельности": "ПОПД", "прикладное программирование": "ПП", "психология общения": "ПсихОбщения", "разработка мобильных приложений": "РМП", "разработка программных модулей": "РПМ", "системное программирование": "СП", "стандартизация, сертификация и техническое документоведение": "ССиТД", "теория вероятностей и математическая статистика": "ТВиМС", "технология разработки и защиты баз данных": "ТРиЗБД", "технология разработки программного обеспечения": "ТРПО", "учебная практика": "УП", "физическая культура": "ФизКультура", "численные методы": "ЧМ", "элементы высшей математики": "ЭВМ", "экономика отрасли": "ЭконОтрасли", 
    "иностранный язык": "ИнЯзык", "основы безопасности и защиты родины": "ОБиЗР", 
    "основы управления персоналом производственного подразделения": "ОУППП", "релейная защита электрооборудования электрических станций, сетей и систем": "РЗСиС", "техническая диагностика и ремонт электрооборудования": "ТДиРЭ", "техническая эксплуатация электрооборудования электрических станций, сетей и систем": "ТЭСиС", 
    "автоматизированные системы управления в электроэнергетических системах": "АСУЭС", "инженерная графика": "ИнжГраф", "измерительная техника": "ИТ", "материаловедение": "Материаловед", "математические методы решения прикладных профессиональных задач": "ММРППЗ", "метрология, стандартизация и сертификация": "МСиС", "наладка электрооборудования подстанций электрических сетей": "НЭЭС", "общая энергетика": "ОбщЭнергет", "основы применения искусственного интеллекта и нейронных сетей в профессиональной деятельности": "ОПИИ", "основы релейной защиты и автоматики": "ОРЗиА", "основы экономики": "ОснЭконом", "основы финансовой грамотности": "ОФГ", "прикладные компьютерные программы в профессиональной деятельности": "ПКППД", "техническая механика": "ТехМех", "техническое обслуживание электрооборудования подстанций электрических сетей": "ТОЭПЭС", "электротехника и электроника": "ЭиЭ", "эксплуатация электротехнического оборудования и трансформаторов": "ЭЭОиТ", 
    "атомные электростанции": "АЭС", "информационные технологии в профессиональной деятельности": "ИТПД", "контроль и защита теплоэнергетического оборудования и технических систем атомных электростанций": "КиЗТОиТСАЭ", "обеспечение безопасности атомных станций": "ОБАС", "основы обеспечения безопасного ведения и контроля технологических процессов хранения отработанного ядерного топлива": "ОБВиКТПХОЯТ", "основы эксплуатации теплоэнергетического оборудования и технических систем атомных электростанций": "ОЭТОиТСАЭ", "основы технического обслуживания основного и вспомогательного теплоэнергетического оборудования и систем атомных электростанций": "ТООиВТОиСАЭ", "управление персоналом": "УпрПерсонал", "электрические и гидравлические машины": "ЭиГМ", "экологические основы природопользования": "ЭОП", "ядерные установки атомных станций": "ЯУАС", 
    "моделирование технологических процессов": "МТП", "организация работ по устранению неполадок и отказов автоматизированного оборудования": "ОРУНиОАО", "осуществление текущего мониторинга состояния систем автоматизации": "ОТМССА", "программирование чпу для автоматизированного оборудования": "ПАО", "разработка, организация и контроль качества работ по монтажу, наладке и техническому обслуживанию систем и средств автоматизации": "РОиККРМНиТОС", "экономика организации": "ЭконОрганиз", 
    "автоматизация проектирования технологических процессов": "АПТП", "атомные электрические станции и их технологическое оборудование": "АЭСиТО", "выполнение работ по настройке и конфигурированию программируемых логических контроллеров": "ВРНиКПЛК", "гидравлические и пневматические системы": "ГиПС", "информационные и цифровые технологии в профессиональной деятельности, с применением нейронных сетей и искусственного интеллекта": "ИЦТПД НСиИИ", "математические методы моделирования производственных процессов": "МММПП", "осуществление анализа структуры технологического процесса и характеристик его элементов для разработки маршрутного технологического процесса на робототехнологическом комплексе": "ОАСТП", "осуществление комплекса пусконаладочных работ и технического обслуживания робототехнологических комплексов с формированием пакета технической документации": "ОКПРиТО", "организация работ по монтажу и наладке средства автоматизации и механизации, текущему мониторингу состояния системы": "ОРМНСА", "охрана труда и бережливое производство": "ОТиБП", "основы ядерной физики и дозиметрических измерений": "ОЯФиДИ", "планирование материально-технического обеспечения эксплуатации робототехнических комплексов": "ПМТОЭРК", "проектирование приспособлений и технологической оснастки": "ППиТО", "программирование систем с числовым программным управлением": "ПСЧПС", "процессы формообразования и инструменты": "ПФиИ", "разработка и тестирование модели системы автоматизации и механизации с формированием пакета технической документации": "РТСА", "технологическое оборудование и приспособления": "ТОиП"
}

NORM_ABBR_MAP = {re.sub(r'[^а-яa-z0-9]', '', k.lower().replace('ё', 'е')): v for k, v in ABBR_MAP.items()}

def get_abbr(name):
    clean_name = re.sub(r'[^а-яa-z0-9]', '', name.lower().replace('ё', 'е'))
    if clean_name in NORM_ABBR_MAP:
        return NORM_ABBR_MAP[clean_name]
    for k, v in NORM_ABBR_MAP.items():
        if len(clean_name) > 20 and len(k) > 20:
            if clean_name[:25] in k or k[:25] in clean_name:
                return v
        elif k in clean_name or clean_name in k:
            return v
    return name[:30] + "..." if len(name) > 30 else name

# ============================================================
# КЭШ + АНТИСПАМ
# ============================================================

_visits_cache = OrderedDict()
_cache_lock = threading.Lock()
CACHE_TTL = 60
CACHE_MAX_SIZE = 50

def _cache_get(key):
    now = time.time()
    with _cache_lock:
        entry = _visits_cache.get(key)
        if not entry:
            return None
        ts, val = entry
        if now - ts >= CACHE_TTL:
            del _visits_cache[key]
            return None
        _visits_cache.move_to_end(key)
        return val

def _cache_set(key, val):
    with _cache_lock:
        _visits_cache[key] = (time.time(), val)
        _visits_cache.move_to_end(key)
        while len(_visits_cache) > CACHE_MAX_SIZE:
            _visits_cache.popitem(last=False)

_cooldowns = {}
_cooldown_lock = threading.Lock()
COOLDOWN_SECONDS = 5

def _check_cooldown(tg_id, command):
    key = (tg_id, command)
    now = time.time()
    with _cooldown_lock:
        last = _cooldowns.get(key, 0)
        if now - last < COOLDOWN_SECONDS:
            return int(COOLDOWN_SECONDS - (now - last)) + 1
        _cooldowns[key] = now
    return None

_session_cache = {}
_session_lock = threading.Lock()
SESSION_TTL = 30

def _session_get(login):
    now = time.time()
    with _session_lock:
        entry = _session_cache.get(login)
        if entry and now - entry[0] < SESSION_TTL:
            return entry[1], entry[2]
    return None, None

def _session_set(login, session, term_id):
    with _session_lock:
        _session_cache[login] = (time.time(), session, term_id)

def _session_drop(login):
    with _session_lock:
        _session_cache.pop(login, None)

# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def is_absence(mark):
    if not mark:
        return False
    norm = re.sub(r'[\s/\\]', '', mark.strip().lower())
    return norm in {'н', 'нб'}

def plural_pairs(n):
    n_abs = abs(n) % 100
    if 11 <= n_abs <= 14:
        return "пар"
    n1 = n_abs % 10
    if n1 == 1:
        return "пара"
    if 2 <= n1 <= 4:
        return "пары"
    return "пар"

def _esc(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ============================================================
# БАЗОВЫЕ ФУНКЦИИ
# ============================================================

def login_and_get_term(login, password):
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
        check.encoding = 'utf-8'
        if "Электронный дневник" in check.text:
            soup_sched = BeautifulSoup(check.text, 'html.parser')
            term_id = "5"
            selected_span = soup_sched.find('span', class_='custom-select__selected')
            if selected_span:
                selected_text = selected_span.text.strip()
                for li in soup_sched.find_all('li'):
                    if 'term' in str(li.get('data-action', '')) and li.text.strip() == selected_text:
                        term_id = li.get('data-value', '5')
                        break
            return session, term_id
        return None, None
    except Exception as e:
        print(f"Login error: {e}")
        return None, None

def get_cached_session(login, password):
    sess, tid = _session_get(login)
    if sess:
        return sess, tid
    sess, tid = login_and_get_term(login, password)
    if sess:
        _session_set(login, sess, tid)
    return sess, tid

def get_disciplines(session, term_id):
    try:
        url = f"https://marks-urtk.mephi.ru/student/disciplines?term_id={term_id}"
        res = session.get(url, timeout=15)
        res.encoding = 'utf-8'
        if "Электронный дневник" not in res.text:
            return None, "Сессия прервалась"
        soup = BeautifulSoup(res.text, 'html.parser')
        disciplines = []
        containers = soup.find_all('div', class_='discipline__container')
        for div in containers:
            title_div = div.find('div', class_='subtitle')
            link_a = div.find('a', class_='link')
            if title_div and link_a:
                name = title_div.text.strip()
                if "классный час" in name.lower() or "кл. час" in name.lower():
                    continue
                href = link_a['href']
                try:
                    disc_id = href.split('/')[3]
                    disciplines.append({'id': disc_id, 'name': name})
                except IndexError:
                    continue
        if not disciplines:
            return [], f"В HTML не найдены предметы (контейнеров: {len(containers)})"
        return disciplines, None
    except requests.exceptions.Timeout:
        return None, "Таймаут при запросе предметов"
    except Exception as e:
        return None, f"Ошибка сети: {e}"

# ============================================================
# ЗАГРУЗКА VISITS
# ============================================================

_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

def _fetch_one(cookies, disc_id):
    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update({'User-Agent': _UA})
    url = f"https://marks-urtk.mephi.ru/student/disciplines/{disc_id}/visits"
    for attempt in range(2):
        try:
            res = s.get(url, timeout=15)
            res.encoding = 'utf-8'
            if 'marks-urtk.mephi.ru' not in res.url:
                return disc_id, None
            if res.status_code == 200:
                return disc_id, res.text
        except Exception:
            pass
        if attempt == 0:
            time.sleep(0.4)
    return disc_id, None

def fetch_visits_parallel(session, login, term_id, disc_ids, max_workers=5):
    cookies = session.cookies.get_dict()
    results = {}
    to_fetch = []
    for disc_id in disc_ids:
        key = (login, term_id, disc_id)
        cached = _cache_get(key)
        if cached is not None:
            results[disc_id] = cached
        else:
            to_fetch.append(disc_id)
    if not to_fetch:
        return results
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_fetch_one, cookies, d) for d in to_fetch]
        for f in as_completed(futures):
            disc_id, html = f.result()
            if html:
                _cache_set((login, term_id, disc_id), html)
            results[disc_id] = html
    return results

def fetch_visits_one(session, login, term_id, disc_id):
    key = (login, term_id, disc_id)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    _, html = _fetch_one(session.cookies.get_dict(), disc_id)
    if html:
        _cache_set(key, html)
    return html

# ============================================================
# ОЦЕНКИ ПРЕДМЕТА
# ============================================================

def get_grades(session, login, term_id, disc_id):
    try:
        html = fetch_visits_one(session, login, term_id, disc_id)
        if not html:
            return "❌ Ошибка при получении оценок: сессия истекла или нет доступа"

        soup = BeautifulSoup(html, 'lxml')

        title_span = soup.find('span', class_='text-bold')
        subject_name = title_span.text.strip() if title_span else "Предмет"
        abbr = get_abbr(subject_name)

        dates = []
        for th in soup.find_all('th', class_='table-date-ceil-header'):
            date_div = th.find('div', class_='date')
            week_div = th.find('div', class_='week')
            if date_div:
                d = date_div.text.strip()
                w = week_div.text.strip() if week_div else ""
                dates.append(f"{d} (пс)" if w == "пс" else d)

        grades = []
        row = soup.find('tr', class_='table-body-row')
        if row:
            for cell in row.find_all('td', class_='table-date-ceil')[1:]:
                grades.append(cell.text.strip())

        avg_grade = ""
        avg_cell = soup.find(class_='average_grade')
        if avg_cell:
            avg_grade = avg_cell.text.strip()

        msg = f"📚 {_esc(abbr)}\n\n"
        has_grades = False
        for d, g in zip(dates, grades):
            if g:
                msg += f"⬝ {_esc(d)} — {_esc(g)}\n"
                has_grades = True

        if not has_grades:
            msg += "Оценок пока нет"
        elif avg_grade:
            msg += f"\n⬝ ср. балл — {_esc(avg_grade)}"

        return msg
    except Exception as e:
        return f"❌ Ошибка при получении оценок: {e}"

# ============================================================
# КОМАНДЫ
# ============================================================

@bot.message_handler(commands=['start'])
@owner_only
def start(message):
    text = (
        "Я — неофициальный бот электронного дневника УрТК НИЯУ МИФИ\n\n"
        "Доступные команды:\n"
        "⬝ /login — авторизоваться\n"
        "⬝ /marks — посмотреть оценки\n"
        "⬝ /gaps — посчитать пропуски"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['login'])
@owner_only
def login_start(message):
    msg = bot.send_message(message.chat.id, "Введите ваш логин от дневника:")
    bot.register_next_step_handler(message, process_login, msg.message_id)

def process_login(message, prompt_id):
    # защита на случай, если кто-то пролез через register_next_step_handler
    if not message.from_user or not is_allowed(message.from_user.id):
        return
    login = message.text.strip()
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    try:
        bot.edit_message_text("Введите ваш пароль:", message.chat.id, prompt_id)
    except:
        pass
    bot.register_next_step_handler(message, process_password, login, prompt_id)

def process_password(message, login, prompt_id):
    if not message.from_user or not is_allowed(message.from_user.id):
        return
    password = message.text.strip()
    tg_id = message.from_user.id
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    try:
        bot.edit_message_text("⏳ Проверяю данные...", message.chat.id, prompt_id)
    except:
        pass

    session, _ = login_and_get_term(login, password)
    if not session:
        try:
            bot.edit_message_text("❌ Ошибка входа\nВведен не правильный логин или пароль", message.chat.id, prompt_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка входа\nВведен не правильный логин или пароль")
        return

    _session_drop(login)

    try:
        supabase.table('users').upsert({
            "telegram_id": tg_id,
            "urtk_login": login,
            "urtk_password": password
        }).execute()
        try:
            bot.edit_message_text("✅ Аккаунт успешно привязан!\nОтправьте /marks для просмотра оценок", message.chat.id, prompt_id)
        except:
            bot.send_message(message.chat.id, "✅ Аккаунт успешно привязан!\nОтправьте /marks для просмотра оценок")
    except Exception as e:
        try:
            bot.edit_message_text(f"Ошибка сохранения в БД: {e}", message.chat.id, prompt_id)
        except:
            pass

@bot.message_handler(commands=['marks'])
@owner_only
def marks(message):
    tg_id = message.from_user.id

    wait = _check_cooldown(tg_id, 'marks')
    if wait:
        bot.send_message(message.chat.id, f"⏳ Подождите {wait} сек перед повторной командой")
        return

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
        session, term_id = get_cached_session(login, password)
        if not session:
            bot.edit_message_text("❌ Ошибка входа\nВозможно, пароль изменился\nВведите /login заново", message.chat.id, msg.message_id)
            return

        disciplines, err = get_disciplines(session, term_id)

        if err == "Сессия прервалась":
            _session_drop(login)
            session, term_id = login_and_get_term(login, password)
            if not session:
                bot.edit_message_text("❌ Ошибка входа\nВозможно, пароль изменился\nВведите /login заново", message.chat.id, msg.message_id)
                return
            _session_set(login, session, term_id)
            disciplines, err = get_disciplines(session, term_id)

        if err:
            bot.edit_message_text(f"❌ Не удалось загрузить список\nПричина: {err}", message.chat.id, msg.message_id)
            return
        if not disciplines:
            bot.edit_message_text("❌ В текущем семестре нет предметов", message.chat.id, msg.message_id)
            return

        markup = InlineKeyboardMarkup()
        for d in disciplines:
            btn_text = get_abbr(d['name'])
            markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"disc_{d['id']}"))

        bot.edit_message_text("📚 Выберите предмет", message.chat.id, msg.message_id, reply_markup=markup)
    except Exception as e:
        bot.edit_message_text(f"❌ Произошла ошибка: {e}", message.chat.id, msg.message_id)

@bot.message_handler(commands=['gaps'])
@owner_only
def gaps(message):
    tg_id = message.from_user.id

    wait = _check_cooldown(tg_id, 'gaps')
    if wait:
        bot.send_message(message.chat.id, f"⏳ Подождите {wait} сек перед повторной командой")
        return

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

    msg = bot.send_message(message.chat.id, "⏳ Считаю пропуски...")

    try:
        session, term_id = get_cached_session(login, password)
        if not session:
            bot.edit_message_text("❌ Ошибка входа\nВозможно, пароль изменился\nВведите /login заново", message.chat.id, msg.message_id)
            return

        disciplines, err = get_disciplines(session, term_id)

        if err == "Сессия прервалась":
            _session_drop(login)
            session, term_id = login_and_get_term(login, password)
            if not session:
                bot.edit_message_text("❌ Ошибка входа\nВозможно, пароль изменился\nВведите /login заново", message.chat.id, msg.message_id)
                return
            _session_set(login, session, term_id)
            disciplines, err = get_disciplines(session, term_id)

        if err:
            bot.edit_message_text(f"❌ Не удалось загрузить список\nПричина: {err}", message.chat.id, msg.message_id)
            return
        if not disciplines:
            bot.edit_message_text("❌ В текущем семестре нет предметов", message.chat.id, msg.message_id)
            return

        disc_ids = [d['id'] for d in disciplines]
        pages = fetch_visits_parallel(session, login, term_id, disc_ids)

        if pages and all(v is None for v in pages.values()):
            _session_drop(login)
            session, term_id = login_and_get_term(login, password)
            if not session:
                bot.edit_message_text("❌ Сессия истекла\nАвторизуйтесь заново /login", message.chat.id, msg.message_id)
                return
            _session_set(login, session, term_id)
            pages = fetch_visits_parallel(session, login, term_id, disc_ids)
            if pages and all(v is None for v in pages.values()):
                bot.edit_message_text("❌ Не удалось загрузить данные\nПопробуйте позже", message.chat.id, msg.message_id)
                return

        total_gaps = 0
        for disc_id, html in pages.items():
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            row = soup.find('tr', class_='table-body-row')
            if row:
                for cell in row.find_all('td', class_='table-date-ceil')[1:]:
                    if is_absence(cell.text.strip()):
                        total_gaps += 1

        hours = total_gaps * 2
        bot.edit_message_text(
            f"⚠️ Пропущено: {hours} ч. ({total_gaps} {plural_pairs(total_gaps)})",
            message.chat.id, msg.message_id
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Произошла ошибка: {e}", message.chat.id, msg.message_id)

# ============================================================
# КНОПКИ
# ============================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # защита: чужие нажатия игнорируем
    if not call.from_user or not is_allowed(call.from_user.id):
        bot.answer_callback_query(call.id)
        return

    tg_id = call.from_user.id
    try:
        response = supabase.table('users').select('*').eq('telegram_id', tg_id).execute()
        user_data = response.data[0]
        login, password = user_data['urtk_login'], user_data['urtk_password']
    except Exception:
        bot.answer_callback_query(call.id, "Ошибка данных. Авторизуйтесь через /login")
        return

    if call.data.startswith('disc_'):
        disc_id = call.data.split('_')[1]
        bot.edit_message_text("⏳ Загружаю оценки...", call.message.chat.id, call.message.message_id)

        try:
            session, term_id = get_cached_session(login, password)
            if not session:
                bot.edit_message_text("❌ Сессия истекла\nАвторизуйтесь заново /login", call.message.chat.id, call.message.message_id)
                return

            grades_text = get_grades(session, login, term_id, disc_id)

            if "сессия истекла" in grades_text.lower():
                _session_drop(login)
                session, term_id = login_and_get_term(login, password)
                if session:
                    _session_set(login, session, term_id)
                    grades_text = get_grades(session, login, term_id, disc_id)

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_disciplines"))
            bot.edit_message_text(grades_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, call.message.message_id)

    elif call.data == "back_to_disciplines":
        bot.edit_message_text("⏳ Загружаю...", call.message.chat.id, call.message.message_id)
        try:
            session, term_id = get_cached_session(login, password)
            if not session:
                bot.edit_message_text("❌ Сессия истекла\nАвторизуйтесь заново /login", call.message.chat.id, call.message.message_id)
                return

            disciplines, err = get_disciplines(session, term_id)
            if err == "Сессия прервалась":
                _session_drop(login)
                session, term_id = login_and_get_term(login, password)
                if not session:
                    bot.edit_message_text("❌ Сессия истекла\nАвторизуйтесь заново /login", call.message.chat.id, call.message.message_id)
                    return
                _session_set(login, session, term_id)
                disciplines, err = get_disciplines(session, term_id)

            if err:
                bot.edit_message_text(f"❌ Ошибка: {err}", call.message.chat.id, call.message.message_id)
                return

            markup = InlineKeyboardMarkup()
            for d in disciplines:
                btn_text = get_abbr(d['name'])
                markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"disc_{d['id']}"))

            bot.edit_message_text("📚 Выберите предмет", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, call.message.message_id)

    bot.answer_callback_query(call.id)

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот запущен...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            if "409" in str(e):
                time.sleep(5)
            else:
                print(f"Ошибка: {e}")
                time.sleep(5)