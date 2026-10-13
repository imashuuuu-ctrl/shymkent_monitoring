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

    # Сохраняем ID публикаций и комментариев
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

st.title("Медиамониторинг города — Шымкент")



with st.sidebar:
    st.header("Данные")

    mode = "Мои публикации (Threads API)"
    st.write("**Мои публикации (Threads API)**")

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

            # Оформление Threads
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
                    <img src="https://cdn.simpleicons.org/threads/000000">
                </div>
                <div>
                    <div class="threads-name">Threads API</div>
                    <div class="threads-description">
                        Мониторинг публикаций
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="threads-status">
            <span style="color:#4adeae;">✓</span>
            &nbsp; Загрузка комментариев
        </div>
        """, unsafe_allow_html=True)

        # Настройки загрузки
        with_replies = st.checkbox(
            "Загружать комментарии под постами",
            value=True
        )

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
            "↻ Загрузить из Threads",
            use_container_width=True,
            type="primary"
        )



if mode != "Файл Excel/CSV":

    if load_btn:

        if not token:

            st.error("Не задан THREADS_TOKEN (.streamlit/secrets.toml или переменная окружения).")

            st.stop()

        since_val = d_from.isoformat()

        until_val = None if d_to >= date.today() else (d_to + timedelta(days=1)).isoformat()

        if mode == "Поиск по словам (Threads API)":

            qs = tuple(q.strip() for q in queries_text.splitlines() if q.strip())

            if not qs:

                st.error("Укажите хотя бы одно ключевое слово.")

                st.stop()

            api_df, api_errors = fetch_threads(token, qs, search_type, since_val,

                                               until_val, int(max_pages))

        else:

            api_df, api_errors = fetch_own_threads(token, since_val, until_val,

                                                   int(max_pages), with_replies)

        for err in api_errors:

            st.warning(err)

        st.session_state["api_df"] = api_df

    api_df = st.session_state.get("api_df")

    if api_df is None or api_df.empty:

        st.info("Задайте ключевые слова и нажмите «Загрузить из Threads» в боковой панели.")

        st.stop()

    sheets = {"Threads API": api_df}

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



with st.expander("Качество данных и сопоставление колонок"):

    q1, q2 = st.columns(2)

    q1.dataframe(pd.DataFrame({"Показатель": list(quality), "Значение": list(quality.values())}),

                 hide_index=True)

    q2.dataframe(pd.DataFrame({

        "Поле": [FIELD_LABELS[k].replace(" *", "") for k in FIELD_LABELS],

        "Колонка файла": [mapping[k] or "—" for k in FIELD_LABELS],

    }), hide_index=True)

    st.caption("Автор хранится только в виде хеша. Язык определяется по буквам "

               "казахского алфавита, если колонка языка не выбрана.")



df = data.copy()

st.subheader("Найти нужные сообщения")
filter_cols = st.columns([1, 2, 1])
with filter_cols[0]:
    kind_filter = st.selectbox("Что показать", ["Все сообщения", "Проблемы", "Благодарности"])
with filter_cols[1]:
    query = st.text_input("Поиск по словам, адресу или объекту", placeholder="Например: вода, Нурсат, освещение")
with filter_cols[2]:
    date_filter = st.selectbox("Период", ["За всё время", "За последние 7 дней", "За последние 30 дней"])

filtered = df.copy()
if date_filter != "За всё время" and filtered["date"].notna().any():
    days = 7 if date_filter == "За последние 7 дней" else 30
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=days - 1)
    filtered = filtered[filtered["date"].isna() | (filtered["date"] >= cutoff)]
if kind_filter == "Проблемы":
    filtered = filtered[filtered["is_problem"]]
elif kind_filter == "Благодарности":
    filtered = filtered[filtered["msg_type"] == "Благодарность"]
if query.strip():
    filtered = filtered[
        filtered["text"].str.contains(query.strip(), case=False, na=False, regex=False)
        | filtered["place"].astype(str).str.contains(query.strip(), case=False, na=False, regex=False)
        | filtered["district"].astype(str).str.contains(query.strip(), case=False, na=False, regex=False)
        | filtered["categories"].map(lambda values: query.strip().casefold() in ", ".join(values).casefold())
    ]

if filtered.empty:
    st.info("По этим условиям сообщений не найдено. Попробуйте изменить поиск или период.")
    st.stop()

f = filtered.copy()
total = len(f)
problems = int(f["is_problem"].sum())
negative = int((f["sentiment"] == "Негативная").sum())
positive = int((f["sentiment"] == "Позитивная").sum())

st.divider()
st.subheader("Кратко о сообщениях")


# Красивые интерактивные карточки статистики
thanks_count = int((f["msg_type"] == "Благодарность").sum())

st.markdown("""
<style>
div.st-key-stat_all button,
div.st-key-stat_problems button,
div.st-key-stat_thanks button {
    min-height: 125px;
    border-radius: 18px;
    background: #152238;
    border: 1px solid #30435e;
    color: #f3f7ff;
    font-size: 19px;
    font-weight: 700;
    white-space: pre-line;
    line-height: 1.8;
    width: 100%;
    transition: 0.2s ease;
}

