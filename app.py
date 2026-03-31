import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

from db import get_task_statuses, get_team_progress, init_db, set_task_completion
from utils import get_greeting


st.set_page_config(
    page_title="Ikos B2B Daily Task Tracker",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TIMEZONE = "Europe/Athens"
GREETING_SECONDS = 3
API_KEY = st.secrets.get("API_KEY", "")

OFFICE_LOCATIONS = {
    "Thessaloniki": {"lat": 40.566848672247765, "lon": 22.986678738493765},
}


def init_session() -> None:
    defaults = {
        "logged_in": False,
        "username": None,
        "display_name": None,
        "theme_mode": "Light",
        "intro_shown": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def get_today_str() -> str:
    return get_now().date().isoformat()


def get_today_tasks() -> list[str]:
    weekday = get_now().weekday()
    if weekday in [0, 3]:  # Monday, Thursday
        return [
            "Occupancy Charts 2026",
            "Occupancy Charts 2027",
            "Out of Order Report",
        ]
    return [
        "Occupancy Charts 2026",
        "Out of Order Report",
    ]


def get_motivation(pct: int) -> str:
    if pct == 0:
        return "Let’s get started."
    if pct < 50:
        return "Good progress. Keep moving."
    if pct < 100:
        return "Keep going, almost there."
    return "Completed — great job team."


def get_weather_icon_svg(weather: str) -> str:
    weather = (weather or "").strip()

    icons = {
        "Clear": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="4.2" fill="#F5B301"></circle>
              <g stroke="#F5B301" stroke-width="1.8" stroke-linecap="round">
                <line x1="12" y1="2.5" x2="12" y2="5.2"></line>
                <line x1="12" y1="18.8" x2="12" y2="21.5"></line>
                <line x1="2.5" y1="12" x2="5.2" y2="12"></line>
                <line x1="18.8" y1="12" x2="21.5" y2="12"></line>
                <line x1="5.2" y1="5.2" x2="7.1" y2="7.1"></line>
                <line x1="16.9" y1="16.9" x2="18.8" y2="18.8"></line>
                <line x1="16.9" y1="7.1" x2="18.8" y2="5.2"></line>
                <line x1="5.2" y1="18.8" x2="7.1" y2="16.9"></line>
              </g>
            </svg>
        """,
        "Clouds": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <ellipse cx="10" cy="13.2" rx="5.2" ry="3.4" fill="#C8D0DF"></ellipse>
              <ellipse cx="14.8" cy="12.8" rx="4.5" ry="3.1" fill="#B5C0D3"></ellipse>
              <ellipse cx="7.2" cy="14.1" rx="3.2" ry="2.5" fill="#D6DDE9"></ellipse>
            </svg>
        """,
        "Rain": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <ellipse cx="10" cy="10.8" rx="5.2" ry="3.4" fill="#C8D0DF"></ellipse>
              <ellipse cx="14.8" cy="10.4" rx="4.5" ry="3.1" fill="#B5C0D3"></ellipse>
              <g stroke="#4A90E2" stroke-width="1.8" stroke-linecap="round">
                <line x1="8" y1="15.2" x2="6.8" y2="18.2"></line>
                <line x1="12" y1="15.2" x2="10.8" y2="18.2"></line>
                <line x1="16" y1="15.2" x2="14.8" y2="18.2"></line>
              </g>
            </svg>
        """,
        "Drizzle": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <ellipse cx="10" cy="10.8" rx="5.2" ry="3.4" fill="#C8D0DF"></ellipse>
              <ellipse cx="14.8" cy="10.4" rx="4.5" ry="3.1" fill="#B5C0D3"></ellipse>
              <g stroke="#67A7EF" stroke-width="1.5" stroke-linecap="round">
                <line x1="9" y1="15.5" x2="8.2" y2="17.4"></line>
                <line x1="13" y1="15.5" x2="12.2" y2="17.4"></line>
                <line x1="17" y1="15.5" x2="16.2" y2="17.4"></line>
              </g>
            </svg>
        """,
        "Thunderstorm": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <ellipse cx="10" cy="10.8" rx="5.2" ry="3.4" fill="#C8D0DF"></ellipse>
              <ellipse cx="14.8" cy="10.4" rx="4.5" ry="3.1" fill="#B5C0D3"></ellipse>
              <polygon points="12,14.4 9.5,18.6 12.4,18.6 10.8,21.4 15.2,16.6 12.4,16.6 14,14.4" fill="#F5B301"></polygon>
            </svg>
        """,
        "Snow": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <ellipse cx="10" cy="10.8" rx="5.2" ry="3.4" fill="#C8D0DF"></ellipse>
              <ellipse cx="14.8" cy="10.4" rx="4.5" ry="3.1" fill="#B5C0D3"></ellipse>
              <g stroke="#7FB7FF" stroke-width="1.4" stroke-linecap="round">
                <line x1="8" y1="15.4" x2="8" y2="18.2"></line>
                <line x1="6.6" y1="16.8" x2="9.4" y2="16.8"></line>
                <line x1="12.5" y1="15.4" x2="12.5" y2="18.2"></line>
                <line x1="11.1" y1="16.8" x2="13.9" y2="16.8"></line>
                <line x1="16.5" y1="15.4" x2="16.5" y2="18.2"></line>
                <line x1="15.1" y1="16.8" x2="17.9" y2="16.8"></line>
              </g>
            </svg>
        """,
        "Mist": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <g stroke="#B8C2D1" stroke-width="1.8" stroke-linecap="round">
                <line x1="5" y1="8" x2="19" y2="8"></line>
                <line x1="3.5" y1="12" x2="17.5" y2="12"></line>
                <line x1="6.5" y1="16" x2="20.5" y2="16"></line>
              </g>
            </svg>
        """,
        "Fog": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <g stroke="#B8C2D1" stroke-width="1.8" stroke-linecap="round">
                <line x1="5" y1="8" x2="19" y2="8"></line>
                <line x1="3.5" y1="12" x2="17.5" y2="12"></line>
                <line x1="6.5" y1="16" x2="20.5" y2="16"></line>
              </g>
            </svg>
        """,
        "Haze": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <g stroke="#B8C2D1" stroke-width="1.8" stroke-linecap="round">
                <line x1="5" y1="8" x2="19" y2="8"></line>
                <line x1="3.5" y1="12" x2="17.5" y2="12"></line>
                <line x1="6.5" y1="16" x2="20.5" y2="16"></line>
              </g>
            </svg>
        """,
        "Unavailable": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="4" fill="#D3D8E2"></circle>
            </svg>
        """,
    }

    return icons.get(
        weather,
        """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="9" r="3.6" fill="#F5B301"></circle>
          <ellipse cx="12" cy="13.2" rx="5.2" ry="3.4" fill="#C8D0DF"></ellipse>
          <ellipse cx="16.2" cy="12.9" rx="4.1" ry="2.8" fill="#B5C0D3"></ellipse>
        </svg>
        """,
    )


@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(location: dict, api_key: str) -> dict:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "appid": api_key,
        "units": "metric",
        "lat": location["lat"],
        "lon": location["lon"],
    }
    response = requests.get(url, params=params, timeout=10)
    return {"status_code": response.status_code, "json": response.json()}


def get_weather_for_city(location: dict) -> dict:
    if not API_KEY:
        return {"temp": "—", "weather": "Unavailable", "icon": get_weather_icon_svg("Unavailable")}

    try:
        result = fetch_weather(location, API_KEY)
        if result["status_code"] != 200:
            return {"temp": "—", "weather": "Unavailable", "icon": get_weather_icon_svg("Unavailable")}

        data = result["json"]
        temp = round(data["main"]["temp"])
        weather = data["weather"][0]["main"]
        return {
            "temp": f"{temp}°C",
            "weather": weather,
            "icon": get_weather_icon_svg(weather),
        }
    except Exception:
        return {"temp": "—", "weather": "Unavailable", "icon": get_weather_icon_svg("Unavailable")}


def get_theme_css(dark_mode: bool) -> str:
    bg = "#0B1220" if dark_mode else "#F3F4F6"
    card_bg = "#111827" if dark_mode else "#FFFFFF"
    title = "#F8FAFC" if dark_mode else "#0F172A"
    text = "#E5E7EB" if dark_mode else "#111827"
    muted = "#94A3B8" if dark_mode else "#6B7280"
    border = "#243041" if dark_mode else "#E5E7EB"
    accent = "#2563EB"
    shadow = "0 10px 30px rgba(0,0,0,0.22)" if dark_mode else "0 10px 30px rgba(15,23,42,0.08)"
    weather_bg = "#0F172A" if dark_mode else "#FFFFFF"
    weather_border = "#243041" if dark_mode else "#E5E7EB"
    weather_icon_bg = "#172554" if dark_mode else "#EFF6FF"

    return f"""
    <style>
    .stApp {{
        background: {bg};
    }}

    header, footer, #MainMenu {{
        visibility: hidden;
    }}

    .block-container {{
        max-width: 1280px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }}

    h1, h2, h3, h4, h5, h6, p, div, label {{
        color: {text};
    }}

    [data-testid="stSidebar"] {{
        background: {card_bg};
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 22px;
        box-shadow: {shadow};
    }}

    .app-title {{
        text-align: center;
        color: {title};
        font-size: 3.4rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin: 0;
        line-height: 1;
    }}

    .app-subtitle {{
        text-align: center;
        color: {muted};
        font-size: 1.18rem;
        margin-top: 0.7rem;
        margin-bottom: 0.85rem;
    }}

    .app-datetime {{
        text-align: center;
        color: {muted};
        font-size: 1.04rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }}

    .weather-pill {{
        display: inline-flex;
        align-items: center;
        gap: 12px;
        padding: 0.85rem 1.05rem;
        border-radius: 999px;
        border: 1px solid {weather_border};
        background: {weather_bg};
        box-shadow: {shadow};
    }}

    .weather-pill-wrap {{
        text-align: center;
        margin-bottom: 1.35rem;
    }}

    .weather-icon-wrap {{
        width: 34px;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        background: {weather_icon_bg};
    }}

    .weather-icon-wrap svg {{
        width: 22px;
        height: 22px;
        display: block;
    }}

    .weather-text {{
        color: {text};
        font-size: 0.98rem;
        font-weight: 600;
    }}

    .hello-text {{
        color: {title};
        font-size: 2.05rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }}

    .hello-sub {{
        color: {muted};
        font-size: 0.98rem;
        margin-bottom: 1rem;
    }}

    .task-meta {{
        color: {muted};
        font-size: 0.88rem;
        margin: -0.2rem 0 0.7rem 2rem;
    }}

    .metric-big {{
        color: {accent};
        font-size: 3rem;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 0.25rem;
    }}

    .metric-sub {{
        color: {muted};
        font-size: 0.96rem;
        margin-bottom: 0.8rem;
    }}

    .greeting-screen {{
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: {bg};
    }}

    .greeting-text {{
        font-size: 112px;
        font-weight: 800;
        line-height: 1;
        color: {title};
        text-align: center;
        animation: fadeInOut 4s ease-in-out forwards;
        padding: 0 30px;
        letter-spacing: -0.03em;
    }}

    @keyframes fadeInOut {{
        0% {{ opacity: 0; transform: translateY(8px); }}
        15% {{ opacity: 1; transform: translateY(0); }}
        75% {{ opacity: 1; transform: translateY(0); }}
        100% {{ opacity: 0; transform: translateY(-8px); }}
    }}

    div[data-testid="stProgressBar"] > div > div {{
        border-radius: 999px;
    }}
    </style>
    """

def render_intro() -> None:
    if not st.session_state.intro_shown:
        st.markdown(
            f"""
            <div class="greeting-screen">
                <div class="greeting-text">{get_greeting(get_now())}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(GREETING_SECONDS)
        st.session_state.intro_shown = True
        st.rerun()


def render_theme_toggle() -> None:
    top_left, top_right = st.columns([8, 1.2])
    with top_right:
        dark = st.toggle(
            "Dark mode",
            value=st.session_state.theme_mode == "Dark",
            key="dark_mode_toggle",
        )
        st.session_state.theme_mode = "Dark" if dark else "Light"


def render_header() -> None:
    now = get_now()
    st.markdown('<h1 class="app-title">Ikos B2B</h1>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Daily Task Tracker</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="app-datetime">{now.strftime("%A, %d %B %Y • %H:%M • Europe/Athens")}</div>',
        unsafe_allow_html=True,
    )

    parts = []
    for label, query in OFFICE_LOCATIONS.items():
        info = get_weather_for_city(query)
        parts.append(
            f"""
            <span class="weather-pill">
                <span class="weather-icon-wrap">{info["icon"]}</span>
                <span class="weather-text">{label} • {info["weather"]} • {info["temp"]}</span>
            </span>
            """
        )

    st.markdown(
        f'<div class="weather-pill-wrap">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def authenticate(username: str, password: str) -> bool:
    users = st.secrets.get("users", {})
    stored = users.get(username)
    return bool(stored and stored == password)


def get_display_name(username: str) -> str:
    return st.secrets.get("display_names", {}).get(username, username)


def render_login() -> None:
    with st.container(border=True):
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if authenticate(username.strip(), password):
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.session_state.display_name = get_display_name(username.strip())
                st.rerun()
            else:
                st.error("Invalid username or password.")


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### Settings")
        st.write(f"Logged in as: **{st.session_state.display_name}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.display_name = None
            st.session_state.intro_shown = False
            st.rerun()


def render_tasks() -> tuple[int, int]:
    today = get_today_str()
    task_names = get_today_tasks()
    statuses = get_task_statuses(today, task_names)

    with st.container(border=True):
        st.markdown(f'<div class="hello-text">Hello, {st.session_state.display_name}</div>', unsafe_allow_html=True)
        st.markdown('<div class="hello-sub">Today’s team tasks</div>', unsafe_allow_html=True)

        for row in statuses:
            task_name = row["task_name"]
            completed = bool(row["completed"])
            key = f"team_task_{today}_{task_name}"

            new_value = st.checkbox(task_name, value=completed, key=key)

            if new_value != completed:
                set_task_completion(
                    day=today,
                    task_name=task_name,
                    completed=new_value,
                    updated_by=st.session_state.display_name,
                )
                st.rerun()

            if new_value and row["updated_by"]:
                updated_at = row["updated_at"] or ""
                try:
                    if len(updated_at) >= 16:
                        updated_at = updated_at[11:16]
                except Exception:
                    pass
                st.markdown(
                    f'<div class="task-meta">Completed by {row["updated_by"]} • {updated_at}</div>',
                    unsafe_allow_html=True,
                )

    return get_team_progress(today, task_names)[:2]


def render_progress() -> None:
    today = get_today_str()
    task_names = get_today_tasks()
    completed, total, pct = get_team_progress(today, task_names)

    with st.container(border=True):
        st.subheader("Team Progress")
        st.markdown(f'<div class="metric-big">{pct}%</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-sub">{completed}/{total} tasks completed today</div>',
            unsafe_allow_html=True,
        )
        st.progress(pct / 100 if total else 0)

def main() -> None:
    init_session()
    init_db()

    dark_mode = st.session_state.theme_mode == "Dark"
    st.markdown(get_theme_css(dark_mode), unsafe_allow_html=True)

    render_intro()

    render_theme_toggle()

    dark_mode = st.session_state.theme_mode == "Dark"
    st.markdown(get_theme_css(dark_mode), unsafe_allow_html=True)

    render_header()

    if not st.session_state.logged_in:
        render_login()
        return

    render_sidebar()

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        render_tasks()
    with right:
        render_progress()


if __name__ == "__main__":
    main()