"""
checkin_manager.py

Handles creating, cancelling, and looking up check-ins.
Works alongside occupancy_manager.py (expiry + counts).

Check-ins only collect name and group_size — no DuckIDs or
official student data, per project requirements.
"""

from datetime import datetime

# Provides functions to manage check-in lifecycle, including creating new check-ins,
# cancelling existing ones, and fetching check-in data by ID or by facility.
def create_checkin(db_connection, facility_id: str, name: str, group_size: int) -> int | None:
    """
    Insert a new active check-in for a facility.

    Returns the new row's ID, or None if the insert failed.

    Example:
        checkin_id = create_checkin(conn, "REC00001", "Alex", 3)
    """
    if group_size < 1:
        raise ValueError("group_size must be at least 1.")
    if not name or not name.strip():
        raise ValueError("name cannot be empty.")

    cursor = db_connection.cursor()
    cursor.execute(
        """
        INSERT INTO checkins (name, group_size, facility_id, status, timestamp)
        VALUES (?, ?, ?, 'active', ?)
        """,
        (name.strip(), group_size, facility_id, datetime.now()),
    )
    db_connection.commit()
    return cursor.lastrowid


def cancel_checkin(db_connection, checkin_id: int) -> bool:
    """
    Mark a specific check-in as cancelled (manual early check-out).

    Returns True if a row was updated, False if the ID was not found
    or was already inactive.

    Example:
        success = cancel_checkin(conn, 42)
    """
    cursor = db_connection.cursor()
    cursor.execute(
        """
        UPDATE checkins
        SET status = 'cancelled'
        WHERE id = ? AND status = 'active'
        """,
        (checkin_id,),
    )
    db_connection.commit()
    return cursor.rowcount > 0


def get_checkin(db_connection, checkin_id: int) -> dict | None:
    """
    Fetch a single check-in row by ID.

    Returns a dict with keys: id, name, group_size, facility_id, status, timestamp.
    Returns None if not found.

    Example:
        row = get_checkin(conn, 42)
        if row:
            print(row["name"], row["status"])
    """
    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT id, name, group_size, facility_id, status, timestamp
        FROM checkins
        WHERE id = ?
        """,
        (checkin_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "group_size": row[2],
        "facility_id": row[3],
        "status": row[4],
        "timestamp": row[5],
    }


def get_active_checkins(db_connection, facility_id: str) -> list[dict]:
    """
    Return all active check-ins for a facility, most recent first.

    Each item is a dict with: id, name, group_size, timestamp.

    Example:
        rows = get_active_checkins(conn, "REC00001")
        for r in rows:
            print(r["name"], r["group_size"])
    """
    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT id, name, group_size, timestamp
        FROM checkins
        WHERE facility_id = ? AND status = 'active'
        ORDER BY timestamp DESC
        """,
        (facility_id,),
    )
    return [
        {"id": r[0], "name": r[1], "group_size": r[2], "timestamp": r[3]}
        for r in cursor.fetchall()
    ]


# ----------------- PRIVATE LOCAL TEST CODE -----------------
if __name__ == "__main__":
    import sqlite3
    from datetime import timedelta
    from occupancy_manager import get_current_occupancy, expire_old_checkins

    conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("""
        CREATE TABLE checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            group_size INTEGER,
            facility_id TEXT,
            status TEXT,
            timestamp TIMESTAMP
        )
    """)

    print("--- 1. Creating check-ins ---")
    id_a = create_checkin(conn, "REC00001", "Alex", 3)
    id_b = create_checkin(conn, "REC00001", "Jamie", 2)
    print(f"Created check-in IDs: {id_a}, {id_b}")

    print("\n--- 2. Occupancy after check-ins ---")
    print(f"Facility REC00001 occupancy: {get_current_occupancy(conn, 'REC00001')}")  # expect 5

    print("\n--- 3. Cancel one check-in ---")
    success = cancel_checkin(conn, id_a)
    print(f"Cancelled ID {id_a}: {success}")
    print(f"Facility REC00001 occupancy: {get_current_occupancy(conn, 'REC00001')}")  # expect 2

    print("\n--- 4. Fetch a check-in by ID ---")
    row = get_checkin(conn, id_b)
    print(f"Check-in {id_b}: {row}")

    print("\n--- 5. List active check-ins ---")
    active = get_active_checkins(conn, "REC00001")
    print(f"Active check-ins for REC00001: {active}")

    print("\n--- 6. Expire old check-ins ---")
    # Manually age id_b's timestamp to 3 hours ago so expiry picks it up
    three_hours_ago = datetime.now() - timedelta(hours=3)
    conn.execute("UPDATE checkins SET timestamp = ? WHERE id = ?", (three_hours_ago, id_b))
    conn.commit()
    expire_old_checkins(conn, expiration_hours=2)
    print(f"Facility REC00001 occupancy after expiry: {get_current_occupancy(conn, 'REC00001')}")  # expect 0