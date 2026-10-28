import hashlib

import io

import numbers

import os

import re

from datetime import date, timedelta


import pandas as pd

import requests

import streamlit as st


MAX_ROWS = 50000

PLACE_DEFAULT = "Местоположение не определено"

NOT_SET = "Не указан"


SENTIMENTS = ["Позитивная", "Нейтральная", "Негативная"]

MSG_TYPES = ["Жалоба", "Вопрос", "Предложение", "Благодарность", "Информация"]

CATEGORIES = [

    "Дороги", "Общественный транспорт", "Освещение", "Мусор и санитария",

    "Водоснабжение", "Отопление", "Газ", "Электричество", "Благоустройство и дворы",

    "Строительство", "Экология", "Безопасность", "Образование", "Здравоохранение",

    "Социальная помощь", "ЖКХ", "Предпринимательство", "Работа городских служб", "Другое",

]

LEVEL_ORDER = {"Критический": 0, "Повышенный": 1, "Средний": 2, "Низкий": 3}


FIELD_LABELS = {
    "text": "Текст сообщения *",
    "date": "Дата и время",
    "source": "Источник",
    "record_type": "Тип записи (пост / комментарий)",
    "author": "Автор",
    "url": "Ссылка",
    "likes": "Лайки / реакции",
    "comments_count": "Количество комментариев",
    "views": "Просмотры",
    "place": "Район / адрес / место",
    "language": "Язык",
    "post_id": "ID публикации",
    "message_id": "ID сообщения",
}


SYNONYMS = {

    "text": ["текст", "комментарий", "комментарии", "коммент", "сообщение", "публикация",

             "содержание", "text", "comment", "message", "content", "body", "caption",

             "мәтін", "пікір", "хабарлама"],

    "date": ["дата", "время", "дата публикации", "date", "time", "datetime", "created",

             "timestamp", "published", "уақыт", "күні"],

    "source": ["источник", "платформа", "соцсеть", "source", "platform", "network",

               "channel", "канал", "дереккөз"],

    "record_type": ["тип записи", "тип", "вид", "type", "kind", "тип сообщения"],

    "author": ["автор", "ник", "логин", "пользователь", "пайдаланушы", "author", "user", "username",

               "owner", "профиль", "id автора"],

    "url": ["ссылка", "url", "link", "permalink", "сілтеме"],

    "likes": ["лайки", "лайк", "реакции", "реакция", "likes", "like", "reactions",

              "нравится", "ұнату"],

    "comments_count": ["количество комментариев", "кол-во комментариев", "число комментариев",

                       "комментариев", "comments", "replies", "ответов", "пікірлер"],

    "views": ["просмотры", "просмотр", "views", "view", "охват", "reach", "көрілім"],

    "place": ["район", "адрес", "место", "локация", "улица", "микрорайон", "location",

              "address", "place", "district", "street", "мекенжай", "аудан", "орын"],

    "language": ["язык", "language", "lang", "тіл"],
    "post_id": ["id публикации", "post_id", "parent_post_id"],
    "message_id": ["id", "message_id", "thread_id"],

}

CONTAINS_ORDER = [
    "comments_count", "likes", "views", "url", "date",
    "author", "source", "record_type", "place",
    "language", "text", "post_id", "message_id"
]


PLACES = [

    {"name": "Площадь Аль-Фараби", "district": "Аль-Фараби",

     "aliases": ["площадь аль-фараби", "площади аль-фараби"]},

    {"name": "Проспект Тауке хана", "district": "Абай",

     "aliases": ["тауке хана", "тәуке хан", "тауке хан"]},

    {"name": "Больница №1", "district": "Абай",

     "aliases": ["больница №1", "больнице №1", "больницы №1"]},

    {"name": "Дендропарк", "district": "Аль-Фараби", "aliases": ["дендропарк"]},

    {"name": "Центральный рынок", "district": "Абай",

     "aliases": ["центральный рынок", "центральном рынке", "орталық базар", "алтын орда"]},

    {"name": "Мкр Нурсат", "district": "Каратау", "aliases": ["нурсат", "нұрсәт", "нұрсат"]},

    {"name": "Мкр Самал", "district": "Абай", "aliases": ["самал"]},

    {"name": "Мкр Тассай", "district": "Аль-Фараби", "aliases": ["тассай", "тассае", "тасқай"]},

    {"name": "Район Абай", "district": "Абай", "aliases": ["абай", "абае"]},

    {"name": "Район Аль-Фараби", "district": "Аль-Фараби",

     "aliases": ["аль-фараби", "әл-фараби", "альфараби", "әл фараби"]},

    {"name": "Район Енбекши", "district": "Енбекши", "aliases": ["енбекши", "еңбекші"]},

    {"name": "Район Каратау", "district": "Каратау", "aliases": ["каратау", "қаратау"]},

]


KEYWORDS = {

    "Водоснабжение": ["вода", "воды", "воду", "воде", "водой", "водоснаб", "водопровод",

                      "водоканал", "су жоқ", "су келм", "су өш", "сусыз"],

    "Дороги": ["яма", "ямы", "ямой", "яму", "ямах", "дорог", "дорож", "асфальт", "тротуар",

               "жол", "шұңқыр", "снег", "гололед", "гололёд", "светофор", "жарықбағдар",

               "пробк", "затор"],

    "Общественный транспорт": ["автобус", "маршрут", "остановк", "троллейбус", "такси",

                               "общественный транспорт", "аялдама", "көлік"],

    "Освещение": ["освещен", "фонар", "көше жарығ", "жарықтандыр", "қараңғ", "темно"],

    "Электричество": ["электр", "свет мигает", "свет отключ", "отключили свет", "нет света",

                      "свет пропал", "жарық өш", "жарық жоқ", "жарық сөн", "трансформатор"],

    "Мусор и санитария": ["мусор", "қоқыс", "свалк", "контейнер", "антисанитар", "грязь",

                          "грязн"],

    "Отопление": ["отоплен", "батаре", "жылу", "жылыт", "теплотрасс", "тепловая"],

    "Газ": ["газ$", "газа", "газу", "газом", "газе", "газов", "газоснаб"],

    "Здравоохранение": ["больниц", "поликлиник", "врач", "терапевт", "скорая", "емхана",

                        "аурухана", "дәрігер", "медицин", "лекарств"],

    "Образование": ["школ", "мектеп", "класс", "детсад", "детский сад", "балабақша",

                    "учител", "мұғалім", "колледж", "университет", "оқушы"],

    "Строительство": ["строят", "строительств", "стройк", "құрылыс", "застройк", "котлован"],

    "Экология": ["воздух", "ауа$", "ауада", "ауаның", "смог", "дым", "түтін", "выброс",

                 "экологи", "загрязн"],

    "Безопасность": ["полици", "хулиган", "драк", "краж", "ограбл", "преступ", "дауыс-шу",

                     "тонау", "қылмыс", "ұрлық", "безопасн"],

    "Благоустройство и дворы": ["двор", "ойын алаң", "детская площадка", "благоустрой",

                                "парк$", "парке", "парка", "парку", "парки", "дендропарк",

                                "сквер", "скамейк", "газон", "клумб", "абаттандыр", "аула"],

    "Предпринимательство": ["предпринимат", "бизнес", "кәсіпкер", "налог", "салық", "лицензи"],

    "Социальная помощь": ["пособи", "жәрдемақы", "социальн", "субсиди", "льгот", "малоимущ",

                          "инвалид", "пенсия", "пенсион", "зейнетақы", "әлеуметтік"],

    "ЖКХ": ["жкх", "коммунал", "квартплат", "тариф", "кск$", "осжк$", "канализац", "кәріз",

            "лифт", "подъезд", "крыш", "пәтерақы", "счётчик", "счетчик", "есептегіш"],

    "Работа городских служб": ["аким", "әкім", "горсовет", "служб", "обращени", "109$",

                               "qoldau", "не реагир", "игнорир", "жауап бермейді"],

}


NEG_WORDS = [

    "нет$", "нету", "жоқ", "отсутств", "не хватает", "опять", "снова", "ужас", "кошмар",

    "плох", "хуже", "страшно", "опасн", "қауіпті", "вонь", "воня", "смрад", "грязь", "грязн",

    "мусор", "қоқыс", "свалк", "антисанитар", "переполнен", "толып", "суық", "холод",

    "слаб", "әлсіз", "шум$", "шумно", "шу$", "мигает", "өшіп", "өшті", "өшкен", "сөнді",

    "кешік", "кешіг", "задерж", "опозда", "яма", "ямы", "ямой", "яму", "ямах", "шұңқыр",

    "келмей", "не приш", "не убира", "не вывоз", "не приезж", "не едет", "не едут",

    "не реагир", "не работа", "не горит", "не горят", "не починя", "отключ", "перебои",

    "перебой", "авари", "сломан", "сломал", "разбит", "разруш", "течет", "течёт", "протечк",

    "прорыв", "затоп", "жалоб", "шағым", "недоволь", "возмущ", "безобрази", "надоел",

    "проблем", "пробк", "затор", "очередь", "очереди", "стоим", "дымит", "түтін", "лас$",

    "хулиган", "драк", "краж", "ограбл", "ұрлық", "тонау", "қиын", "пропал", "пропад",

    "исчез",

]

POS_WORDS = [

    "спасибо", "благодар", "рақмет", "алғыс", "молодц", "отличн", "супер$", "прекрасн",

    "замечательн", "хорош", "жақсы", "керемет", "тамаша", "әдемі", "красив", "удобн",

    "починил", "исправил", "убрал", "открыл", "ашылды", "ашылған", "жөндел", "сделал",

    "жасалды", "решил", "наконец", "довольн", "нравится", "ұнайды", "одобр",

]

