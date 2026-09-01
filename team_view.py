"""
team_view.py — TAMU Rowing, rower-facing view
Read-only: no scores, no editing. Connects to the SAME database as the coach app.

Run with:  streamlit run team_view.py
"""

import sqlite3
import calendar as cal_module
import datetime as dt_module
import pandas as pd
import streamlit as st

DB_PATH = "rowing_season_2026.db"

st.set_page_config(page_title="TAMU Rowing — Team", layout="wide")

# ---------------------------------------------------------------
# Simple password gate — same pattern as the coach app. Keeps real names,
# contact info, and lineups from being publicly viewable by anyone who
# has (or finds) this URL, since this repo is public.
# ---------------------------------------------------------------
def check_password():
    def password_entered():
        try:
            correct = st.session_state.get("password_input") == st.secrets.get("TEAM_PASSWORD")
        except Exception:
            correct = False
        if correct:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("""
    <style>
        [data-testid="stTextInput"] input {
            border: 2px solid #500000 !important;
            border-radius: 8px !important;
            text-align: center;
            padding: 10px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    lc1, lc2, lc3 = st.columns([1, 1.1, 1])
    with lc2:
        st.markdown(
            "<h2 style='text-align:center; color:#500000; font-family:Georgia,serif; margin-top:60px; margin-bottom:2px;'>🚣 TAMU Rowing — Team</h2>"
            "<p style='text-align:center; color:#8A8177; font-size:13px; margin-bottom:18px;'>Enter the password to continue</p>",
            unsafe_allow_html=True,
        )
        st.text_input("Password", type="password", on_change=password_entered, key="password_input", label_visibility="collapsed", placeholder="Password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Incorrect password.")
    return False


try:
    has_team_password = "TEAM_PASSWORD" in st.secrets
except Exception:
    has_team_password = False

if has_team_password and not check_password():
    st.stop()

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


def get_conn():
    # Not cached — Turso's remote connections can expire server-side ("stream
    # not found"), and reusing a stale one crashes the app. Opening fresh each
    # call is cheap; the @st.cache_data-decorated loaders below do the real
    # work of avoiding repeat round-trips.
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
    return run_query("SELECT rower_name, gender, experience_level, years_rowing, phone, email FROM Rowers ORDER BY rower_name")


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
        SELECT l.boat_name, l.seat_number, l.side, r.rower_name, reg.name AS regatta, eq.name AS boat_used
        FROM Lineups l
        JOIN Rowers r ON r.rower_id = l.rower_id
        LEFT JOIN Regattas reg ON reg.regatta_id = l.regatta_id
        LEFT JOIN Equipment eq ON eq.equipment_id = l.equipment_id
        WHERE l.is_visible_to_team = 1
        ORDER BY reg.name, l.boat_name, l.seat_number
    """)


@st.cache_data(ttl=120)
def load_announcements():
    today_str = str(pd.Timestamp.now().date())
    return run_query(
        "SELECT * FROM Announcements WHERE expires_date IS NULL OR expires_date >= ? ORDER BY posted_date DESC, announcement_id DESC",
        (today_str,),
    )


@st.cache_data(ttl=120)
def load_events():
    return run_query("SELECT * FROM PracticeEvents ORDER BY event_date ASC")


@st.cache_data(ttl=120)
def load_signup_events_cal():
    return run_query("SELECT event_date, title FROM SignUpEvents")


@st.cache_data(ttl=120)
def load_regattas_cal():
    return run_query("SELECT name, event_date FROM Regattas WHERE event_date IS NOT NULL")


@st.cache_data(ttl=120)
def load_gendered_assignments_by_date():
    return run_query("""
        SELECT da.event_date, r.gender, da.location, COUNT(*) AS n
        FROM DailyAssignments da JOIN Rowers r ON r.rower_id = da.rower_id
        GROUP BY da.event_date, r.gender, da.location
    """)


@st.cache_data(ttl=120)
def load_daily_assignments_view(date_str):
    return run_query("""
        SELECT r.rower_name, r.gender, da.location, da.is_coxswain
        FROM DailyAssignments da JOIN Rowers r ON r.rower_id = da.rower_id
        WHERE da.event_date = ?
    """, (date_str,))


@st.cache_data(ttl=120)
def load_daily_coaches_view(date_str):
    return run_query("SELECT location, coach_name FROM DailyCoaches WHERE event_date = ?", (date_str,))


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

