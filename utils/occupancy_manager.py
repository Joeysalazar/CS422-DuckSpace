"""
occupancy_manager.py

This module provides functions to manage occupancy data, including expiring old check-ins
 and calculating current occupancy for facilities. It interacts with the 'checkins' table in the database, 
 which should have the following schema: 
    - id (INTEGER PRIMARY KEY AUTOINCREMENT)
    - name (TEXT)
    - group_size (INTEGER)
    - facility_id (TEXT)
    - status (TEXT) -- e.g., 'active', 'cancelled', 'expired'
    - timestamp (TEXT or TIMESTAMP)

Functions:
- expire_old_checkins(db_connection, expiration_hours=2): Marks check-ins as 'expired' if they are older than the specified number of hours.
- get_current_occupancy(db_connection, facility_id): Returns the total number of people currently checked in (active) for a given facility.

"""

import sqlite3
from datetime import datetime, timedelta

# Provides functions to manage occupancy data, including expiring old check-ins 
# and calculating current occupancy for facilities.
def expire_old_checkins(db_connection, expiration_hours=2):
    cursor = db_connection.cursor()
    
    # Calculate the cutoff time (e.g., 2 hours ago)
    cutoff_time = datetime.now() - timedelta(hours=expiration_hours)
    
    # Update rows that match criteria
    cursor.execute("""
        UPDATE checkins 
        SET status = 'expired' 
        WHERE status = 'active' AND timestamp < ?
    """, (cutoff_time,))
    
    db_connection.commit()
    print(f"Cleanup complete. Rows updated: {cursor.rowcount}")

# Calculates the current occupancy for a given facility by summing the group sizes of all active check-ins.
def get_current_occupancy(db_connection, facility_id):
    cursor = db_connection.cursor()
    
    cursor.execute("""
        SELECT SUM(group_size) 
        FROM checkins 
        WHERE facility_id = ? AND status = 'active'
    """, (facility_id,))
    
    result = cursor.fetchone()[0]
    
    return result if result is not None else 0



# ----------------- PRIVATE LOCAL TEST CODE -----------------
if __name__ == "__main__":

    mock_db = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = mock_db.cursor()
    
    
    cursor.execute("""
        CREATE TABLE checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            group_size INTEGER,
            facility_id INTEGER,
            status TEXT,
            timestamp TIMESTAMP
        )
    """)
    
    now = datetime.now()
    three_hours_ago = now - timedelta(hours=3)
    

    cursor.execute("INSERT INTO checkins (name, group_size, facility_id, status, timestamp) VALUES (?, ?, ?, ?, ?)", 
                   ("Recent Group A", 2, 101, "active", now))
    cursor.execute("INSERT INTO checkins (name, group_size, facility_id, status, timestamp) VALUES (?, ?, ?, ?, ?)", 
                   ("Recent Group B", 3, 101, "active", now))
    cursor.execute("INSERT INTO checkins (name, group_size, facility_id, status, timestamp) VALUES (?, ?, ?, ?, ?)", 
                   ("Expired Group", 4, 101, "active", three_hours_ago))
    mock_db.commit()
    
    print("--- 1. Testing Occupancy Count Before Cleanup ---")
    print(f"Total people counted in Facility 101: {get_current_occupancy(mock_db, 101)}") 

    print("\n--- 2. Running Cleanup Engine ---")
    expire_old_checkins(mock_db, expiration_hours=2)
    
    print("\n--- 3. Testing Occupancy Count After Cleanup ---")
    print(f"Total people counted in Facility 101: {get_current_occupancy(mock_db, 101)}")