SUGGEST_WORDS = ["предлага", "предложени", "ұсын", "хорошо бы", "было бы хорошо",

                 "жақсы болар еді"]


SOURCE_NAMES = {

    "instagram": "Instagram", "инстаграм": "Instagram", "threads": "Threads",

    "telegram": "Telegram", "телеграм": "Telegram", "tiktok": "TikTok", "тикток": "TikTok",

    "youtube": "YouTube", "ютуб": "YouTube", "facebook": "Facebook", "фейсбук": "Facebook",

    "twitter": "X (Twitter)", "вконтакте": "VK",

}


URL_RX = re.compile(r"https?://\S+|www\.\S+")

KAZ_LETTERS_RX = re.compile(r"[әіңғүұқөһӘІҢҒҮҰҚӨҺ]")

CYRILLIC_RX = re.compile(r"[а-яёА-ЯЁ]")

PLATFORM_RX = re.compile("|".join(re.escape(k) for k in SOURCE_NAMES), re.IGNORECASE)

DATE_PATTERN_RX = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}|\d{1,2}:\d{2}")

NUMERIC_VALUE_RX = re.compile(r"[\d\s.,]+(?:тыс\.?|млн\.?|[kKкКmMмМ])?")


def build_rx(words):

    parts = []

    for w in words:

        if w.endswith("$"):

            parts.append(re.escape(w[:-1]) + r"(?!\w)")

        else:

            parts.append(re.escape(w))

    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + ")")


CATEGORY_RX = {c: build_rx(w) for c, w in KEYWORDS.items()}

NEG_RX = build_rx(NEG_WORDS)

POS_RX = build_rx(POS_WORDS)

SUGGEST_RX = build_rx(SUGGEST_WORDS)


def norm(name):

    return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", str(name).strip().lower()))


SYNONYMS = {k: [norm(x) for x in v] for k, v in SYNONYMS.items()}


def unique_columns(cols):

    seen = {}

    out = []

    for c in cols:

        c = str(c).strip()

        if c in seen:

            seen[c] += 1

            out.append(f"{c}.{seen[c]}")

        else:

            seen[c] = 0

            out.append(c)

    return out


def column_profile(series):

    v = series.dropna().astype(str).str.strip()

    v = v[v != ""].head(100)

    if v.empty:

        return None

    is_dt = pd.api.types.is_datetime64_any_dtype(series)

    is_num = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)

    numeric = 1.0 if is_num else float(v.map(lambda x: NUMERIC_VALUE_RX.fullmatch(x) is not None).mean())

    url = float(v.str.match(r"(https?://|www\.)", case=False).mean())

    platform = float(v.map(lambda x: len(x) <= 40 and PLATFORM_RX.search(x) is not None).mean())

    if is_dt:

        date = 1.0

    elif is_num:

        date = 0.0

    else:

        cand = v[v.map(lambda x: len(x) <= 40 and DATE_PATTERN_RX.search(x) is not None)]

        date = 0.0

        if len(cand):

            date = float(len(cand) / len(v) * parse_dates(cand.head(50)).notna().mean())

    serial = False

    if is_num:

        nums = series.dropna()

        serial = bool(len(nums)) and nums.min() >= 20000 and nums.max() <= 80000

    return {"numeric": numeric, "url": url, "platform": platform, "date": date,

            "len": float(v.str.len().mean()), "serial": serial}


def field_ok(field, p):

    if p is None:

        return False

    if field == "text":

        return p["numeric"] < 0.5 and p["url"] < 0.5 and p["date"] < 0.5 and p["len"] >= 5

    if field == "date":

        return p["date"] >= 0.5 or p["serial"]

    if field == "url":

        return p["url"] >= 0.3

    if field in ("likes", "comments_count", "views"):

        return p["numeric"] >= 0.6

    if field == "source":

        return p["numeric"] < 0.5 and p["len"] <= 40 and p["url"] < 0.3

    if field == "record_type":

        return p["numeric"] < 0.5 and p["len"] <= 30

    if field == "author":

        return p["len"] <= 60 and p["url"] < 0.3

    if field == "place":

        return p["numeric"] < 0.5 and p["len"] <= 80

    if field == "language":

        return p["len"] <= 15

    return True


def guess_mapping(raw):

    profiles = {c: column_profile(raw[c]) for c in raw.columns}

    normed = {c: norm(c) for c in raw.columns}

    result = {}

    used = set()


    def take(field, col):

        result[field] = col

        used.add(col)


    for field, syns in SYNONYMS.items():

        for c, n in normed.items():

            if c not in used and n in syns and field_ok(field, profiles[c]):

                take(field, c)

                break

    for field in CONTAINS_ORDER:

        if field in result:

            continue

        min_len = 3 if field == "url" else 4

        for c, n in normed.items():

            if (c not in used and any(x in n for x in SYNONYMS[field] if len(x) >= min_len)

                    and field_ok(field, profiles[c])):

                take(field, c)

                break

    for field, key, thr in (("date", "date", 0.8), ("url", "url", 0.6), ("source", "platform", 0.5)):

        if field in result:

            continue

        for c in raw.columns:

            p = profiles[c]

            if c not in used and p and p[key] >= thr and field_ok(field, p):

                take(field, c)

                break

    if "comments_count" not in result:

        for c, n in normed.items():

            p = profiles[c]

            if (c not in used and p and p["numeric"] >= 0.6

                    and any(x in n for x in ("коммент", "comment", "пікір"))):

                take("comments_count", c)

                break

    if "text" not in result:

        cands = [c for c in raw.columns

                 if c not in used and field_ok("text", profiles[c]) and profiles[c]["platform"] < 0.5]

        if cands:

            result["text"] = max(cands, key=lambda c: profiles[c]["len"])

    return result


def parse_num(v):

    try:

        if pd.isna(v):

            return 0

    except (TypeError, ValueError):

        return 0

    if isinstance(v, numbers.Number):

        return int(v)

    s = str(v).lower().replace("\xa0", " ").strip()

    compact = s.replace(" ", "")

    m = re.search(r"\d+(?:[.,]\d+)?", compact)

    if not m:

        return 0

    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", compact):

        return int(re.sub(r"[.,]", "", compact))

    num = float(m.group().replace(",", "."))

    if "млн" in s or s.endswith("m") or s.endswith("м"):

        num *= 1_000_000

    elif "тыс" in s or s.endswith("k") or s.endswith("к"):

        num *= 1000

    return int(num)


def parse_dates(s):

    if pd.api.types.is_datetime64_any_dtype(s):

        d = s

    elif pd.api.types.is_numeric_dtype(s):

        d = pd.to_datetime(s, unit="D", origin="1899-12-30", errors="coerce")

    else:

        try:

            d = pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")

        except (TypeError, ValueError):

            d = pd.to_datetime(s, errors="coerce", dayfirst=True)

    if getattr(d.dt, "tz", None) is not None:

        d = d.dt.tz_localize(None)

    return d


def is_empty(v):

    try:

        if pd.isna(v):

            return True

    except (TypeError, ValueError):

        return False

    return str(v).strip() == ""


def norm_source(v):

    if is_empty(v):

        return NOT_SET

    s = str(v).strip()

    low = s.lower()

    for key, name in SOURCE_NAMES.items():

        if key in low:

            return name

    return s


def norm_record_type(v):

    if is_empty(v):

        return NOT_SET

    s = str(v).strip()

    low = s.lower()

    if any(k in low for k in ("коммент", "comment", "пікір", "reply", "ответ")):

        return "Комментарий"

    if any(k in low for k in ("пост", "публик", "post", "новост", "news")):

        return "Публикация"

    return s


def norm_language(v):

    if is_empty(v):

        return NOT_SET

    s = str(v).strip()

    low = s.lower()

    if low in ("kk", "kz", "kaz", "kazakh") or low.startswith(("каз", "қаз")):

        return "Казахский"

    if low in ("ru", "rus", "russian") or low.startswith("рус"):

        return "Русский"

    return s


def detect_language(text):

    if KAZ_LETTERS_RX.search(text):

        return "Казахский"

    if CYRILLIC_RX.search(text):

        return "Русский"

    return "Другой"


def hash_author(v):

    if is_empty(v):

        return NOT_SET

    return hashlib.sha1(str(v).strip().lower().encode("utf-8")).hexdigest()[:10]


def analyze(text, place_text):

    t = URL_RX.sub(" ", text).lower()

    cats = [c for c, rx in CATEGORY_RX.items() if rx.search(t)] or ["Другое"]

    pos = len(POS_RX.findall(t))

    neg = len(NEG_RX.findall(t))

    if pos > neg:

        sentiment = "Позитивная"

    elif neg > pos:

        sentiment = "Негативная"

    else:

        sentiment = "Нейтральная"

    if SUGGEST_RX.search(t):

        msg_type = "Предложение"

    elif sentiment == "Позитивная":

        msg_type = "Благодарность"

    elif sentiment == "Негативная":

        msg_type = "Жалоба"

    elif "?" in t:

        msg_type = "Вопрос"

    else:

        msg_type = "Информация"

    found = None

    for src in (place_text.lower(), t):

        if not src:

            continue

        for p in PLACES:

            if any(a in src for a in p["aliases"]):

                found = p

                break

        if found:

            break

    if found:

        place, district = found["name"], found["district"]

    else:

        place, district = (place_text or PLACE_DEFAULT), PLACE_DEFAULT

    return {

        "categories": cats[:3],

        "sentiment": sentiment,

        "msg_type": msg_type,

        "is_problem": msg_type == "Жалоба",

        "place": place,

        "district": district,

    }