tab_lineups, tab_roster, tab_announce, tab_calendar, tab_signups, tab_availability, tab_weekly = st.tabs(
    ["Lineups", "Roster", "Announcements", "Calendar", "Sign-Ups", "Availability", "Weekly Schedule"]
)

with tab_lineups:
    st.title("Lineups")

    st.subheader("This Week's Practice Lineups")
    weekly_lineups_df = run_query("""
        SELECT boat_name, race_date, seat_number, side, r.rower_name, eq.name AS boat_used
        FROM Lineups l JOIN Rowers r ON r.rower_id = l.rower_id
        LEFT JOIN Equipment eq ON eq.equipment_id = l.equipment_id
        WHERE l.regatta_id IS NULL AND l.race_date IS NOT NULL AND l.is_visible_to_team = 1
        ORDER BY race_date, boat_name, seat_number
    """)
    if weekly_lineups_df.empty:
        st.caption("No practice lineups posted yet.")
    else:
        for race_date, day_group in weekly_lineups_df.groupby("race_date", sort=True):
            day_label = pd.Timestamp(race_date).strftime("%A, %B %-d") if hasattr(pd.Timestamp(race_date), "strftime") else race_date
            with st.expander(f"{day_label} ({day_group['boat_name'].nunique()} boat(s))"):
                for boat_name, group in day_group.groupby("boat_name", sort=True):
                    st.markdown(f"**{boat_name}**")
                    boat_used = group["boat_used"].iloc[0]
                    if pd.notna(boat_used) and boat_used:
                        st.caption(f"🚣 Boat: {boat_used}")
                    display = group.sort_values("seat_number")[["seat_number", "side", "rower_name"]]
                    display.columns = ["Seat", "Side", "Rower"]
                    st.dataframe(display, width='stretch', hide_index=True)

    st.divider()
    st.subheader("Regatta Lineups")
    st.caption("Click a regatta to see its lineups.")

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
            with st.expander(f"{reg['name']} ({this_regatta['boat_name'].nunique()} boat(s))"):
                for boat_name, group in this_regatta.groupby("boat_name", sort=True):
                    st.markdown(f"**{boat_name}**")
                    boat_used = group["boat_used"].iloc[0] if "boat_used" in group.columns else None
                    if pd.notna(boat_used) and boat_used:
                        st.caption(f"🚣 Boat: {boat_used}")
                    display = group.sort_values("seat_number")[["seat_number", "side", "rower_name"]]
                    display.columns = ["Seat", "Side", "Rower"]
                    st.dataframe(display, width='stretch', hide_index=True)
        if not any_shown:
            st.info("No regatta lineups posted yet for this season.")

with tab_roster:
    st.title("Roster")
    roster_df = load_roster()
    if roster_df.empty:
        st.info("No rowers on the roster yet.")
    else:
        def contact_line(r):
            parts = []
            if pd.notna(r.get("phone")) and r.get("phone"):
                parts.append(f"📞 {r['phone']}")
            if pd.notna(r.get("email")) and r.get("email"):
                parts.append(f"✉️ {r['email']}")
            return " · ".join(parts)

        col_w, col_m = st.columns(2)
        women = roster_df[roster_df["gender"] == "women"]
        men = roster_df[roster_df["gender"] == "men"]
        with col_w:
            st.subheader(f"Women ({len(women)})")
            for _, r in women.iterrows():
                st.markdown(f"**{r['rower_name']}** — {r['experience_level']}, {r['years_rowing']} yr(s)")
                contact = contact_line(r)
                if contact:
                    st.caption(contact)
        with col_m:
            st.subheader(f"Men ({len(men)})")
            for _, r in men.iterrows():
                st.markdown(f"**{r['rower_name']}** — {r['experience_level']}, {r['years_rowing']} yr(s)")
                contact = contact_line(r)
                if contact:
                    st.caption(contact)

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
    signup_events_df_cal = load_signup_events_cal()
    regattas_cal_df = load_regattas_cal()

    type_colors = {"water": "#2E7D9A", "erg": "#B8925A", "off": "#8A8177"}
    gender_icon = {"men": "♂", "women": "♀"}
    events_by_date = {}

    gendered_df = load_gendered_assignments_by_date()
    dates_with_assignments = set(gendered_df["event_date"].tolist())

    for _, r in practice_events_df.iterrows():
        if r["event_date"] in dates_with_assignments:
            continue
        label = {"water": "🚣 Water", "erg": "🏋️ Erg", "off": "❌ Off"}.get(r["event_type"], r["event_type"])
        events_by_date.setdefault(r["event_date"], []).append((label, type_colors.get(r["event_type"], "#500000")))
    for _, row in gendered_df.iterrows():
        loc_label = {"water": "Water", "land": "Land"}.get(row["location"], row["location"])
        label = f"{gender_icon.get(row['gender'], row['gender'])} {loc_label}"
        color = type_colors.get(row["location"] if row["location"] != "land" else "erg", "#500000")
        events_by_date.setdefault(row["event_date"], []).append((label, color))
    for _, r in signup_events_df_cal.iterrows():
        events_by_date.setdefault(r["event_date"], []).append((f"📝 {r['title']}", "#7A5C8E"))
    for _, r in regattas_cal_df.iterrows():
        events_by_date.setdefault(r["event_date"], []).append((f"🏆 {r['name']}", "#500000"))

    render_month_calendar(events_by_date, st.session_state["cal_year"], st.session_state["cal_month"], "cal")
    st.caption("🚣 Water · 🏋️ Erg/Land · ❌ Off · 📝 Sign-up · 🏆 Regatta · ♂ Men · ♀ Women")

