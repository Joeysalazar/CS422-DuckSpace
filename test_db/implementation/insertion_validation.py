from models import db, Facility, Facility_Hours, Rule, Schedule, Admin, User, CheckIn
from datetime import datetime, time

# Fields for each object in the database
FACILITY_FIELDS = ["facility_id", "name", "location", "facility_type",
                   "managing_office", "description", "map_x", "map_y"]
FACILITY_HOURS_FIELDS = ["hours_id", "facility_id", "day_of_week", "open_time", "close_time"]
RULE_FIELDS = ["rule_id", "facility_id", "cost_status", "cost_notes",       # Bug fix: missing comma caused "cost_notesreservation_type" string concat
               "reservation_type", "group_size_limit", "restrictions", "rule_notes"]
SCHEDULE_FIELDS = ["schedule_id", "facility_id", "day_of_week", "start_time",
                   "end_time", "status", "note"]
ADMIN_FIELDS = ["admin_id", "username", "password_hash"]
USER_FIELDS = ["name", "email"]
CHECKIN_FIELDS = ["checkin_id", "facility_id", "user_id", "day_of_week",
                  "start_time", "end_time", "group_size", "status", "note"]

# Weekdays
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Bounds are placeholders
MAP_X_BOUNDS = [-10.0, 10.0]
MAP_Y_BOUNDS = [-10.0, 10.0]

# ------------- General Utilities -------------
def clean_fields(db_object: dict) -> None:
    """
    Strip all interior and leading/trailing whitespace from the keys of a
    database-record dict, modifying it in place.

    Keys whose whitespace-free form already matches the original are left
    unchanged.  Useful for normalising user-supplied JSON before field
    validation.

    Args:
        db_object: A dict representing one database record.  Modified in place;
                   nothing is returned.
    """
    for key in list(db_object.keys()):    
        new_key = "".join(key.split())
        if new_key != key:
            db_object[new_key] = db_object.pop(key)    

def verify_time(t: time) -> bool:         
    """
    Return True if ``t`` represents a valid on-the-quarter-hour time slot.

    A valid slot must have:
    - minutes that are a multiple of 15 (0, 15, 30, or 45)
    - seconds == 0
    - microseconds == 0

    This enforces the scheduling convention that all time slots are aligned
    to 15-minute boundaries.

    Args:
        t: A ``datetime.time`` object to validate.

    Returns:
        True if ``t`` is on a 15-minute boundary with no sub-minute
        precision; False otherwise.
    """
    if t.minute % 15 != 0:
        return False
    if t.second != 0:
        return False
    if t.microsecond != 0:
        return False
    return True

# ------------- Facility Validation -------------
def validate_facility(facility: dict) -> bool:
    """
    Validate the fields of a facility record before insertion or update.

    Checks that the dict contains exactly the expected keys
    (``FACILITY_FIELDS``) and that every value satisfies the column
    constraints defined in the database schema:

    - ``facility_id``: 8-character string
    - ``facility_type``: string, ≤ 50 characters
    - ``name``: string, ≤ 100 characters
    - ``location``: string, ≤ 100 characters
    - ``managing_office``: string, ≤ 100 characters
    - ``description``: non-empty string (no length cap)
    - ``map_x``: float within ``MAP_X_BOUNDS``
    - ``map_y``: float within ``MAP_Y_BOUNDS``

    Args:
        facility: Dict representing a facility row.

    Returns:
        True if all fields are valid; False otherwise.
    """
    if sorted(facility.keys()) != sorted(FACILITY_FIELDS):
        return False

    if type(facility["facility_id"]) != str or len(facility["facility_id"]) != 8:
        return False
    if type(facility["facility_type"]) != str or len(facility["facility_type"]) > 50:
        return False
    if type(facility["name"]) != str or len(facility["name"]) > 100:
        return False
    if type(facility["location"]) != str or len(facility["location"]) > 100:
        return False
    if type(facility["managing_office"]) != str or len(facility["managing_office"]) > 100:
        return False
    if type(facility["description"]) != str:
        return False
    if type(facility["map_x"]) != float or facility["map_x"] < MAP_X_BOUNDS[0] or facility["map_x"] > MAP_X_BOUNDS[1]:
        return False
    if type(facility["map_y"]) != float or facility["map_y"] < MAP_Y_BOUNDS[0] or facility["map_y"] > MAP_Y_BOUNDS[1]:
        return False

    return True
# ------------- Facility Hours Validation -------------
def duplicate_facility_hours(facility_hours: dict, exclude_id = None) -> bool:
    """
    Returns true if facility hours object already exists in database
    """
    query = Facility_Hours.query.filter(
        Facility_Hours.facility_id == facility_hours["facility_id"],
        Facility_Hours.day_of_week == facility_hours["day_of_week"]
    )

    if exclude_id is not None:
        query = query.filter(Facility_Hours.facility_id != exclude_id)
    return query.first() is not None

