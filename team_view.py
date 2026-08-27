"""
team_view.py — TAMU Rowing, rower-facing view
Read-only: no scores, no editing. Connects to the SAME database as the coach app.

Run with:  streamlit run team_view.py
"""

import sqlite3
import calendar as cal_module
import pandas as pd
import streamlit as st

DB_PATH = "rowing_season_2026.db"

st.set_page_config(page_title="TAMU Rowing — Team", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #FAF8F5; }
    h1 { color: #500000 !important; font-family: Georgia, serif; }
    h2, h3 { color: #1F1B18 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #E4DFD6; margin-bottom: 12px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 18px; font-size: 18px !important; font-weight: 700 !important; color: #8A8177 !important; }
    .stTabs [aria-selected="true"] { color: #500000 !important; border-bottom: 3px solid #500000 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#500000; padding:16px 20px; border-radius:6px; margin-bottom:16px;">
  <span style="color:#fff; font-family:Georgia,serif; font-size:22px; font-weight:700;">
    TAMU Rowing — Team Site
  </span>
</div>
""", unsafe_allow_html=True)


@st.cache_resource
def get_conn():
    try:
        has_turso_secrets = "TURSO_DATABASE_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets
    except Exception:
        has_turso_secrets = False
    if has_turso_secrets:
        import libsql
        return libsql.connect(database=st.secrets["TURSO_DATABASE_URL"], auth_token=st.secrets["TURSO_AUTH_TOKEN"])
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run_query(sql, params=None):
    return pd.read_sql_query(sql, get_conn(), params=params)


def run_write(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    st.cache_data.clear()
    return cur.lastrowid


@st.cache_data(ttl=120)
def load_roster():
    # Deliberately NOT selecting any of the coach-score columns or weight —
    # this view is meant to be safe to share with the whole team.
    return run_query("SELECT rower_name, gender, experience_level, years_rowing FROM Rowers ORDER BY rower_name")


@st.cache_data(ttl=120)
def load_regattas():
    df = run_query("SELECT * FROM Regattas ORDER BY regatta_id")
    if not df.empty:
        df["_is_practice"] = df["name"] == "Practice"
        df["_sort_date"] = pd.to_datetime(df["event_date"], errors="coerce")
        df = df.sort_values(by=["_is_practice", "_sort_date"], ascending=[False, True], na_position="last") \
               .drop(columns=["_is_practice", "_sort_date"])
    return df


@st.cache_data(ttl=120)
def load_lineups():
    return run_query("""
        SELECT l.boat_name, l.seat_number, l.side, r.rower_name, reg.name AS regatta
        FROM Lineups l
        JOIN Rowers r ON r.rower_id = l.rower_id
        LEFT JOIN Regattas reg ON reg.regatta_id = l.regatta_id
        ORDER BY reg.name, l.boat_name, l.seat_number
    """)


@st.cache_data(ttl=120)
def load_announcements():
    return run_query("SELECT * FROM Announcements ORDER BY posted_date DESC, announcement_id DESC")


@st.cache_data(ttl=120)
def load_events():
    return run_query("SELECT * FROM PracticeEvents ORDER BY event_date ASC")


def render_month_calendar(events_by_date, year, month, key_prefix):
    nav1, nav2, nav3, nav4 = st.columns([1, 1, 3, 1])
    if nav1.button("◀ Prev", key=f"{key_prefix}_prev"):
        new_month, new_year = (month - 1, year) if month > 1 else (12, year - 1)
        st.session_state[f"{key_prefix}_year"] = new_year
        st.session_state[f"{key_prefix}_month"] = new_month
        st.rerun()
    if nav4.button("Next ▶", key=f"{key_prefix}_next"):
        new_month, new_year = (month + 1, year) if month < 12 else (1, year + 1)
        st.session_state[f"{key_prefix}_year"] = new_year
        st.session_state[f"{key_prefix}_month"] = new_month
        st.rerun()
    nav3.markdown(f"<h3 style='text-align:center; margin:0;'>{cal_module.month_name[month]} {year}</h3>", unsafe_allow_html=True)

    weeks = cal_module.Calendar(firstweekday=6).monthdayscalendar(year, month)
    day_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    html = ['<div style="display:grid; grid-template-columns:repeat(7,1fr); gap:4px; font-family:sans-serif;">']
    for h in day_headers:
        html.append(f'<div style="text-align:center; font-size:11px; color:#8A8177; text-transform:uppercase; padding:4px;">{h}</div>')

    today_str = str(pd.Timestamp.now().date())
    for week in weeks:
        for day in week:
            if day == 0:
                html.append('<div style="min-height:80px; background:#F4F0E9; border-radius:4px;"></div>')
                continue
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            is_today = date_str == today_str
            border = "2px solid #500000" if is_today else "1px solid #E4DFD6"
            day_events = events_by_date.get(date_str, [])
            badges = "".join(
                f'<div style="background:{color}; color:#fff; font-size:10px; border-radius:3px; padding:1px 4px; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{label}</div>'
                for label, color in day_events[:4]
            )
            more = f'<div style="font-size:10px; color:#8A8177;">+{len(day_events) - 4} more</div>' if len(day_events) > 4 else ""
            html.append(
                f'<div style="min-height:80px; background:#fff; border:{border}; border-radius:4px; padding:4px;">'
                f'<div style="font-size:12px; font-weight:{"700" if is_today else "400"}; color:{"#500000" if is_today else "#1F1B18"};">{day}</div>'
                f'{badges}{more}</div>'
            )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


st.markdown('<div style="font-size:11px; color:#8A8177; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Season</div>', unsafe_allow_html=True)
season_choice = st.pills("Season", ["Spring (2k)", "Fall (5k)"], default="Spring (2k)", label_visibility="collapsed", key="team_season")
if season_choice is None:
    season_choice = "Spring (2k)"
season = "2k" if "2k" in season_choice else "5k"
st.caption("Affects which regattas show under Lineups.")

tab_lineups, tab_roster, tab_announce, tab_calendar, tab_signups = st.tabs(
    ["Lineups", "Roster", "Announcements", "Calendar", "Sign-Ups"]
)

with tab_lineups:
    st.title("Lineups")

    regattas_df = load_regattas()
    if not regattas_df.empty:
        regattas_df = regattas_df[(regattas_df["name"] == "Practice") | (regattas_df["season"] == season)]

    if regattas_df.empty:
        st.info("No regattas set up yet for this season — check back soon, or try the other season.")
    else:
        lineups_df = load_lineups()
        any_shown = False
        for _, reg in regattas_df.iterrows():
            this_regatta = lineups_df[lineups_df["regatta"] == reg["name"]]
            if this_regatta.empty:
                continue
            any_shown = True
            st.markdown(f"## {reg['name']}")
            for boat_name, group in this_regatta.groupby("boat_name", sort=True):
                st.markdown(f"**{boat_name}**")
                display = group.sort_values("seat_number")[["seat_number", "side", "rower_name"]]
                display.columns = ["Seat", "Side", "Rower"]
                st.dataframe(display, width='stretch', hide_index=True)
            st.divider()
        if not any_shown:
            st.info("No lineups posted yet for this season.")

with tab_roster:
    st.title("Roster")
    roster_df = load_roster()
    if roster_df.empty:
        st.info("No rowers on the roster yet.")
    else:
        col_w, col_m = st.columns(2)
        women = roster_df[roster_df["gender"] == "women"]
        men = roster_df[roster_df["gender"] == "men"]
        with col_w:
            st.subheader(f"Women ({len(women)})")
            for _, r in women.iterrows():
                st.markdown(f"**{r['rower_name']}** — {r['experience_level']}, {r['years_rowing']} yr(s)")
        with col_m:
            st.subheader(f"Men ({len(men)})")
            for _, r in men.iterrows():
                st.markdown(f"**{r['rower_name']}** — {r['experience_level']}, {r['years_rowing']} yr(s)")

with tab_announce:
    st.title("Announcements")
    announcements_df = load_announcements()
    if announcements_df.empty:
        st.info("No announcements yet.")
    else:
        for _, a in announcements_df.iterrows():
            with st.container(border=True):
                st.caption(a["posted_date"])
                st.markdown(a["message"])

with tab_calendar:
    st.title("Practice Calendar")

    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = pd.Timestamp.now().year
        st.session_state["cal_month"] = pd.Timestamp.now().month

    practice_events_df = load_events()
    signup_events_df_cal = run_query("SELECT event_date, title FROM SignUpEvents")
    regattas_cal_df = run_query("SELECT name, event_date FROM Regattas WHERE event_date IS NOT NULL")

    type_colors = {"water": "#2E7D9A", "erg": "#B8925A", "off": "#8A8177"}
    events_by_date = {}
    for _, r in practice_events_df.iterrows():
        label = {"water": "🚣 Water", "erg": "🏋️ Erg", "off": "❌ Off"}.get(r["event_type"], r["event_type"])
        events_by_date.setdefault(r["event_date"], []).append((label, type_colors.get(r["event_type"], "#500000")))
    for _, r in signup_events_df_cal.iterrows():
        events_by_date.setdefault(r["event_date"], []).append((f"📝 {r['title']}", "#7A5C8E"))
    for _, r in regattas_cal_df.iterrows():
        events_by_date.setdefault(r["event_date"], []).append((f"🏆 {r['name']}", "#500000"))

    render_month_calendar(events_by_date, st.session_state["cal_year"], st.session_state["cal_month"], "cal")
    st.caption("🚣 Water · 🏋️ Erg House · ❌ Off · 📝 Sign-up · 🏆 Regatta")

with tab_signups:
    st.title("Sign-Ups")
    st.caption("Pick your name once, then sign up for anything below.")

    roster_names_df = run_query("SELECT rower_id, rower_name FROM Rowers ORDER BY rower_name")
    if roster_names_df.empty:
        st.info("No rowers on the roster yet.")
    else:
        my_name = st.selectbox("I am:", roster_names_df["rower_name"].tolist())
        my_id = int(roster_names_df[roster_names_df["rower_name"] == my_name]["rower_id"].iloc[0])

        events_df = run_query("SELECT * FROM SignUpEvents ORDER BY event_date ASC")
        today_str = str(pd.Timestamp.now().date())

        if events_df.empty:
            st.info("No sign-up events posted yet.")
        else:
            upcoming = events_df[events_df["event_date"] >= today_str]
            past = events_df[events_df["event_date"] < today_str]

            def render_event(ev):
                responses_df = run_query(
                    "SELECT r.rower_id, r.rower_name FROM SignUpResponses sr JOIN Rowers r ON r.rower_id = sr.rower_id WHERE sr.event_id = ?",
                    (int(ev["event_id"]),),
                )
                names = responses_df["rower_name"].tolist()
                already_signed_up = my_id in responses_df["rower_id"].tolist()
                has_cap = pd.notna(ev.get("max_spots"))
                is_full = has_cap and len(names) >= int(ev["max_spots"])
                spots_text = f" — {len(names)}/{int(ev['max_spots'])} spots filled" if has_cap else f" — {len(names)} signed up"
                time_text = f" ({ev['time_label']})" if pd.notna(ev.get("time_label")) and ev.get("time_label") else ""

                with st.container(border=True):
                    st.markdown(f"**{ev['title']}** — {ev['event_date']}{time_text}{spots_text}")
                    if pd.notna(ev.get("notes")) and ev.get("notes"):
                        st.caption(ev["notes"])
                    st.write(", ".join(names) if names else "*Nobody signed up yet*")

                    if already_signed_up:
                        if st.button("Remove me", key=f"remove_{ev['event_id']}"):
                            run_write("DELETE FROM SignUpResponses WHERE event_id = ? AND rower_id = ?", (int(ev["event_id"]), my_id))
                            st.rerun()
                    elif is_full:
                        st.caption("Full.")
                    else:
                        if st.button("Sign me up", key=f"signup_{ev['event_id']}"):
                            run_write("INSERT OR IGNORE INTO SignUpResponses (event_id, rower_id) VALUES (?, ?)", (int(ev["event_id"]), my_id))
                            st.rerun()

            if upcoming.empty:
                st.info("No upcoming sign-ups right now.")
            else:
                for _, ev in upcoming.iterrows():
                    render_event(ev)

            if not past.empty:
                with st.expander(f"Past sign-ups ({len(past)})"):
                    for _, ev in past.iterrows():
                        render_event(ev)