def fix_header(fr):

    unnamed = sum(str(c).startswith("Unnamed") for c in fr.columns)

    if unnamed <= len(fr.columns) / 2:

        return fr

    for i in range(min(15, len(fr))):

        row = fr.iloc[i]

        filled = row.dropna()

        if len(filled) >= max(2, len(fr.columns) / 2) and all(isinstance(x, str) for x in filled):

            out = fr.iloc[i + 1:].copy()

            out.columns = [x.strip() if isinstance(x, str) else f"Колонка {j + 1}"

                           for j, x in enumerate(row)]

            return out.reset_index(drop=True)

    return fr


@st.cache_data(show_spinner="Чтение файла...")

def read_all(raw_bytes, name):

    if name.lower().endswith(".csv"):

        frame = None

        for enc in ("utf-8-sig", "cp1251", "utf-8"):

            try:

                frame = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine="python", encoding=enc)

                break

            except Exception:

                frame = None

        if frame is None:

            raise ValueError("не удалось прочитать CSV")

        frames = {"CSV": frame}

    else:

        xl = pd.ExcelFile(io.BytesIO(raw_bytes))

        frames = {sn: xl.parse(sn) for sn in xl.sheet_names}

    out = {}

    for sn, fr in frames.items():

        fr = fr.dropna(how="all").dropna(axis=1, how="all")

        fr = fix_header(fr)

        fr = fr.dropna(how="all").dropna(axis=1, how="all")

        if fr.empty:

            continue

        fr.columns = unique_columns(fr.columns)

        out[sn] = fr.reset_index(drop=True)

    return out


@st.cache_data(show_spinner="Обработка данных...")

def prepare(raw, mapping):

    quality = {"Строк в файле": str(len(raw))}

    if len(raw) > MAX_ROWS:

        raw = raw.head(MAX_ROWS)

        quality["Обрезано до лимита строк"] = str(MAX_ROWS)

    df = pd.DataFrame(index=raw.index)

    for f in FIELD_LABELS:

        col = mapping.get(f)

        df[f] = raw[col] if col else None

    
    for field in ("post_id", "message_id"):
        col = mapping.get(field)

        if col and col in raw.columns:
            df[field] = raw[col].fillna("").astype(str).str.strip()
        else:
            df[field] = ""

    text = df["text"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    empty = df["text"].isna() | text.str.lower().isin(["", "nan", "none", "nat"])

    quality["Пустых текстов удалено"] = str(int(empty.sum()))

    df = df[~empty].copy()

    df["text"] = text[~empty]


    df["_key"] = df["text"].str.lower()

    subset = ["_key"] + [f for f in ("source", "author", "date") if mapping.get(f)]

    before = len(df)

    df = df.drop_duplicates(subset=subset).drop(columns="_key")

    quality["Дубликатов удалено"] = str(before - len(df))


    if mapping.get("date"):

        df["date"] = parse_dates(df["date"])

        quality["Строк без распознанной даты"] = str(int(df["date"].isna().sum()))

    else:

        df["date"] = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

        quality["Строк без распознанной даты"] = "колонка даты не выбрана"


    for f in ("likes", "comments_count", "views"):

        df[f] = df[f].map(parse_num) if mapping.get(f) else 0


    df["source"] = df["source"].map(norm_source) if mapping.get("source") else NOT_SET

    df["record_type"] = (df["record_type"].map(norm_record_type)

                         if mapping.get("record_type") else NOT_SET)

    df["author"] = df["author"].map(hash_author) if mapping.get("author") else NOT_SET

    df["url"] = df["url"].map(lambda v: "" if is_empty(v) else str(v).strip())


    detected = df["text"].map(detect_language)

    if mapping.get("language"):

        given = df["language"].map(norm_language)

        df["language"] = given.where(given != NOT_SET, detected)

    else:

        df["language"] = detected


    place_raw = df["place"].map(lambda v: "" if is_empty(v) else str(v).strip())

    results = [analyze(t, p) for t, p in zip(df["text"], place_raw)]

    res = pd.DataFrame(results, index=df.index)

    df = pd.concat([df.drop(columns="place"), res], axis=1).reset_index(drop=True)

    df["id"] = df.index + 1


    n = len(df)

    quality["Принято в анализ"] = str(n)

    if n:

        located = int((df["district"] != PLACE_DEFAULT).sum())

        other = int(df["categories"].map(lambda c: c == ["Другое"]).sum())

        quality["Определён район"] = f"{located} ({located / n:.0%})"

        quality["Тема не определена («Другое»)"] = f"{other} ({other / n:.0%})"

    return df, quality


def growth_table(f, hours, mid, high, crit, min_count):

    d = f.dropna(subset=["date"])

    if d.empty:

        return None, "В данных нет распознанных дат, рост тем оценить нельзя."

    t_max = d["date"].max()

    t_min = d["date"].min()

    start = t_max - pd.Timedelta(hours=hours)

    prior_hours = (start - t_min).total_seconds() / 3600

    if prior_hours < hours:

        return None, (f"Период данных короче двух окон по {hours} ч, "

                      "для оценки роста недостаточно истории.")

    ex = d.explode("categories")

    recent = ex[ex["date"] > start].groupby("categories").size()

    prior = ex[ex["date"] <= start].groupby("categories").size()

    n_windows = prior_hours / hours

    rows = []

    for c in recent.index:

        r = int(recent[c])

        avg = int(prior.get(c, 0)) / n_windows

        ratio = r / avg if avg > 0 else float("inf")

        if r < min_count:

            level = "Низкий"

        elif ratio >= crit:

            level = "Критический"

        elif ratio >= high:

            level = "Повышенный"

        elif ratio >= mid:

            level = "Средний"

        else:

            level = "Низкий"

        rows.append({

            "Категория": c,

            f"Сообщений за {hours} ч": r,

            "В среднем за такой же период ранее": round(avg, 1),

            "Рост": "новая тема" if avg == 0 else f"×{ratio:.1f}",

            "Уровень сигнала": level,

            "_lvl": LEVEL_ORDER[level],

        })

    if not rows:

        return None, f"За последние {hours} ч сообщений нет."

    table = pd.DataFrame(rows).sort_values(

        ["_lvl", f"Сообщений за {hours} ч"], ascending=[True, False]).drop(columns="_lvl")

    return table.reset_index(drop=True), ""


def dynamics(f):

    d = f.dropna(subset=["date"])

    if d.empty:

        return None, None

    span = (d["date"].max() - d["date"].min()).total_seconds() / 86400

    freq = "h" if span <= 3 else "D"

    bucket = d["date"].dt.floor(freq)

    pv = (d.groupby([bucket, "sentiment"]).size().unstack(fill_value=0)

          .reindex(columns=SENTIMENTS, fill_value=0))

    return pv, freq


def build_summary(f, top, growth, growth_msg, hours, pv, freq):

    total = len(f)

    lines = []

    dates = f["date"].dropna()

    if len(dates):

        lines.append(f"Обработано сообщений: {total}. Период данных: "

                     f"{dates.min():%d.%m.%Y %H:%M} – {dates.max():%d.%m.%Y %H:%M}.")

    else:

        lines.append(f"Обработано сообщений: {total}. Даты публикаций в данных не распознаны.")

    pos = int((f["sentiment"] == "Позитивная").sum())

    neu = int((f["sentiment"] == "Нейтральная").sum())

    neg = int((f["sentiment"] == "Негативная").sum())

    problems = int(f["is_problem"].sum())

    lines.append(f"Тональность: негативных {neg} ({neg / total:.0%}), нейтральных {neu} "

                 f"({neu / total:.0%}), позитивных {pos} ({pos / total:.0%}). "

                 f"Жалоб и проблемных сообщений: {problems}.")

    named = top[top.index != "Другое"].head(3)

    if len(named):

        parts = [f"{c} ({int(r['Сообщений'])})" for c, r in named.iterrows()]

        lines.append("Чаще всего обсуждаются темы: " + ", ".join(parts) + ".")

    pl = f[f["is_problem"] & (f["place"] != PLACE_DEFAULT)]["place"].value_counts().head(3)

    if len(pl):

        lines.append("Больше всего проблемных сообщений связано с местами: "

                     + ", ".join(f"{k} ({v})" for k, v in pl.items()) + ".")

    src = f["source"].value_counts()

    if not (len(src) == 1 and src.index[0] == NOT_SET):

        lines.append(f"Основной источник: {src.index[0]} ({src.iloc[0] / total:.0%} сообщений).")

    lang = f["language"].value_counts()

    lines.append("Языки сообщений: "

                 + ", ".join(f"{k} — {v / total:.0%}" for k, v in lang.items()) + ".")

    if pv is not None:

        s = pv.sum(axis=1)

        ts = s.idxmax()

        label = f"{ts:%d.%m.%Y %H:00}" if freq == "h" else f"{ts:%d.%m.%Y}"

        lines.append(f"Пик активности: {label} ({int(s.max())} сообщений).")

    if growth is not None:

        hot = growth[growth["Уровень сигнала"].isin(["Повышенный", "Критический"])]

        if len(hot):

            parts = [f"{r['Категория']} ({r['Рост']}, {r['Уровень сигнала'].lower()} уровень)"

                     for _, r in hot.iterrows()]

            lines.append("Зафиксирован рост сообщений пользователей по темам: "

                         + ", ".join(parts) + ".")

        else:

            lines.append(f"Существенного роста обсуждений за последние {hours} ч не зафиксировано.")

    else:

        lines.append(growth_msg)

    lines.append("Выводы носят аналитический характер и основаны на сообщениях пользователей. "

                 "Они не подтверждают факты (например, аварии) без проверки официальными данными.")

    return lines


def messages_export(f):

    e = pd.DataFrame({

        "Дата": f["date"],

        "Источник": f["source"],

        "Тип записи": f["record_type"],

        "Автор (хеш)": f["author"],

        "Текст": f["text"],

        "Категории": f["categories"].map(", ".join),

        "Тональность": f["sentiment"],

        "Тип сообщения": f["msg_type"],

        "Проблема": f["is_problem"].map({True: "Да", False: "Нет"}),

        "Район": f["district"],

        "Место": f["place"],

        "Язык": f["language"],

        "Реакции": f["likes"],

        "Комментариев": f["comments_count"],

        "Просмотры": f["views"],

    })

    if (f["url"] != "").any():

        e["Ссылка"] = f["url"]

    return e


def autofit(writer):

    for ws in writer.book.worksheets:

        for col in ws.columns:

            width = max((len(str(c.value)) for c in col[:300] if c.value is not None), default=8)

            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 70)