def validate_facility_hours(facility_hours: dict, exclude_id = None) -> bool:
    """
    Validate the fields of a facility_hours record before insertion or update.

    Checks that the dict contains exactly the expected keys
    (``FACILITY_HOURS_FIELDS``) and that every value satisfies the column
    constraints defined in the database schema:

    - ``hours_id``: integer
    - ``facility_id``: 8-character string
    - ``day_of_week``: string matching a valid weekday (case-insensitive)
    - ``open_time``: ``datetime.time`` on a 15-minute boundary
    - ``close_time``: ``datetime.time`` on a 15-minute boundary

    Args:
        facility_hours: Dict representing a facility_hours row.

    Returns:
        True if all fields are valid; False otherwise.
    """
    if sorted(facility_hours.keys()) != sorted(FACILITY_HOURS_FIELDS):
        return False

    if type(facility_hours["hours_id"]) != int:
        return False
    if type(facility_hours["facility_id"]) != str or len(facility_hours["facility_id"]) != 8:
        return False
    if type(facility_hours["day_of_week"]) != str or facility_hours["day_of_week"].lower() not in WEEKDAYS:  # Bug fix: day_of_week was never validated
        return False
    if type(facility_hours["open_time"]) != time or not verify_time(facility_hours["open_time"]):
        return False
    if type(facility_hours["close_time"]) != time or not verify_time(facility_hours["close_time"]):
        return False

    return not duplicate_facility_hours(facility_hours, exclude_id) 

# ------------- Rule Validation -------------
def duplicate_rule(rule: dict) -> bool:
    """
    Checks if a rule for the given facility already exists in the database.
    The rule object is represented as a dictionary.
    """
    query = Rule.query.filter(
        Rule.facility_id == rule["facility_id"]
    )
    return query.first() is not None

def validate_rule(rule: dict) -> bool:
    """
    Validate the fields of a rule record before insertion or update.

    Checks that the dict contains exactly the expected keys
    (``RULE_FIELDS``) and that every value satisfies the column constraints
    defined in the database schema:

    - ``rule_id``: integer
    - ``facility_id``: 8-character string
    - ``cost_status``: string, ≤ 20 characters (e.g. "free", "paid", "depends")
    - ``cost_notes``: string (no length cap)
    - ``reservation_type``: string, ≤ 30 characters (e.g. "reservable", "first-come")
    - ``group_size_limit``: integer between 1 and 250 inclusive
    - ``restrictions``: string (no length cap)
    - ``rule_notes``: string (no length cap)

    Args:
        rule: Dict representing a rules row.

    Returns:
        True if all fields are valid; False otherwise.
    """
    if sorted(rule.keys()) != sorted(RULE_FIELDS):
        return False

    if type(rule["rule_id"]) != int:
        return False
    if type(rule["facility_id"]) != str or len(rule["facility_id"]) != 8:
        return False
    if type(rule["cost_status"]) != str or len(rule["cost_status"]) > 20:
        return False
    if type(rule["cost_notes"]) != str:
        return False
    if type(rule["reservation_type"]) != str or len(rule["reservation_type"]) > 30:
        return False
    if type(rule["group_size_limit"]) != int or rule["group_size_limit"] < 1 or rule["group_size_limit"] > 250:
        return False
    if type(rule["restrictions"]) != str:
        return False
    if type(rule["rule_notes"]) != str:
        return False

    return not duplicate_rule(rule)

# ------------- Schedule Validation -------------
def duplicate_schedule(schedule: dict, exclude_id=None) -> bool:
    """
    Checks if schedule already exists in the database.
    The schedule object is represented as a dictionary.
    """
    query = Schedule.query.filter(
        Schedule.facility_id == schedule["facility_id"],
        Schedule.day_of_week == schedule["day_of_week"],
        Schedule.start_time == schedule["start_time"],
        Schedule.end_time == schedule["end_time"]
    )
    if exclude_id is not None:
        query = query.filter(Schedule.schedule_id != exclude_id)
    return query.first() is not None

def schedule_conflict(facility_id, day_of_week, start_time, end_time, exclude_id=None) -> bool:
    """
    Return True if a non-open schedule slot overlaps the requested time range.

    Queries the ``schedules`` table for any slot whose status is not "open"
    (i.e. a class, reservation, or closure) that overlaps the half-open
    interval [``start_time``, ``end_time``).  Overlap is detected with the
    standard interval test: existing.start < new.end AND existing.end > new.start.

    Args:
        facility_id: The 8-character facility ID to check.
        day_of_week: Day name string (e.g. "Monday") to restrict the search.
        start_time:  Proposed slot start as a ``datetime.time``.
        end_time:    Proposed slot end as a ``datetime.time``.
        exclude_id:  Optional ``schedule_id`` to exclude from the conflict
                     search (used when updating an existing slot so it does
                     not conflict with itself).

    Returns:
        True if a conflicting schedule slot exists; False otherwise.
    """
    query = Schedule.query.filter(
        Schedule.facility_id == facility_id,
        Schedule.day_of_week == day_of_week,
        Schedule.status      != "open",
        Schedule.start_time  <  end_time,
        Schedule.end_time    >  start_time
    )

    if exclude_id:
        query = query.filter(Schedule.schedule_id != exclude_id)

    return query.first() is not None   

