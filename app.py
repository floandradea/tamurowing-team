"""
app.py — TAMU Rowing Dashboard
Run with:  streamlit run app.py
"""

import sqlite3
import calendar as cal_module
import pandas as pd
import streamlit as st
import plotly.express as px

DB_PATH = "rowing_season_2026.db"  # only used if no Turso secrets are configured (local fallback)

MAROON = "#500000"
MAROON_LIGHT = "#8B3A3A"
GOLD = "#B8925A"

st.set_page_config(page_title="TAMU Rowing Dashboard", layout="wide")

# ---------------------------------------------------------------
# Simple password gate — keeps real athlete data from being publicly
# viewable by anyone who has (or finds) the app URL. Not bank-grade
# security, but blocks casual/accidental access.
# ---------------------------------------------------------------
def check_password():
    def password_entered():
        try:
            correct = st.session_state.get("password_input") == st.secrets.get("APP_PASSWORD")
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
            "<h2 style='text-align:center; color:#500000; font-family:Georgia,serif; margin-top:60px; margin-bottom:2px;'>🚣 TAMU Rowing</h2>"
            "<p style='text-align:center; color:#8A8177; font-size:13px; margin-bottom:18px;'>Enter the password to continue</p>",
            unsafe_allow_html=True,
        )
        st.text_input("Password", type="password", on_change=password_entered, key="password_input", label_visibility="collapsed", placeholder="Password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Incorrect password.")
    return False


try:
    has_app_password = "APP_PASSWORD" in st.secrets
except Exception:
    has_app_password = False

if has_app_password and not check_password():
    st.stop()