def build_excel(sheets):

    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:

        for name, frame in sheets.items():

            frame.to_excel(writer, sheet_name=name[:31], index=False)

        autofit(writer)

    return buf.getvalue()


def template_bytes():

    sample = pd.DataFrame({

        "Дата": ["2026-10-05 08:15", "2026-10-05 09:40", "2026-10-05 10:05"],

        "Источник": ["Instagram", "Threads", "Instagram"],

        "Тип записи": ["Комментарий", "Комментарий", "Публикация"],

        "Автор": ["user_001", "user_002", "official_page"],

        "Текст": ["В Нурсате нет воды с утра", "Абайда қоқыс шығарылмай жатыр",

                  "Спасибо за новую детскую площадку в Аль-Фараби"],

        "Ссылка": ["https://example.com/1", "https://example.com/2", "https://example.com/3"],

        "Лайки": [5, 12, 40],

        "Кол-во комментариев": [0, 2, 15],

        "Просмотры": [120, 340, 5200],

        "Район": ["Нурсат", "Абай", "Аль-Фараби"],

        "Язык": ["Русский", "Казахский", "Русский"],

    })

    return build_excel({"Данные": sample})


API_BASE = "https://graph.threads.net/v1.0"

API_FIELDS = "id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply"


@st.cache_data(ttl=900, show_spinner="Запрос к Threads API...")

def fetch_threads(token, queries, search_type, since, until, max_pages):

    rows, seen, errors = [], set(), []

    for q in queries:

        params = {"q": q, "search_type": search_type, "fields": API_FIELDS,

                  "limit": 100, "access_token": token}

        if since:

            params["since"] = since

        if until:

            params["until"] = until

        url, pages = f"{API_BASE}/keyword_search", 0

        while url and pages < max_pages:

            try:

                r = requests.get(url, params=params if pages == 0 else None, timeout=30)

            except requests.RequestException as e:

                errors.append(f"«{q}»: {e}")

                break

            if r.status_code != 200:

                errors.append(f"«{q}»: {r.status_code} {r.text[:200]}")

                break

            j = r.json()

            for m in j.get("data", []):

                if m["id"] in seen:

                    continue

                seen.add(m["id"])

                rows.append({

                    "Дата": m.get("timestamp"),

                    "Источник": "Threads",

                    "Тип записи": "Комментарий" if m.get("is_reply") else "Публикация",

                    "Автор": m.get("username"),

                    "Текст": m.get("text"),

                    "Ссылка": m.get("permalink"),

                })

            url = j.get("paging", {}).get("next")

            pages += 1

    return pd.DataFrame(rows), errors


@st.cache_data(ttl=900, show_spinner="Загрузка публикаций и комментариев...")

def fetch_own_threads(token, since, until, max_pages, with_replies):

    rows, errors, seen = [], [], set()

    post_fields = "id,text,timestamp,username,permalink,is_quote_post"

    reply_fields = "id,text,timestamp,username,permalink,is_reply"


    def get_pages(url, params, limit_pages):

        out, pages = [], 0

        while url and pages < limit_pages:

            try:

                r = requests.get(url, params=params if pages == 0 else None, timeout=30)

            except requests.RequestException as e:

                errors.append(str(e))

                break

            if r.status_code != 200:

                errors.append(f"{r.status_code} {r.text[:200]}")

                break

            j = r.json()

            out.extend(j.get("data", []))

            url = j.get("paging", {}).get("next")

            pages += 1

        return out


    params = {"fields": post_fields, "limit": 25, "access_token": token}

    if since:

        params["since"] = since

    if until:

        params["until"] = until

    posts = get_pages(f"{API_BASE}/me/threads", params, max_pages)

    for m in posts:

        if m["id"] in seen:

            continue

        seen.add(m["id"])

        rows.append({
    "ID": m["id"],
    "ID публикации": m["id"],
    "Дата": m.get("timestamp"),
    "Источник": "Threads",
    "Тип записи": "Публикация",
    "Автор": m.get("username"),
    "Текст": m.get("text"),
    "Ссылка": m.get("permalink")
})

    if with_replies:

        for m in posts[:50]:

            replies = get_pages(f"{API_BASE}/{m['id']}/conversation",

                                {"fields": reply_fields, "limit": 100,

                                 "access_token": token}, 3)

            for rep in replies:

                if rep["id"] in seen:

                    continue

                seen.add(rep["id"])

                rows.append({
    "ID": rep["id"],
    "ID публикации": m["id"],
    "Дата": rep.get("timestamp"),
    "Источник": "Threads",
    "Тип записи": "Комментарий",
    "Автор": rep.get("username"),
    "Текст": rep.get("text"),
    "Ссылка": rep.get("permalink")
})

    return pd.DataFrame(rows), errors




@st.cache_data(ttl=300, show_spinner="Обновляем Telegram…", max_entries=12)
def fetch_telegram_public_channels(api_id, api_hash, channels, post_limit=40, comments_limit=40):
    """Read public Telegram channels with a session from Secrets or local development."""
    import asyncio
    from pathlib import Path
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.errors import RPCError

    try:
        session_string = st.secrets.get("TELEGRAM_SESSION_STRING", "")
    except Exception:
        session_string = ""
    session_string = session_string or os.environ.get("TELEGRAM_SESSION_STRING", "")
    local_session = Path(__file__).resolve().parent / ".streamlit" / "shymkent_telegram_session"
    if session_string:
        session = StringSession(session_string)
    elif local_session.with_suffix(".session").exists():
        session = str(local_session)
    else:
        return pd.DataFrame(), ["Telegram: добавьте TELEGRAM_SESSION_STRING в Streamlit Cloud → Settings → Secrets."]

    async def collect():
        rows, errors = [], []
        client = TelegramClient(session, int(api_id), str(api_hash))
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return [], ["Telegram: сессия не авторизована. Повторите вход через QR."]
            for channel in channels:
                channel = channel.strip()
                if not channel:
                    continue
                try:
                    entity = await client.get_entity(channel)
                    username = getattr(entity, "username", None)
                    chat_id = str(entity.id)
                    async for post in client.iter_messages(entity, limit=int(post_limit)):
                        post_text = post.message or ""
                        if not post_text.strip():
                            continue
                        parent = f"tg:{chat_id}:{post.id}"
                        post_link = f"https://t.me/{username}/{post.id}" if username else ""
                        rows.append({
                            "ID": parent, "ID публикации": parent,
                            "Дата": post.date.isoformat(), "Источник": "Telegram",
                            "Тип записи": "Публикация", "Автор": getattr(entity, "title", channel),
                            "Текст": post_text, "Ссылка": post_link,
                        })
                        if not (getattr(post, "replies", None) and post.replies.replies):
                            continue
                        try:
                            async for comment in client.iter_messages(entity, reply_to=post.id, limit=int(comments_limit)):
                                comment_text = comment.message or ""
                                if not comment_text.strip():
                                    continue
                                sender = await comment.get_sender()
                                author = getattr(sender, "username", None) or getattr(sender, "first_name", None) or "Участник Telegram"
                                rows.append({
                                    "ID": f"tg:comment:{chat_id}:{post.id}:{comment.id}",
                                    "ID публикации": parent, "Дата": comment.date.isoformat(),
                                    "Источник": "Telegram", "Тип записи": "Комментарий",
                                    "Автор": author, "Текст": comment_text,
                                    "Ссылка": post_link,
                                })
                        except (RPCError, ValueError) as exc:
                            errors.append(f"Комментарии {channel}, пост {post.id}: {type(exc).__name__}: {exc}")
                except (RPCError, ValueError) as exc:
                    errors.append(f"Канал {channel}: {type(exc).__name__}: {exc}")
            return rows, errors
        finally:
            await client.disconnect()

    try:
        rows, errors = asyncio.run(collect())
        return pd.DataFrame(rows), errors
    except Exception as exc:
        return pd.DataFrame(), [f"Telegram: {type(exc).__name__}: {exc}"]


st.set_page_config(page_title="Медиамониторинг города", layout="wide")

