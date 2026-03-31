import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import requests

from auth import verify_password
from db import (
    init_db,
    get_tasks,
    set_task_completion,
    get_user_by_username,
)

from utils import get_greeting


TIMEZONE = "Europe/Athens"
GREETING_SECONDS = 3


# -----------------------------
# WEATHER CONFIG
# -----------------------------
API_KEY = st.secrets.get("API_KEY", "")

OFFICE_LOCATIONS = {
    "Thessaloniki": {"lat": 40.5668, "lon": 22.9866},
}


@st.cache_data(ttl=600)
def fetch_weather(location):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "appid": API_KEY,
        "units": "metric",
        "lat": location["lat"],
        "lon": location["lon"],
    }
    return requests.get(url, params=params).json()


def render_weather():
    if not API_KEY:
        return

    for city, loc in OFFICE_LOCATIONS.items():
        data = fetch_weather(loc)
        temp = round(data["main"]["temp"])
        weather = data["weather"][0]["main"]

        st.markdown(
            f"""
            <div style="text-align:center; font-size:1rem; margin-top:5px;">
                {city} • {weather} • {temp}°C
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# SESSION
# -----------------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.intro_shown = False
        st.session_state.dark = False


# -----------------------------
# GREETING SCREEN
# -----------------------------
def show_intro():
    if not st.session_state.intro_shown:
        now = datetime.now(ZoneInfo(TIMEZONE))
        st.markdown(
            f"""
            <div style="height:100vh; display:flex; align-items:center; justify-content:center;">
                <div style="font-size:100px; font-weight:800;">
                    {get_greeting(now)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(GREETING_SECONDS)
        st.session_state.intro_shown = True
        st.rerun()


# -----------------------------
# LOGIN
# -----------------------------
def render_login():
    st.markdown("### Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        stored = st.secrets["users"].get(username)

        if stored and password == stored:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Invalid credentials")


# -----------------------------
# TASK LOGIC
# -----------------------------
def get_today_tasks():
    weekday = datetime.now(ZoneInfo(TIMEZONE)).weekday()

    if weekday in [0, 3]:  # Monday, Thursday
        return [
            "Occupancy Charts 2026",
            "Occupancy Charts 2027",
            "Out of Order Report",
        ]
    else:
        return [
            "Occupancy Charts 2026",
            "Out of Order Report",
        ]


def render_tasks():
    display_name = st.secrets["display_names"][st.session_state.user]
    st.markdown(f"### Hello, {display_name}")

    tasks = get_today_tasks()
    completed = 0

    for task in tasks:
        if st.checkbox(task):
            completed += 1

    return completed, len(tasks)


# -----------------------------
# TEAM PROGRESS
# -----------------------------
def render_team_progress(completed, total):
    pct = int((completed / total) * 100) if total else 0

    st.markdown("### Team Progress")
    st.metric("Completion", f"{pct}%")

    if pct == 0:
        msg = "Let's get started"
    elif pct < 50:
        msg = "Good progress"
    elif pct < 100:
        msg = "Keep going, almost there"
    else:
        msg = "Completed — great job team"

    st.info(msg)


# -----------------------------
# MAIN
# -----------------------------
def main():
    st.set_page_config(layout="wide")
    init_db()
    init_session()

    show_intro()

    # HEADER
    now = datetime.now(ZoneInfo(TIMEZONE))
    st.markdown(
        f"""
        <div style="text-align:center;">
            <h1>Ikos B2B</h1>
            <div>Daily Task Tracker</div>
            <div style="margin-top:5px;">
                {now.strftime("%A, %d %B %Y • %H:%M")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_weather()

    if not st.session_state.logged_in:
        render_login()
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        completed, total = render_tasks()

    with col2:
        render_team_progress(completed, total)


if __name__ == "__main__":
    main()