# ---------------------------------------------------------------
# Custom styling — matches the mockup's maroon/cream look
# ---------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #FAF8F5; }
    [data-testid="stSidebar"] { background-color: #500000; }
    [data-testid="stSidebar"] * { color: #F4E9DD !important; }
    [data-testid="stMetric"] {
        background: #F4F0E9; border: 1px solid #E4DFD6; border-radius: 6px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #8A8177 !important; text-transform: uppercase; font-size: 11px !important; }
    [data-testid="stMetricValue"] { color: #500000 !important; }
    h1 { color: #500000 !important; font-family: Georgia, serif; }
    h2, h3 { color: #1F1B18 !important; }
    .stButton button[kind="primary"] { background-color: #500000; border-color: #500000; }
    /* Pill-style buttons (st.pills widget) */
    [data-testid="stPills"] label {
        border-radius: 999px !important; border: 1px solid #E4DFD6 !important;
    }
    [data-testid="stPills"] label[data-checked="true"] {
        background-color: #500000 !important; border-color: #500000 !important; color: #fff !important;
    }
    /* Top-level page navigation (st.tabs) — bigger, bolder, visually distinct from filter pills */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; border-bottom: 2px solid #E4DFD6; margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto; padding: 10px 18px; font-size: 18px !important; font-weight: 700 !important;
        color: #8A8177 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #500000 !important; border-bottom: 3px solid #500000 !important;
    }
    [data-testid="stCaptionContainer"] { color: #8A8177 !important; }
    /* Section labels above pill groups, small caps like the mockup */
    .pill-label {
        font-size: 11px; color: #8A8177; text-transform: uppercase;
        letter-spacing: 0.05em; margin-bottom: 2px;
    }
    /* Top navigation bar — visually distinct from filter pills: bigger, boxier, maroon-outlined */
    .st-key-nav_pills {
        background: #F4E9DD; border: 2px solid #500000; border-radius: 10px;
        padding: 10px 14px; margin-bottom: 18px;
    }
    .st-key-nav_pills [data-testid="stPills"] label {
        border-radius: 6px !important; border: 2px solid #500000 !important;
        background: #fff !important; padding: 10px 20px !important;
    }
    .st-key-nav_pills [data-testid="stPills"] label p {
        font-size: 17px !important; font-weight: 700 !important; color: #500000 !important;
    }
    .st-key-nav_pills [data-testid="stPills"] label[data-checked="true"] {
        background-color: #500000 !important;
    }
    .st-key-nav_pills [data-testid="stPills"] label[data-checked="true"] p {
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#500000; padding:16px 20px; border-radius:6px; margin-bottom:16px;">
  <span style="color:#fff; font-family:Georgia,serif; font-size:22px; font-weight:700;">
    TAMU Rowing — Lineup &amp; Performance
  </span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="pill-label">Season</div>', unsafe_allow_html=True)
season_choice = st.pills(
    "Season", ["Spring (2k)", "Fall (5k)"], default="Spring (2k)",
    label_visibility="collapsed", key="global_season",
)
if season_choice is None:
    season_choice = "Spring (2k)"
season = "2k" if "2k" in season_choice else "5k"
st.caption(f"Applies to Overview, Lineup Builder, Regatta Lineups, and the split shown on Rower Profile — Team Roster stays season-independent.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    ["Overview", "Team Roster", "Rower Profile", "Lineup Builder", "Regatta Lineups", "Team & Calendar", "Weekly Schedule", "Weekly Lineups", "Equipment"]
)

# ---------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------
def get_conn():
    """
    Connects to Turso (persistent, cloud) if secrets are configured — this is what
    makes data survive Streamlit Cloud restarts. Falls back to a local SQLite file
    for offline/local development if no secrets are set (or no secrets.toml exists
    at all, which Streamlit otherwise raises on instead of just saying "not found").

    NOTE: this intentionally does NOT cache/reuse the connection object across
    reruns. Turso's remote connections can expire server-side ("stream not
    found" errors) — reusing a stale one crashes the app. Opening a fresh
    connection per call is cheap and avoids that entirely. The real caching
    win lives in the @st.cache_data-decorated read functions below, which
    still avoid most repeat round-trips.
    """
    try:
        has_turso_secrets = "TURSO_DATABASE_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets
    except Exception:
        has_turso_secrets = False

    if has_turso_secrets:
        import libsql
        return libsql.connect(
            database=st.secrets["TURSO_DATABASE_URL"],
            auth_token=st.secrets["TURSO_AUTH_TOKEN"],
        )
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run_query(sql, params=None):
    conn = get_conn()
    return pd.read_sql_query(sql, conn, params=params)


def run_write(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    result = cur.lastrowid
    # Any write can affect data that's currently cached elsewhere in the app —
    # clearing everything after a write is the safe, simple guarantee that the
    # next rerun shows fresh data instead of a stale cached read.
    st.cache_data.clear()
    return result


def split_label(seconds):
    if pd.isna(seconds):
        return "—"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:04.1f}"


def seconds_to_mmss(seconds):
    """Format total seconds as m:ss.s for display in an editable text field."""
    if seconds is None or pd.isna(seconds):
        return ""
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:04.1f}"


def parse_mmss(text):
    """Parse 'm:ss.s' into total seconds. Raises ValueError if the colon format isn't used. Returns None for blank input."""
    text = (text or "").strip()
    if not text:
        return None
    if ":" not in text:
        raise ValueError("Missing colon — use m:ss.s format (e.g. 6:55.3)")
    minutes_str, seconds_str = text.split(":", 1)
    minutes = float(minutes_str)
    seconds = float(seconds_str)
    if seconds < 0 or seconds >= 60:
        raise ValueError("Seconds must be between 0 and 59.9")
    if minutes < 0:
        raise ValueError("Minutes cannot be negative")
    return minutes * 60 + seconds


SCORE_FIELDS = [
    "technical", "consistency", "boat_moving", "rhythm", "balance",
    "pressure", "coachability", "reliability", "rating_control", "makes_boat_better",
]

# Seat-fit weight tables — same formulas as the mockup, one per seat role
WEIGHTS = {
    "Bow":     {"technical": .25, "balance": .20, "consistency": .15, "rhythm": .15, "boat_moving": .10, "split2k": .10, "reliability": .05},
    "2-Seat":  {"technical": .20, "rhythm": .20, "boat_moving": .20, "consistency": .15, "split2k": .15, "balance": .10},
    "Engine":  {"split2k": .30, "boat_moving": .20, "watts": .15, "technical": .15, "consistency": .10, "rhythm": .10},
    "7-Seat":  {"split2k": .25, "boat_moving": .20, "rhythm": .20, "technical": .15, "consistency": .10, "pressure": .10},
    "Stroke":  {"rhythm": .25, "technical": .20, "consistency": .15, "rating_control": .15, "pressure": .10, "split2k": .10, "coachability": .05},
    "Single":  {"split2k": .30, "watts": .15, "technical": .15, "rhythm": .15, "consistency": .15, "pressure": .10},
}

# Which seat role each numbered seat is, per boat class
BOAT_SEAT_MAP = {
    "8+": {1: "Bow", 2: "2-Seat", 3: "Engine", 4: "Engine", 5: "Engine", 6: "Engine", 7: "7-Seat", 8: "Stroke"},
    "4+": {1: "Bow", 2: "Engine", 3: "Engine", 4: "Stroke"},
    "4x": {1: "Bow", 2: "Engine", 3: "Engine", 4: "Stroke"},
    "2+": {1: "Bow", 2: "Stroke"},
    "2x": {1: "Bow", 2: "Stroke"},
    "1x": {1: "Single"},
}
SWEEP_CLASSES = ["8+", "4+", "2+"]
BOAT_LABELS = {"8+": "Eight (8+)", "4+": "Four w/ cox (4+)", "4x": "Quad (4x)", "2+": "Coxed pair (2+)", "2x": "Double (2x)", "1x": "Single (1x)"}


def normalize(series, lower_is_better):
    lo, hi = series.min(), series.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(100, index=series.index)
    if lower_is_better:
        return 100 * (hi - series) / (hi - lo)
    return 100 * (series - lo) / (hi - lo)


def compute_fit(df, role):
    weights = WEIGHTS[role]
    norm2k = normalize(df["time_2k_sec"], lower_is_better=True)
    normwatts = normalize(df["max_watts"], lower_is_better=False)
    score = pd.Series(0.0, index=df.index)
    for key, w in weights.items():
        if key == "split2k":
            vals = norm2k
        elif key == "watts":
            vals = normwatts
        else:
            vals = df[key].fillna(70)  # neutral default for unrated scores
        score += vals.fillna(50) * w
    return score.round(1)


ROLE_NOTES = {
    "Bow": "Lightest & most technical — sets the catch",
    "2-Seat": "Bridges the bow pair and the engine room",
    "Engine": "Power seat — biggest output, still needs to move the boat cleanly",
    "7-Seat": "Bridges the engine room and stroke",
    "Stroke": "Sets the rating — needs rhythm, composure & technical consistency",
    "Single": "Full responsibility for pace, steering, and power",
}

PHRASES = {
    "technical": "technical consistency", "balance": "balance and set", "consistency": "consistency",
    "rhythm": "rhythm", "boat_moving": "boat-moving ability", "split2k": "2k performance",
    "reliability": "reliability", "watts": "peak power", "pressure": "performance under pressure",
    "rating_control": "rating control", "coachability": "coachability",
}


def compute_fit_and_explain(df, role):
    """Same math as compute_fit, but also returns a 'Strong X and Y.' explanation per row."""
    weights = WEIGHTS[role]
    norm2k = normalize(df["time_2k_sec"], lower_is_better=True)
    normwatts = normalize(df["max_watts"], lower_is_better=False)
    contributions = {}
    total = pd.Series(0.0, index=df.index)
    for key, w in weights.items():
        if key == "split2k":
            vals = norm2k
        elif key == "watts":
            vals = normwatts
        else:
            vals = df[key].fillna(70)
        vals = vals.fillna(50)
        contrib = vals * w
        contributions[key] = contrib
        total += contrib
    contrib_df = pd.DataFrame(contributions)
    explanations = []
    for idx in df.index:
        ranked = contrib_df.loc[idx].sort_values(ascending=False)
        top2 = [PHRASES.get(k, k) for k in ranked.index[:2]]
        explanations.append(f"Strong {top2[0]} and {top2[1]}." if len(top2) > 1 else f"Strong {top2[0]}.")
    return total.round(1), pd.Series(explanations, index=df.index)


def boat_cohesion(assigned_df):
    """100 minus a small penalty for how spread-out rhythm/technical/balance are across the crew."""
    if len(assigned_df) < 2:
        return 100.0
    penalty = (
        assigned_df["rhythm"].fillna(70).std()
        + assigned_df["technical"].fillna(70).std()
        + assigned_df["balance"].fillna(70).std()
    ) * 0.4
    return max(0.0, min(100.0, 100.0 - penalty))


def render_month_calendar(events_by_date, year, month, key_prefix):
    """
    Renders a native HTML month-grid calendar (no external package — avoids any
    install risk). events_by_date: {date_str "YYYY-MM-DD": [(label, color_hex), ...]}
    """
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

    weeks = cal_module.Calendar(firstweekday=6).monthdayscalendar(year, month)  # Sunday-first
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


def auto_assign_boat(pool_df, seat_map, already_taken=None):
    """
    Greedy best-fit assignment (same idea as the mockup): score every (rower, seat)
    combination, then lock in the highest-scoring pairs first without reusing a seat
    or a rower. Only fills seats not already in `already_taken`.
    """
    already_taken = already_taken or {}
    open_seats = {s: role for s, role in seat_map.items() if not already_taken.get(s)}
    taken_names = {v for v in already_taken.values() if v}
    available = pool_df[~pool_df["rower_name"].isin(taken_names)]
    if available.empty or not open_seats:
        return {}

    pairs = []
    for seat_num, role in open_seats.items():
        fits = compute_fit(available, role)
        for idx, name in zip(available.index, available["rower_name"]):
            pairs.append((fits[idx], seat_num, name))
    pairs.sort(key=lambda x: -x[0])

    assignment = {}
    used_seats, used_rowers = set(), set()
    for score, seat_num, name in pairs:
        if seat_num in used_seats or name in used_rowers:
            continue
        assignment[seat_num] = name
        used_seats.add(seat_num)
        used_rowers.add(name)
        if len(used_seats) == len(open_seats):
            break
    return assignment


# ---------------------------------------------------------------
# Load base data (shared across pages)
# ---------------------------------------------------------------
@st.cache_data(ttl=300)
def load_rowers():
    return run_query("SELECT * FROM Rowers")


@st.cache_data(ttl=300)
def load_erg_scores():
    return run_query("""
        SELECT e.*, r.rower_name, r.gender, r.experience_level, r.weight
        FROM Erg_Score e JOIN Rowers r ON r.rower_id = e.rower_id
    """)


@st.cache_data(ttl=300)
def load_regattas():
    return run_query("SELECT * FROM Regattas ORDER BY regatta_id")


@st.cache_data(ttl=300)
def load_availability_for(regatta_id):
    return run_query(
        "SELECT r.rower_name FROM Availability a JOIN Rowers r ON r.rower_id = a.rower_id "
        "WHERE a.regatta_id = ? AND a.is_available = 0", (regatta_id,),
    )


@st.cache_data(ttl=300)
def load_unavailable_pairs():
    return run_query("""
        SELECT reg.name AS regatta, r.rower_name
        FROM Availability a
        JOIN Rowers r ON r.rower_id = a.rower_id
        JOIN Regattas reg ON reg.regatta_id = a.regatta_id
        WHERE a.is_available = 0
    """)


@st.cache_data(ttl=300)
def load_lineups_filtered(regatta, boat_name_pattern):
    return run_query("""
        SELECT l.boat_name, l.seat_number, l.side, r.rower_name, reg.name AS regatta, l.regatta_id AS regatta_id_raw, l.is_visible_to_team, eq.name AS boat_used
        FROM Lineups l
        JOIN Rowers r ON r.rower_id = l.rower_id
        LEFT JOIN Regattas reg ON reg.regatta_id = l.regatta_id
        LEFT JOIN Equipment eq ON eq.equipment_id = l.equipment_id
        WHERE reg.name = ? AND l.boat_name LIKE ?
        ORDER BY l.boat_name, l.seat_number
    """, (regatta, boat_name_pattern))


@st.cache_data(ttl=300)
def load_all_lineups():
    return run_query("""
        SELECT l.boat_name, l.seat_number, l.side, r.rower_name, reg.name AS regatta, l.regatta_id AS regatta_id_raw, l.is_visible_to_team, eq.name AS boat_used
        FROM Lineups l
        JOIN Rowers r ON r.rower_id = l.rower_id
        LEFT JOIN Regattas reg ON reg.regatta_id = l.regatta_id
        LEFT JOIN Equipment eq ON eq.equipment_id = l.equipment_id
        ORDER BY reg.name, l.boat_name, l.seat_number
    """)


@st.cache_data(ttl=300)
def load_regatta_view_lineups(selected_regatta):
    return run_query("""
        SELECT l.boat_name, l.seat_number, l.side, r.rower_name, r.gender, reg.name AS regatta
        FROM Lineups l
        JOIN Rowers r ON r.rower_id = l.rower_id
        LEFT JOIN Regattas reg ON reg.regatta_id = l.regatta_id
        WHERE reg.name = ?
        ORDER BY l.boat_name, l.seat_number
    """, (selected_regatta,))


@st.cache_data(ttl=300)
def load_unavailable_for_regatta(selected_regatta):
    return run_query("""
        SELECT r.rower_name
        FROM Availability a
        JOIN Rowers r ON r.rower_id = a.rower_id
        JOIN Regattas reg ON reg.regatta_id = a.regatta_id
        WHERE reg.name = ? AND a.is_available = 0
    """, (selected_regatta,))


@st.cache_data(ttl=300)
def load_calendar_sources():
    practice = run_query("SELECT event_date, event_type, notes FROM PracticeEvents")
    signups = run_query("SELECT event_date, title FROM SignUpEvents")
    regattas = run_query("SELECT name, event_date FROM Regattas WHERE event_date IS NOT NULL")
    return practice, signups, regattas


@st.cache_data(ttl=300)
def load_announcements():
    return run_query("SELECT * FROM Announcements ORDER BY posted_date DESC, announcement_id DESC")


@st.cache_data(ttl=300)
def load_practice_events():
    return run_query("SELECT * FROM PracticeEvents ORDER BY event_date ASC")


@st.cache_data(ttl=300)
def load_signup_events():
    return run_query("SELECT * FROM SignUpEvents ORDER BY event_date ASC")


@st.cache_data(ttl=300)
def load_signup_slots(event_id):
    return run_query("SELECT * FROM SignUpSlots WHERE event_id = ? ORDER BY start_time", (event_id,))


@st.cache_data(ttl=300)
def load_slot_responses(slot_id):
    return run_query(
        "SELECT r.rower_name FROM SignUpResponses sr JOIN Rowers r ON r.rower_id = sr.rower_id WHERE sr.slot_id = ?",
        (slot_id,),
    )


@st.cache_data(ttl=300)
def load_attendance_settings():
    return run_query("SELECT * FROM AttendanceSettings LIMIT 1")


@st.cache_data(ttl=300)
def load_absences():
    return run_query("""
        SELECT da.event_date, r.rower_name, da.reason
        FROM DayAbsences da JOIN Rowers r ON r.rower_id = da.rower_id
        ORDER BY da.event_date ASC
    """)


@st.cache_data(ttl=300)
def load_daily_assignments(date_str):
    return run_query("SELECT rower_id, location, is_coxswain FROM DailyAssignments WHERE event_date = ?", (date_str,))


@st.cache_data(ttl=300)
def load_daily_coaches(date_str):
    return run_query("SELECT location, coach_name FROM DailyCoaches WHERE event_date = ?", (date_str,))


@st.cache_data(ttl=300)
def load_equipment():
    return run_query("SELECT * FROM Equipment ORDER BY category, name")


@st.cache_data(ttl=300)
def load_purchase_requests():
    return run_query("SELECT * FROM PurchaseRequests ORDER BY requested_date DESC")


@st.cache_data(ttl=300)
def load_gendered_assignments_by_date():
    return run_query("""
        SELECT da.event_date, r.gender, da.location, COUNT(*) AS n
        FROM DailyAssignments da JOIN Rowers r ON r.rower_id = da.rower_id
        GROUP BY da.event_date, r.gender, da.location
    """)


rowers_df = load_rowers()
erg_df = load_erg_scores()

if rowers_df.empty:
    st.warning("No rowers in the database yet. Add some on the Team Roster page to get started.")

# =================================================================
# PAGE: Overview
# =================================================================
with tab1:
    st.title("Overview")
    st.caption(f"Showing {'Spring (2k)' if season == '2k' else 'Fall (5k)'} data — change the season selector above to switch.")

    st.markdown('<div class="pill-label">Squad</div>', unsafe_allow_html=True)
    squad = st.pills("Squad", ["All", "Women", "Men"], default="All", label_visibility="collapsed")

    df = erg_df.copy()
    if squad != "All":
        df = df[df["gender"] == squad.lower()]

    split_col = "time_2k_sec" if season == "2k" else "time_5k_sec"
    df = df.dropna(subset=[split_col]).sort_values(split_col)
    divisor = 4 if season == "2k" else 10  # 2k = 4x 500m, 5k = 10x 500m

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rowers Shown", len(df))
    c2.metric(f"Avg {season} 500m Split", split_label(df[split_col].mean() / divisor) if len(df) else "—")
    c3.metric("Fastest 500m Split", split_label(df[split_col].min() / divisor) if len(df) else "—")
    c4.metric("Avg Max Watts", f"{df['max_watts'].mean():.0f}" if len(df) else "—")

    if len(df):
        df["split_500m"] = df[split_col] / divisor
        df["split_label"] = df["split_500m"].apply(split_label)
        fig = px.bar(
            df, x="split_500m", y="rower_name", orientation="h",
            color="gender", color_discrete_map={"women": MAROON, "men": MAROON_LIGHT},
            labels={"split_500m": "500m split (min:sec)", "rower_name": ""},
            custom_data=["split_label"],
        )
        fig.update_yaxes(categoryorder="total descending")
        fig.update_layout(plot_bgcolor="#FAF8F5", paper_bgcolor="#FAF8F5", font_color="#1F1B18")
        fig.update_traces(hovertemplate="%{y}: %{customdata[0]}<extra></extra>")

        # Build clean mm:ss tick marks instead of raw seconds
        lo, hi = df["split_500m"].min(), df["split_500m"].max()
        step = 5 if (hi - lo) < 40 else 10
        start = int(lo // step) * step
        tickvals = list(range(start, int(hi) + step, step))
        fig.update_xaxes(tickvals=tickvals, ticktext=[split_label(t) for t in tickvals])

        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No erg scores yet for this filter.")

# =================================================================
# PAGE: Team Roster (editable — writes straight back to SQL)
# =================================================================
with tab2:
    st.title("Team Roster")
    st.caption("Click a rower to expand and edit their info, grouped by what it means — physical stats, experience, and coach scores are kept separate.")

    if "add_rower_expanded" not in st.session_state:
        st.session_state["add_rower_expanded"] = False

    with st.expander("+ Add a new rower", expanded=st.session_state["add_rower_expanded"]):
        nc1, nc2, nc3, nc4 = st.columns(4)
        new_name = nc1.text_input("Name (first and last)", key="new_rower_name")
        new_gender = nc2.selectbox("Gender", ["women", "men"], key="new_rower_gender")
        new_weight = nc3.number_input("Weight (lb)", min_value=0.0, step=1.0, key="new_rower_weight")
        new_years = nc4.number_input("Years rowing", min_value=0, step=1, key="new_rower_years")
        nc5, nc6, nc7, nc8 = st.columns(4)
        new_exp = nc5.selectbox("Experience", ["novice", "varsity"], key="new_rower_exp")
        new_height_ft = nc6.number_input("Height (ft)", min_value=0, max_value=8, step=1, key="new_rower_height_ft")
        new_height_in = nc7.number_input("Height (in)", min_value=0, max_value=11, step=1, key="new_rower_height_in")
        new_side = nc8.selectbox("Side preference", ["port", "starboard", "both"], key="new_rower_side")
        new_height = new_height_ft * 12 + new_height_in

        nc9, nc10 = st.columns(2)
        new_phone = nc9.text_input("Phone (optional)", key="new_rower_phone")
        new_email = nc10.text_input("Email (optional)", key="new_rower_email")

        add_clicked = st.button("Add Rower", type="primary")

        if add_clicked:
            name_parts = new_name.strip().split()
            if len(name_parts) < 2:
                st.session_state["add_rower_expanded"] = True
                st.error("Please enter both a first and last name.")
            else:
                clean_name = " ".join(p.capitalize() for p in name_parts)
                score_cols = ", ".join(SCORE_FIELDS)
                score_placeholders = ", ".join(["?"] * len(SCORE_FIELDS))
                score_defaults = [70] * len(SCORE_FIELDS)  # neutral default — matches what the app already assumes for unrated rowers
                run_write(
                    f"INSERT INTO Rowers (rower_name, gender, weight, years_rowing, experience_level, height_in, sweep_side, phone, email, {score_cols}) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, {score_placeholders})",
                    (clean_name, new_gender, new_weight, new_years, new_exp, new_height, new_side,
                     new_phone.strip() or None, new_email.strip() or None, *score_defaults),
                )
                st.session_state["add_rower_expanded"] = True
                for k in ["new_rower_name", "new_rower_gender", "new_rower_weight", "new_rower_years",
                          "new_rower_exp", "new_rower_height_ft", "new_rower_height_in", "new_rower_side",
                          "new_rower_phone", "new_rower_email"]:
                    st.session_state.pop(k, None)
                st.toast(f"Added {clean_name}.", icon="✅")
                st.rerun()

    def roster_column(title, gender_key):
        st.subheader(f"{title} ({len(rowers_df[rowers_df['gender'] == gender_key])})")
        subset = rowers_df[rowers_df["gender"] == gender_key].sort_values("rower_name")
        for _, r in subset.iterrows():
            rid = int(r["rower_id"])
            cox_badge = "  🎯 COX" if r.get("is_coxswain") else ""
            with st.expander(f"{r['rower_name']}  ·  {r['experience_level']}{cox_badge}"):
                st.markdown("**Physical**")
                current_height = int(r["height_in"]) if pd.notna(r["height_in"]) else 0
                cur_ft, cur_in = divmod(current_height, 12)
                p1, p2, p3 = st.columns(3)
                weight = p1.number_input("Weight (lb)", value=float(r["weight"]), key=f"weight_{rid}")
                height_ft = p2.number_input("Height (ft)", min_value=0, max_value=8, value=int(cur_ft), key=f"height_ft_{rid}")
                height_in_part = p3.number_input("Height (in)", min_value=0, max_value=11, value=int(cur_in), key=f"height_in_{rid}")
                height = height_ft * 12 + height_in_part

                st.markdown("**Experience**")
                e1, e2, e3 = st.columns(3)
                years = e1.number_input("Years rowing", value=int(r["years_rowing"]), key=f"years_{rid}")
                exp = e2.selectbox("Experience level", ["novice", "varsity"],
                                    index=["novice", "varsity"].index(r["experience_level"]), key=f"exp_{rid}")
                side_options = ["port", "starboard", "both"]
                current_side = r.get("sweep_side")
                side_index = side_options.index(current_side) if current_side in side_options else 0
                side = e3.selectbox("Side preference", side_options, index=side_index, key=f"side_{rid}")

                is_cox = st.checkbox("🎯 This rower is a coxswain", value=bool(r.get("is_coxswain")), key=f"cox_{rid}")

                st.markdown("**Contact**")
                ct1, ct2 = st.columns(2)
                phone = ct1.text_input("Phone", value=r.get("phone") or "", key=f"phone_{rid}")
                email = ct2.text_input("Email", value=r.get("email") or "", key=f"email_{rid}")

                st.markdown("**Coach Scores** (0–100)")
                score_pairs = [SCORE_FIELDS[i:i + 2] for i in range(0, len(SCORE_FIELDS), 2)]
                score_values = {}
                for pair in score_pairs:
                    cols = st.columns(2)
                    for i, field in enumerate(pair):
                        current = r.get(field)
                        current = int(current) if pd.notna(current) else 70
                        score_values[field] = cols[i].number_input(
                            field.replace("_", " ").title(), min_value=0, max_value=100,
                            value=current, key=f"{field}_{rid}"
                        )

                if st.button("💾 Save", key=f"save_rower_{rid}"):
                    all_fields = {"weight": weight, "height_in": height, "years_rowing": years,
                                   "experience_level": exp, "sweep_side": side, "is_coxswain": 1 if is_cox else 0,
                                   "phone": phone.strip() or None, "email": email.strip() or None, **score_values}
                    set_clause = ", ".join([f"{c} = ?" for c in all_fields])
                    run_write(f"UPDATE Rowers SET {set_clause} WHERE rower_id = ?", list(all_fields.values()) + [rid])
                    st.toast(f"Saved {r['rower_name']}.", icon="✅")
                    st.rerun()

                st.divider()
                st.markdown("**Erg Test Results**")
                st.caption("Updates this rower's most recent test — no need to touch Excel or the database directly. Enter times as m:ss.s (e.g. 6:55.3), not raw seconds.")
                latest = erg_df[erg_df["rower_name"] == r["rower_name"]].sort_values("test_date_2k", ascending=False)
                existing = latest.iloc[0] if len(latest) else None

                g1, g2 = st.columns(2)
                d2k_val = pd.to_datetime(existing["test_date_2k"]).date() if existing is not None and pd.notna(existing.get("test_date_2k")) else None
                test_date_2k = g1.date_input("2k test date", value=d2k_val, key=f"date2k_{rid}")
                time_2k_text = g2.text_input(
                    "2k time (m:ss.s)",
                    value=seconds_to_mmss(existing["time_2k_sec"]) if existing is not None else "",
                    key=f"time2k_{rid}", placeholder="e.g. 6:55.3",
                )
                time_2k_error = None
                try:
                    time_2k = parse_mmss(time_2k_text)
                    if time_2k:
                        g2.caption(f"500m split: {split_label(time_2k / 4)}")
                except ValueError as e:
                    time_2k = None
                    time_2k_error = str(e)
                    g2.caption(f"⚠ {e}")

                g3, g4 = st.columns(2)
                d5k_val = pd.to_datetime(existing["test_date_5k"]).date() if existing is not None and pd.notna(existing.get("test_date_5k")) else None
                test_date_5k = g3.date_input("5k test date", value=d5k_val, key=f"date5k_{rid}")
                time_5k_text = g4.text_input(
                    "5k time (m:ss.s)",
                    value=seconds_to_mmss(existing["time_5k_sec"]) if existing is not None else "",
                    key=f"time5k_{rid}", placeholder="e.g. 17:42.5",
                )
                time_5k_error = None
                try:
                    time_5k = parse_mmss(time_5k_text)
                    if time_5k:
                        g4.caption(f"500m split: {split_label(time_5k / 10)}")
                except ValueError as e:
                    time_5k = None
                    time_5k_error = str(e)
                    g4.caption(f"⚠ {e}")

                max_watts = st.number_input("Max watts", min_value=0.0, step=1.0,
                                             value=float(existing["max_watts"]) if existing is not None and pd.notna(existing.get("max_watts")) else 0.0,
                                             key=f"watts_{rid}")

                if st.button("💾 Save Erg Scores", key=f"save_erg_{rid}"):
                    if time_2k_error or time_5k_error:
                        st.error("Fix the time format above before saving — use m:ss.s, e.g. 6:55.3.")
                    elif existing is not None:
                        run_write(
                            "UPDATE Erg_Score SET test_date_2k=?, time_2k_sec=?, test_date_5k=?, time_5k_sec=?, max_watts=? WHERE score_id=?",
                            (str(test_date_2k) if test_date_2k else None, time_2k or None,
                             str(test_date_5k) if test_date_5k else None, time_5k or None, max_watts, int(existing["score_id"])),
                        )
                    else:
                        run_write(
                            "INSERT INTO Erg_Score (rower_id, test_date_2k, time_2k_sec, test_date_5k, time_5k_sec, max_watts) VALUES (?, ?, ?, ?, ?, ?)",
                            (rid, str(test_date_2k) if test_date_2k else None, time_2k or None,
                             str(test_date_5k) if test_date_5k else None, time_5k or None, max_watts),
                        )
                    st.toast(f"Saved erg scores for {r['rower_name']}.", icon="✅")
                    st.rerun()

                st.divider()
                confirm_key = f"confirm_remove_{rid}"
                confirmed = st.checkbox(f"Yes, permanently remove {r['rower_name']} from the roster", key=confirm_key)
                if st.button("🗑 Remove from Roster", key=f"remove_rower_{rid}", disabled=not confirmed):
                    with get_conn() as conn:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM Lineups WHERE rower_id = ?", (rid,))
                        cur.execute("DELETE FROM Erg_Score WHERE rower_id = ?", (rid,))
                        cur.execute("DELETE FROM Availability WHERE rower_id = ?", (rid,))
                        cur.execute("DELETE FROM Rowers WHERE rower_id = ?", (rid,))
                        conn.commit()
                    st.toast(f"Removed {r['rower_name']} from the roster.", icon="🗑")
                    st.rerun()

    if rowers_df.empty:
        st.info("No rowers yet — add your first one above.")
    else:
        col_w, col_m = st.columns(2)
        with col_w:
            roster_column("Women", "women")
        with col_m:
            roster_column("Men", "men")

# =================================================================
# PAGE: Rower Profile
# =================================================================
with tab3:
    st.title("Rower Profile")

    if rowers_df.empty:
        st.info("No rowers yet — add some on the Team Roster page.")
    else:
        name = st.selectbox("Select a rower", sorted(rowers_df["rower_name"].unique()))
        rower = rowers_df[rowers_df["rower_name"] == name].iloc[0]
        latest_erg = erg_df[erg_df["rower_name"] == name].sort_values("test_date_2k", ascending=False)
        rp_split_field = "time_2k_sec" if season == "2k" else "time_5k_sec"
        rp_divisor = 4 if season == "2k" else 10
        rp_split_val = latest_erg[rp_split_field].iloc[0] if len(latest_erg) and pd.notna(latest_erg[rp_split_field].iloc[0]) else None

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Weight", f"{rower['weight']} lb")
        c2.metric("Height", f"{int(rower['height_in'])//12}'{int(rower['height_in'])%12}\"" if pd.notna(rower["height_in"]) else "—")
        c3.metric(f"{'2k' if season == '2k' else '5k'} Split", split_label(rp_split_val / rp_divisor) if rp_split_val is not None else "—")
        c4.metric("Max Watts", f"{latest_erg['max_watts'].iloc[0]:.0f}" if len(latest_erg) else "—")
        avg_score = sum(rower.get(f) if pd.notna(rower.get(f)) else 70 for f in SCORE_FIELDS) / len(SCORE_FIELDS)
        c5.metric("Avg Score", f"{avg_score:.0f}")

        side_display = rower.get("sweep_side")
        st.caption(f"Side preference: **{side_display.title()}**" if pd.notna(side_display) else "Side preference: not set")

        st.subheader("Scores")
        for field in SCORE_FIELDS:
            val = rower.get(field)
            val = val if pd.notna(val) else 70
            st.progress(int(val) / 100, text=f"{field.replace('_', ' ').title()}: {int(val)}")

# =================================================================
# PAGE: Lineup Builder
# =================================================================
with tab4:
    st.title("Lineup Builder")
    st.caption("Boats you add here live in this browser session until you click Save — saving writes the lineup permanently to the database.")

    if "boats" not in st.session_state:
        st.session_state.boats = []  # each: {id, boat_class, category, weight_class, regatta, seats:{}, sides:{}}
    if "next_boat_id" not in st.session_state:
        st.session_state.next_boat_id = 1

    # A swap requested by the "Apply swap" button below can't touch a seat widget's
    # state after that widget has already rendered this run — Streamlit disallows it.
    # So we stash the request and apply it here, at the very top, before any seat
    # widget for this run has been created yet.
    if "pending_swap" in st.session_state:
        swap = st.session_state.pop("pending_swap")
        for b in st.session_state.boats:
            if b["id"] == swap["boat_id"]:
                b["seats"][swap["seat_num"]] = swap["new_name"]
                st.session_state[f"seat_{swap['boat_id']}_{swap['seat_num']}"] = swap["new_name"] if swap["new_name"] else "— empty —"
                if swap.get("other_seat") is not None:
                    b["seats"][swap["other_seat"]] = swap["other_name"]
                    st.session_state[f"seat_{swap['boat_id']}_{swap['other_seat']}"] = swap["other_name"] if swap["other_name"] else "— empty —"
                break

    # --- Top filter row — this both filters what's shown AND is the template for new boats ---
    regattas_df = load_regattas()
    # Only regattas for the current season (or season-agnostic ones like Practice) show up
    if not regattas_df.empty:
        regattas_df = regattas_df[(regattas_df["name"] == "Practice") | (regattas_df["season"] == season)]
    if not regattas_df.empty:
        # Practice always first, everything else ordered by date (undated regattas go last)
        regattas_df["_is_practice"] = regattas_df["name"] == "Practice"
        regattas_df["_sort_date"] = pd.to_datetime(regattas_df["event_date"], errors="coerce")
        regattas_df = regattas_df.sort_values(
            by=["_is_practice", "_sort_date"], ascending=[False, True], na_position="last"
        ).drop(columns=["_is_practice", "_sort_date"])
    regatta_names = regattas_df["name"].tolist() if not regattas_df.empty else ["Practice"]

    st.markdown('<div class="pill-label">Squad</div>', unsafe_allow_html=True)
    squad_label = st.pills("Squad", ["Women", "Men"], default="Women", label_visibility="collapsed")
    squad = squad_label.lower()

    st.markdown('<div class="pill-label">Regatta</div>', unsafe_allow_html=True)
    regatta = st.pills("Regatta", regatta_names, default=regatta_names[0], label_visibility="collapsed")
    if regatta is None:
        regatta = regatta_names[0]

    with st.expander("+ Add a new regatta"):
        rc1, rc2, rc3, rc4 = st.columns([2, 1, 1, 1])
        new_regatta_name = rc1.text_input("Regatta name", key="new_regatta_name")
        new_regatta_date = rc2.date_input("Date", key="new_regatta_date", value=None)
        new_regatta_season = rc3.selectbox("Season", ["Spring (2k)", "Fall (5k)"], key="new_regatta_season")
        if rc4.button("Add Regatta"):
            if new_regatta_name.strip():
                clean_regatta_name = " ".join(w.capitalize() for w in new_regatta_name.strip().split())
                existing_names_lower = [n.lower() for n in run_query("SELECT name FROM Regattas")["name"].tolist()]
                if clean_regatta_name.lower() in existing_names_lower:
                    st.error(f'A regatta named "{clean_regatta_name}" already exists — pick a different name or use the existing one.')
                else:
                    season_val = "2k" if "2k" in new_regatta_season else "5k"
                    run_write("INSERT OR IGNORE INTO Regattas (name, event_date, season) VALUES (?, ?, ?)",
                               (clean_regatta_name, str(new_regatta_date) if new_regatta_date else None, season_val))
                    st.rerun()

    with st.expander("🗑 Delete a regatta"):
        st.caption("This also removes any lineups/availability saved under it.")
        dc1, dc2 = st.columns([2, 1])
        deletable = [n for n in regatta_names if n != "Practice"]
        if deletable:
            regatta_to_delete = dc1.selectbox("Regatta to delete", deletable, key="regatta_to_delete")
            if dc2.button("🗑 Delete Regatta"):
                row = regattas_df[regattas_df["name"] == regatta_to_delete]
                rid_to_delete = int(row["regatta_id"].iloc[0]) if not row.empty else None
                if rid_to_delete is not None:
                    with get_conn() as conn:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM Lineups WHERE regatta_id = ?", (rid_to_delete,))
                        cur.execute("DELETE FROM Availability WHERE regatta_id = ?", (rid_to_delete,))
                        cur.execute("DELETE FROM Regattas WHERE regatta_id = ?", (rid_to_delete,))
                        conn.commit()
                    st.toast(f"Deleted {regatta_to_delete}.", icon="🗑")
                    st.rerun()
        else:
            st.caption("No deletable regattas — \"Practice\" is protected as the default.")

    with st.expander("✏️ Set a regatta's season"):
        st.caption("Fixes regattas that don't have a season assigned yet — those won't show up under either season until fixed.")
        all_regattas_df = load_regattas()
        editable = [n for n in all_regattas_df["name"].tolist() if n != "Practice"]
        if editable:
            ec1, ec2, ec3 = st.columns([2, 1, 1])
            regatta_to_edit = ec1.selectbox("Regatta", editable, key="regatta_to_edit_season")
            current_season_row = all_regattas_df[all_regattas_df["name"] == regatta_to_edit]
            current_season_val = current_season_row["season"].iloc[0] if not current_season_row.empty else None
            season_options = ["Spring (2k)", "Fall (5k)"]
            default_index = 1 if current_season_val == "5k" else 0
            edit_season_choice = ec2.selectbox("Season", season_options, index=default_index, key="regatta_edit_season_choice")
            if ec3.button("Update Season"):
                new_season_val = "2k" if "2k" in edit_season_choice else "5k"
                row = all_regattas_df[all_regattas_df["name"] == regatta_to_edit]
                rid_to_edit = int(row["regatta_id"].iloc[0]) if not row.empty else None
                if rid_to_edit is not None:
                    run_write("UPDATE Regattas SET season = ? WHERE regatta_id = ?", (new_season_val, rid_to_edit))
                    st.toast(f"{regatta_to_edit} is now tagged {edit_season_choice}.", icon="✅")
                    st.rerun()
        else:
            st.caption("No regattas to edit yet besides Practice.")

    # --- Availability toggle for this regatta ---
    squad_rowers = sorted(rowers_df[rowers_df["gender"] == squad]["rower_name"].tolist())
    if squad_rowers:
        st.markdown(f'<div class="pill-label">Availability for {regatta} — click to mark unavailable</div>', unsafe_allow_html=True)
        regatta_row = regattas_df[regattas_df["name"] == regatta]
        regatta_id_for_avail = int(regatta_row["regatta_id"].iloc[0]) if not regatta_row.empty else None
        existing_unavailable = []
        if regatta_id_for_avail is not None:
            avail_df = load_availability_for(regatta_id_for_avail)
            existing_unavailable = avail_df["rower_name"].tolist()
        unavailable_selected = st.pills(
            "Unavailable", squad_rowers, selection_mode="multi",
            default=[n for n in existing_unavailable if n in squad_rowers],
            label_visibility="collapsed", key=f"avail_{regatta}_{squad}",
        )
        if regatta_id_for_avail is not None and st.button("Save availability", key=f"save_avail_{regatta}_{squad}"):
            with get_conn() as conn:
                cur = conn.cursor()
                for name in squad_rowers:
                    rid = int(rowers_df[rowers_df["rower_name"] == name]["rower_id"].iloc[0])
                    is_avail = 0 if name in (unavailable_selected or []) else 1
                    cur.execute("DELETE FROM Availability WHERE rower_id = ? AND regatta_id = ?", (rid, regatta_id_for_avail))
                    cur.execute("INSERT INTO Availability (rower_id, regatta_id, is_available) VALUES (?, ?, ?)",
                                (rid, regatta_id_for_avail, is_avail))
                conn.commit()
            st.success("Availability saved.")
    else:
        unavailable_selected = []

    st.markdown('<div class="pill-label">Boat Class</div>', unsafe_allow_html=True)
    boat_class_filter = st.pills("Boat Class", list(BOAT_SEAT_MAP.keys()), default="8+", label_visibility="collapsed")
    if boat_class_filter is None:
        boat_class_filter = "8+"

    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown('<div class="pill-label">Category</div>', unsafe_allow_html=True)
        category_label = st.pills("Category", ["Varsity", "Novice"], default="Varsity", label_visibility="collapsed")
        category = (category_label or "Varsity").lower()
    with fc2:
        st.markdown('<div class="pill-label">Weight Class</div>', unsafe_allow_html=True)
        weight_label = st.pills("Weight Class", ["Openweight", "Lightweight"], default="Openweight", label_visibility="collapsed")
        weight_class = "lightweight" if weight_label == "Lightweight" else "open"

    if st.button("+ Add another boat here", type="primary"):
        st.session_state.boats.append({
            "id": st.session_state.next_boat_id,
            "boat_class": boat_class_filter, "category": category,
            "weight_class": weight_class, "regatta": regatta, "squad": squad,
            "seats": {}, "sides": {},
        })
        st.session_state.next_boat_id += 1
        st.rerun()

    # --- Eligible pool for current filter ---
    weight_cap = 160 if squad == "men" else 130
    pool = rowers_df[rowers_df["gender"] == squad].copy()
    if category == "novice":
        pool = pool[pool["experience_level"] == "novice"]
    if weight_class == "lightweight":
        pool = pool[pool["weight"] <= weight_cap]
    pool = pool[~pool["rower_name"].isin(unavailable_selected or [])]
    split_field = "time_2k_sec" if season == "2k" else "time_5k_sec"
    sort_date_field = "test_date_2k" if season == "2k" else "test_date_5k"
    latest = erg_df.sort_values(sort_date_field).groupby("rower_id").last().reset_index()
    season_erg = latest[["rower_id", split_field, "max_watts"]].rename(columns={split_field: "time_2k_sec"})
    pool = pool.merge(season_erg, on="rower_id", how="left")
    # Don't drop rowers who haven't tested yet this season — they still need to be
    # placeable in a lineup and scored on everything else. Missing split/watts just
    # fall back to a neutral default inside compute_fit().

    visible_boats = [b for b in st.session_state.boats
                      if b["squad"] == squad and b["category"] == category
                      and b["weight_class"] == weight_class and b["regatta"] == regatta
                      and b["boat_class"] == boat_class_filter]

    st.markdown(f"**Showing {regatta} — {category.title()} {weight_class.title()} {squad.title()} {boat_class_filter} — {len(visible_boats)} boat(s)**")

    if not visible_boats:
        st.info("No boats yet in this category — use the controls above to add one.")

    # Count boats per class for A/B/C labeling
    class_counts = {}
    used_across_boats = set()  # rowers already placed in an EARLIER boat within this same view
    boat_label_map = {}  # boat id -> label, reused below for Athlete Profile / What If

    for boat in visible_boats:
        class_counts[boat["boat_class"]] = class_counts.get(boat["boat_class"], 0) + 1
        letter = chr(64 + class_counts[boat["boat_class"]])  # A, B, C...
        label = f"{boat['boat_class']} {letter}"
        boat_label_map[boat["id"]] = label

        with st.container(border=True):
            hc1, hc2 = st.columns([5, 1])
            hc1.markdown(f"### {label} — {category.title()} {squad.title()}")
            if hc2.button("🗑 Remove", key=f"remove_{boat['id']}"):
                st.session_state.boats = [b for b in st.session_state.boats if b["id"] != boat["id"]]
                st.rerun()

            if pool.empty:
                st.warning("No eligible rowers with erg scores for this filter yet.")
                continue

            boats_available_lb = load_equipment()
            boats_available_lb = boats_available_lb[boats_available_lb["category"] == "Boat"] if not boats_available_lb.empty else boats_available_lb
            boat_option_names_lb = ["— not assigned —"] + boats_available_lb["name"].tolist() if not boats_available_lb.empty else ["— not assigned —"]
            current_equipment_name = boat.get("equipment_name") or "— not assigned —"
            if current_equipment_name not in boat_option_names_lb:
                current_equipment_name = "— not assigned —"
            selected_equipment_name = st.selectbox(
                "🚣 Physical boat used (optional)", boat_option_names_lb,
                index=boat_option_names_lb.index(current_equipment_name),
                key=f"equipment_select_{boat['id']}",
            )
            boat["equipment_name"] = None if selected_equipment_name == "— not assigned —" else selected_equipment_name

            seat_map = BOAT_SEAT_MAP[boat["boat_class"]]
            is_sweep = boat["boat_class"] in SWEEP_CLASSES

            # This boat's own current selections stay selectable even if "used" —
            # only rowers used in EARLIER boats are excluded from the dropdown.
            own_current = {v for v in boat["seats"].values() if v}
            pool_this_boat = pool[~pool["rower_name"].isin(used_across_boats - own_current)]
            if len(used_across_boats - own_current) > 0:
                st.caption(f"Already placed in an earlier boat this view: {', '.join(sorted(used_across_boats - own_current))}")

            afc1, afc2 = st.columns([1, 3])
            if afc1.button("🪄 Auto-fill empty seats", key=f"autofill_{boat['id']}"):
                if len(pool_this_boat) == 0:
                    st.warning("No eligible, available rowers left to auto-fill with.")
                else:
                    suggestion = auto_assign_boat(pool_this_boat, seat_map, already_taken=boat["seats"])
                    for seat_num, name in suggestion.items():
                        boat["seats"][seat_num] = name
                        # The dropdown widget has its own stored value under this key —
                        # updating boat["seats"] alone won't change what it displays,
                        # so we have to set the widget's own state directly too.
                        st.session_state[f"seat_{boat['id']}_{seat_num}"] = name
                    if suggestion and is_sweep:
                        # Default alternating side pattern: seat 1 port, seat 2 starboard, seat 3 port...
                        for seat_num in sorted(seat_map.keys()):
                            side_val = "port" if seat_num % 2 == 1 else "starboard"
                            boat["sides"][seat_num] = side_val
                            st.session_state[f"side_{boat['id']}_{seat_num}"] = side_val
                    if suggestion:
                        st.toast(f"Filled {len(suggestion)} seat(s) using best available fit.", icon="🪄")
                    st.rerun()
            afc2.caption("Fills only empty seats — already-picked rowers stay put. Skips anyone unavailable or already used in an earlier boat. Sides default to alternating port/starboard.")

            # Pre-read current widget values (from session_state) BEFORE rendering,
            # so duplicate detection reflects THIS run's selections, not last run's.
            preview_names = []
            for seat_num in seat_map:
                key = f"seat_{boat['id']}_{seat_num}"
                val = st.session_state.get(key, boat["seats"].get(seat_num) or "— empty —")
                if val and val != "— empty —":
                    preview_names.append(val)
            dupes = {n for n in preview_names if preview_names.count(n) > 1}

            for seat_num, role in seat_map.items():
                fit_scores = compute_fit(pool_this_boat, role) if len(pool_this_boat) else pd.Series(dtype=float)
                pool_ranked = pool_this_boat.assign(fit=fit_scores).sort_values("fit", ascending=False) if len(pool_this_boat) else pool_this_boat
                options = ["— empty —"] + pool_ranked["rower_name"].tolist()

                current_val = boat["seats"].get(seat_num, "— empty —")
                if current_val not in options:
                    options = options + [current_val] if current_val != "— empty —" else options
                    if current_val not in options:
                        current_val = "— empty —"

                cols = st.columns([0.6, 1.4, 2.2, 1, 1.2]) if is_sweep else st.columns([0.6, 1.4, 2.6, 1.4])

                cols[0].markdown(f"**Seat {seat_num}**")
                cols[1].markdown(f"*{role}*")

                chosen = cols[2].selectbox(
                    "Rower", options, index=options.index(current_val),
                    key=f"seat_{boat['id']}_{seat_num}", label_visibility="collapsed"
                )
                boat["seats"][seat_num] = None if chosen == "— empty —" else chosen

                if chosen != "— empty —":
                    fit_row = pool_ranked[pool_ranked["rower_name"] == chosen]
                    fit_val = fit_row["fit"].iloc[0] if len(fit_row) else None
                    fit_color = "🔴" if chosen in dupes else ""
                    fit_text = f"Fit: **{fit_val:.1f}**" if fit_val is not None else "Fit: —"
                    cols[3].markdown(f"{fit_text} {fit_color}")
                    if chosen in (unavailable_selected or []):
                        st.error(f"⚠ {chosen} is marked unavailable for {regatta} but is sitting in Seat {seat_num} of this boat.")

                if is_sweep:
                    side_val = boat["sides"].get(seat_num, "")
                    side = cols[4].selectbox(
                        "Side", ["", "port", "starboard"], index=["", "port", "starboard"].index(side_val),
                        key=f"side_{boat['id']}_{seat_num}", label_visibility="collapsed"
                    )
                    boat["sides"][seat_num] = side

            if dupes:
                st.error(f"⚠ Repeated rower(s) in this boat: {', '.join(dupes)} — fix one of the seats above before saving.")

            assigned_names_now = [v for v in boat["seats"].values() if v]
            assigned_splits = pool_this_boat[pool_this_boat["rower_name"].isin(assigned_names_now)]["time_2k_sec"]
            split_divisor = 4 if season == "2k" else 10
            avg_split_val = (assigned_splits.mean() / split_divisor) if len(assigned_splits) else None
            st.metric(f"Avg 500m Split ({'2k' if season == '2k' else '5k'})", split_label(avg_split_val) if avg_split_val is not None else "—")

            if is_sweep:
                sides_filled = [boat["sides"].get(s) for s in seat_map if boat["seats"].get(s)]
                port_n = sides_filled.count("port")
                star_n = sides_filled.count("starboard")
                if len(sides_filled) == len(seat_map) and len(seat_map) > 0:
                    expected = len(seat_map) // 2
                    if port_n != expected or star_n != expected:
                        st.warning(f"⚠ Side imbalance: {port_n} port / {star_n} starboard — a {boat['boat_class']} needs {expected} and {expected}.")

            if st.button(f"💾 Save {label} to Database", key=f"save_{boat['id']}"):
                regatta_row = regattas_df[regattas_df["name"] == regatta]
                regatta_id = int(regatta_row["regatta_id"].iloc[0]) if not regatta_row.empty else None
                boat_name = f"{squad.title()} {category.title()} {label}"

                boat_equipment_id = None
                if boat.get("equipment_name") and not boats_available_lb.empty:
                    match = boats_available_lb[boats_available_lb["name"] == boat["equipment_name"]]
                    if not match.empty:
                        boat_equipment_id = int(match["equipment_id"].iloc[0])

                # Clear any earlier saved rows for this exact boat first, so re-saving doesn't duplicate
                run_write("DELETE FROM Lineups WHERE boat_name = ? AND regatta_id IS ?", (boat_name, regatta_id))
                saved = 0
                for seat_num, rower_name in boat["seats"].items():
                    if not rower_name:
                        continue
                    rower_id = int(rowers_df[rowers_df["rower_name"] == rower_name]["rower_id"].iloc[0])
                    side = boat["sides"].get(seat_num, "")
                    run_write(
                        "INSERT INTO Lineups (boat_name, race_date, seat_number, side, rower_id, regatta_id, equipment_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (boat_name, None, seat_num, side, rower_id, regatta_id, boat_equipment_id),
                    )
                    saved += 1
                st.success(f"Saved {saved} seat(s) for {boat_name} to the database.")

        # This boat's picks are now off-limits for the NEXT boat in this same view
        used_across_boats |= own_current

    # -----------------------------------------------------------
    # Athlete Profile — full score breakdown + seat fit for every
    # role used in a chosen boat
    # -----------------------------------------------------------
    st.divider()
    with st.expander("👤 Athlete Profile", expanded=False):
        st.caption("Full score breakdown and seat fit for every role used in the focused boat.")

        if visible_boats:
            focus_names = [f"{boat_label_map[b['id']]} focus" for b in visible_boats]
            focus_choice = st.selectbox("Focus boat", focus_names, key="focus_boat_select")
            focus_boat = visible_boats[focus_names.index(focus_choice)]
            focus_seat_map = BOAT_SEAT_MAP[focus_boat["boat_class"]]
            distinct_roles = list(dict.fromkeys(focus_seat_map.values()))  # unique, keeps first-seen order

            profile_options = sorted(pool["rower_name"].tolist()) if len(pool) else []
            profile_name = st.selectbox("Rower", profile_options, key="profile_rower_select") if profile_options else None

            if profile_name:
                prow = pool[pool["rower_name"] == profile_name].iloc[0]
                erg_row = erg_df[erg_df["rower_name"] == profile_name].sort_values("test_date_2k", ascending=False)
                e = erg_row.iloc[0] if len(erg_row) else None

                pc1, pc2 = st.columns(2)
                with pc1:
                    st.markdown("**Raw scores**")
                    for field in SCORE_FIELDS:
                        val = prow.get(field)
                        val = int(val) if pd.notna(val) else 70
                        st.progress(val / 100, text=f"{field.replace('_', ' ').title()}: {val}")
                    if e is not None:
                        st.caption(
                            f"2k {split_label(e['time_2k_sec'] / 4) if pd.notna(e.get('time_2k_sec')) else '—'} · "
                            f"5k {split_label(e['time_5k_sec'] / 10) if pd.notna(e.get('time_5k_sec')) else '—'} · "
                            f"{e['max_watts']:.0f}w peak · {prow['weight']} lb · "
                            f"{prow.get('sweep_side') or '—'} · prefers {prow.get('preferred_seat') or '—'}"
                        )
                    if pd.notna(prow.get("prior_experience")) and prow.get("prior_experience"):
                        st.caption(prow["prior_experience"])
                with pc2:
                    st.markdown(f"**Seat fit — {focus_boat['boat_class']}**")
                    for role in distinct_roles:
                        if len(pool):
                            fits_for_role = compute_fit(pool, role)
                            idx_match = pool[pool["rower_name"] == profile_name].index
                            fval = fits_for_role[idx_match[0]] if len(idx_match) else None
                        else:
                            fval = None
                        fc1, fc2 = st.columns([3, 1])
                        fc1.markdown(role)
                        fc2.markdown(f"**{fval:.1f}**" if fval is not None else "—")
        else:
            st.caption("No boats to inspect yet — add one above.")

    # -----------------------------------------------------------
    # What If? — compare the current seat occupant against an
    # alternate before committing to the swap
    # -----------------------------------------------------------
    with st.expander("🔁 What If?", expanded=False):
        st.caption("Compare the focused boat's current occupant against any eligible rower in this category.")

        if visible_boats:
            seat_display = [f"Seat {s} — {focus_seat_map[s]}" for s in sorted(focus_seat_map)]
            seat_choice = st.selectbox("Seat", seat_display, key="whatif_seat_select") if seat_display else None
            alt_options = sorted(pool["rower_name"].tolist()) if len(pool) else []
            alt_rower = st.selectbox("Alternate rower", alt_options, key="whatif_alt_select") if alt_options else None

            if seat_choice and alt_rower:
                seat_num_sel = int(seat_choice.split()[1])
                role = focus_seat_map[seat_num_sel]
                current_name = focus_boat["seats"].get(seat_num_sel)

                fits_role = compute_fit(pool, role) if len(pool) else pd.Series(dtype=float)

                def _fit_for(name):
                    idx = pool[pool["rower_name"] == name].index
                    return fits_role[idx[0]] if name and len(idx) else None

                current_fit = _fit_for(current_name)
                alt_fit = _fit_for(alt_rower)

                other_seat = next((s for s, n in focus_boat["seats"].items() if n == alt_rower and s != seat_num_sel), None)

                def _boat_avg_fit(seats_dict):
                    vals = []
                    for s, n in seats_dict.items():
                        if n:
                            r = focus_seat_map.get(s)
                            f = compute_fit(pool, r) if r and len(pool) else pd.Series(dtype=float)
                            idx = pool[pool["rower_name"] == n].index
                            if len(idx) and idx[0] in f.index:
                                vals.append(f[idx[0]])
                    return sum(vals) / len(vals) if vals else None

                current_boat_fit = _boat_avg_fit(focus_boat["seats"])
                temp_seats = dict(focus_boat["seats"])
                temp_seats[seat_num_sel] = alt_rower
                if other_seat:
                    temp_seats[other_seat] = current_name
                resulting_fit = _boat_avg_fit(temp_seats)

                wc1, wc2, wc3 = st.columns(3)
                wc1.metric(f"Current: {current_name or 'empty'}", f"Fit {current_fit:.1f}" if current_fit is not None else "—")
                wc2.metric(f"Alternate: {alt_rower}", f"Fit {alt_fit:.1f}" if alt_fit is not None else "—")
                if resulting_fit is not None and current_boat_fit is not None:
                    delta = resulting_fit - current_boat_fit
                    wc3.metric("Resulting boat fit", f"{resulting_fit:.1f}", delta=f"{delta:+.1f}")
                else:
                    wc3.metric("Resulting boat fit", "—")

                if st.button("🔁 Apply swap", key="whatif_apply"):
                    st.session_state["pending_swap"] = {
                        "boat_id": focus_boat["id"], "seat_num": seat_num_sel, "new_name": alt_rower,
                        "other_seat": other_seat, "other_name": current_name,
                    }
                    st.rerun()
        else:
            st.caption("No boats to compare yet — add one above.")

    unavailable_pairs_df = load_unavailable_pairs()
    unavailable_pairs = set(zip(unavailable_pairs_df["regatta"], unavailable_pairs_df["rower_name"]))

    def render_grouped_lineups(df, key_prefix):
        if df.empty:
            st.caption("Nothing saved yet.")
            return
        df = df.copy()
        df["regatta"] = df["regatta"].fillna("(no regatta)")
        for regatta_name, reg_group in df.groupby("regatta", sort=True):
            st.markdown(f"#### {regatta_name}")
            for boat_name, boat_group in reg_group.groupby("boat_name", sort=True):
                c1, c2, c3 = st.columns([4, 1.3, 1])
                c1.markdown(f"**{boat_name}**")

                raw_id = boat_group["regatta_id_raw"].iloc[0]
                rid = int(raw_id) if pd.notna(raw_id) else None
                is_visible = bool(boat_group["is_visible_to_team"].iloc[0])

                new_visible = c2.toggle("Visible to team", value=is_visible, key=f"vis_{key_prefix}_{regatta_name}_{boat_name}")
                if new_visible != is_visible:
                    if rid is not None:
                        run_write("UPDATE Lineups SET is_visible_to_team = ? WHERE boat_name = ? AND regatta_id = ?",
                                   (1 if new_visible else 0, boat_name, rid))
                    else:
                        run_write("UPDATE Lineups SET is_visible_to_team = ? WHERE boat_name = ? AND regatta_id IS NULL",
                                   (1 if new_visible else 0, boat_name))
                    st.rerun()

                if c3.button("🗑 Delete", key=f"del_{key_prefix}_{regatta_name}_{boat_name}"):
                    # Use the ACTUAL regatta_id straight from this group's own rows, not a
                    # name-based re-lookup — that lookup breaks for orphaned lineups whose
                    # regatta was already deleted (they show as "(no regatta)", which never
                    # matches anything, so the delete silently found nothing).
                    if rid is not None:
                        run_write("DELETE FROM Lineups WHERE boat_name = ? AND regatta_id = ?", (boat_name, rid))
                    else:
                        run_write("DELETE FROM Lineups WHERE boat_name = ? AND regatta_id IS NULL", (boat_name,))
                    st.toast(f"Deleted {boat_name} ({regatta_name}).", icon="🗑")
                    st.rerun()

                conflicts = [row["rower_name"] for _, row in boat_group.iterrows()
                             if (regatta_name, row["rower_name"]) in unavailable_pairs]
                if conflicts:
                    st.error(f"⚠ Marked unavailable for {regatta_name} but still in this lineup: {', '.join(sorted(set(conflicts)))}")

                boat_used_name = boat_group["boat_used"].iloc[0] if "boat_used" in boat_group.columns else None
                if pd.notna(boat_used_name) and boat_used_name:
                    st.caption(f"🚣 Boat: {boat_used_name}")

                display_df = boat_group[["seat_number", "side", "rower_name"]].copy()
                display_df["⚠"] = display_df["rower_name"].apply(
                    lambda n: "🔴 unavailable" if (regatta_name, n) in unavailable_pairs else ""
                )
                st.dataframe(display_df, width='stretch', hide_index=True)

    st.divider()
    st.subheader(f"Saved Lineups — {regatta} — {category.title()} {squad.title()} {boat_class_filter}")
    st.caption("Only showing boats matching your current filters above.")
    lineups_df = load_lineups_filtered(regatta, f"{squad.title()} {category.title()} {boat_class_filter}%")
    render_grouped_lineups(lineups_df, "filtered")

    with st.expander("View ALL saved lineups (every regatta, every category)"):
        all_lineups_df = load_all_lineups()
        render_grouped_lineups(all_lineups_df, "all")

with tab5:
    st.title("Regatta Lineups")
    st.caption("Pick a regatta to see every lineup saved for it, read-only — go to Lineup Builder to make changes.")

    st.caption(f"Showing {'Spring (2k)' if season == '2k' else 'Fall (5k)'} regattas — change the season selector above to switch.")

    regattas_view_df = load_regattas()
    if not regattas_view_df.empty:
        regattas_view_df = regattas_view_df[(regattas_view_df["name"] == "Practice") | (regattas_view_df["season"] == season)]
    if not regattas_view_df.empty:
        regattas_view_df["_is_practice"] = regattas_view_df["name"] == "Practice"
        regattas_view_df["_sort_date"] = pd.to_datetime(regattas_view_df["event_date"], errors="coerce")
        regattas_view_df = regattas_view_df.sort_values(
            by=["_is_practice", "_sort_date"], ascending=[False, True], na_position="last"
        ).drop(columns=["_is_practice", "_sort_date"])
    regatta_view_names = regattas_view_df["name"].tolist() if not regattas_view_df.empty else []

    if not regatta_view_names:
        st.info("No regattas yet — add one on the Lineup Builder page.")
    else:
        selected_regatta = st.selectbox("Regatta", regatta_view_names, key="regatta_lineups_select")
        sel_row = regattas_view_df[regattas_view_df["name"] == selected_regatta]
        sel_date = sel_row["event_date"].iloc[0] if not sel_row.empty else None
        if pd.notna(sel_date):
            st.caption(f"Date: {sel_date}")

        view_lineups_df = load_regatta_view_lineups(selected_regatta)

        unavailable_view_df = load_unavailable_for_regatta(selected_regatta)
        unavailable_view_names = set(unavailable_view_df["rower_name"].tolist())

        k1, k2, k3 = st.columns(3)
        k1.metric("Boats", view_lineups_df["boat_name"].nunique() if not view_lineups_df.empty else 0)
        k2.metric("Rowers Assigned", view_lineups_df["rower_name"].nunique() if not view_lineups_df.empty else 0)
        k3.metric("Unavailable Conflicts", len(set(view_lineups_df["rower_name"]) & unavailable_view_names) if not view_lineups_df.empty else 0)

        if view_lineups_df.empty:
            st.info(f"No lineups saved yet for {selected_regatta}.")
        else:
            season_split_field = "time_2k_sec" if season == "2k" else "time_5k_sec"
            season_sort_field = "test_date_2k" if season == "2k" else "test_date_5k"
            latest_erg_view = erg_df.sort_values(season_sort_field).groupby("rower_id").last().reset_index()
            season_erg_view = latest_erg_view[["rower_id", season_split_field, "max_watts"]].rename(columns={season_split_field: "time_2k_sec"})
            rower_full_df = rowers_df.merge(season_erg_view, on="rower_id", how="left")

            def show_squad_boats(gender_key, label):
                st.subheader(label)
                squad_df = view_lineups_df[view_lineups_df["gender"] == gender_key]
                if squad_df.empty:
                    st.caption("No boats yet.")
                    return
                for boat_name, boat_group in squad_df.groupby("boat_name", sort=True):
                    parts = boat_name.split()
                    boat_class = next((p for p in parts if p in BOAT_SEAT_MAP), None)
                    seat_map = BOAT_SEAT_MAP.get(boat_class, {})
                    is_sweep = boat_class in SWEEP_CLASSES

                    with st.container(border=True):
                        st.markdown(f"### {boat_name} — {BOAT_LABELS.get(boat_class, boat_class or '')}")
                        st.caption(f"{len(boat_group)} of {len(seat_map)} seats filled")

                        boat_rowers = rower_full_df[rower_full_df["rower_name"].isin(boat_group["rower_name"])].copy()
                        # Keep rowers even without a test yet this season — see note in Lineup Builder.

                        fits, whys = {}, {}
                        for seat_num, role in seat_map.items():
                            if len(boat_rowers):
                                f, w = compute_fit_and_explain(boat_rowers, role)
                                fits[role] = dict(zip(boat_rowers["rower_name"], f))
                                whys[role] = dict(zip(boat_rowers["rower_name"], w))

                        avg_fit = None
                        fit_values = []
                        for _, row in boat_group.iterrows():
                            role = seat_map.get(row["seat_number"])
                            v = fits.get(role, {}).get(row["rower_name"])
                            if v is not None:
                                fit_values.append(v)
                        if fit_values:
                            avg_fit = sum(fit_values) / len(fit_values)

                        cohesion = boat_cohesion(boat_rowers) if len(boat_rowers) else 100.0
                        makes_better_avg = boat_rowers["makes_boat_better"].fillna(70).mean() if len(boat_rowers) else 70.0
                        split_divisor_view = 4 if season == "2k" else 10
                        avg_split_view = (boat_rowers["time_2k_sec"].mean() / split_divisor_view) if len(boat_rowers) else None

                        s1, s2, s3, s4 = st.columns(4)
                        s1.metric("Boat Fit", f"{avg_fit:.1f}" if avg_fit is not None else "—")
                        s2.metric("Cohesion", f"{cohesion:.0f}")
                        s3.metric("Makes-Better Avg", f"{makes_better_avg:.0f}")
                        s4.metric(f"Avg Split ({'2k' if season == '2k' else '5k'})", split_label(avg_split_view) if avg_split_view is not None else "—")

                        conflicts = [n for n in boat_group["rower_name"] if n in unavailable_view_names]
                        if conflicts:
                            st.error(f"⚠ Marked unavailable for {selected_regatta} but still listed: {', '.join(sorted(set(conflicts)))}")

                        if is_sweep and len(boat_group) == len(seat_map) and len(seat_map) > 0:
                            port_n = (boat_group["side"] == "port").sum()
                            star_n = (boat_group["side"] == "starboard").sum()
                            expected = len(seat_map) // 2
                            if port_n != expected or star_n != expected:
                                st.warning(f"⚠ Side imbalance: {port_n} port / {star_n} starboard — needs {expected} and {expected}.")

                        rows = []
                        for _, row in boat_group.sort_values("seat_number").iterrows():
                            role = seat_map.get(row["seat_number"], "—")
                            fit_val = fits.get(role, {}).get(row["rower_name"])
                            why_val = whys.get(role, {}).get(row["rower_name"], "—")
                            rows.append({
                                "Seat": row["seat_number"],
                                "Role": role,
                                "Rower": row["rower_name"] + (" 🔴" if row["rower_name"] in unavailable_view_names else ""),
                                "Side": row["side"] or "—",
                                "Fit": f"{fit_val:.1f}" if fit_val is not None else "—",
                                "Why": why_val,
                            })
                        seat_table = pd.DataFrame(rows)
                        st.dataframe(seat_table, width='stretch', hide_index=True)

            show_squad_boats("women", "Women")
            show_squad_boats("men", "Men")

with tab6:
    st.title("Team & Calendar")
    st.caption("Post announcements and manage the practice schedule — both show up on the rower-facing site.")

    st.subheader("📅 Calendar")
    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = pd.Timestamp.now().year
        st.session_state["cal_month"] = pd.Timestamp.now().month

    practice_events_df, signup_events_df_cal, regattas_cal_df = load_calendar_sources()

    type_colors = {"water": "#2E7D9A", "erg": "#B8925A", "off": "#8A8177"}
    gender_icon = {"men": "♂", "women": "♀"}
    events_by_date = {}

    gendered_df = load_gendered_assignments_by_date()
    dates_with_assignments = set(gendered_df["event_date"].tolist())

    for _, r in practice_events_df.iterrows():
        if r["event_date"] in dates_with_assignments:
            continue  # Weekly Schedule has more specific (gender-split) info for this day — skip the generic badge
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

    st.divider()
    tc1, tc2 = st.columns(2)

    with tc1:
        st.subheader("📣 Announcements")
        with st.form("new_announcement_form", clear_on_submit=True):
            new_message = st.text_area("New announcement", placeholder="e.g. Bring water bottles tomorrow, forecast is hot.")
            ann_has_expiry = st.checkbox("Auto-hide after a date?")
            ann_expiry = st.date_input("Hide after", value=pd.Timestamp.now().date() + pd.Timedelta(days=7)) if ann_has_expiry else None
            posted = st.form_submit_button("Post")
            if posted and new_message.strip():
                run_write("INSERT INTO Announcements (message, posted_date, expires_date) VALUES (?, ?, ?)",
                           (new_message.strip(), str(pd.Timestamp.now().date()), str(ann_expiry) if ann_expiry else None))
                st.toast("Announcement posted.", icon="📣")
                st.rerun()

        announcements_df = load_announcements()
        if announcements_df.empty:
            st.caption("No announcements yet.")
        else:
            today_str_ann = str(pd.Timestamp.now().date())
            for _, a in announcements_df.iterrows():
                ac1, ac2 = st.columns([5, 1])
                expired = pd.notna(a.get("expires_date")) and a["expires_date"] < today_str_ann
                expiry_note = f" · hides {a['expires_date']}" if pd.notna(a.get("expires_date")) else ""
                strike = "~~" if expired else ""
                ac1.markdown(f"**{a['posted_date']}**{expiry_note} — {strike}{a['message']}{strike}" + (" *(hidden from team)*" if expired else ""))
                if ac2.button("🗑", key=f"del_announce_{a['announcement_id']}"):
                    run_write("DELETE FROM Announcements WHERE announcement_id = ?", (int(a["announcement_id"]),))
                    st.rerun()

    with tc2:
        st.subheader("📅 Practice Calendar")
        with st.form("new_event_form", clear_on_submit=True):
            ev_date = st.date_input("Date")
            ev_type = st.selectbox("Type", ["water", "erg", "off"])
            ev_notes = st.text_input("Notes (optional)", placeholder="e.g. 6am, meet at the boathouse")
            added = st.form_submit_button("Add to Calendar")
            if added:
                run_write("INSERT INTO PracticeEvents (event_date, event_type, notes) VALUES (?, ?, ?)",
                           (str(ev_date), ev_type, ev_notes.strip() or None))
                st.toast("Added to calendar.", icon="📅")
                st.rerun()

        events_df = load_practice_events()
        if events_df.empty:
            st.caption("No practice days scheduled yet.")
        else:
            type_icon = {"water": "🚣 Water", "erg": "🏋️ Erg House", "off": "❌ Off"}
            for _, e in events_df.iterrows():
                ec1, ec2 = st.columns([5, 1])
                label = type_icon.get(e["event_type"], e["event_type"])
                note_text = f" — {e['notes']}" if pd.notna(e.get("notes")) and e.get("notes") else ""
                ec1.markdown(f"**{e['event_date']}** · {label}{note_text}")
                if ec2.button("🗑", key=f"del_event_{e['event_id']}"):
                    run_write("DELETE FROM PracticeEvents WHERE event_id = ?", (int(e["event_id"]),))
                    st.rerun()

    st.divider()
    st.subheader("📝 Sign-Ups")
    st.caption("One-off events with specific time slots rowers can claim — LTR sessions, bannering, tabling, etc. Past events move out of the way automatically.")

    with st.form("new_signup_event_form", clear_on_submit=True):
        sc1, sc2 = st.columns(2)
        su_title = sc1.text_input("Event title", placeholder="e.g. LTR Session, Bannering")
        su_date = sc2.date_input("Date")
        su_has_deadline = st.checkbox("Set a sign-up deadline (can be before the event date)?")
        su_deadline = st.date_input("Sign-ups close after", value=su_date) if su_has_deadline else None
        su_notes = st.text_input("Notes (optional)")
        su_submit = st.form_submit_button("Create Event")
        if su_submit:
            if su_title.strip():
                run_write(
                    "INSERT INTO SignUpEvents (title, event_date, notes, signup_deadline) VALUES (?, ?, ?, ?)",
                    (su_title.strip(), str(su_date), su_notes.strip() or None, str(su_deadline) if su_deadline else None),
                )
                st.toast("Event created — now add time slots below.", icon="📝")
                st.rerun()
            else:
                st.error("Give the event a title.")

    signup_events_df = load_signup_events()
    today_str = str(pd.Timestamp.now().date())

    if signup_events_df.empty:
        st.caption("No sign-up events yet.")
    else:
        upcoming = signup_events_df[signup_events_df["event_date"] >= today_str]
        past = signup_events_df[signup_events_df["event_date"] < today_str]

        def render_signup_event(ev):
            eid = int(ev["event_id"])
            deadline_text = f" · sign-ups close {ev['signup_deadline']}" if pd.notna(ev.get("signup_deadline")) else ""

            with st.container(border=True):
                hcol1, hcol2 = st.columns([5, 1])
                hcol1.markdown(f"**{ev['title']}** — {ev['event_date']}{deadline_text}")
                if hcol2.button("🗑 Event", key=f"del_signup_event_{eid}"):
                    run_write("DELETE FROM SignUpResponses WHERE event_id = ?", (eid,))
                    run_write("DELETE FROM SignUpSlots WHERE event_id = ?", (eid,))
                    run_write("DELETE FROM SignUpEvents WHERE event_id = ?", (eid,))
                    st.rerun()
                if pd.notna(ev.get("notes")) and ev.get("notes"):
                    st.caption(ev["notes"])

                with st.expander("+ Auto-generate time slots"):
                    gc1, gc2, gc3, gc4, gc5 = st.columns(5)
                    gen_start = gc1.time_input("Start time", key=f"gen_start_{eid}")
                    gen_len = gc2.number_input("Slot length (min)", min_value=5, step=5, value=30, key=f"gen_len_{eid}")
                    gen_gap = gc3.number_input("Gap between (min)", min_value=0, step=5, value=0, key=f"gen_gap_{eid}")
                    gen_num = gc4.number_input("How many slots", min_value=1, step=1, value=2, key=f"gen_num_{eid}")
                    gen_spots = gc5.number_input("Spots per slot", min_value=1, step=1, value=2, key=f"gen_spots_{eid}")
                    if st.button("Generate slots", key=f"gen_btn_{eid}"):
                        import datetime as dt_module
                        cur_dt = dt_module.datetime.combine(dt_module.date.today(), gen_start)
                        for _ in range(int(gen_num)):
                            slot_start = cur_dt
                            slot_end = cur_dt + dt_module.timedelta(minutes=int(gen_len))
                            run_write(
                                "INSERT INTO SignUpSlots (event_id, start_time, end_time, max_spots) VALUES (?, ?, ?, ?)",
                                (eid, slot_start.strftime("%H:%M"), slot_end.strftime("%H:%M"), int(gen_spots)),
                            )
                            cur_dt = slot_end + dt_module.timedelta(minutes=int(gen_gap))
                        st.toast(f"Generated {int(gen_num)} slot(s).", icon="🕒")
                        st.rerun()

                slots_df = load_signup_slots(eid)
                if slots_df.empty:
                    st.caption("No time slots yet — use the generator above.")
                else:
                    for _, slot in slots_df.iterrows():
                        sid = int(slot["slot_id"])
                        responses_df = load_slot_responses(sid)
                        names = responses_df["rower_name"].tolist()
                        max_spots = int(slot["max_spots"]) if pd.notna(slot.get("max_spots")) else None
                        spots_text = f"{len(names)}/{max_spots}" if max_spots is not None else f"{len(names)}"
                        st.markdown(f"**{slot['start_time']}–{slot['end_time']}** · {spots_text} spots — {', '.join(names) if names else '*nobody yet*'}")

                        with st.expander(f"Edit {slot['start_time']}–{slot['end_time']}"):
                            ec1, ec2, ec3 = st.columns(3)
                            edit_start = ec1.text_input("Start (HH:MM)", value=slot["start_time"], key=f"edit_start_{sid}")
                            edit_end = ec2.text_input("End (HH:MM)", value=slot["end_time"], key=f"edit_end_{sid}")
                            edit_max = ec3.number_input("Max spots", min_value=1, step=1,
                                                         value=max_spots if max_spots is not None else 2, key=f"edit_max_{sid}")
                            esave, edel = st.columns(2)
                            if esave.button("💾 Save", key=f"save_slot_{sid}"):
                                run_write("UPDATE SignUpSlots SET start_time = ?, end_time = ?, max_spots = ? WHERE slot_id = ?",
                                           (edit_start, edit_end, int(edit_max), sid))
                                st.rerun()
                            if edel.button("🗑 Delete slot", key=f"del_slot_{sid}"):
                                run_write("DELETE FROM SignUpResponses WHERE slot_id = ?", (sid,))
                                run_write("DELETE FROM SignUpSlots WHERE slot_id = ?", (sid,))
                                st.rerun()

        for _, ev in upcoming.iterrows():
            render_signup_event(ev)

        if not past.empty:
            with st.expander(f"Past sign-ups ({len(past)})"):
                for _, ev in past.iterrows():
                    render_signup_event(ev)

    st.divider()
    st.subheader("🚫 Absences")
    st.caption("Rowers mark themselves absent from upcoming practice/regatta days on the team site. Shown here so nothing is a last-minute surprise.")

    settings_df = load_attendance_settings()
    current_deadline_days = int(settings_df["days_before_deadline"].iloc[0]) if not settings_df.empty else 1

    dl1, dl2 = st.columns([1, 3])
    new_deadline_days = dl1.number_input("Must respond at least this many days before", min_value=0, step=1, value=current_deadline_days)
    if new_deadline_days != current_deadline_days:
        if settings_df.empty:
            run_write("INSERT INTO AttendanceSettings (days_before_deadline) VALUES (?)", (int(new_deadline_days),))
        else:
            run_write("UPDATE AttendanceSettings SET days_before_deadline = ?", (int(new_deadline_days),))
        st.rerun()

    absences_df = load_absences()
    today_ts = pd.Timestamp.now().date()
    if absences_df.empty:
        st.caption("No absences marked yet.")
    else:
        upcoming_absences = absences_df[pd.to_datetime(absences_df["event_date"]).dt.date >= today_ts]
        if upcoming_absences.empty:
            st.caption("No upcoming absences.")
        else:
            for event_date, group in upcoming_absences.groupby("event_date"):
                lines = "; ".join(f"{row['rower_name']} ({row['reason'] or 'no reason given'})" for _, row in group.iterrows())
                st.markdown(f"**{event_date}** — {lines}")

with tab7:
    st.title("Weekly Schedule")
    st.caption("Assign each rower to Water or Land per day, plus who's coaching each location. Update this every weekend for the coming week — it shows up on the rower-facing site automatically.")

    week_start = st.date_input("Pick any date in the week you're setting up", value=pd.Timestamp.now().date())
    week_start_dt = pd.Timestamp(week_start)
    monday = week_start_dt - pd.Timedelta(days=week_start_dt.weekday())
    weekdays = [monday + pd.Timedelta(days=i) for i in range(6)]  # Mon-Sat

    men_names = sorted(rowers_df[rowers_df["gender"] == "men"]["rower_name"].tolist()) if not rowers_df.empty else []
    women_names = sorted(rowers_df[rowers_df["gender"] == "women"]["rower_name"].tolist()) if not rowers_df.empty else []

    for day in weekdays:
        date_str = str(day.date())
        with st.expander(f"{day.strftime('%A')} — {date_str}", expanded=False):
            existing = load_daily_assignments(date_str)
            id_to_name = dict(zip(rowers_df["rower_id"], rowers_df["rower_name"])) if not rowers_df.empty else {}
            existing_water = [id_to_name.get(rid) for rid in existing[existing["location"] == "water"]["rower_id"] if rid in id_to_name]
            existing_land = [id_to_name.get(rid) for rid in existing[existing["location"] == "land"]["rower_id"] if rid in id_to_name]
            existing_cox = [id_to_name.get(rid) for rid in existing[(existing["location"] == "water") & (existing["is_coxswain"] == 1)]["rower_id"] if rid in id_to_name]

            st.markdown("**🚣 Water**")
            wm1, wm2 = st.columns(2)
            water_men = wm1.multiselect("Men", men_names, default=[n for n in existing_water if n in men_names], key=f"water_men_{date_str}")
            water_women = wm2.multiselect("Women", women_names, default=[n for n in existing_water if n in women_names], key=f"water_women_{date_str}")
            water_people = water_men + water_women

            st.markdown("**🏋️ Land**")
            lm1, lm2 = st.columns(2)
            land_men = lm1.multiselect("Men", men_names, default=[n for n in existing_land if n in men_names], key=f"land_men_{date_str}")
            land_women = lm2.multiselect("Women", women_names, default=[n for n in existing_land if n in women_names], key=f"land_women_{date_str}")
            land_people = land_men + land_women

            cox_names_from_profile = set(rowers_df[rowers_df["is_coxswain"] == 1]["rower_name"].tolist()) if not rowers_df.empty else set()
            cox_people = st.multiselect("Which of the water group are coxing?", water_people,
                                         default=[n for n in existing_cox if n in water_people], key=f"cox_{date_str}")
            flagged_in_water = [n for n in water_people if n in cox_names_from_profile]
            if flagged_in_water:
                st.caption(f"🎯 Marked as coxswain on their profile: {', '.join(sorted(flagged_in_water))}")

            coaches_df = load_daily_coaches(date_str)
            coach_map = dict(zip(coaches_df["location"], coaches_df["coach_name"]))
            cc1, cc2 = st.columns(2)
            water_coach = cc1.text_input("Water coach", value=coach_map.get("water", ""), key=f"wcoach_{date_str}")
            land_coach = cc2.text_input("Land coach", value=coach_map.get("land", ""), key=f"lcoach_{date_str}")

            if st.button("💾 Save this day", key=f"save_day_{date_str}"):
                run_write("DELETE FROM DailyAssignments WHERE event_date = ?", (date_str,))
                name_to_id = dict(zip(rowers_df["rower_name"], rowers_df["rower_id"])) if not rowers_df.empty else {}
                for name in water_people:
                    run_write("INSERT INTO DailyAssignments (event_date, rower_id, location, is_coxswain) VALUES (?, ?, 'water', ?)",
                               (date_str, int(name_to_id[name]), 1 if name in cox_people else 0))
                for name in land_people:
                    run_write("INSERT INTO DailyAssignments (event_date, rower_id, location, is_coxswain) VALUES (?, ?, 'land', 0)",
                               (date_str, int(name_to_id[name])))
                run_write("INSERT INTO DailyCoaches (event_date, location, coach_name) VALUES (?, 'water', ?) "
                           "ON CONFLICT(event_date, location) DO UPDATE SET coach_name = excluded.coach_name",
                           (date_str, water_coach.strip() or None))
                run_write("INSERT INTO DailyCoaches (event_date, location, coach_name) VALUES (?, 'land', ?) "
                           "ON CONFLICT(event_date, location) DO UPDATE SET coach_name = excluded.coach_name",
                           (date_str, land_coach.strip() or None))
                st.toast(f"Saved {day.strftime('%A')}.", icon="💾")
                st.rerun()

with tab8:
    st.title("Weekly Lineups")
    st.caption("Build actual boat lineups for regular practice days — Monday practice, Tuesday practice, etc. Update this every weekend; rowers see it on the team site. Unlike Lineup Builder, these aren't tied to a regatta.")

    if "pending_wl_swap" in st.session_state:
        swap = st.session_state.pop("pending_wl_swap")
        for seat_num, name in swap["seats"].items():
            st.session_state[f"wl_seat_{swap['key']}_{seat_num}"] = name if name else "— empty —"

    wl_week_start = st.date_input("Pick any date in the week you're building lineups for", value=pd.Timestamp.now().date(), key="wl_week_start")
    wl_week_start_dt = pd.Timestamp(wl_week_start)
    wl_monday = wl_week_start_dt - pd.Timedelta(days=wl_week_start_dt.weekday())
    wl_weekdays = [wl_monday + pd.Timedelta(days=i) for i in range(6)]  # Mon-Sat

    for day in wl_weekdays:
        date_str = str(day.date())
        with st.expander(f"{day.strftime('%A')} — {date_str}", expanded=False):
            wc1, wc2, wc3, wc4 = st.columns(4)
            wl_squad = wc1.selectbox("Squad", ["women", "men"], key=f"wl_squad_{date_str}")
            wl_category = wc2.selectbox("Category", ["varsity", "novice"], key=f"wl_category_{date_str}")
            wl_boat_class = wc3.selectbox("Boat class", list(BOAT_SEAT_MAP.keys()), key=f"wl_class_{date_str}")
            wl_label = wc4.text_input("Boat label", value="A", key=f"wl_label_{date_str}", help="Use B, C, etc. for a second boat of the same class on the same day.")

            boat_name = f"{wl_squad.title()} {wl_category.title()} {wl_boat_class} {wl_label}"
            combo_key = f"{date_str}_{wl_squad}_{wl_category}_{wl_boat_class}_{wl_label}"

            boats_available = load_equipment()
            boats_available = boats_available[boats_available["category"] == "Boat"] if not boats_available.empty else boats_available
            boat_option_names = ["— not assigned —"] + boats_available["name"].tolist() if not boats_available.empty else ["— not assigned —"]

            weight_cap = 160 if wl_squad == "men" else 130
            pool = rowers_df[rowers_df["gender"] == wl_squad].copy()
            if wl_category == "novice":
                pool = pool[pool["experience_level"] == "novice"]
            split_field = "time_2k_sec" if season == "2k" else "time_5k_sec"
            sort_date_field = "test_date_2k" if season == "2k" else "test_date_5k"
            latest_wl = erg_df.sort_values(sort_date_field).groupby("rower_id").last().reset_index()
            season_erg_wl = latest_wl[["rower_id", split_field, "max_watts"]].rename(columns={split_field: "time_2k_sec"})
            pool = pool.merge(season_erg_wl, on="rower_id", how="left")

            seat_map = BOAT_SEAT_MAP[wl_boat_class]
            is_sweep = wl_boat_class in SWEEP_CLASSES

            existing_lineup_df = run_query(
                "SELECT seat_number, side, rower_id, equipment_id FROM Lineups WHERE race_date = ? AND regatta_id IS NULL AND boat_name = ?",
                (date_str, boat_name),
            )
            id_to_name_wl = dict(zip(rowers_df["rower_id"], rowers_df["rower_name"])) if not rowers_df.empty else {}
            existing_seats_wl = {int(row["seat_number"]): id_to_name_wl.get(row["rower_id"]) for _, row in existing_lineup_df.iterrows()}
            existing_sides_wl = {int(row["seat_number"]): row["side"] for _, row in existing_lineup_df.iterrows()}
            existing_equipment_id = int(existing_lineup_df["equipment_id"].iloc[0]) if len(existing_lineup_df) and pd.notna(existing_lineup_df["equipment_id"].iloc[0]) else None
            existing_equipment_name = "— not assigned —"
            if existing_equipment_id is not None and not boats_available.empty:
                match = boats_available[boats_available["equipment_id"] == existing_equipment_id]
                if not match.empty:
                    existing_equipment_name = match["name"].iloc[0]

            selected_boat_name = st.selectbox(
                "🚣 Physical boat used (optional)", boat_option_names,
                index=boat_option_names.index(existing_equipment_name) if existing_equipment_name in boat_option_names else 0,
                key=f"wl_equipment_{combo_key}",
            )

            if st.button("🪄 Auto-fill", key=f"wl_autofill_{combo_key}"):
                if len(pool):
                    suggestion = auto_assign_boat(pool, seat_map, already_taken={})
                    st.session_state["pending_wl_swap"] = {"key": combo_key, "seats": suggestion}
                    if is_sweep:
                        for seat_num in sorted(seat_map.keys()):
                            st.session_state[f"wl_side_{combo_key}_{seat_num}"] = "port" if seat_num % 2 == 1 else "starboard"
                    st.rerun()
                else:
                    st.warning("No eligible rowers with erg scores for this filter yet.")

            seats_now = {}
            sides_now = {}
            for seat_num, role in seat_map.items():
                fit_scores = compute_fit(pool, role) if len(pool) else pd.Series(dtype=float)
                pool_ranked = pool.assign(fit=fit_scores).sort_values("fit", ascending=False) if len(pool) else pool
                options = ["— empty —"] + pool_ranked["rower_name"].tolist()
                current_val = existing_seats_wl.get(seat_num, "— empty —") or "— empty —"
                if current_val not in options:
                    options = options + [current_val]

                cols = st.columns([0.6, 1.4, 2.2, 1, 1.2]) if is_sweep else st.columns([0.6, 1.4, 2.6, 1.4])
                cols[0].markdown(f"**Seat {seat_num}**")
                cols[1].markdown(f"*{role}*")
                chosen = cols[2].selectbox("Rower", options, index=options.index(current_val),
                                            key=f"wl_seat_{combo_key}_{seat_num}", label_visibility="collapsed")
                seats_now[seat_num] = None if chosen == "— empty —" else chosen
                if chosen != "— empty —":
                    fit_row = pool_ranked[pool_ranked["rower_name"] == chosen]
                    fit_val = fit_row["fit"].iloc[0] if len(fit_row) else None
                    cols[3].markdown(f"Fit: **{fit_val:.1f}**" if fit_val is not None else "Fit: —")
                if is_sweep:
                    side_default = existing_sides_wl.get(seat_num, "")
                    side_val = cols[4].selectbox("Side", ["", "port", "starboard"],
                                                  index=["", "port", "starboard"].index(side_default) if side_default in ["", "port", "starboard"] else 0,
                                                  key=f"wl_side_{combo_key}_{seat_num}", label_visibility="collapsed")
                    sides_now[seat_num] = side_val

            if st.button(f"💾 Save {boat_name}", key=f"wl_save_{combo_key}"):
                selected_equipment_id = None
                if selected_boat_name != "— not assigned —" and not boats_available.empty:
                    match = boats_available[boats_available["name"] == selected_boat_name]
                    if not match.empty:
                        selected_equipment_id = int(match["equipment_id"].iloc[0])

                run_write("DELETE FROM Lineups WHERE race_date = ? AND regatta_id IS NULL AND boat_name = ?", (date_str, boat_name))
                name_to_id_wl = dict(zip(rowers_df["rower_name"], rowers_df["rower_id"])) if not rowers_df.empty else {}
                saved = 0
                for seat_num, rower_name in seats_now.items():
                    if not rower_name:
                        continue
                    run_write(
                        "INSERT INTO Lineups (boat_name, race_date, seat_number, side, rower_id, regatta_id, is_visible_to_team, equipment_id) VALUES (?, ?, ?, ?, ?, NULL, 1, ?)",
                        (boat_name, date_str, seat_num, sides_now.get(seat_num, ""), int(name_to_id_wl[rower_name]), selected_equipment_id),
                    )
                    saved += 1
                st.toast(f"Saved {saved} seat(s) for {boat_name}.", icon="💾")
                st.rerun()

with tab9:
    st.title("Equipment")
    st.caption("Track boats, oars, and gear — flag anything broken, and queue up purchase requests for the treasurer to see.")

    CATEGORY_OPTIONS = ["Boat", "Oar", "Rigger", "Erg", "Safety Equipment", "Trailer", "Tools", "Uniform/Apparel", "Other"]
    STATUS_OPTIONS = ["Good", "Needs Repair", "Broken", "Retired"]
    STATUS_COLORS = {"Good": "🟢", "Needs Repair": "🟡", "Broken": "🔴", "Retired": "⚪"}

    eq_tab1, eq_tab2 = st.tabs(["📦 Inventory", "🛒 Purchase Requests"])

    with eq_tab1:
        with st.expander("+ Add equipment"):
            ec1, ec2, ec3, ec4 = st.columns(4)
            eq_name = ec1.text_input("Name", placeholder="e.g. Empacher 8+ #3", key="new_eq_name")
            eq_category = ec2.selectbox("Category", CATEGORY_OPTIONS, key="new_eq_category")
            eq_status = ec3.selectbox("Status", STATUS_OPTIONS, key="new_eq_status")
            eq_qty = ec4.number_input("Quantity", min_value=1, step=1, value=1, key="new_eq_qty")
            eq_notes = st.text_input("Notes (optional)", placeholder="e.g. bow seat cracked, needs new shoes", key="new_eq_notes")
            if st.button("Add to Inventory", type="primary"):
                if eq_name.strip():
                    run_write(
                        "INSERT INTO Equipment (name, category, status, quantity, notes, updated_date) VALUES (?, ?, ?, ?, ?, ?)",
                        (eq_name.strip(), eq_category, eq_status, int(eq_qty), eq_notes.strip() or None, str(pd.Timestamp.now().date())),
                    )
                    for k in ["new_eq_name", "new_eq_category", "new_eq_status", "new_eq_qty", "new_eq_notes"]:
                        st.session_state.pop(k, None)
                    st.toast(f"Added {eq_name.strip()}.", icon="📦")
                    st.rerun()
                else:
                    st.error("Give the item a name.")

        equipment_df = load_equipment()
        if equipment_df.empty:
            st.info("No equipment logged yet — add your first item above.")
        else:
            fc1, fc2 = st.columns(2)
            filter_category = fc1.selectbox("Filter by category", ["All"] + CATEGORY_OPTIONS, key="eq_filter_category")
            filter_status = fc2.selectbox("Filter by status", ["All"] + STATUS_OPTIONS, key="eq_filter_status")

            flagged = equipment_df[equipment_df["status"].isin(["Needs Repair", "Broken"])]
            if not flagged.empty:
                st.warning(f"⚠ {len(flagged)} item(s) need attention: " + ", ".join(f"{STATUS_COLORS[r['status']]} {r['name']}" for _, r in flagged.iterrows()))

            shown = equipment_df.copy()
            if filter_category != "All":
                shown = shown[shown["category"] == filter_category]
            if filter_status != "All":
                shown = shown[shown["status"] == filter_status]

            for _, item in shown.iterrows():
                eid = int(item["equipment_id"])
                with st.container(border=True):
                    ic1, ic2, ic3 = st.columns([3, 1, 1])
                    ic1.markdown(f"**{STATUS_COLORS.get(item['status'], '')} {item['name']}** — {item['category']} · qty {int(item['quantity'])}")
                    new_status = ic2.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(item["status"]), key=f"eq_status_{eid}", label_visibility="collapsed")
                    if ic3.button("🗑 Remove", key=f"eq_del_{eid}"):
                        run_write("DELETE FROM Equipment WHERE equipment_id = ?", (eid,))
                        st.rerun()
                    if pd.notna(item.get("notes")) and item.get("notes"):
                        st.caption(item["notes"])
                    if new_status != item["status"]:
                        run_write("UPDATE Equipment SET status = ?, updated_date = ? WHERE equipment_id = ?",
                                   (new_status, str(pd.Timestamp.now().date()), eid))
                        st.toast(f"{item['name']} marked {new_status}.", icon="🔧")
                        st.rerun()

    with eq_tab2:
        st.caption("Anything the team needs to buy — visible here for the treasurer too.")
        with st.expander("+ Add a purchase request"):
            pc1, pc2, pc3 = st.columns(3)
            pr_item = pc1.text_input("Item needed", placeholder="e.g. New oar set (4x)", key="new_pr_item")
            pr_cost = pc2.number_input("Estimated cost ($, optional)", min_value=0.0, step=10.0, key="new_pr_cost")
            pr_priority = pc3.selectbox("Priority", ["Low", "Medium", "High"], index=1, key="new_pr_priority")
            pr_reason = st.text_area("Reason", placeholder="Why is this needed?", key="new_pr_reason")
            pr_by = st.text_input("Requested by", placeholder="Your name", key="new_pr_by")
            if st.button("Submit Request", type="primary"):
                if pr_item.strip():
                    run_write(
                        "INSERT INTO PurchaseRequests (item_name, reason, estimated_cost, priority, requested_by, requested_date) VALUES (?, ?, ?, ?, ?, ?)",
                        (pr_item.strip(), pr_reason.strip() or None, pr_cost if pr_cost else None, pr_priority, pr_by.strip() or None, str(pd.Timestamp.now().date())),
                    )
                    for k in ["new_pr_item", "new_pr_cost", "new_pr_priority", "new_pr_reason", "new_pr_by"]:
                        st.session_state.pop(k, None)
                    st.toast(f"Requested {pr_item.strip()}.", icon="🛒")
                    st.rerun()
                else:
                    st.error("Give the item a name.")

        requests_df = load_purchase_requests()
        if requests_df.empty:
            st.info("No purchase requests yet.")
        else:
            priority_icon = {"High": "🔴 High", "Medium": "🟡 Medium", "Low": "🟢 Low"}
            status_options_pr = ["Requested", "Approved", "Purchased", "Denied"]
            for _, req in requests_df.iterrows():
                rid = int(req["request_id"])
                with st.container(border=True):
                    rc1, rc2, rc3 = st.columns([3, 1.3, 1])
                    cost_text = f" — ${req['estimated_cost']:.2f}" if pd.notna(req.get("estimated_cost")) else ""
                    rc1.markdown(f"**{req['item_name']}**{cost_text} · {priority_icon.get(req['priority'], req['priority'])}")
                    new_pr_status = rc2.selectbox("Status", status_options_pr, index=status_options_pr.index(req["status"]), key=f"pr_status_{rid}", label_visibility="collapsed")
                    if rc3.button("🗑 Remove", key=f"pr_del_{rid}"):
                        run_write("DELETE FROM PurchaseRequests WHERE request_id = ?", (rid,))
                        st.rerun()
                    meta = []
                    if pd.notna(req.get("requested_by")) and req.get("requested_by"):
                        meta.append(f"Requested by {req['requested_by']}")
                    if pd.notna(req.get("requested_date")):
                        meta.append(str(req["requested_date"]))
                    if meta:
                        st.caption(" · ".join(meta))
                    if pd.notna(req.get("reason")) and req.get("reason"):
                        st.caption(req["reason"])
                    if new_pr_status != req["status"]:
                        run_write("UPDATE PurchaseRequests SET status = ? WHERE request_id = ?", (new_pr_status, rid))
                        st.toast(f"{req['item_name']} marked {new_pr_status}.", icon="🛒")
                        st.rerun()