st.markdown("""
<style>
/* Основной фон */
.stApp {
    background-color: #0b1120;
    color: #e8eef8;
}

/* Центральная часть */
.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Боковая панель */
section[data-testid="stSidebar"] {
    background-color: #111b2e;
    border-right: 1px solid #293a52;
}

/* Заголовки */
h1, h2, h3 {
    color: #f3f7ff !important;
}

h1 {
    font-weight: 800 !important;
    letter-spacing: -0.7px;
}

/* Кнопки */
.stButton > button {
    background: #192a43;
    color: #ffffff;
    border: 1px solid #365170;
    border-radius: 12px;
    min-height: 48px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #244366;
    border-color: #67b0ff;
    color: #ffffff;
}

/* Карточки сообщений */
div[data-testid="stExpander"] {
    background: #152238;
    border: 1px solid #2d435f;
    border-radius: 14px;
    margin-bottom: 12px;
}

/* Поля ввода */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div {
    background: #16263e;
    border-radius: 10px;
}

/* Разделители */
hr {
    border-color: #293a52 !important;
}

/* Ссылки */
a {
    color: #75baff;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 1rem !important;
}

h1, h2, h3 {
    margin-top: 0.3rem !important;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.65rem;
}
</style>

""", unsafe_allow_html=True)



st.markdown("""
<style>
.stApp { background: radial-gradient(ellipse at 18% 0%, #1b0b42 0%, #090e25 45%, #071329 100%) !important; color:#f4f0ff; }
section[data-testid="stSidebar"] { background:linear-gradient(165deg,#24105a 0%,#101633 55%,#0b142d 100%) !important; border-right:1px solid #4c3386 !important; }
.block-container { max-width:1550px !important; }
h1,h2,h3,h4 { color:#f7f3ff !important; }
div.st-key-stat_all button { background:linear-gradient(115deg,#4024a0,#241353) !important; border:1px solid #8056ff !important; box-shadow:0 8px 25px #652bba33 !important; }
div.st-key-stat_problems button { background:linear-gradient(115deg,#672044,#32152e) !important; border:1px solid #b83c79 !important; box-shadow:0 8px 25px #d72c7730 !important; }
div.st-key-stat_thanks button { background:linear-gradient(115deg,#086d5c,#073b45) !important; border:1px solid #18a88b !important; box-shadow:0 8px 25px #00b89422 !important; }
div.stButton > button { background:#151a39; border:1px solid #39345d; color:#f4f0ff; border-radius:11px; }
div.stButton > button:hover { background:#292052; border-color:#9065ff; color:white; }
div.stButton > button[kind="primary"] { background:linear-gradient(105deg,#5a30d6,#42209a) !important; border:1px solid #9d79ff !important; color:white !important; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { background:#151a39 !important; border:1px solid #39345d !important; border-radius:10px; }
div[data-testid="stVerticalScrollContainer"], div[data-testid="stContainer"] { border-color:#302c55; }
.stDownloadButton > button { border:1px solid #6f51b4 !important; }
</style>
""", unsafe_allow_html=True)


# --- Авторизация и управление источниками ---
import hmac
import secrets as secure_random
import time
from urllib.parse import urlparse


def config_value(name):
    try:
        return str(st.secrets.get(name, "") or "")
    except Exception:
        return str(os.environ.get(name, "") or "")


def db_connection():
    import psycopg
    return psycopg.connect(config_value("DATABASE_URL"), connect_timeout=5)


def password_hash(password, salt=None):
    salt = salt or secure_random.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 350000)
    return salt + ":" + value.hex()


def password_matches(password, stored):
    try:
        salt, _ = stored.split(":", 1)
        return hmac.compare_digest(password_hash(password, salt), stored)
    except (ValueError, TypeError):
        return False


@st.cache_resource(show_spinner=False)
def initialize_database():
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS monitoring_users (
                username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin','viewer')),
                enabled BOOLEAN NOT NULL DEFAULT TRUE)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS monitoring_channels (
                url TEXT PRIMARY KEY)""")
            cur.execute("SELECT count(*) FROM monitoring_users WHERE role='admin'")
            if cur.fetchone()[0] == 0:
                username, password = config_value("ADMIN_USERNAME"), config_value("ADMIN_PASSWORD")
                if not username or not password or len(password) < 12:
                    raise RuntimeError("Задайте ADMIN_USERNAME и ADMIN_PASSWORD (минимум 12 символов) в Secrets")
                cur.execute("INSERT INTO monitoring_users(username,password_hash,role) VALUES (%s,%s,'admin') ON CONFLICT DO NOTHING",
                            (username, password_hash(password)))


def authenticate(username, password):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash,role FROM monitoring_users WHERE username=%s AND enabled=TRUE", (username,))
            result = cur.fetchone()
    if result and password_matches(password, result[0]):
        return result[1]
    return None


def channels_list():
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM monitoring_channels ORDER BY url")
            return [r[0] for r in cur.fetchall()]


def valid_telegram_url(value):
    parsed = urlparse(value.strip())
    return (parsed.scheme == 'https' and parsed.hostname in ('t.me','www.t.me')
            and bool(re.fullmatch(r'/[A-Za-z0-9_]{5,32}/?', parsed.path)))


def admin_panel():
    st.title("🛡️ Панель администратора")
    tab1, tab2 = st.tabs(["Telegram-каналы", "Пользователи"])
    with tab1:
        st.caption("Ключи Telegram и Threads остаются в Streamlit Secrets. Здесь добавляются только публичные каналы.")
        current = channels_list()
        st.write("Подключённые каналы:", len(current))
        for channel in current:
            left, right = st.columns([5, 1])
            left.write(channel)
            if right.button("Удалить", key="delete_" + hashlib.sha256(channel.encode()).hexdigest()[:12]):
                with db_connection() as conn:
                    conn.execute("DELETE FROM monitoring_channels WHERE url=%s", (channel,))
                st.rerun()
        with st.form("add_channel"):
            new_channel = st.text_input("Ссылка публичного Telegram-канала", placeholder="https://t.me/shymkentonline")
            if st.form_submit_button("Добавить канал"):
                if not valid_telegram_url(new_channel):
                    st.error("Укажи публичный канал вида https://t.me/channelname")
                else:
                    with db_connection() as conn:
                        conn.execute("INSERT INTO monitoring_channels(url) VALUES (%s) ON CONFLICT DO NOTHING", (new_channel.strip(),))
                    st.success("Канал добавлен")
                    st.rerun()
    with tab2:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT username,role,enabled FROM monitoring_users ORDER BY username")
                users = cur.fetchall()
        st.dataframe(pd.DataFrame(users, columns=["Логин", "Роль", "Активен"]), hide_index=True)
        with st.form("new_user"):
            username = st.text_input("Логин нового пользователя")
            password = st.text_input("Временный пароль (минимум 12 символов)", type="password")
            if st.form_submit_button("Создать пользователя"):
                if not re.fullmatch(r'[A-Za-z0-9_.-]{3,40}', username) or len(password) < 12:
                    st.error("Логин: 3–40 латинских символов/цифр; пароль: минимум 12 символов")
                else:
                    with db_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT 1 FROM monitoring_users WHERE username=%s", (username,))
                            exists = cur.fetchone()
                            if not exists:
                                cur.execute("INSERT INTO monitoring_users(username,password_hash,role) VALUES (%s,%s,'viewer')",
                                            (username, password_hash(password)))
                    if exists:
                        st.error("Такой пользователь уже существует")
                    else:
                        st.success("Пользователь создан. Передай пароль безопасным способом.")
                        st.rerun()
        viewers = [u[0] for u in users if u[1] == 'viewer']
        if viewers:
            with st.form("manage_viewer"):
                selected = st.selectbox("Управление пользователем", viewers)
                action = st.selectbox("Действие", ["Заблокировать", "Разблокировать", "Сбросить пароль"])
                new_password = st.text_input("Новый пароль (для сброса)", type="password")
                if st.form_submit_button("Применить"):
                    with db_connection() as conn:
                        if action == "Сбросить пароль":
                            if len(new_password) < 12:
                                st.error("Минимум 12 символов")
                                st.stop()
                            conn.execute("UPDATE monitoring_users SET password_hash=%s WHERE username=%s AND role='viewer'",
                                         (password_hash(new_password), selected))
                        else:
                            conn.execute("UPDATE monitoring_users SET enabled=%s WHERE username=%s AND role='viewer'",
                                         (action == "Разблокировать", selected))
                    st.success("Изменения сохранены")
                    st.rerun()


if not config_value("DATABASE_URL"):
    st.error("Для входа настрой DATABASE_URL, ADMIN_USERNAME и ADMIN_PASSWORD в Streamlit Cloud → Secrets.")
    st.stop()
try:
    initialize_database()
except Exception as exc:
    st.error("Не удалось подключить базу данных. Проверь DATABASE_URL и параметры администратора.")
    st.stop()

if 'login_role' not in st.session_state:
    st.session_state.login_role = None
if not st.session_state.login_role:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display:none !important}
    [data-testid="stSidebarCollapsedControl"] {display:none !important}
    .block-container {max-width: 1100px !important; padding-top: 6vh !important}
    .login-hero {text-align:center;padding:22px 10px 26px}
    .login-mark {display:inline-flex;align-items:center;justify-content:center;width:68px;height:68px;
      border-radius:20px;background:linear-gradient(135deg,#8757ff,#4d2bc1);
      font-size:31px;box-shadow:0 15px 50px #6936df55;margin-bottom:22px}
    .login-title {font-size:clamp(28px,4vw,40px);font-weight:850;letter-spacing:-1.2px;color:#fff}
    .login-sub {color:#a9a8ca;font-size:15px;margin-top:9px}
    div[data-testid="stForm"] {background:linear-gradient(145deg,#1b2044,#111832) !important;
      border:1px solid #47416e !important;border-radius:22px !important;
      padding:30px !important;box-shadow:0 24px 70px #02041370}
    div[data-testid="stForm"] button[kind="primary"] {width:100%;min-height:50px;
      background:linear-gradient(100deg,#7b4bfa,#5631c8) !important}
    </style>
    <div class="login-hero">
      <div class="login-mark">◈</div>
      <div class="login-title">Shymkent Monitoring</div>
      <div class="login-sub">Единая платформа мониторинга городских обращений</div>
    </div>
    """, unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.25, 1])
    with center:
      with st.form("login_form"):
          login = st.text_input("Логин")
          password = st.text_input("Пароль", type="password")
          if st.form_submit_button("Войти", type="primary"):
              role = authenticate(login.strip(), password)
              if role:
                  st.session_state.login_role = role
                  st.session_state.login_name = login.strip()
                  st.rerun()
              else:
                  st.error("Неверный логин или пароль")
    st.stop()