def validate_schedule(schedule: dict, update_schedule: bool) -> bool:
    """
    Validate the fields of a schedule record and check for time conflicts.

    Checks that the dict contains exactly the expected keys
    (``SCHEDULE_FIELDS``), that every value satisfies the column constraints,
    and — if the record passes field-level validation — that the slot does not
    conflict with any existing non-open schedule slot for the same facility and
    day.

    Field constraints:
    - ``schedule_id``: integer
    - ``facility_id``: 8-character string
    - ``day_of_week``: valid weekday string, ≤ 10 characters (case-insensitive)
    - ``start_time``: ``datetime.time`` on a 15-minute boundary
    - ``end_time``: ``datetime.time`` on a 15-minute boundary
    - ``status``: string, ≤ 20 characters (e.g. "open", "class", "closed")
    - ``note``: string (no length cap)

    Args:
        schedule:        Dict representing a schedules row.
        update_schedule: If True, the current record's own ``schedule_id`` is
                         excluded from the conflict search so a slot can be
                         updated without conflicting with itself.

    Returns:
        True if all fields are valid and no time conflict exists; False
        otherwise.
    """
    if sorted(schedule.keys()) != sorted(SCHEDULE_FIELDS):
        return False

    if type(schedule["schedule_id"]) != int:
        return False
    if type(schedule["facility_id"]) != str or len(schedule["facility_id"]) != 8:
        return False
    if type(schedule["day_of_week"]) != str or len(schedule["day_of_week"]) > 10 or schedule["day_of_week"].lower() not in WEEKDAYS:
        return False
    if type(schedule["start_time"]) != time or not verify_time(schedule["start_time"]):     
        return False
    if type(schedule["end_time"]) != time or not verify_time(schedule["end_time"]):        
        return False
    if type(schedule["status"]) != str or len(schedule["status"]) > 20:
        return False
    if type(schedule["note"]) != str:
        return False
    
    exclude = schedule["schedule_id"] if update_schedule else None
    if duplicate_schedule(schedule, exclude_id=exclude):
        return False

    if update_schedule:
        return not schedule_conflict(schedule["facility_id"], schedule["day_of_week"], schedule["start_time"], schedule["end_time"], schedule["schedule_id"])
    else:
        return not schedule_conflict(schedule["facility_id"], schedule["day_of_week"], schedule["start_time"], schedule["end_time"])

# ------------- Checkin Validation -------------
def duplicate_checkin(checkin: dict) -> bool:
    """
    Returns true if checkin already exists
    """
    query = CheckIn.query.filter(
        CheckIn.facility_id == checkin["facility_id"],
        CheckIn.day_of_week == checkin["day_of_week"],
        CheckIn.start_time == checkin["start_time"],
        CheckIn.end_time == checkin["end_time"]
    )
    return query.first() is not None

def checkin_conflict(facility_id, day_of_week, start_time, end_time, exclude_id=None) -> bool:
    """
    Returns True if the requested time slot overlaps with either:
    - A schedule slot that isn't open (class, closed etc.)
    - An existing active check-in
    """

    # Check against schedule table (classes, closures etc.)
    sched_conflict = Schedule.query.filter(   
        Schedule.facility_id == facility_id,
        Schedule.day_of_week == day_of_week,
        Schedule.status      != "open",
        Schedule.start_time  <  end_time,
        Schedule.end_time    >  start_time
    ).first()

    if sched_conflict:
        return True

    # Check against existing active check-ins
    query = CheckIn.query.filter(
        CheckIn.facility_id == facility_id,
        CheckIn.day_of_week == day_of_week,
        CheckIn.status      == "active",
        CheckIn.start_time  <  end_time,
        CheckIn.end_time    >  start_time
    )

    if exclude_id:
        query = query.filter(CheckIn.checkin_id != exclude_id)

    return query.first() is not None