with tab_signups:
    st.title("Sign-Ups")
    st.caption("Pick your name once, then sign up for a specific time slot below.")

    roster_names_df = run_query("SELECT rower_id, rower_name FROM Rowers ORDER BY rower_name")
    if roster_names_df.empty:
        st.info("No rowers on the roster yet.")
    else:
        my_name = st.selectbox("I am:", roster_names_df["rower_name"].tolist(), key="signups_my_name")
        my_id = int(roster_names_df[roster_names_df["rower_name"] == my_name]["rower_id"].iloc[0])

        events_df = run_query("SELECT * FROM SignUpEvents ORDER BY event_date ASC")
        today_str = str(pd.Timestamp.now().date())

        if events_df.empty:
            st.info("No sign-up events posted yet.")
        else:
            upcoming = events_df[events_df["event_date"] >= today_str]

            def render_event(ev):
                eid = int(ev["event_id"])
                deadline_passed = pd.notna(ev.get("signup_deadline")) and ev["signup_deadline"] < today_str
                deadline_text = f" · sign-ups close {ev['signup_deadline']}" if pd.notna(ev.get("signup_deadline")) else ""

                with st.container(border=True):
                    st.markdown(f"**{ev['title']}** — {ev['event_date']}{deadline_text}")
                    if pd.notna(ev.get("notes")) and ev.get("notes"):
                        st.caption(ev["notes"])
                    if deadline_passed:
                        st.caption("⚠ Sign-ups are closed for this event.")

                    slots_df = run_query("SELECT * FROM SignUpSlots WHERE event_id = ? ORDER BY start_time", (eid,))
                    if slots_df.empty:
                        st.caption("No time slots posted for this yet.")
                        return

                    for _, slot in slots_df.iterrows():
                        sid = int(slot["slot_id"])
                        responses_df = run_query(
                            "SELECT r.rower_id, r.rower_name FROM SignUpResponses sr JOIN Rowers r ON r.rower_id = sr.rower_id WHERE sr.slot_id = ?",
                            (sid,),
                        )
                        names = responses_df["rower_name"].tolist()
                        already_signed_up = my_id in responses_df["rower_id"].tolist()
                        max_spots = int(slot["max_spots"]) if pd.notna(slot.get("max_spots")) else None
                        is_full = max_spots is not None and len(names) >= max_spots
                        spots_text = f"{len(names)}/{max_spots}" if max_spots is not None else f"{len(names)}"

                        sc1, sc2 = st.columns([3, 1])
                        sc1.markdown(f"**{slot['start_time']}–{slot['end_time']}** · {spots_text} spots — {', '.join(names) if names else '*nobody yet*'}")
                        if already_signed_up:
                            if sc2.button("Remove me", key=f"remove_{sid}"):
                                run_write("DELETE FROM SignUpResponses WHERE slot_id = ? AND rower_id = ?", (sid, my_id))
                                st.rerun()
                        elif deadline_passed:
                            sc2.caption("Closed")
                        elif is_full:
                            sc2.caption("Full")
                        else:
                            if sc2.button("Sign up", key=f"signup_{sid}"):
                                run_write("INSERT OR IGNORE INTO SignUpResponses (event_id, rower_id, slot_id) VALUES (?, ?, ?)", (eid, my_id, sid))
                                st.rerun()

            if upcoming.empty:
                st.info("No upcoming sign-ups right now.")
            else:
                for _, ev in upcoming.iterrows():
                    render_event(ev)