# Проверяем актуальность роли и блокировку при каждом обновлении страницы.
with db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT role FROM monitoring_users WHERE username=%s AND enabled=TRUE",
                    (st.session_state.get('login_name', ''),))
        current_user = cur.fetchone()
if not current_user or current_user[0] != st.session_state.login_role:
    st.session_state.clear()
    st.warning("Доступ изменён. Войдите снова.")
    st.stop()

with st.sidebar:
    st.caption("Пользователь: " + st.session_state.get('login_name', ''))
    if st.button("Выйти"):
        st.session_state.clear()
        st.rerun()
    if st.session_state.login_role == 'admin':
        show_admin = st.toggle("Панель администратора", value=False)
    else:
        show_admin = False
if show_admin:
    admin_panel()
    st.stop()

with st.sidebar:
    st.markdown("""
    <div style="padding:10px 2px 16px;border-bottom:1px solid #30415b;margin-bottom:16px;">
        <div style="font-size:12px;letter-spacing:1.5px;color:#8fb9e7;font-weight:700;margin-bottom:6px;">ГОРОДСКАЯ АНАЛИТИКА</div>
        <div style="font-size:21px;line-height:1.25;font-weight:800;color:#f3f7ff;">Медиамониторинг</div>
        <div style="font-size:21px;line-height:1.25;font-weight:800;color:#f3f7ff;">города Шымкент</div>
    </div>
    """, unsafe_allow_html=True)

    mode = "Мои публикации (Threads API)"
    source_choice = st.selectbox(
        "Источник данных", ["Threads", "Telegram", "Все источники"],
        help="Можно просматривать отдельно Threads, Telegram или оба источника вместе."
    )

    telegram_channels_text = "\n".join(channels_list())
    if source_choice in ("Telegram", "Все источники"):
        st.caption(f"Telegram-каналов подключено: {len(channels_list())}. Источники изменяет только администратор.")
    # Лимиты загрузки заданы внутри приложения, без дополнительных полей в панели.
    telegram_post_limit = 30
    telegram_comments_limit = 30

    uploaded = None
    load_btn = False

    if mode == "Файл Excel/CSV":

        uploaded = st.file_uploader("Excel (.xlsx) или CSV", type=["xlsx", "xlsm", "csv"])

        st.download_button(

            "Скачать шаблон Excel",

            data=template_bytes(),

            file_name="шаблон_медиамониторинг.xlsx",

            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        )

    else:

        try:

            token = st.secrets["THREADS_TOKEN"]

        except Exception:

            token = os.environ.get("THREADS_TOKEN", "")

        with_replies = True

        queries_text, search_type = "", "RECENT"

        if mode == "Поиск по словам (Threads API)":

            queries_text = st.text_area("Ключевые слова (по одному в строке)",

                                        "Шымкент\nШымкент вода\nШымкент свет")

            search_type = st.selectbox("Сортировка", ["RECENT", "TOP"])

        else:      

            
            brand_icon = ("https://cdn.simpleicons.org/telegram/229ED9" if source_choice == "Telegram"
                          else "https://cdn.simpleicons.org/threads/000000")
            brand_title = ("Telegram" if source_choice == "Telegram"
                           else "Threads + Telegram" if source_choice == "Все источники"
                           else "Threads API")
            st.markdown("""
            <style>
            .threads-brand {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px 12px;
                background: #111b2e;
                border-radius: 14px 14px 0 0;
            }
            .threads-logo {
                width: 44px;
                height: 44px;
                background: white;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .threads-logo img {
                width: 28px;
                height: 28px;
            }
            .threads-name {
                font-size: 17px;
                font-weight: 700;
                color: white;
            }
            .threads-description {
                font-size: 12px;
                color: #a8b8cf;
            }
            .threads-status {
                padding: 13px 12px;
                background: #111b2e;
                color: #e5edf8;
                font-size: 13px;
                border-top: 1px solid #30415b;
            }
            .threads-period {
                padding: 12px;
                background: #1b304d;
                border-radius: 12px;
                color: #e5edf8;
                margin-top: 8px;
            }
            div.stButton > button[kind="primary"] {
                background: #2b61b0;
                color: white;
                border: none;
                border-radius: 10px;
                min-height: 50px;
                font-weight: 700;
            }
            </style>
    
            <div class="threads-brand">
                <div class="threads-logo">
                    <img src="__SOURCE_ICON__">
                </div>
                <div>
                    <div class="threads-name">__SOURCE_TITLE__</div>
                    <div class="threads-description">
                        Мониторинг публикаций
                    </div>
                </div>
            </div>
            """.replace("__SOURCE_ICON__", brand_icon).replace("__SOURCE_TITLE__", brand_title), unsafe_allow_html=True)

        with_replies = True

        st.markdown("**Период мониторинга**")

        c1, c2 = st.columns(2)

        d_from = c1.date_input(
            "С",
            value=date.today() - timedelta(days=7),
            key="api_from"
        )

        d_to = c2.date_input(
            "По",
            value=date.today(),
            key="api_to"
        )

        max_pages = st.number_input(
            "Макс. страниц на запрос (по 100 постов)",
            1, 20, 3
        )

        load_btn = st.button(
            "↻ Загрузить данные",
            use_container_width=True,
            type="primary"
        )


if mode != "Файл Excel/CSV":

    if load_btn:
        if source_choice in ("Threads", "Все источники") and not token:
            st.warning("THREADS_TOKEN не задан — Threads загрузить нельзя.")

        since_val = d_from.isoformat()
        until_val = None if d_to >= date.today() else (d_to + timedelta(days=1)).isoformat()

        loading_screen = st.empty()
        loading_screen.markdown("""
        <div style="background:linear-gradient(135deg,#132642,#0c192d);border:1px solid #2b4566;border-radius:18px;padding:60px 24px;text-align:center;max-width:850px;margin:24px auto;color:#e8eef8;">
          <div style="font-size:38px;color:#70b6ff;margin-bottom:14px;">◌</div>
          <div style="font-size:24px;font-weight:750;margin-bottom:12px;">Загружаем данные источников</div>
          <div style="font-size:15px;color:#b5c5db;line-height:1.7;">Получаем доступные сообщения<br>Подготавливаем аналитику обращений жителей Шымкента</div>
          <div style="font-size:13px;color:#80baff;margin-top:22px;">Пожалуйста, подождите…</div>
        </div>
        """, unsafe_allow_html=True)

        try:
            if source_choice in ("Threads", "Все источники") and token:
                if mode == "Поиск по словам (Threads API)":
                    qs = tuple(q.strip() for q in queries_text.splitlines() if q.strip())
                    threads_df, threads_errors = fetch_threads(token, qs, search_type, since_val,
                                                               until_val, int(max_pages))
                else:
                    threads_df, threads_errors = fetch_own_threads(token, since_val, until_val,
                                                                   int(max_pages), with_replies)
                st.session_state["threads_df"] = threads_df
                for err in threads_errors:
                    st.warning(err)
            if source_choice in ("Telegram", "Все источники"):
                try:
                    tg_id = st.secrets.get("TELEGRAM_API_ID")
                    tg_hash = st.secrets.get("TELEGRAM_API_HASH")
                except Exception:
                    tg_id, tg_hash = None, None
                tg_id = tg_id or os.environ.get("TELEGRAM_API_ID")
                tg_hash = tg_hash or os.environ.get("TELEGRAM_API_HASH")
                if not tg_id or not tg_hash:
                    st.warning("Для Telegram добавьте TELEGRAM_API_ID и TELEGRAM_API_HASH в Streamlit Cloud → Settings → Secrets")
                else:
                    tg_channels = [line.strip() for line in telegram_channels_text.splitlines() if line.strip()]
                    tg_df, tg_errors = fetch_telegram_public_channels(
                        tg_id, tg_hash, tuple(tg_channels), int(telegram_post_limit), int(telegram_comments_limit)
                    )
                    st.session_state["telegram_df"] = tg_df
                    for err in tg_errors:
                        st.warning(err)
        finally:
            loading_screen.empty()

    source_frames = []
    if source_choice in ("Threads", "Все источники"):
        source_frames.append(st.session_state.get("threads_df", pd.DataFrame()))
    if source_choice in ("Telegram", "Все источники"):
        source_frames.append(st.session_state.get("telegram_df", pd.DataFrame()))
    source_frames = [frame for frame in source_frames if frame is not None and not frame.empty]
    api_df = pd.concat(source_frames, ignore_index=True) if source_frames else None
    if api_df is not None:
        api_df = api_df.drop_duplicates(subset=["ID"], keep="last")
        if "Дата" in api_df.columns:
            dates = pd.to_datetime(api_df["Дата"], errors="coerce", utc=True)
            start = pd.Timestamp(d_from).tz_localize("UTC")
            end = (pd.Timestamp(d_to) + pd.Timedelta(days=1)).tz_localize("UTC")
            api_df = api_df[(dates >= start) & (dates < end)].copy()
    if api_df is None:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#132642,#0c192d);border:1px solid #2b4566;border-radius:18px;padding:58px 24px;text-align:center;max-width:850px;margin:24px auto;color:#e8eef8;">
          <div style="font-size:30px;margin-bottom:16px;">◎</div>
          <div style="font-size:24px;font-weight:750;margin-bottom:12px;">Медиамониторинг города</div>
          <div style="font-size:15px;color:#b5c5db;line-height:1.7;">Выберите источник, период и нажмите «Загрузить данные»<br>в левой панели, чтобы увидеть обращения и аналитику.</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    if api_df.empty:
        st.info("Публикации за выбранный период не найдены. Попробуйте изменить период и загрузить данные снова.")
        st.stop()

    sheets = {"Источники": api_df}

