[README_team_site.md](https://github.com/user-attachments/files/32135984/README_team_site.md)
# TAMU Rowing — Team Site

The rower-facing companion to the coach dashboard — a read-only window into schedules, lineups, and team info, kept intentionally simple and safe to share with the whole team.

**🔗 Live app:** *https://tamurowingteam.streamlit.app/*

**Access:** password-protected (rowyourboat) — this repo is public, but the site itself isn't

## What this is

Everything here is entered by coaches on the [coach dashboard](../rowing-app) and shows up here automatically — rowers never edit anything coaches manage, and coaches never edit anything rowers submit here. The two apps share one Turso database, updating in near real time.

**Deliberately excluded:** coach-assessed scores, weight, and any other data that shouldn't be broadcast to the whole team.

## Features

### Weekly Schedule

This week's Water/Land assignments, split by squad, with coxswains flagged and each location's coach named.

### Lineups

Two sources, both collapsible by regatta/day so it's easy to find the one you're looking for:

* **This Week's Practice Lineups** — boat assignments for regular practice days, automatically limited to the current week onward (past ones roll off)
* **Regatta Lineups** — saved lineups for upcoming regattas, filtered to the selected season

### Roster

Full team list split by squad, with contact info (phone/email) where a rower has provided it.

### Announcements

Coach posts, newest first. Auto-hides once a coach sets an expiration date on one.

### Availability

* **Standing Weekly Availability** — set once at the start of the semester (e.g. "land only on Mondays, 8am class"). Coaches see this as a reference when scheduling.
* **Day-by-day absence calendar** — click a day to mark yourself out, add a reason inline, save. Days too close to the deadline (coach-configurable) lock automatically so nothing's a last-minute surprise. Practice is assumed every day except Sunday unless a coach says otherwise.
* **Regatta Attendance** — mark yourself unable to attend a specific regatta with a reason, before that regatta's response deadline.

### Calendar

Visual month view combining practice days, sign-ups, and regattas — color-coded, and split by gender (♂/♀) once a day has Weekly Schedule assignments.

### Sign-Ups

Claim a specific time slot for one-off events (bannering, LTR sessions, etc.) — each slot has its own capacity, so it's clear when something's full.

## Tech Stack

`Python` · `Streamlit` · `Turso (libSQL)` — same database as the coach app, no separate backend

## Setup

1. `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` with:

```toml
   TURSO\_DATABASE\_URL = "libsql://your-db.turso.io"
   TURSO\_AUTH\_TOKEN = "your-token"
   TEAM\_PASSWORD = "your-chosen-password"
   ```

   (same Turso credentials as the coach app — this site reads from the identical database)

3. `streamlit run team\_view.py`

## Why a separate app?

Streamlit Community Cloud allows only one *private* app per account on the free tier. Since this site has no sensitive data (no scores, no coach-only tools), it lives in its own public repo so it can be deployed as a second, independent app — while the coach dashboard stays in a private repo.

