"""
add_availability_and_attendance.py — one-time script to add:
  - WeeklyAvailability table (standing weekly patterns like "8am Monday class")
  - AttendanceSettings.season_start_date (for computing attendance rate)
  - Regattas.response_deadline (rowers must respond by this date)
  - Availability.reason (why a rower can't attend a regatta)

Run this ONCE from your rowing-app folder:

    python add_availability_and_attendance.py
"""

import libsql

TURSO_DATABASE_URL = "libsql://tamurowing-floandradea.aws-us-east-2.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODcwMjczODcsImlkIjoiMDFhMDEzMjAtOWEwMS03YzcyLWFiMWEtZThjYzAwMjNhOTFhIiwia2lkIjoiQTN1cWNtRXhzZHYweWE0V3kxcmdsZWdsZGxxZWRTU1JuOEluZFJGUWl1MCIsInJpZCI6IjJmYWE4ZDA2LTNiZDgtNDE1OC1hYjBiLTAzYWZmMzQ2YmE3YyJ9.A_SJb8kd9LKJPnWo56pnGnsuJMrX4rxPInT-m9lHj1Vq2m3Uo3Q_LSskOWXMdw4HVDkwMCl4BAh70HlHnKT2Cw"

CREATE_WEEKLY_AVAILABILITY = """
CREATE TABLE IF NOT EXISTS WeeklyAvailability (
    weekly_avail_id INTEGER PRIMARY KEY,
    rower_id INTEGER NOT NULL,
    day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')),
    status VARCHAR(15) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'land_only', 'unavailable')),
    notes TEXT,
    FOREIGN KEY (rower_id) REFERENCES Rowers(rower_id),
    UNIQUE(rower_id, day_of_week)
);
"""

NEW_COLUMNS = [
    ("AttendanceSettings", "season_start_date", "DATE"),
    ("Regattas", "response_deadline", "DATE"),
    ("Availability", "reason", "TEXT"),
]


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main():
    conn = libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    cur = conn.cursor()

    try:
        cur.execute(CREATE_WEEKLY_AVAILABILITY)
        conn.commit()
        print("OK    table ready: WeeklyAvailability")
    except Exception as e:
        print(f"FAIL  WeeklyAvailability -> {e}")

    for table, col_name, col_type in NEW_COLUMNS:
        if column_exists(cur, table, col_name):
            print(f"SKIP  (already exists): {table}.{col_name}")
            continue
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"OK    added: {table}.{col_name}")
        except Exception as e:
            print(f"FAIL  {table}.{col_name} -> {e}")

    print("\nVerifying all tables present:")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for row in cur.fetchall():
        print(" ", row[0])


if __name__ == "__main__":
    main()
