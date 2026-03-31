from datetime import datetime
from zoneinfo import ZoneInfo

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


TIMEZONE = ZoneInfo("Europe/Athens")


def get_now() -> datetime:
    return datetime.now(TIMEZONE)


def get_today_str() -> str:
    return get_now().date().isoformat()


def init_session_state() -> None:
    defaults = {
        "logged_in": False,
        "user_id": None,
        "username": None,
        "is_admin": False,
        "theme_mode": "Light",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_css(theme_mode: str) -> None:
    dark_mode = theme_mode == "Dark"

    bg = "#0B1220" if dark_mode else "#F5F7FB"
    card_bg = "#111827" if dark_mode else "#FFFFFF"
    border = "#243041" if dark_mode else "#E5E7EB"
    text = "#F8FAFC" if dark_mode else "#111827"
    muted = "#94A3B8" if dark_mode else "#6B7280"
    accent = "#2563EB"
    secondary = "#0F172A" if dark_mode else "#F8FAFC"
    success = "#16A34A"
    warning = "#D97706"

    st.markdown(
        f"""
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

        .main-title {{
            font-size: 2.2rem;
            font-weight: 800;
            color: {text};
            margin-bottom: 0.25rem;
        }}

        .subtle-text {{
            color: {muted};
            font-size: 0.98rem;
            margin-bottom: 1.25rem;
        }}

        .card {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 1.2rem 1.2rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
        }}

        .greeting {{
            font-size: 1.65rem;
            font-weight: 700;
            color: {text};
            margin-bottom: 0.35rem;
        }}

        .meta {{
            color: {muted};
            font-size: 0.95rem;
        }}

        .section-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {text};
            margin-bottom: 0.8rem;
        }}

        .pill {{
            display: inline-block;
            padding: 0.38rem 0.75rem;
            border-radius: 999px;
            background: {secondary};
            border: 1px solid {border};
            color: {text};
            font-size: 0.88rem;
            margin-right: 0.4rem;
            margin-bottom: 0.4rem;
        }}

        .metric-big {{
            font-size: 2rem;
            font-weight: 800;
            color: {accent};
            line-height: 1.1;
        }}

        .metric-label {{
            color: {muted};
            font-size: 0.92rem;
            margin-top: 0.2rem;
        }}

        .good {{
            color: {success};
            font-weight: 700;
        }}

        .warn {{
            color: {warning};
            font-weight: 700;
        }}

        .stDataFrame, .stTable {{
            border-radius: 14px;
            overflow: hidden;
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

        .login-wrap {{
            max-width: 480px;
            margin: 2rem auto 0 auto;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown('<div class="main-title">Ikos B2B</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtle-text">Daily Task Tracker</div>',
        unsafe_allow_html=True,
    )


def render_login() -> None:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Login</div>',
        unsafe_allow_html=True,
    )

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
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.info(
        "Version 1 note: the app resets completion automatically each day based on the current date."
    )

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
            st.rerun()


def render_greeting_card() -> None:
    now = get_now()
    greeting = get_greeting(now)
    pretty_date = now.strftime("%A, %d %B %Y")
    current_time = now.strftime("%H:%M")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="greeting">{greeting}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="meta">{pretty_date} • {current_time} • Europe/Athens</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_user_tasks() -> None:
    day = get_today_str()
    statuses = get_user_task_status(st.session_state.user_id, day)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Today’s Tasks</div>', unsafe_allow_html=True)

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

    st.markdown("</div>", unsafe_allow_html=True)


def render_progress_card() -> None:
    day = get_today_str()
    completed, total = get_user_progress(st.session_state.user_id, day)
    pct = percentage(completed, total)
    message = progress_message(completed, total)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Your Progress</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-big">{pct}%</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-label">{completed}/{total} tasks completed</div>',
        unsafe_allow_html=True,
    )
    st.progress(pct / 100 if total else 0)
    st.markdown(
        f'<div class="meta" style="margin-top: 0.6rem;">{message}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_team_card() -> None:
    day = get_today_str()
    avg = round(get_team_average(day))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Team Average</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-big">{avg}%</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-label">Average completion across all users today</div>',
        unsafe_allow_html=True,
    )
    st.progress(avg / 100)
    st.markdown("</div>", unsafe_allow_html=True)


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
                "User": row["username"],
                "Completed": f"{completed}/{total}",
                "Progress %": pct,
                "Status": status,
            }
        )

    df = pd.DataFrame(data)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Today’s Leaderboard</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No leaderboard data yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_admin_panel() -> None:
    tasks = get_tasks()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Admin Panel</div>', unsafe_allow_html=True)
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

    st.markdown("</div>", unsafe_allow_html=True)


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

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Initial User Credentials</div>',
        unsafe_allow_html=True,
    )
    st.warning(
        "For first setup only. After testing, I recommend removing this panel or moving credentials to a safer admin-only source."
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    init_db()
    init_session_state()
    inject_css(st.session_state.theme_mode)
    render_header()

    if not st.session_state.logged_in:
        render_login()
        return

    render_sidebar()
    render_greeting_card()

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