else:

    if uploaded is None:

        st.info("Загрузите файл с комментариями и публикациями в боковой панели. "

                "Обязательна только колонка с текстом. Остальные колонки (дата, источник, "

                "ссылка, лайки, район и т.д.) система определит сама.")

        st.stop()

    try:

        sheets = read_all(uploaded.getvalue(), uploaded.name)

    except Exception as e:

        st.error(f"Не удалось прочитать файл: {e}")

        st.stop()


if not sheets:

    st.error("В файле нет данных.")

    st.stop()


with st.sidebar:

    sheet = st.selectbox("Лист", list(sheets)) if len(sheets) > 1 else next(iter(sheets))


raw = sheets[sheet]

guess = guess_mapping(raw)

signature = hashlib.md5("|".join(map(str, raw.columns)).encode("utf-8")).hexdigest()[:8]

mapping = {field: guess.get(field) for field in FIELD_LABELS}


if not mapping["text"]:

    st.warning("Не удалось определить колонку с текстом. Выберите её вручную.")

    mapping["text"] = st.selectbox("Колонка с текстом сообщений", list(raw.columns),

                                   key=f"map_text_{signature}")


data, quality = prepare(raw, mapping)


if data.empty:

    st.error("После очистки не осталось сообщений. Проверьте выбранную колонку с текстом.")

    st.stop()


df = data.copy()


st.markdown("""<style>
.block-container {max-width: 1720px !important; padding-top: .9rem !important;}
div.st-key-category_all button, div.st-key-category_problems button,
div.st-key-category_thanks button, div.st-key-category_questions button,
div.st-key-category_suggestions button, div.st-key-category_information button {
  white-space: pre-line; min-height: 66px; text-align: left; justify-content: flex-start;
  font-size: 13px; line-height: 1.6; padding: 9px 11px; border-radius: 11px;
}
div.st-key-category_all button {border-left: 4px solid #996aff !important;}
div.st-key-category_problems button {border-left: 4px solid #fb4b76 !important;}
div.st-key-category_thanks button {border-left: 4px solid #20cda5 !important;}
div.st-key-category_questions button {border-left: 4px solid #4a9bff !important;}
div.st-key-category_suggestions button {border-left: 4px solid #f6ba49 !important;}
div.st-key-category_information button {border-left: 4px solid #b58aff !important;}
</style>""", unsafe_allow_html=True)

st.markdown("### Медиамониторинг обращений")
search_col, period_col = st.columns([3, 1], gap="small")
with search_col:
    query = st.text_input("Поиск по словам, адресу или объекту", placeholder="Например: вода, Нурсат, освещение")
with period_col:
    date_filter = st.selectbox("Период", ["За всё время", "За последние 7 дней", "За последние 30 дней"])

filtered = df.copy()
if date_filter != "За всё время" and filtered["date"].notna().any():
    days = 7 if date_filter == "За последние 7 дней" else 30
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=days - 1)
    filtered = filtered[filtered["date"].isna() | (filtered["date"] >= cutoff)]
if query.strip():
    filtered = filtered[
        filtered["text"].str.contains(query.strip(), case=False, na=False, regex=False)
        | filtered["place"].astype(str).str.contains(query.strip(), case=False, na=False, regex=False)
        | filtered["district"].astype(str).str.contains(query.strip(), case=False, na=False, regex=False)
        | filtered["categories"].map(lambda values: query.strip().casefold() in ", ".join(values).casefold())
    ]

f = filtered.copy()
total = len(f)
problems = int(f["is_problem"].sum())
negative = int((f["sentiment"] == "Негативная").sum())
positive = int((f["sentiment"] == "Позитивная").sum())
thanks_count = int((f["msg_type"] == "Благодарность").sum())
type_counts = f["msg_type"].value_counts()
category_counts = f[f["is_problem"]].explode("categories")["categories"].value_counts()
if category_counts.empty:
    category_counts = f.explode("categories")["categories"].value_counts()
ordered = f.sort_values("date", ascending=False, na_position="last")

all_posts = df[df["record_type"] == "Публикация"].copy()
all_comments = df[df["record_type"] == "Комментарий"].copy()
posts = all_posts.copy()

def detect_priority(text, is_problem=False):
    text = str(text or "").lower()

    critical_words = [
        "авария", "пожар", "взрыв", "затопление",
        "нет воды", "без воды", "нет отопления",
        "без отопления", "опасность", "угроза жизни",
        "обрыв провода", "утечка газа",
    ]

    high_words = [
        "яма", "разбитая дорога", "не работает свет",
        "нет освещения", "мусор", "свалка",
        "канализация", "не работает", "жалоба",
    ]

    medium_words = [
        "ремонт", "благоустройство", "предлагаю",
        "установить", "остановка", "тротуар",
        "озеленение", "пешеход",
    ]

    if any(word in text for word in critical_words):
        return 1
    if any(word in text for word in high_words):
        return 2
    if is_problem or any(word in text for word in medium_words):
        return 3
    return 4


comment_data = all_comments.copy()
comment_data["post_id"] = comment_data["post_id"].astype(str)

comment_texts = comment_data.groupby("post_id")["text"].agg(
    lambda values: " ".join(values.fillna("").astype(str))
)

comment_problems = comment_data.groupby("post_id")["is_problem"].agg(
    lambda values: values.fillna(False).eq(True).any()
)

posts["priority"] = posts.apply(
    lambda post: detect_priority(
        str(post.get("text", "")) + " " +
        str(comment_texts.get(str(post["post_id"]), "")),
        bool(post.get("is_problem", False)) or
        bool(comment_problems.get(str(post["post_id"]), False))
    ),
    axis=1
)


STATUS_OPTIONS = ["Без ответа", "В процессе", "Выполнено", "Требует проверки"]
STATUS_LABELS = {
    "Без ответа": "⚪ Без ответа",
    "В процессе": "🟠 В процессе",
    "Выполнено": "🟢 Выполнено",
    "Требует проверки": "🔵 Требует проверки",
}

def infer_work_status(post_id):
    replies = comment_data[comment_data["post_id"] == str(post_id)]
    if replies.empty:
        return "Без ответа"

    texts = replies.sort_values("date", na_position="first")["text"].fillna("").astype(str).tolist()
    progress = re.compile(
        r"в работе|в процессе|работы ведутся|ведутся работы|приступили|"
        r"направлен[оы]?|передан[оы]?|принят[оы]? в работу|"
        r"рассматрива[ею]|проверя[ею]|специалисты выехали|"
        r"жұмыс жүргізіл|қарастырылуда|тексерілуде|қабылданды|"
        r"жөндеу жұмыстары|қалпына келтіру жұмыстары",
        re.IGNORECASE,
    )
    completed = re.compile(
        r"работы завершены|проблема решена|устранен[аоы]?|"
        r"восстановлен[аоы]?|отремонтирован[аоы]?|"
        r"жұмыс аяқталды|мәселе шешілді|қалпына келтірілді",
        re.IGNORECASE,
    )
    for message in reversed(texts):
        if completed.search(message):
            return "Требует проверки"
        if progress.search(message):
            return "В процессе"
    return "Требует проверки"


posts["work_status"] = posts["post_id"].astype(str).map(infer_work_status)

# Категории слева относятся ТОЛЬКО к самим публикациям.
# Комментарии классифицируются и фильтруются отдельно в правой колонке.
filtered_publications = f[f["record_type"].eq("Публикация")].copy()

CATEGORY_CHOICES = [
    ("all", "📝", "Все публикации", len(filtered_publications)),
    ("problems", "🚨", "Жалобы", int(filtered_publications["msg_type"].eq("Жалоба").sum())),
    ("thanks", "💚", "Благодарности", int(filtered_publications["msg_type"].eq("Благодарность").sum())),
    ("questions", "❔", "Вопросы", int(filtered_publications["msg_type"].eq("Вопрос").sum())),
    ("suggestions", "💡", "Предложения", int(filtered_publications["msg_type"].eq("Предложение").sum())),
    ("information", "ℹ️", "Информация", int(filtered_publications["msg_type"].eq("Информация").sum())),
]
if "message_filter" not in st.session_state or st.session_state["message_filter"] not in [x[0] for x in CATEGORY_CHOICES]:
    st.session_state["message_filter"] = "all"
selected_filter = st.session_state["message_filter"]

category_types = {
    "problems": "Жалоба",
    "thanks": "Благодарность",
    "questions": "Вопрос",
    "suggestions": "Предложение",
    "information": "Информация",
}
selected_publications = (
    filtered_publications if selected_filter == "all"
    else filtered_publications[filtered_publications["msg_type"].eq(category_types[selected_filter])]
)
matched_ids = set(selected_publications["post_id"].dropna().astype(str))
posts = posts[posts["post_id"].astype(str).isin(matched_ids)].copy()



