"""Отдельная карта городских обращений для медиамониторинга Шымкента."""
import html
import time
from urllib.parse import urlparse
import requests
import pandas as pd
import streamlit as st

CITY_CENTER = (42.3155, 69.5869)  # центр обзора, НЕ координаты обращений
COLORS = {"Жалоба": "#f04d72", "Вопрос": "#4e9eff", "Предложение": "#f4b740", "Благодарность": "#29c7a0", "Информация": "#a78bfa"}

@st.cache_data(ttl=86400, show_spinner=False)
def geocode_known_place(place):
    """Ищет явно упомянутую локацию; не подменяет её центром города."""
    import re
    name = str(place).strip()
    # Nominatim лучше находит названия без префиксов «мкр» и «район».
    clean = re.sub(r"^(?:мкр\.?|микрорайон|район|проспект|ул\.?|улица)\s+", "", name, flags=re.I).strip()
    queries = list(dict.fromkeys([
        f"{clean}, Шымкент, Казахстан",
        f"{clean}, Shymkent, Kazakhstan",
        f"{name}, Shymkent, Kazakhstan",
    ]))
    for query in queries:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 3, "countrycodes": "kz"},
                headers={"User-Agent": "ShymkentMediaMonitoring/1.1 (local community research)"},
                timeout=12,
            )
            response.raise_for_status()
            for item in response.json():
                lat, lon = float(item["lat"]), float(item["lon"])
                if 42.0 <= lat <= 42.65 and 69.1 <= lon <= 70.1:
                    return (lat, lon)
        except (requests.RequestException, ValueError, KeyError, IndexError):
            pass
        time.sleep(1.1)
    return None


def render_problem_map(df):
    st.markdown("### 🗺️ Карта проблем Шымкента")
    st.caption("Светлая интерактивная карта в стиле городского геопортала. Метки — по доступным геоданным OpenStreetMap, не точные адреса заявителей.")
    try:
        import folium
        import streamlit.components.v1 as components
    except ImportError:
        st.warning("Для карты установите Folium: python -m pip install folium")
        return

    messages = df[df["record_type"].eq("Публикация")].copy()
    # Для карты нужны обращения с определённым местом, а не любой текст.
    messages = messages[messages["place"].notna() & ~messages["place"].astype(str).isin(["", "Местоположение не определено"])].copy()
    source_values = sorted(messages["source"].dropna().astype(str).unique().tolist())
    category_values = list(COLORS)
    c1, c2 = st.columns(2)
    with c1:
        chosen_sources = st.multiselect("Источники на карте", source_values, default=source_values, key="map_sources")
    with c2:
        chosen_types = st.multiselect("Тип обращения", category_values, default=category_values, key="map_types")
    messages = messages[messages["source"].astype(str).isin(chosen_sources) & messages["msg_type"].isin(chosen_types)]
    if messages.empty:
        st.info("Пока нет публикаций с распознанным местом для выбранных фильтров. В основном разделе публикации остаются доступными.")
        st.caption("Если в тексте есть адрес, но поле «Место» не распознано, потребуется расширить словарь названий.")

    # Геокодируем только явные распознанные места. Не ставим все сообщения в центр города.
    places = list(dict.fromkeys(messages["place"].astype(str)))[:12]
    if st.button("📍 Найти места на карте", key="map_geocode", type="primary"):
        with st.spinner("Уточняем координаты мест через OpenStreetMap..."):
            coords = dict(st.session_state.get("map_coords", {}))
            for place in places:
                if place not in coords:
                    coords[place] = geocode_known_place(place)
                    time.sleep(1.1)  # не чаще 1 запроса в секунду
            st.session_state["map_coords"] = coords

    coords = st.session_state.get("map_coords", {})
    unresolved = [p for p in places if coords.get(p) is None]
    if unresolved:
        with st.expander(f"Места без координат ({len(unresolved)})"):
            st.write("Не удалось найти точное положение через OpenStreetMap:")
            st.write(", ".join(unresolved))
            st.caption("Такие места не отмечаются случайной точкой. Можно уточнить название места в исходных данных.")
    fmap = folium.Map(location=CITY_CENTER, zoom_start=11, tiles="OpenStreetMap", control_scale=True)
    plotted = 0
    for _, msg in messages.head(250).iterrows():
        point = coords.get(str(msg["place"]))
        if point is None:
            continue
        msg_type = str(msg["msg_type"])
        snippet = html.escape(str(msg["text"])[:300])
        place = html.escape(str(msg["place"]))
        source = html.escape(str(msg["source"]))
        raw_url = str(msg.get("url", "") or "")
        parsed = urlparse(raw_url)
        link = (f'<a href="{html.escape(raw_url, quote=True)}" target="_blank" rel="noopener noreferrer">Открыть публикацию</a>'
                if parsed.scheme in ("http", "https") and parsed.netloc else "")
        popup = folium.Popup(f'<div style="width:260px;font-family:Arial"><b>{html.escape(msg_type)}</b> · {source}<br><b>{place}</b><p>{snippet}</p>{link}</div>', max_width=310)
        folium.CircleMarker(location=point, radius=7, color=COLORS.get(msg_type, "#a78bfa"),
                            fill=True, fill_opacity=.83, weight=2, popup=popup,
                            tooltip=f"{msg_type}: {place}").add_to(fmap)
        plotted += 1
    components.html(fmap.get_root().render(), height=620, scrolling=False)
    st.caption(f"Показано меток: {plotted}. Публикации без подтверждённой геопозиции не размещаются на карте. "
               "Метки могут совпадать, если обращения относятся к одному месту.")
    missing = len(messages) - plotted
    if missing > 0:
        st.info(f"Без координат: {missing} публикаций. Нажмите «Найти места на карте»; если место не найдено, оно останется без метки.")
