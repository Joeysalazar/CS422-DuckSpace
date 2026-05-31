"""
facility_manager.py

Facility-level helpers: capacity checks, busyness labels, and
open/closed status based on hours stored in the database.

Depends on:
  - occupancy_manager.get_current_occupancy()
  - The `facilities`, `rules`, and `facility_hours` tables
    that Kai's schema defines and Robert's seed script populates.
"""

from datetime import datetime
from occupancy_manager import get_current_occupancy


# ---------------------------------------------------------------------------
# Capacity helpers
# ---------------------------------------------------------------------------

def get_group_size_limit(db_connection, facility_id: str) -> int | None:
    """
    Return the group_size_limit for a facility from the rules table.
    Returns None if no rule row exists for this facility.

    Example:
        limit = get_group_size_limit(conn, "REC00001")
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT group_size_limit FROM rules WHERE facility_id = ?",
        (facility_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def is_at_capacity(db_connection, facility_id: str) -> bool:
    """
    Return True if current active occupancy meets or exceeds the group size limit.
    Returns False if the facility has no limit set (treated as unlimited).

    Example:
        if is_at_capacity(conn, "REC00001"):
            print("Space is full.")
    """
    limit = get_group_size_limit(db_connection, facility_id)
    if limit is None:
        return False
    current = get_current_occupancy(db_connection, facility_id)
    return current >= limit


def get_busyness_label(db_connection, facility_id: str) -> str:
    """
    Return a human-readable busyness label based on how full the space is.

    Labels:
        "Empty"      — 0 people checked in
        "Light"      — up to 33% of limit
        "Moderate"   — 34–66% of limit
        "Busy"       — 67–99% of limit
        "At Capacity"— at or over limit
        "Unknown"    — no limit data available

    Example:
        label = get_busyness_label(conn, "REC00001")
        print(f"Current busyness: {label}")
    """
    limit = get_group_size_limit(db_connection, facility_id)
    current = get_current_occupancy(db_connection, facility_id)

    if current == 0:
        return "Empty"
    if limit is None:
        return "Unknown"

    ratio = current / limit
    if ratio >= 1.0:
        return "At Capacity"
    if ratio >= 0.67:
        return "Busy"
    if ratio >= 0.34:
        return "Moderate"
    return "Light"


# ---------------------------------------------------------------------------
# Hours helpers
# ---------------------------------------------------------------------------

# Maps Python's weekday() (0=Monday) to the day strings used in the DB
_WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


def is_open_now(db_connection, facility_id: str, now: datetime | None = None) -> bool:
    """
    Return True if the facility has an hours row for today whose
    open_time <= current time < close_time.

    Pass `now` explicitly in tests; defaults to datetime.now().

    Example:
        if is_open_now(conn, "REC00001"):
            print("Currently open.")
    """
    if now is None:
        now = datetime.now()

    day_name = _WEEKDAY_NAMES[now.weekday()]
    current_time = now.time()

    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT open_time, close_time
        FROM facility_hours
        WHERE facility_id = ? AND day_of_week = ?
        """,
        (facility_id, day_name),
    )
    row = cursor.fetchone()
    if row is None:
        return False  # No hours on file for today = treat as closed

    open_time, close_time = row

    # Hours may come back as strings ("HH:MM:SS") or time objects
    # depending on sqlite3 detect_types setting — normalise both.
    if isinstance(open_time, str):
        from datetime import time as dt_time
        parts = open_time.split(":")
        open_time = dt_time(int(parts[0]), int(parts[1]))
    if isinstance(close_time, str):
        from datetime import time as dt_time
        parts = close_time.split(":")
        close_time = dt_time(int(parts[0]), int(parts[1]))

    return open_time <= current_time < close_time


