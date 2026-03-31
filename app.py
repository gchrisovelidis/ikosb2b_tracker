from datetime import datetime
from zoneinfo import ZoneInfo
import time

import pandas as pd
import streamlit as st

from auth import verify_password
from db import (
    get_leaderboard,
    get_tasks,
    get_team_average,
    get_user_by_username,
    get_user_progress,
    get_user_task_status,
    init_db,
    set_task_completion,
    update_task,
)
from utils import get_greeting, percentage, progress_message


st.set_page_config(
    page_title="Ikos B2B Daily Task Tracker",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TIMEZONE = "Europe/Athens"
GREETING_SECONDS = 3.2


def get_now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def get_today_str() -> str:
    return get_now().date().isoformat()


def init_session_state() -> None:
    defaults = {
        "logged_in": False,
        "user_id": None,
        "username": None,
        "is_admin": False,
        "theme_mode": "Light",
        "intro_shown": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_theme_css(dark_mode: bool) -> str:
    bg = "#0B1220" if dark_mode else "#F3F4F6"
    greeting_bg = "#0B1220" if dark_mode else "#F3F4F6"
    card_bg = "#111827" if dark_mode else "#FFFFFF"
    border = "#243041" if dark_mode else "#E5E7EB"
    title = "#F8FAFC" if dark_mode else "#0F172A"
    text = "#E5E7EB" if dark_mode else "#111827"
    muted = "#94A3B8" if dark_mode else "#6B7280"
    accent = "#2563EB"
    shadow = "0 10px 24px rgba(0, 0, 0, 0.22)" if dark_mode else "0 8px 24px rgba(15, 23, 42, 0.08)"

    return f"""
    <style>
    .stApp {{
        background: {bg};
    }}

    header, footer, #MainMenu {{
        visibility: hidden;
    }}

    .block-container {{
        max-width: 1300px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }}

    .title-wrap {{
        text-align: center;
        margin-bottom: 1.2rem;
    }}

    .main-title {{
        font-size: 2.7rem;
        font-weight: 800;
        color: {title};
        margin-bottom: 0.15rem;
        letter-spacing: -0.03em;
    }}

    .subtle-text {{
        color: {muted};
        font-size: 1.08rem;
    }}

    .datetime-wrap {{
        text-align: center;
        margin-top: 0.15rem;
    }}

    .datetime-text {{
        color: {muted};
        font-size: 1rem;
        font-weight: 500;
    }}

    .section-card {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 18px;
        padding: 1.15rem 1.15rem;
        box-shadow: {shadow};
        margin-bottom: 1rem;
    }}

    .section-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {title};
        margin-bottom: 0.8rem;
    }}

    .metric-big {{
        font-size: 2rem;
        font-weight: 800;
        color: {accent};
        line-height: 1.1;
    }}

    .metric-label {{
        color: {muted};
        font-size: 0.95rem;
        margin-top: 0.2rem;
    }}

    .helper-text {{
        color: {muted};
        font-size: 0.98rem;
        margin-top: 0.7rem;
    }}

    .login-wrap {{
        max-width: 480px;
        margin: 2rem auto 0 auto;
    }}

    .greeting-screen {{
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: {greeting_bg};
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
        0% {{
            opacity: 0;
            transform: translateY(8px);
        }}
        15% {{
            opacity: 1;
            transform: translateY(0);
        }}
        75% {{
            opacity: 1;
            transform: translateY(0);
        }}
        100% {{
            opacity: 0;
            transform: translateY(-8px);
        }}
    }}

    div[data-testid="stMetric"] {{
        background: {card_bg};
        border: 1px solid {border};
        padding: 1rem;
        border-radius: 16px;
    }}

    div[data-testid="stProgressBar"] > div > div {{
        border-radius: 999px;
    }}

    [data-testid="stSidebar"] {{
        background: {card_bg};
    }}

    [data-testid="stCheckbox"] label p,
    .stTextInput label,
    .stRadio label,
    .stCaption,
    .stMarkdown,
    .stDataFrame,
    .stAlert {{
        color: {text};
    }}
    </style>
    """


def render_section_start(title: str) -> None:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{title}</div>
        """,
        unsafe_allow_html=True,
    )


def render_section_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_header() -> None:
    now = get_now()
    pretty_date = now.strftime("%A, %d %B %Y")
    current_time = now.strftime("%H:%M")

    st.markdown(
        f"""
        <div class="title-wrap">
            <div class="main-title">Ikos B2B</div>
            <div class="subtle-text">Daily Task Tracker</div>
        </div>
        <div class="datetime-wrap">
            <div class="datetime-text">{pretty_date} • {current_time} • Europe/Athens</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login() -> None:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Login</div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        user = get_user_by_username(username.strip())

        if not user:
            st.error("Invalid username or password.")
        elif not verify_password(password, user["password_hash"]):
            st.error("Invalid username or password.")
        else:
            st.session_state.logged_in = True
            st.session_state.user_id = user["id"]
            st.session_state.username = user["username"]
            st.session_state.is_admin = bool(user["is_admin"])
            st.session_state.intro_shown = False
            st.rerun()

    st.info("The daily checklist resets automatically based on the current date.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### Settings")
        theme = st.radio(
            "Theme",
            options=["Light", "Dark"],
            index=0 if st.session_state.theme_mode == "Light" else 1,
        )
        st.session_state.theme_mode = theme

        st.markdown("---")
        st.write(f"Logged in as: **{st.session_state.username}**")
        if st.session_state.is_admin:
            st.caption("Admin account")

        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.is_admin = False
            st.session_state.intro_shown = False
            st.rerun()


def render_intro_greeting() -> None:
    if not st.session_state.intro_shown:
        now = get_now()
        st.markdown(
            f"""
            <div class="greeting-screen">
                <div class="greeting-text">{get_greeting(now)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(GREETING_SECONDS)
        st.session_state.intro_shown = True
        st.rerun()


def render_user_tasks() -> None:
    day = get_today_str()
    statuses = get_user_task_status(st.session_state.user_id, day)

    render_section_start("Today’s Tasks")

    for row in statuses:
        key = f"task_{row['task_id']}_{day}_{st.session_state.user_id}"
        current_value = bool(row["completed"])

        new_value = st.checkbox(
            row["task_name"],
            value=current_value,
            key=key,
        )

        if new_value != current_value:
            set_task_completion(
                user_id=st.session_state.user_id,
                task_id=row["task_id"],
                day=day,
                completed=new_value,
            )
            st.rerun()

    render_section_end()


def render_progress_card() -> None:
    day = get_today_str()
    completed, total = get_user_progress(st.session_state.user_id, day)
    pct = percentage(completed, total)
    message = progress_message(completed, total)

    render_section_start("Your Progress")
    st.markdown(f'<div class="metric-big">{pct}%</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-label">{completed}/{total} tasks completed</div>',
        unsafe_allow_html=True,
    )
    st.progress(pct / 100 if total else 0)
    st.markdown(f'<div class="helper-text">{message}</div>', unsafe_allow_html=True)
    render_section_end()


def render_team_card() -> None:
    day = get_today_str()
    avg = round(get_team_average(day))

    render_section_start("Team Average")
    st.markdown(f'<div class="metric-big">{avg}%</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-label">Average completion across all users today</div>',
        unsafe_allow_html=True,
    )
    st.progress(avg / 100)
    render_section_end()


def render_leaderboard() -> None:
    day = get_today_str()
    rows = get_leaderboard(day)

    data = []
    for idx, row in enumerate(rows, start=1):
        total = row["total_count"] or 0
        completed = row["completed_count"] or 0
        pct = percentage(completed, total)
        status = "✅ Completed" if pct == 100 else "In Progress"

        data.append(
            {
                "Rank": idx,
                "User": row["display_name"],
                "Completed": f"{completed}/{total}",
                "Progress %": pct,
                "Status": status,
            }
        )

    df = pd.DataFrame(data)

    render_section_start("Today’s Leaderboard")
    if df.empty:
        st.info("No leaderboard data yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
    render_section_end()


def render_admin_panel() -> None:
    tasks = get_tasks()

    render_section_start("Admin Panel")
    st.caption("You can rename the shared tasks below.")

    with st.form("admin_task_form"):
        new_names = []
        for task in tasks:
            new_name = st.text_input(
                f"Task {task['display_order']}",
                value=task["task_name"],
                key=f"admin_task_{task['id']}",
            )
            new_names.append((task["id"], new_name))

        submitted = st.form_submit_button("Save Task Names", use_container_width=True)

    if submitted:
        invalid = [name for _, name in new_names if not name.strip()]
        if invalid:
            st.error("Task names cannot be empty.")
        else:
            for task_id, new_name in new_names:
                update_task(task_id, new_name)
            st.success("Tasks updated successfully.")
            st.rerun()

    render_section_end()


def render_admin_credentials_reference() -> None:
    passwords = [
        {"Username": "gmichailidis", "Password": "gmich59853"},
        {"Username": "nmichailidou", "Password": "nmich47291"},
        {"Username": "oemichailidou", "Password": "oemic38476"},
        {"Username": "nspanopoulou", "Password": "nspan91824"},
        {"Username": "idimopoulos", "Password": "idimo56317"},
        {"Username": "ggatidis", "Password": "ggati24068"},
        {"Username": "edkorderi", "Password": "edkor85193"},
        {"Username": "rkougioumtzidou", "Password": "rkoug41756"},
        {"Username": "gchrisovelidis", "Password": "gchrisovelidis22193"},
    ]
    df = pd.DataFrame(passwords)

    render_section_start("Initial User Credentials")
    st.warning("For first setup only. Remove this section later.")
    st.dataframe(df, use_container_width=True, hide_index=True)
    render_section_end()

import os
if os.path.exists("tracker.db"):
    os.remove("tracker.db")
def main() -> None:
    init_db()
    init_session_state()

    dark_mode = st.session_state.theme_mode == "Dark"
    st.markdown(get_theme_css(dark_mode), unsafe_allow_html=True)

    if not st.session_state.logged_in:
        render_header()
        render_login()
        return

    render_sidebar()

    dark_mode = st.session_state.theme_mode == "Dark"
    st.markdown(get_theme_css(dark_mode), unsafe_allow_html=True)

    render_intro_greeting()
    render_header()

    left, right = st.columns([1.35, 1], gap="large")

    with left:
        render_user_tasks()
        render_leaderboard()

    with right:
        render_progress_card()
        render_team_card()
        if st.session_state.is_admin:
            render_admin_panel()
            render_admin_credentials_reference()


if __name__ == "__main__":
    main()