st.markdown("#### Публикации и комментарии")
filter_col, status_col, sort_col = st.columns([1, 1, 1], gap="small")

with filter_col:
    priority_filter = st.selectbox(
        "Приоритет",
        [
            "Все приоритеты",
            "🔴 P1 — Критический",
            "🟠 P2 — Высокий",
            "🔵 P3 — Средний",
            "🟢 P4 — Низкий",
        ],
        label_visibility="collapsed",
        key="priority_filter",
    )

with status_col:
    work_status_filter = st.selectbox(
        "Статус выполнения",
        ["Все статусы"] + STATUS_OPTIONS,
        format_func=lambda value: "Все статусы" if value == "Все статусы" else STATUS_LABELS[value],
        label_visibility="collapsed",
        key="work_status_filter",
    )

with sort_col:
    sort_mode = st.selectbox(
        "Сортировка",
        [
            "Сначала новые",
            "Сначала старые",
            "Самые обсуждаемые",
            "По приоритету",
        ],
        label_visibility="collapsed",
        key="posts_sort_mode",
    )


priority_map = {
    "🔴 P1 — Критический": 1,
    "🟠 P2 — Высокий": 2,
    "🔵 P3 — Средний": 3,
    "🟢 P4 — Низкий": 4,
}

if priority_filter != "Все приоритеты":
    posts = posts[
        posts["priority"] == priority_map[priority_filter]
    ].copy()


if work_status_filter != "Все статусы":
    posts = posts[
        posts["post_id"].astype(str).map(
            lambda post_id: infer_work_status(post_id)
        ) == work_status_filter
    ].copy()

comment_counts = comment_data["post_id"].value_counts()

posts["comment_count"] = (
    posts["post_id"].astype(str)
    .map(comment_counts)
    .fillna(0)
    .astype(int)
)


if sort_mode == "Самые обсуждаемые":
    posts = posts.sort_values(
        ["comment_count", "date"],
        ascending=[False, False],
        na_position="last",
    )
elif sort_mode == "Сначала старые":
    posts = posts.sort_values(
        "date", ascending=True, na_position="last"
    )
elif sort_mode == "По приоритету":
    posts = posts.sort_values(
        ["priority", "date"],
        ascending=[True, False],
        na_position="last",
    )
else:
    posts = posts.sort_values(
        "date", ascending=False, na_position="last"
    )


st.caption(f"Найдено публикаций: {len(posts)} · Статусы предварительно определяются по комментариям.")


st.markdown("""
<style>
div[class*="st-key-post_select_"] button {
    height: auto !important;
    min-height: 112px !important;
    padding: 16px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: pre-wrap !important;
    line-height: 1.65 !important;
    margin-bottom: 10px !important;
}
div[class*="st-key-post_select_"] button p {
    text-align: left !important;
    white-space: pre-wrap !important;
    overflow-wrap: anywhere !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
@media (min-width: 900px) {
  html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
    height: 100vh !important;
    overflow: hidden !important;
  }
  section[data-testid="stMain"] { height: 100vh !important; overflow: hidden !important; }
  section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
    height: 100vh !important;
    overflow: hidden !important;
  }
  div.st-key-category_scroll [data-testid="stVerticalScrollContainer"],
  div.st-key-posts_scroll [data-testid="stVerticalScrollContainer"],
  div.st-key-details_scroll [data-testid="stVerticalScrollContainer"] {
    height: clamp(220px, calc(100vh - 350px), 900px) !important;
    max-height: calc(100vh - 350px) !important;
    overflow-y: auto !important;
  }
}
@media (max-width: 899px) {
  div.st-key-category_scroll [data-testid="stVerticalScrollContainer"],
  div.st-key-posts_scroll [data-testid="stVerticalScrollContainer"],
  div.st-key-details_scroll [data-testid="stVerticalScrollContainer"] {
    max-height: 55vh !important;
  }
}
</style>
""", unsafe_allow_html=True)

category_col, left_col, right_col = st.columns([0.78, 1.65, 1.65], gap="small")

if "selected_post_id" not in st.session_state:
    st.session_state["selected_post_id"] = None

with category_col:
    st.markdown("#### Категории")
    with st.container(height=480, border=False, key="category_scroll"):
        for category_key, category_icon, category_title, category_count in CATEGORY_CHOICES:
            if st.button(
                f"{category_icon} {category_title} · {category_count}",
                key=f"category_{category_key}",
                type="primary" if selected_filter == category_key else "secondary",
                use_container_width=True,
            ):
                st.session_state["message_filter"] = category_key
                st.rerun()
with left_col:
    st.markdown("#### Публикации")
    section_posts = posts
    visible_posts = section_posts.head(200).reset_index(drop=True)
    visible_ids = visible_posts["post_id"].astype(str).tolist()
    if visible_ids and st.session_state["selected_post_id"] not in visible_ids:
        st.session_state["selected_post_id"] = visible_ids[0]

    st.caption(f"Найдено публикаций: {len(section_posts)}")
    with st.container(height=480, border=False, key="posts_scroll"):
        if visible_posts.empty:
            st.info("В этом разделе публикаций нет.")
        for i, post in visible_posts.iterrows():
            post_id = str(post["post_id"])
            is_selected = st.session_state["selected_post_id"] == post_id
            priority = int(post["priority"])
            priority_labels = {
                1: "🔴 P1 · Критический",
                2: "🟠 P2 · Высокий",
                3: "🔵 P3 · Средний",
                4: "🟢 P4 · Низкий",
            }
            work_label = STATUS_LABELS[infer_work_status(post_id)]
            count = int(post["comment_count"])
            label = (
                f"{priority_labels[priority]}  ·  {work_label}\n\n"
                f"{str(post['text'])}\n\n"
                f"{post.get('source', 'Источник')}  ·  💬 {count} комментариев"
            )
            if st.button(
                label,
                key=f"post_select_{i}_{post_id}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                st.session_state["selected_post_id"] = post_id
                st.rerun()

with right_col:
    st.markdown("#### Публикация и комментарии")
    with st.container(height=480, border=False, key="details_scroll"):

        selected_id = st.session_state["selected_post_id"]

        selected_rows = visible_posts[
            visible_posts["post_id"].astype(str) == selected_id
        ]


        if not selected_rows.empty:
            post = selected_rows.iloc[0]

            post_comments = all_comments[
                all_comments["post_id"].astype(str) == selected_id
            ].copy()

            with st.container(border=True):
                st.caption(f"{post.get('source', 'Источник')} · Публикация")
                st.write(post["text"])

                url = str(post.get("url", "") or "").strip()
                if url.startswith(("https://", "http://")):
                    st.link_button(
                        f"Открыть в {post.get('source', 'источнике')}",
                        url,
                        use_container_width=True,
                    )

            st.markdown(f"**Комментарии ({len(post_comments)})**")
            comment_labels = {
                "Все": "Все комментарии",
                "Жалобы": "Жалоба",
                "Вопросы": "Вопрос",
                "Предложения": "Предложение",
                "Благодарности": "Благодарность",
                "Информация": "Информация",
            }
            # Обычные кнопки вместо segmented_control: без системной красной/белой подсветки.
            if "comment_type_filter_choice" not in st.session_state:
                st.session_state["comment_type_filter_choice"] = "Все"
            comment_options = list(comment_labels)
            for start in (0, 3):
                cols = st.columns(3, gap="small")
                for col, option in zip(cols, comment_options[start:start + 3]):
                    with col:
                        is_selected = st.session_state["comment_type_filter_choice"] == option
                        if st.button(
                            option,
                            key=f"comment_filter_btn_{option}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["comment_type_filter_choice"] = option
                            st.rerun()
            selected_comment_tab = st.session_state["comment_type_filter_choice"]
            comment_type = comment_labels[selected_comment_tab]
            shown_comments = (
                post_comments if comment_type == "Все комментарии"
                else post_comments[post_comments["msg_type"] == comment_type]
            )
            st.caption(f"Показано: {len(shown_comments)} из {len(post_comments)}")
            with st.container(border=False):
                if shown_comments.empty:
                    st.info("Комментариев выбранного типа нет.")
                else:
                    for _, comment in shown_comments.iterrows():
                        with st.container(border=True):
                            st.write(comment["text"])
                            st.caption(f"Тип: {comment.get('msg_type', 'Не определён')}")
        else:
            st.info("Выберите публикацию слева.")

if posts.empty:
    st.info("Публикаций по выбранным условиям не найдено.")

if len(posts) > 200:
    st.info("Показаны первые 200 публикаций.")

with st.sidebar:
    with st.expander("Темы и выгрузка Excel", expanded=False):
        st.markdown("#### На что чаще всего обращают внимание")

        if category_counts.empty:
            st.caption("Популярные темы пока не определены.")
        else:
            st.markdown(
                " · ".join(
                    f"**{category}** — {int(count)}"
                    for category, count in category_counts.head(5).items()
                )
            )

        st.subheader("Скачать данные")
        report_sheets = {
            "Сводка": pd.DataFrame({"Показатель": ["Всего сообщений", "Жалобы и проблемы", "Негативные сообщения", "Благодарности"],
                                     "Значение": [total, problems, negative, positive]}),
            "Частые темы": category_counts.rename_axis("Тема").reset_index(name="Сообщений"),
            "Сообщения": messages_export(ordered),
            "Качество данных": pd.DataFrame({"Показатель": list(quality), "Значение": list(quality.values())}),
        }
        excel_data = build_excel(report_sheets)
        st.download_button(
            "Скачать результаты в Excel",
            data=excel_data,
            file_name="медиамониторинг_Шымкент.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