def get_todays_hours(db_connection, facility_id: str, now: datetime | None = None) -> dict | None:
    """
    Return today's open/close times for a facility as a dict, or None if
    the facility has no hours entry for today.

    Return format: {"day": "Monday", "open": "08:00", "close": "22:00"}

    Example:
        hours = get_todays_hours(conn, "REC00001")
        if hours:
            print(f"Open {hours['open']} – {hours['close']}")
    """
    if now is None:
        now = datetime.now()

    day_name = _WEEKDAY_NAMES[now.weekday()]

    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT open_time, close_time
        FROM facility_hours
        WHERE facility_id = ? AND day_of_week = ?
        """,
        (facility_id, day_name),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    # Normalise to "HH:MM" strings regardless of how sqlite3 returns them
    def _fmt(t) -> str:
        if isinstance(t, str):
            return t[:5]  # "HH:MM:SS" → "HH:MM"
        return t.strftime("%H:%M")

    return {"day": day_name, "open": _fmt(row[0]), "close": _fmt(row[1])}


# ---------------------------------------------------------------------------
# Snapshot helper (useful for API routes)
# ---------------------------------------------------------------------------

def get_facility_status_snapshot(db_connection, facility_id: str) -> dict:
    """
    Return a single dict summarising current status for a facility.
    Designed to be dropped straight into a JSON API response.

    Keys:
        facility_id, current_occupancy, group_size_limit,
        busyness_label, is_at_capacity, is_open_now, todays_hours

    Example:
        snapshot = get_facility_status_snapshot(conn, "REC00001")
        # → {"facility_id": "REC00001", "current_occupancy": 3, ...}
    """
    return {
        "facility_id": facility_id,
        "current_occupancy": get_current_occupancy(db_connection, facility_id),
        "group_size_limit": get_group_size_limit(db_connection, facility_id),
        "busyness_label": get_busyness_label(db_connection, facility_id),
        "is_at_capacity": is_at_capacity(db_connection, facility_id),
        "is_open_now": is_open_now(db_connection, facility_id),
        "todays_hours": get_todays_hours(db_connection, facility_id),
    }


# ----------------- PRIVATE LOCAL TEST CODE -----------------
if __name__ == "__main__":
    import sqlite3
    from datetime import time, timedelta

    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, group_size INTEGER,
            facility_id TEXT, status TEXT, timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE rules (
            facility_id TEXT PRIMARY KEY,
            group_size_limit INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE facility_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_id TEXT,
            day_of_week TEXT,
            open_time TEXT,
            close_time TEXT
        )
    """)

    conn.execute("INSERT INTO rules VALUES ('REC00001', 10)")

    # Add hours for every day of the week for easy testing
    for day in _WEEKDAY_NAMES:
        conn.execute(
            "INSERT INTO facility_hours (facility_id, day_of_week, open_time, close_time) VALUES (?,?,?,?)",
            ("REC00001", day, "08:00", "22:00"),
        )

    # Add 3 active check-ins (total group size = 7)
    now_str = datetime.now().isoformat()
    for name, size in [("Alex", 3), ("Jamie", 2), ("Sam", 2)]:
        conn.execute(
            "INSERT INTO checkins (name, group_size, facility_id, status, timestamp) VALUES (?,?,?,?,?)",
            (name, size, "REC00001", "active", now_str),
        )
    conn.commit()

    print("--- Capacity helpers ---")
    print(f"Group size limit:  {get_group_size_limit(conn, 'REC00001')}")   # 10
    print(f"Current occupancy: {get_current_occupancy(conn, 'REC00001')}") # 7
    print(f"At capacity:       {is_at_capacity(conn, 'REC00001')}")         # False
    print(f"Busyness label:    {get_busyness_label(conn, 'REC00001')}")     # Busy

    print("\n--- Hours helpers ---")
    print(f"Open now:          {is_open_now(conn, 'REC00001')}")
    print(f"Today's hours:     {get_todays_hours(conn, 'REC00001')}")

    print("\n--- Status snapshot ---")
    import json
    print(json.dumps(get_facility_status_snapshot(conn, "REC00001"), indent=2, default=str))