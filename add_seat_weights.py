"""
add_seat_weights.py — one-time script to create the SeatWeights table on your
LIVE Turso database, and seed it with the formula's current values (so nothing
changes until a coach actually edits something in the app).

Run this ONCE from your rowing-app folder:

    python add_seat_weights.py
"""

import libsql

TURSO_DATABASE_URL = "PASTE_YOUR_libsql://... URL HERE"
TURSO_AUTH_TOKEN = "PASTE_YOUR_AUTH_TOKEN HERE"

CREATE_SEAT_WEIGHTS = """
CREATE TABLE IF NOT EXISTS SeatWeights (
    seat_weight_id INTEGER PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    factor VARCHAR(30) NOT NULL,
    weight REAL NOT NULL,
    UNIQUE(role, factor)
);
"""

DEFAULT_SEAT_WEIGHTS = {
    "Bow":    {"technical": .25, "balance": .20, "consistency": .15, "rhythm": .15, "boat_moving": .10, "split2k": .10, "reliability": .05},
    "2-Seat": {"technical": .20, "rhythm": .20, "boat_moving": .20, "consistency": .15, "split2k": .15, "balance": .10},
    "Engine": {"split2k": .30, "boat_moving": .20, "watts": .15, "technical": .15, "consistency": .10, "rhythm": .10},
    "7-Seat": {"split2k": .25, "boat_moving": .20, "rhythm": .20, "technical": .15, "consistency": .10, "pressure": .10},
    "Stroke": {"rhythm": .25, "technical": .20, "consistency": .15, "rating_control": .15, "pressure": .10, "split2k": .10, "coachability": .05},
    "Single": {"split2k": .30, "watts": .15, "technical": .15, "rhythm": .15, "consistency": .15, "pressure": .10},
}


def main():
    conn = libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    cur = conn.cursor()

    try:
        cur.execute(CREATE_SEAT_WEIGHTS)
        conn.commit()
        print("OK    table ready: SeatWeights")
    except Exception as e:
        print(f"FAIL  SeatWeights -> {e}")
        return

    cur.execute("SELECT COUNT(*) FROM SeatWeights")
    if cur.fetchone()[0] == 0:
        for role, factors in DEFAULT_SEAT_WEIGHTS.items():
            for factor, weight in factors.items():
                cur.execute("INSERT INTO SeatWeights (role, factor, weight) VALUES (?, ?, ?)", (role, factor, weight))
        conn.commit()
        print("OK    seeded default formula values")
    else:
        print("SKIP  SeatWeights already has data — leaving your existing values alone")

    print("\nVerifying:")
    cur.execute("SELECT role, factor, weight FROM SeatWeights ORDER BY role, factor")
    for row in cur.fetchall():
        print(" ", row)


if __name__ == "__main__":
    main()