div.st-key-stat_all button:hover {
    border-color: #65aeff;
    background: #1b3553;
}

div.st-key-stat_problems button:hover {
    border-color: #ff9486;
    background: #392936;
}

div.st-key-stat_thanks button:hover {
    border-color: #65d5a4;
    background: #193d3b;
}
</style>
""", unsafe_allow_html=True)

k1, k2, k3 = st.columns(3, gap="medium")

with k1:
    if st.button(
        f"📋 Все сообщения\n\n{total}",
        key="stat_all",
        use_container_width=True
    ):
        st.session_state["message_filter"] = "all"

with k2:
    if st.button(
        f"⚠️ Жалобы и проблемы\n\n{problems}",
        key="stat_problems",
        use_container_width=True
    ):
        st.session_state["message_filter"] = "problems"

with k3:
    if st.button(
        f"❤️ Благодарности\n\n{thanks_count}",
        key="stat_thanks",
        use_container_width=True
    ):
        st.session_state["message_filter"] = "thanks"

selected_filter = st.session_state.get("message_filter", "all")

if selected_filter == "problems":
    selected_messages = f[f["is_problem"] == True]
    st.markdown("### ⚠️ Жалобы и проблемы")

elif selected_filter == "thanks":
    selected_messages = f[f["msg_type"] == "Благодарность"]
    st.markdown("### ❤️ Благодарности")

else:
    selected_messages = f
    st.markdown("### 📋 Все сообщения")

st.caption(f"Найдено сообщений: {len(selected_messages)}")


st.subheader("На что чаще всего обращают внимание")
category_counts = f[f["is_problem"]].explode("categories")["categories"].value_counts()
if category_counts.empty:
    category_counts = f.explode("categories")["categories"].value_counts()
if category_counts.empty:
    st.write("Пока нет данных для определения популярных тем.")
else:
    for category, count in category_counts.head(5).items():
        st.markdown(f"- **{category}** — {int(count)} сообщений")

st.divider()
st.subheader("Сообщения жителей")
st.caption(f"Найдено сообщений: {total}. Автоматическая классификация может ошибаться — при необходимости откройте оригинал.")

# Публикации и комментарии Threads

ordered = f.sort_values("date", ascending=False, na_position="last")

# Берём все публикации и комментарии из загруженных данных
all_posts = df[df["record_type"] == "Публикация"].copy()
all_comments = df[df["record_type"] == "Комментарий"].copy()

# Сообщения, соответствующие выбранному фильтру
matched_ids = set(selected_messages["post_id"].dropna().astype(str))

# Показываем публикации, содержащие подходящие сообщения
posts = all_posts[
    all_posts["post_id"].astype(str).isin(matched_ids)
].copy()

posts = posts.sort_values(
    "date", ascending=False, na_position="last"
)

st.caption(f"Найдено публикаций: {len(posts)}")

for _, post in posts.head(200).iterrows():

    post_id = str(post["post_id"])

    post_comments = all_comments[
        all_comments["post_id"].astype(str) == post_id
    ].copy()

    # Для жалоб и благодарностей показываем подходящие комментарии
    if selected_filter == "thanks":
        post_comments = post_comments[
            post_comments["msg_type"] == "Благодарность"
        ]

    elif selected_filter == "problems":
        post_comments = post_comments[
            post_comments["is_problem"] == True
        ]

    title = str(post["text"])
    if len(title) > 110:
        title = title[:110] + "..."

    with st.expander(
        f"📝 {title}  |  💬 {len(post_comments)} комментариев"
    ):

        st.markdown("**Публикация Threads**")
        st.write(post["text"])

        url = str(post.get("url", "") or "").strip()
        if url.startswith(("https://", "http://")):
            st.markdown(f"[Открыть публикацию в Threads]({url})")

        st.divider()
        st.markdown("**Комментарии**")

        if post_comments.empty:
            st.info("Подходящих комментариев нет.")
        else:
            for _, comment in post_comments.iterrows():
                with st.container(border=True):
                    st.write(comment["text"])

                    st.caption(
                        f"Тип: {comment.get('msg_type', 'Не определён')}"
                    )

if posts.empty:
    st.info("Публикаций по выбранным условиям не найдено.")

if len(posts) > 200:
    st.info("Показаны первые 200 публикаций.")

st.divider()
with st.expander("Подробности загрузки"):
    st.write(f"Строк принято в анализ: {len(data)}")
    if quality:
        st.dataframe(
            pd.DataFrame({"Показатель": list(quality), "Значение": list(quality.values())}),
            hide_index=True,
            use_container_width=True,
        )
    st.caption("Авторы не показываются в интерфейсе. Автоматическая классификация и определение местоположения приблизительны.")

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