def validate_checkin(checkin: dict, facility_ids: list[str], user_ids: list[int], update_checkin: bool) -> bool:
    """
    Validate the fields of a check-in record and check for time conflicts.

    Checks that the dict contains exactly the expected keys
    (``CHECKIN_FIELDS``), that every value satisfies the column constraints,
    that the referenced facility and user already exist, and — if the record
    passes field-level validation — that the slot does not conflict with an
    existing schedule slot or active check-in for the same facility and day.

    Field constraints:
    - ``checkin_id``: integer
    - ``user_id``: integer present in ``user_ids``
    - ``facility_id``: 8-character string present in ``facility_ids``
    - ``day_of_week``: valid weekday string, ≤ 10 characters (case-insensitive)
    - ``start_time``: ``datetime.time`` on a 15-minute boundary
    - ``end_time``: ``datetime.time`` on a 15-minute boundary
    - ``group_size``: integer ≥ 1
    - ``status``: string, ≤ 20 characters (e.g. "active", "completed", "cancelled")
    - ``note``: string (no length cap)

    Args:
        checkin:        Dict representing a checkins row.
        facility_ids:   List of facility ID strings that currently exist in
                        the database.
        user_ids:       List of user ID integers that currently exist in the
                        database.
        update_checkin: If True, the current record's own ``checkin_id`` is
                        excluded from the conflict search so a check-in can
                        be updated without conflicting with itself.

    Returns:
        True if all fields are valid and no time conflict exists; False
        otherwise.
    """
    if sorted(checkin.keys()) != sorted(CHECKIN_FIELDS):
        return False

    if type(checkin["checkin_id"]) != int:
        return False
    if type(checkin["user_id"]) != int or checkin["user_id"] not in user_ids:      # Bug fix: user_id is INTEGER, was checked as str
        return False
    if type(checkin["facility_id"]) != str or len(checkin["facility_id"]) != 8 or checkin["facility_id"] not in facility_ids:
        return False
    if type(checkin["day_of_week"]) != str or len(checkin["day_of_week"]) > 10 or checkin["day_of_week"].lower() not in WEEKDAYS:
        return False
    if type(checkin["start_time"]) != time or not verify_time(checkin["start_time"]):   # Bug fix: missing "not" — same inverted logic as schedule
        return False
    if type(checkin["end_time"]) != time or not verify_time(checkin["end_time"]):       # Bug fix: same inverted logic
        return False
    if type(checkin["group_size"]) != int or checkin["group_size"] < 1:                # Bug fix: group_size was never validated
        return False
    if type(checkin["status"]) != str or len(checkin["status"]) > 20:
        return False
    if type(checkin["note"]) != str:
        return False
    
    if duplicate_checkin(checkin):
        return False
    
    if update_checkin:
        return not checkin_conflict(checkin["facility_id"], checkin["day_of_week"], checkin["start_time"], checkin["end_time"], checkin["checkin_id"])   # Bug fix: was checkin["schedule_id"] — that key doesn't exist
    else:
        return not checkin_conflict(checkin["facility_id"], checkin["day_of_week"], checkin["start_time"], checkin["end_time"])

# ------------- User Validation -------------
def duplicate_user(user: dict) -> bool:
    """
    Returns true if user is duplicate false otherwise.
    """
    query = User.query.filter(
        User.name == user["name"],
        User.email == user["email"]
    )

    return query.first() is not None

def validate_user(user: dict) -> bool:
    """
    Validate the fields of a user record before insertion.

    Checks that the dict contains exactly the expected keys
    (``USER_FIELDS``) and that every value satisfies the column constraints
    defined in the database schema:
    - ``name``: string, ≤ 100 characters
    - ``email``: string, ≤ 100 characters

    Note: ``user_id`` is generated by the database (IDENTITY column) and is
    therefore not included in ``USER_FIELDS`` or validated here.

    Args:
        user:     Dict representing a users row (without ``user_id``).

    Returns:
        True if all fields are valid and user isn't a duplicate.
    """
    if sorted(user.keys()) != sorted(USER_FIELDS):
        return False

    if type(user["name"]) != str or len(user["name"]) > 100:
        return False
    if type(user["email"]) != str or len(user["email"]) > 100:
        return False

    return not duplicate_user(user)

# ------------- Admin Validation -------------
def validate_admin(admin: dict, usernames: list[str]) -> bool:
    """
    Validate the fields of an admin record before insertion or update.

    Checks that the dict contains exactly the expected keys
    (``ADMIN_FIELDS``) and that every value satisfies the column constraints
    defined in the database schema:

    - ``admin_id``: integer
    - ``username``: string, ≤ 50 characters
    - ``password_hash``: non-empty string (bcrypt hash — plain-text passwords
      must never be passed here)

    Args:
        admin: Dict representing an admins row.
        usernames: List of usernames that already exist in the database

    Returns:
        True if all fields are valid; False otherwise.
    """
    if sorted(admin.keys()) != sorted(ADMIN_FIELDS):        
        return False

    if type(admin["admin_id"]) != int:                    
        return False
    if type(admin["username"]) != str or len(admin["username"]) > 50 or admin["username"] in usernames:
        return False
    if type(admin["password_hash"]) != str:                
        return False

    return True