with tab_availability:
    st.title("Availability")
    st.caption("Practice is assumed every day except Sunday, unless coaches say otherwise. Click a day to mark yourself out, add a reason, then save. Days too close are locked so coaches aren't surprised last-minute.")

    roster_names_df2 = run_query("SELECT rower_id, rower_name FROM Rowers ORDER BY rower_name")
    if roster_names_df2.empty:
        st.info("No rowers on the roster yet.")
    else:
        my_name2 = st.selectbox("I am:", roster_names_df2["rower_name"].tolist(), key="avail_my_name")
        my_id2 = int(roster_names_df2[roster_names_df2["rower_name"] == my_name2]["rower_id"].iloc[0])

        settings_df2 = run_query("SELECT * FROM AttendanceSettings LIMIT 1")
        deadline_days = int(settings_df2["days_before_deadline"].iloc[0]) if not settings_df2.empty else 1

        practice_events_df = run_query("SELECT event_date, event_type FROM PracticeEvents")
        practice_by_date = dict(zip(practice_events_df["event_date"], practice_events_df["event_type"]))
        regatta_dates_df = run_query("SELECT event_date, name FROM Regattas WHERE event_date IS NOT NULL")
        regatta_by_date = dict(zip(regatta_dates_df["event_date"], regatta_dates_df["name"]))

        my_absences_df = run_query("SELECT event_date, reason FROM DayAbsences WHERE rower_id = ?", (my_id2,))
        my_absence_dates = dict(zip(my_absences_df["event_date"], my_absences_df["reason"]))

        def day_status(date_str, date_obj):
            """Returns (is_relevant, label) — the default-on-every-day-but-Sunday logic."""
            if date_str in regatta_by_date:
                return True, f"🏆 {regatta_by_date[date_str]}"
            explicit = practice_by_date.get(date_str)
            if explicit == "off":
                return False, "Off"
            if explicit is not None:
                return True, {"water": "🚣 Water", "erg": "🏋️ Erg"}.get(explicit, explicit)
            if date_obj.weekday() == 6:  # Sunday
                return False, "Off (Sunday)"
            return True, "Practice"

        if "avail_cal_year" not in st.session_state:
            st.session_state["avail_cal_year"] = pd.Timestamp.now().year
            st.session_state["avail_cal_month"] = pd.Timestamp.now().month

        nav1, nav2, nav3, nav4 = st.columns([1, 1, 3, 1])
        if nav1.button("◀ Prev", key="avail_cal_prev"):
            m, y = st.session_state["avail_cal_month"], st.session_state["avail_cal_year"]
            st.session_state["avail_cal_month"], st.session_state["avail_cal_year"] = (m - 1, y) if m > 1 else (12, y - 1)
            st.rerun()
        if nav4.button("Next ▶", key="avail_cal_next"):
            m, y = st.session_state["avail_cal_month"], st.session_state["avail_cal_year"]
            st.session_state["avail_cal_month"], st.session_state["avail_cal_year"] = (m + 1, y) if m < 12 else (1, y + 1)
            st.rerun()
        cal_year, cal_month = st.session_state["avail_cal_year"], st.session_state["avail_cal_month"]
        nav3.markdown(f"<h3 style='text-align:center; margin:0;'>{cal_module.month_name[cal_month]} {cal_year}</h3>", unsafe_allow_html=True)

        weeks = cal_module.Calendar(firstweekday=6).monthdayscalendar(cal_year, cal_month)
        today = pd.Timestamp.now().date()
        checked_dates = {}

        headers = st.columns(7)
        for h, name in zip(headers, ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            h.markdown(f"<div style='text-align:center; font-size:11px; color:#8A8177; text-transform:uppercase;'>{name}</div>", unsafe_allow_html=True)

        for week in weeks:
            cols = st.columns(7)
            for col, day in zip(cols, week):
                if day == 0:
                    continue
                date_obj = dt_module.date(cal_year, cal_month, day)
                date_str = str(date_obj)
                is_relevant, label = day_status(date_str, date_obj)
                already_marked = date_str in my_absence_dates
                is_past = date_obj < today
                days_away = (date_obj - today).days
                locked = (not is_past) and days_away < deadline_days

                with col:
                    if is_past:
                        st.caption(f"{day}")
                    elif not is_relevant:
                        st.caption(f"{day} · {label}")
                    elif locked:
                        icon = "🔒✅" if already_marked else "🔒"
                        st.caption(f"{day} {icon}")
                    else:
                        checked = st.checkbox(f"{day}", value=already_marked, key=f"absent_{my_id2}_{date_str}")
                        if checked:
                            checked_dates[date_str] = label

        st.caption("🔒 = locked (too close to the deadline to change) · ✅ = you're marked absent")

        if checked_dates:
            st.divider()
            st.subheader("Add a reason for each day you're missing")
            reasons = {}
            for date_str, label in sorted(checked_dates.items()):
                reasons[date_str] = st.text_input(
                    f"{date_str} · {label}", value=my_absence_dates.get(date_str, ""),
                    key=f"reason_{my_id2}_{date_str}", placeholder="Reason (optional)",
                )

            if st.button("💾 Save Absences"):
                # Reconcile every relevant day currently in view: checked+reason -> upsert, unchecked -> delete if it existed
                for week in weeks:
                    for day in week:
                        if day == 0:
                            continue
                        date_obj = dt_module.date(cal_year, cal_month, day)
                        date_str = str(date_obj)
                        if date_obj < today:
                            continue
                        days_away = (date_obj - today).days
                        if days_away < deadline_days:
                            continue
                        if date_str in checked_dates:
                            run_write(
                                "INSERT INTO DayAbsences (rower_id, event_date, reason) VALUES (?, ?, ?) "
                                "ON CONFLICT(rower_id, event_date) DO UPDATE SET reason = excluded.reason",
                                (my_id2, date_str, reasons.get(date_str) or None),
                            )
                        elif date_str in my_absence_dates:
                            run_write("DELETE FROM DayAbsences WHERE rower_id = ? AND event_date = ?", (my_id2, date_str))
                st.toast("Saved.", icon="💾")
                st.rerun()


with tab_weekly:
    st.title("Weekly Schedule")
    st.caption("Where to show up each day — water or land — and who's coaching. Updated by coaches every weekend.")

    week_start2 = st.date_input("Week of", value=pd.Timestamp.now().date(), key="weekly_view_start")
    week_start2_dt = pd.Timestamp(week_start2)
    monday2 = week_start2_dt - pd.Timedelta(days=week_start2_dt.weekday())
    weekdays2 = [monday2 + pd.Timedelta(days=i) for i in range(6)]  # Mon-Sat

    st.info("Every day you're either not scheduled, on land (ergs), or on the water. If you're on the water, boat lineups get sorted out once everyone's at the lake.")

    def render_location_group(container, group, label, coach_name):
        container.markdown(f"**{label}** — Coach: {coach_name or '—'}")
        if group.empty:
            container.caption("Nobody assigned.")
            return
        men = group[group["gender"] == "men"].sort_values("rower_name")
        women = group[group["gender"] == "women"].sort_values("rower_name")
        mcol, wcol = container.columns(2)
        mcol.caption("Men")
        for _, r in men.iterrows():
            cox_tag = " (cox)" if r["is_coxswain"] else ""
            mcol.markdown(f"- {r['rower_name']}{cox_tag}")
        wcol.caption("Women")
        for _, r in women.iterrows():
            cox_tag = " (cox)" if r["is_coxswain"] else ""
            wcol.markdown(f"- {r['rower_name']}{cox_tag}")

    for day in weekdays2:
        date_str = str(day.date())
        assignments_df = load_daily_assignments_view(date_str)
        coaches_df = load_daily_coaches_view(date_str)
        coach_map = dict(zip(coaches_df["location"], coaches_df["coach_name"]))

        with st.container(border=True):
            st.markdown(f"### {day.strftime('%A')} — {date_str}")
            if assignments_df.empty:
                st.caption("Not posted yet.")
                continue

            wc, lc = st.columns(2)
            render_location_group(wc, assignments_df[assignments_df["location"] == "water"], "🚣 Water", coach_map.get("water"))
            render_location_group(lc, assignments_df[assignments_df["location"] == "land"], "🏋️ Land", coach_map.get("land"))

