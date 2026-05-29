from flask import Blueprint, jsonify, request
from models import db, Facility, Facility_Hours, Rule, Schedule, Admin, User, CheckIn
from insertion_validation import (
    validate_facility, validate_facility_hours, validate_rule,
    validate_schedule, validate_checkin, validate_user, validate_admin
)
from datetime import datetime
import bcrypt

api = Blueprint("api", __name__)

# ─────────────────────────────────────────
# HTTPS STATUS CODES
# ─────────────────────────────────────────
#Success Codes
"""
200 OK - Standard success. Used for GET, PUT, DELETE responses when everything went fine.
201 Created — The request succeeded and created something new. Used for POST responses (e.g. creating a user, check-in, facility).
"""
#Client Error Codes
"""
400 Bad Request — The data sent was invalid, missing, or malformed. In this project it covers things like a missing field, 
wrong type, or a time conflict.
401 Unauthorized — Authentication failed. Used in admin_login when the password is wrong.
403 Forbidden — The caller is authenticated (or known) but isn't allowed to do this. Used when a user tries to cancel someone 
else's check-in.
404 Not Found — The resource doesn't exist. Returned by get_or_404() when a facility ID, check-in ID, etc. isn't in the database.
409 Conflict — The request is valid, but it conflicts with the current state of the database — e.g. trying to create a facility whose ID 
already exists, or registering a username that's taken.
"""
#Server Error Codes
"""
5xx The request failed because of something that went wrong on the server (bugs, crashes, database being down). Flask generates these 
automatically — you don't see them explicitly in routes.py, but they can happen.
"""

# ─────────────────────────────────────────
# FACILITY ROUTES
# ─────────────────────────────────────────

# Get all facilities
@api.route("/facilities", methods=["GET"])
def get_facilities():
    """
    GET /api/facilities

    Return a list of all facilities in the database.

    Returns:
        200: JSON array of facility objects, each containing facility_id,
             name, location, facility_type, managing_office, description,
             map_x, and map_y.
    """
    facilities = Facility.query.all()
    return jsonify([{
        "facility_id":     f.facility_id,
        "name":            f.name,
        "location":        f.location,
        "facility_type":   f.facility_type,
        "managing_office": f.managing_office,
        "description":     f.description,
        "map_x":           f.map_x,
        "map_y":           f.map_y
    } for f in facilities])

# Get one facility by ID
@api.route("/facilities/<facility_id>", methods=["GET"])
def get_facility(facility_id):
    """
    GET /api/facilities/<facility_id>

    Return a single facility by its 8-character ID.

    Args:
        facility_id (str): The 8-character facility ID (e.g. "REC00001").

    Returns:
        200: JSON object with the facility's full details.
        404: If no facility with that ID exists.
    """
    f = db.get_or_404(Facility, facility_id)
    return jsonify({
        "facility_id":     f.facility_id,
        "name":            f.name,
        "location":        f.location,
        "facility_type":   f.facility_type,
        "managing_office": f.managing_office,
        "description":     f.description,
        "map_x":           f.map_x,
        "map_y":           f.map_y
    })

# Get facilities by type (e.g. /facilities/type/court)
@api.route("/facilities/type/<facility_type>", methods=["GET"])
def get_facilities_by_type(facility_type):
    """
    GET /api/facilities/type/<facility_type>

    Return a summary list of all facilities matching the given type.

    Args:
        facility_type (str): The facility type to filter on
                             (e.g. "court", "room", "studio", "outdoor").

    Returns:
        200: JSON array of objects containing facility_id, name, and location.
             Returns an empty array if no facilities match the type.
    """
    facilities = Facility.query.filter_by(facility_type=facility_type).all()
    return jsonify([{
        "facility_id": f.facility_id,
        "name":        f.name,
        "location":    f.location,
    } for f in facilities])

# ─────────────────────────────────────────
# FACILITY HOURS ROUTES
# ─────────────────────────────────────────

# Get hours for a facility
@api.route("/facilities/<facility_id>/hours", methods=["GET"])
def get_hours(facility_id):
    """
    GET /api/facilities/<facility_id>/hours

    Return all operating-hours records for a facility, one entry per day.

    Args:
        facility_id (str): The 8-character facility ID.

    Returns:
        200: JSON array of hours objects, each containing hours_id,
             day_of_week, open_time, and close_time (as "HH:MM:SS" strings).
        404: If no facility with that ID exists.
    """
    db.get_or_404(Facility, facility_id)
    hours = Facility_Hours.query.filter_by(facility_id=facility_id).all()
    return jsonify([{
        "hours_id":    h.hours_id,
        "day_of_week": h.day_of_week,
        "open_time":   str(h.open_time),
        "close_time":  str(h.close_time)
    } for h in hours])

# ─────────────────────────────────────────
# RULES ROUTES
# ─────────────────────────────────────────

# Get rules for a facility
@api.route("/facilities/<facility_id>/rules", methods=["GET"])
def get_rules(facility_id):
    """
    GET /api/facilities/<facility_id>/rules

    Return the rules record for a facility (one record per facility).

    Args:
        facility_id (str): The 8-character facility ID.

    Returns:
        200: JSON object containing rule_id, cost_status, cost_notes,
             reservation_type, group_size_limit, restrictions, and rule_notes.
        404: If no facility or rules record exists for that ID.
    """
    rule = Rule.query.filter_by(facility_id=facility_id).first_or_404()
    return jsonify({
        "rule_id":          rule.rule_id,
        "cost_status":      rule.cost_status,
        "cost_notes":       rule.cost_notes,
        "reservation_type": rule.reservation_type,
        "group_size_limit": rule.group_size_limit,
        "restrictions":     rule.restrictions,
        "rule_notes":       rule.rule_notes
    })

# Check group size eligibility
@api.route("/facilities/<facility_id>/check-group", methods=["GET"])
def check_group(facility_id):
    """
    GET /api/facilities/<facility_id>/check-group?size=<n>

    Check whether a group of the given size is eligible to use a facility
    without renting it.  Per UO policy, groups at or above the facility's
    group_size_limit must rent the space.

    Args:
        facility_id (str): The 8-character facility ID.

    Query params:
        size (int): The number of people in the group.

    Returns:
        200: JSON object with:
             - eligible (bool): True if the group is within the limit.
             - notes (str): The facility's rule_notes.
             - warning (str): Present and non-empty only when eligible is False,
               describing the rental requirement.
        400: If the ``size`` query parameter is missing.
        404: If no rules record exists for that facility.
    """
    group_size = request.args.get("size", type=int)
    rule = Rule.query.filter_by(facility_id=facility_id).first_or_404()

    if group_size is None:
        return jsonify({"error": "Please provide a group size"}), 400

    if rule.group_size_limit and group_size >= rule.group_size_limit:
        return jsonify({
            "eligible": False,
            "warning":  f"Groups of {rule.group_size_limit} or more must rent this space.",
            "notes":    rule.rule_notes
        })
    return jsonify({"eligible": True, "notes": rule.rule_notes})

# ─────────────────────────────────────────
# SCHEDULE ROUTES
# ─────────────────────────────────────────

# Get schedule for a facility on a given day
# e.g. /facilities/REC00001/schedule?day=Monday
@api.route("/facilities/<facility_id>/schedule", methods=["GET"])
def get_schedule(facility_id):
    """
    GET /api/facilities/<facility_id>/schedule?day=<day>

    Return schedule slots for a facility, optionally filtered to a single day.
    Results are ordered by start_time.

    Args:
        facility_id (str): The 8-character facility ID.

    Query params:
        day (str, optional): Day name to filter on (e.g. "Monday"). Omit to
                             return slots for all days.

    Returns:
        200: JSON array of schedule objects, each containing schedule_id,
             day_of_week, start_time, end_time, status, and note.
             Returns an empty array if no slots exist.
    """
    day   = request.args.get("day")
    query = Schedule.query.filter_by(facility_id=facility_id)

    if day:
        query = query.filter_by(day_of_week=day)

    slots = query.order_by(Schedule.start_time).all()
    return jsonify([{
        "schedule_id": s.schedule_id,
        "day_of_week": s.day_of_week,
        "start_time":  str(s.start_time),
        "end_time":    str(s.end_time),
        "status":      s.status,
        "note":        s.note
    } for s in slots])

# ─────────────────────────────────────────
# USER ROUTES
# ─────────────────────────────────────────

# Get all check-ins for a user
@api.route("/users/<int:user_id>/checkins", methods=["GET"])
def get_user_checkins(user_id):
    """
    GET /api/users/<user_id>/checkins

    Return all active check-ins for a given user.

    Args:
        user_id (int): The integer primary key of the user.

    Returns:
        200: JSON array of check-in objects, each containing checkin_id,
             facility_id, day_of_week, start_time, end_time, group_size,
             status, and note.  Only check-ins with status "active" are
             returned.  Returns an empty array if none exist.
    """
    checkins = CheckIn.query.filter_by(
        user_id=user_id,
        status="active"
    ).all()

    return jsonify([{
        "checkin_id":  c.checkin_id,
        "facility_id": c.facility_id,
        "day_of_week": c.day_of_week,
        "start_time":  str(c.start_time),
        "end_time":    str(c.end_time),
        "group_size":  c.group_size,
        "status":      c.status,
        "note":        c.note
    } for c in checkins])

# Register a new user
@api.route("/users", methods=["POST"])
def create_user():
    """
    POST /api/users

    Register a new user account.

    Request body (JSON):
        name    (str): Display name, ≤ 100 characters.
        email   (str): Email address, ≤ 100 characters.

    Returns:
        201: JSON object with a confirmation message and the new user_id.
        400: If any field is missing, incorrectly typed, the user is already 
        registered.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_dict = {
        "name":    data.get("name"),
        "email":   data.get("email")
    }
    if not validate_user(user_dict):
        return jsonify({"error": "Invalid user data — check all fields are present, and the user is not already present"}), 400

    user = User(
        name    = data["name"],
        email   = data["email"]
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created", "user_id": user.user_id}), 201

# ─────────────────────────────────────────
# CHECK-IN ROUTES
# ─────────────────────────────────────────

# Create a check-in
@api.route("/checkins", methods=["POST"])
def create_checkin():
    """
    POST /api/checkins

    Record an informal check-in for a user at a facility.  This is not an
    official reservation — it is a best-effort slot claim that other users
    can see.

    Request body (JSON):
        facility_id (str): The 8-character facility ID.
        user_id     (int): The integer ID of the user checking in.
        day_of_week (str): Day name (e.g. "Monday").
        start_time  (str): Slot start in "HH:MM" format on a 15-min boundary.
        end_time    (str): Slot end in "HH:MM" format on a 15-min boundary.
        group_size  (int): Number of people (≥ 1 and below the facility limit).
        note        (str, optional): Any additional note; defaults to "".

    Returns:
        201: JSON object with a confirmation message and the new checkin_id.
        400: If any required field is missing or invalid, the group is too
             large for a standard check-in, times are not in "HH:MM" format,
             or the slot conflicts with an existing booking or scheduled event.
        404: If the facility or its rules record does not exist.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Parse times up front so the validator receives time objects (it type-checks them)
    try:
        start_time = datetime.strptime(data["start_time"], "%H:%M").time() if "start_time" in data else None
        end_time   = datetime.strptime(data["end_time"],   "%H:%M").time() if "end_time"   in data else None
    except ValueError:
        return jsonify({"error": "Times must be in HH:MM format"}), 400

    # Business rule: check group size against the facility's rules before validating
    # (validate_checkin enforces group_size >= 1 but not the per-facility limit)
    rule = Rule.query.filter_by(facility_id=data.get("facility_id")).first_or_404()
    if rule.group_size_limit and data.get("group_size", 0) >= rule.group_size_limit:
        return jsonify({
            "error":   "Group too large for a standard check-in",
            "warning": f"Groups of {rule.group_size_limit} or more should contact {rule.rule_notes}"
        }), 400

    # Fetch IDs so validate_checkin can confirm the facility and user both exist.
    # validate_checkin also internally calls checkin_conflict (schedule + active
    # check-in overlap check), so no separate conflict call is needed.
    facility_ids     = [f.facility_id for f in Facility.query.all()]
    user_ids         = [u.user_id     for u in User.query.all()]

    # checkin_id=0 is a sentinel (validator checks type int; DB assigns the real PK).
    # note defaults to "" because the validator requires type str; the model stores
    # data.get("note") after validation so the DB column can still be NULL.
    checkin_dict = {
        "checkin_id":  0,
        "facility_id": data.get("facility_id"),
        "user_id":     data.get("user_id"),
        "day_of_week": data.get("day_of_week"),
        "start_time":  start_time,
        "end_time":    end_time,
        "group_size":  data.get("group_size"),
        "status":      "active",
        "note":        data.get("note", "")
    }
    if not validate_checkin(checkin_dict, facility_ids, user_ids, update_checkin=False):
        return jsonify({"error": "Invalid or conflicting check-in data — check all fields are present, correctly typed, and the slot doesn't overlap an existing booking or scheduled event"}), 400

    checkin = CheckIn(
        facility_id = data["facility_id"],
        user_id     = data["user_id"],
        day_of_week = data["day_of_week"],
        start_time  = start_time,
        end_time    = end_time,
        group_size  = data["group_size"],
        status      = "active",
        note        = data.get("note")
    )
    db.session.add(checkin)
    db.session.commit()

    return jsonify({
        "message":    "Check-in recorded",
        "checkin_id": checkin.checkin_id
    }), 201

# Get all active check-ins for a facility on a given day
# e.g. /facilities/REC00001/checkins?day=Monday
@api.route("/facilities/<facility_id>/checkins", methods=["GET"])
def get_facility_checkins(facility_id):
    """
    GET /api/facilities/<facility_id>/checkins?day=<day>

    Return all active check-ins at a facility, optionally filtered to a single
    day.  Results are ordered by start_time.

    Args:
        facility_id (str): The 8-character facility ID.

    Query params:
        day (str, optional): Day name to filter on (e.g. "Monday"). Omit to
                             return check-ins across all days.

    Returns:
        200: JSON array of check-in objects, each containing checkin_id,
             day_of_week, start_time, end_time, group_size, and note.  Only
             check-ins with status "active" are returned.  Returns an empty
             array if none exist.
    """
    day   = request.args.get("day")
    query = CheckIn.query.filter_by(
        facility_id=facility_id,
        status="active"
    )

    if day:
        query = query.filter_by(day_of_week=day)

    checkins = query.order_by(CheckIn.start_time).all()
    return jsonify([{
        "checkin_id":  c.checkin_id,
        "day_of_week": c.day_of_week,
        "start_time":  str(c.start_time),
        "end_time":    str(c.end_time),
        "group_size":  c.group_size,
        "note":        c.note
    } for c in checkins])

# Mark a check-in as completed
@api.route("/checkins/<int:checkin_id>/complete", methods=["PUT"])
def complete_checkin(checkin_id):
    """
    PUT /api/checkins/<checkin_id>/complete

    Mark a check-in as completed.  Only the user who created the check-in
    may complete it.

    Args:
        checkin_id (int): The integer ID of the check-in to complete.

    Request body (JSON):
        user_id (int): The ID of the user attempting the action.

    Returns:
        200: JSON confirmation message.
        400: If the request body is missing or does not contain user_id.
        403: If the user_id does not match the check-in's owner.
        404: If no check-in with that ID exists.
    """
    data    = request.get_json()
    checkin = db.get_or_404(CheckIn, checkin_id)

    if not data or "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    if checkin.user_id != data["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    checkin.status = "completed"
    db.session.commit()
    return jsonify({"message": "Check-in marked as completed"})

# Cancel a check-in
@api.route("/checkins/<int:checkin_id>", methods=["DELETE"])
def cancel_checkin(checkin_id):
    """
    DELETE /api/checkins/<checkin_id>

    Cancel a check-in (sets its status to "cancelled").  Only the user who
    created the check-in may cancel it.

    Args:
        checkin_id (int): The integer ID of the check-in to cancel.

    Request body (JSON):
        user_id (int): The ID of the user attempting the cancellation.

    Returns:
        200: JSON confirmation message.
        400: If the request body is missing or does not contain user_id.
        403: If the user_id does not match the check-in's owner.
        404: If no check-in with that ID exists.
    """
    data    = request.get_json()
    checkin = db.get_or_404(CheckIn, checkin_id)

    if not data or "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    if checkin.user_id != data["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    checkin.status = "cancelled"
    db.session.commit()
    return jsonify({"message": "Check-in cancelled"})

# ─────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────

# Admin login
@api.route("/admin/login", methods=["POST"])
def admin_login():
    """
    POST /api/admin/login

    Authenticate an admin with username and bcrypt-verified password.

    Request body (JSON):
        username (str): The admin's username.
        password (str): The admin's plain-text password (verified against the
                        stored bcrypt hash — never stored itself).

    Returns:
        200: JSON object with a confirmation message and the admin_id.
        400: If the request body is missing or either field is absent.
        401: If the username does not exist or the password is incorrect.
    """
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "username and password are required"}), 400

    admin = Admin.query.filter_by(username=data["username"]).first()

    if not admin or not bcrypt.checkpw(
        data["password"].encode(),
        admin.password_hash.encode()
    ):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "admin_id": admin.admin_id})

# Admin: register a new admin account
@api.route("/admin/register", methods=["POST"])
def create_admin():
    """
    POST /api/admin/register

    Register a new admin account.  The password is bcrypt-hashed before
    storage — plain-text passwords are never persisted.

    Request body (JSON):
        username (str): Desired username, ≤ 50 characters, must be unique.
        password (str): Plain-text password to hash and store.

    Returns:
        201: JSON object with a confirmation message and the new admin_id.
        400: If the request body is missing or any field is invalid.
        409: If the username is already taken.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if Admin.query.filter_by(username=data.get("username")).first():
        return jsonify({"error": "Username already taken"}), 409

    # Hash the password before validation so the validator receives the actual
    # password_hash field (validate_admin checks type str on "password_hash", not "password")
    password_hash = bcrypt.hashpw(
        data["password"].encode(), bcrypt.gensalt()
    ).decode() if "password" in data else None

    # admin_id=0 is a sentinel — the validator only checks type (int), the DB assigns the real PK
    admin_dict = {
        "admin_id":      0,
        "username":      data.get("username"),
        "password_hash": password_hash
    }

    existing_usernames = [a.username for a in Admin.query.all()]
    if not validate_admin(admin_dict, existing_usernames):
        return jsonify({"error": "Invalid admin data — username (≤50 chars) and password are required"}), 400

    admin = Admin(
        username      = data["username"],
        password_hash = password_hash
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"message": "Admin created", "admin_id": admin.admin_id}), 201

# Admin: create a new facility
@api.route("/admin/facilities", methods=["POST"])
def create_facility():
    """
    POST /api/admin/facilities

    Create a new facility record.  map_x and map_y are coerced to float so
    that JSON integers (e.g. ``5``) are accepted alongside float literals.

    Request body (JSON):
        facility_id     (str):   Exactly 8 characters (e.g. "REC00001").
        name            (str):   Facility name, ≤ 100 characters.
        location        (str):   Physical location description, ≤ 100 chars.
        facility_type   (str):   Type label, ≤ 50 characters.
        managing_office (str):   Responsible office name, ≤ 100 characters.
        description     (str):   Free-text description.
        map_x           (float): X coordinate within MAP_X_BOUNDS.
        map_y           (float): Y coordinate within MAP_Y_BOUNDS.

    Returns:
        201: JSON object with a confirmation message and the new facility_id.
        400: If any field is missing, incorrectly typed, or out of bounds.
        409: If a facility with that ID already exists.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Coerce map coords to float — JSON integers (e.g. 5) arrive as int but the
    # validator and DB column both expect float.
    try:
        map_x = float(data["map_x"]) if "map_x" in data else None
        map_y = float(data["map_y"]) if "map_y" in data else None
    except (TypeError, ValueError):
        return jsonify({"error": "map_x and map_y must be numbers"}), 400

    facility_dict = {
        "facility_id":     data.get("facility_id"),
        "name":            data.get("name"),
        "location":        data.get("location"),
        "facility_type":   data.get("facility_type"),
        "managing_office": data.get("managing_office"),
        "description":     data.get("description"),
        "map_x":           map_x,
        "map_y":           map_y
    }
    if db.session.get(Facility, facility_dict["facility_id"]):
        return jsonify({"error": f"Facility {facility_dict['facility_id']} already exists"}), 409

    if not validate_facility(facility_dict):
        return jsonify({"error": "Invalid facility data — check all fields are present and correctly typed"}), 400

    facility = Facility(**facility_dict)
    db.session.add(facility)
    db.session.commit()
    return jsonify({"message": "Facility created", "facility_id": facility.facility_id}), 201

# Admin: update a facility
@api.route("/admin/facilities/<facility_id>", methods=["PUT"])
def update_facility(facility_id):
    """
    PUT /api/admin/facilities/<facility_id>

    Update one or more fields on an existing facility.  Only the fields
    present in the request body are changed; omitted fields keep their current
    values.  The ``facility_id`` itself cannot be changed via this route.

    Args:
        facility_id (str): The 8-character ID of the facility to update.

    Request body (JSON, all fields optional):
        name            (str): Facility name, ≤ 100 characters.
        location        (str): Physical location description, ≤ 100 chars.
        facility_type   (str): Type label, ≤ 50 characters.
        managing_office (str): Responsible office name, ≤ 100 characters.
        description     (str): Free-text description.
        map_x           (float): X coordinate within MAP_X_BOUNDS.
        map_y           (float): Y coordinate within MAP_Y_BOUNDS.

    Returns:
        200: JSON confirmation message.
        400: If the request body is missing.
        404: If no facility with that ID exists.
    """
    f    = db.get_or_404(Facility, facility_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["name", "location", "facility_type",
                  "managing_office", "description", "map_x", "map_y"]:
        if field in data:
            setattr(f, field, data[field])

    db.session.commit()
    return jsonify({"message": f"Facility {facility_id} updated"})

# Admin: add hours for a facility
@api.route("/admin/facilities/<facility_id>/hours", methods=["POST"])
def add_hours(facility_id):
    """
    POST /api/admin/facilities/<facility_id>/hours

    Add an operating-hours record for a facility on a specific day.
    A facility may have one hours record per day of the week.

    Args:
        facility_id (str): The 8-character facility ID.

    Request body (JSON):
        day_of_week (str): Day name (e.g. "Monday"), case-insensitive.
        open_time   (str): Opening time in "HH:MM" format on a 15-min boundary.
        close_time  (str): Closing time in "HH:MM" format on a 15-min boundary,
                           must be strictly after open_time.

    Returns:
        201: JSON object with a confirmation message and the new hours_id.
        400: If any field is missing, times are not in "HH:MM" format, times
             are not on a 15-minute boundary, or close_time ≤ open_time.
        404: If no facility with that ID exists.
    """
    db.get_or_404(Facility, facility_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Parse times up front so the validator receives time objects (it type-checks them)
    try:
        open_time  = datetime.strptime(data["open_time"],  "%H:%M").time() if "open_time"  in data else None
        close_time = datetime.strptime(data["close_time"], "%H:%M").time() if "close_time" in data else None
    except ValueError:
        return jsonify({"error": "Times must be in HH:MM format"}), 400

    if open_time and close_time and close_time <= open_time:
        return jsonify({"error": "close_time must be after open_time"}), 400

    # hours_id=0 is a sentinel — the validator only checks type (int), the DB assigns the real PK
    hours_dict = {
        "hours_id":    0,
        "facility_id": facility_id,
        "day_of_week": data.get("day_of_week"),
        "open_time":   open_time,
        "close_time":  close_time
    }
    if not validate_facility_hours(hours_dict):
        return jsonify({"error": "Invalid hours data — check all fields are present and correctly typed"}), 400

    hours = Facility_Hours(
        facility_id = facility_id,
        day_of_week = data["day_of_week"],
        open_time   = open_time,
        close_time  = close_time
    )
    db.session.add(hours)
    db.session.commit()
    return jsonify({"message": "Hours added", "hours_id": hours.hours_id}), 201

# Admin: update hours for a facility
@api.route("/admin/facilities/<facility_id>/hours/<int:hours_id>", methods=["PUT"])
def update_hours(facility_id, hours_id):
    """
    PUT /api/admin/facilities/<facility_id>/hours/<hours_id>

    Update an existing hours record for a facility.  Only the fields present
    in the request body are changed; omitted fields fall back to their current
    database values.

    Args:
        facility_id (str): The 8-character facility ID — used to verify that
                           the hours record belongs to this facility.
        hours_id    (int): The integer ID of the hours record to update.

    Request body (JSON, all fields optional):
        day_of_week (str): Day name (e.g. "Monday"), case-insensitive.
        open_time   (str): Opening time in "HH:MM" format on a 15-min boundary.
        close_time  (str): Closing time in "HH:MM" format on a 15-min boundary,
                           must be strictly after open_time.

    Returns:
        200: JSON confirmation message.
        400: If the request body is missing, times are not in "HH:MM" format,
             or close_time ≤ open_time.
        404: If the hours record does not exist or does not belong to the
             given facility.
    """
    hours = db.get_or_404(Facility_Hours, hours_id)
    if hours.facility_id != facility_id:
        return jsonify({"error": f"Hours record {hours_id} does not belong to facility {facility_id}"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Fall back to the existing DB value for any field not included in the request
    try:
        open_time  = datetime.strptime(data["open_time"],  "%H:%M").time() if "open_time"  in data else hours.open_time
        close_time = datetime.strptime(data["close_time"], "%H:%M").time() if "close_time" in data else hours.close_time
    except ValueError:
        return jsonify({"error": "Times must be in HH:MM format"}), 400

    if close_time <= open_time:
        return jsonify({"error": "close_time must be after open_time"}), 400

    # Use the real hours_id (not a sentinel) — the validator only checks type (int)
    hours_dict = {
        "hours_id":    hours_id,
        "facility_id": facility_id,
        "day_of_week": data.get("day_of_week", hours.day_of_week),
        "open_time":   open_time,
        "close_time":  close_time
    }
    if not validate_facility_hours(hours_dict, facility_id):
        return jsonify({"error": "Invalid hours data — check all fields are correctly typed"}), 400

    hours.day_of_week = hours_dict["day_of_week"]
    hours.open_time   = open_time
    hours.close_time  = close_time

    db.session.commit()
    return jsonify({"message": f"Hours {hours_id} updated"})

# Admin: create rules for a facility
@api.route("/admin/facilities/<facility_id>/rules", methods=["POST"])
def create_rules(facility_id):
    """
    POST /api/admin/facilities/<facility_id>/rules

    Create the rules record for a facility.  Each facility has at most one
    rules record; use PUT to update an existing one.

    Args:
        facility_id (str): The 8-character facility ID.

    Request body (JSON):
        cost_status      (str): Cost category, ≤ 20 characters
                                (e.g. "free", "paid", "depends").
        cost_notes       (str): Free-text cost details.
        reservation_type (str): Booking type, ≤ 30 characters
                                (e.g. "reservable", "first-come", "drop-in").
        group_size_limit (int): Maximum group size before rental is required
                                (1–250 inclusive).
        restrictions     (str): Free-text use restrictions.
        rule_notes       (str): Additional free-text notes.

    Returns:
        201: JSON object with a confirmation message and the new rule_id.
        400: If any field is missing or incorrectly typed.
        404: If no facility with that ID exists.
        409: If a rules record already exists for this facility.
    """
    db.get_or_404(Facility, facility_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if Rule.query.filter_by(facility_id=facility_id).first():
        return jsonify({"error": f"Rules for {facility_id} already exist — use PUT to update"}), 409

    # rule_id=0 is a sentinel — the validator only checks type (int), the DB assigns the real PK
    rule_dict = {
        "rule_id":          0,
        "facility_id":      facility_id,
        "cost_status":      data.get("cost_status"),
        "cost_notes":       data.get("cost_notes"),
        "reservation_type": data.get("reservation_type"),
        "group_size_limit": data.get("group_size_limit"),
        "restrictions":     data.get("restrictions"),
        "rule_notes":       data.get("rule_notes")
    }
    if not validate_rule(rule_dict):
        return jsonify({"error": "Invalid rule data — check all fields are present and correctly typed"}), 400

    rule = Rule(
        facility_id      = facility_id,
        cost_status      = data["cost_status"],
        cost_notes       = data["cost_notes"],
        reservation_type = data["reservation_type"],
        group_size_limit = data["group_size_limit"],
        restrictions     = data["restrictions"],
        rule_notes       = data["rule_notes"]
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({"message": "Rules created", "rule_id": rule.rule_id}), 201

# Admin: update rules for a facility
@api.route("/admin/facilities/<facility_id>/rules", methods=["PUT"])
def update_rules(facility_id):
    """
    PUT /api/admin/facilities/<facility_id>/rules

    Update one or more fields on the existing rules record for a facility.
    Only the fields present in the request body are changed; omitted fields
    keep their current values.

    Args:
        facility_id (str): The 8-character facility ID.

    Request body (JSON, all fields optional):
        cost_status      (str): Cost category, ≤ 20 characters.
        cost_notes       (str): Free-text cost details.
        reservation_type (str): Booking type, ≤ 30 characters.
        group_size_limit (int): Maximum group size before rental is required.
        restrictions     (str): Free-text use restrictions.
        rule_notes       (str): Additional free-text notes.

    Returns:
        200: JSON confirmation message.
        400: If the request body is missing.
        404: If no rules record exists for this facility.
    """
    rule = Rule.query.filter_by(facility_id=facility_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["cost_status", "cost_notes", "reservation_type",
                  "group_size_limit", "restrictions", "rule_notes"]:
        if field in data:
            setattr(rule, field, data[field])

    db.session.commit()
    return jsonify({"message": f"Rules for {facility_id} updated"})

def cancel_conflicting_checkins(facility_id, day_of_week, start_time, end_time, status):
    """
    Delete active check-ins that overlap a non-open schedule slot.

    Open slots don't block check-ins, so this is a no-op when status is "open".
    Staged deletions are added to the current session but not committed —
    the caller is responsible for committing.

    Args:
        facility_id: The 8-character facility ID.
        day_of_week: Day name string (e.g. "Monday").
        start_time:  Slot start as a datetime.time.
        end_time:    Slot end as a datetime.time.
        status:      The schedule slot's status (e.g. "open", "class", "closed").
    """
    if status == "open":
        return

    conflicting = CheckIn.query.filter(
        CheckIn.facility_id == facility_id,
        CheckIn.day_of_week == day_of_week,
        CheckIn.status      == "active",
        CheckIn.start_time  <  end_time,
        CheckIn.end_time    >  start_time
    ).all()

    for checkin in conflicting:
        db.session.delete(checkin)

# Admin: add a schedule slot
@api.route("/admin/facilities/<facility_id>/schedule", methods=["POST"])
def add_schedule(facility_id):
    """
    POST /api/admin/facilities/<facility_id>/schedule

    Add a recurring weekly schedule slot to a facility.  Slots with a status
    other than "open" (e.g. "class", "closed") block check-ins during their
    time range.  The validator rejects slots that overlap any existing non-open
    slot for the same facility and day.

    Args:
        facility_id (str): The 8-character facility ID.

    Request body (JSON):
        day_of_week (str): Day name (e.g. "Monday"), case-insensitive.
        start_time  (str): Slot start in "HH:MM" format on a 15-min boundary.
        end_time    (str): Slot end in "HH:MM" format, must be after start_time.
        status      (str): Slot type, ≤ 20 characters
                           (e.g. "open", "class", "reserved", "closed").
        note        (str, optional): Free-text note; defaults to "".

    Returns:
        201: JSON object with a confirmation message and the new schedule_id.
        400: If any required field is missing or invalid, times are not in
             "HH:MM" format, end_time ≤ start_time, or the slot conflicts
             with an existing non-open slot.
        404: If no facility with that ID exists.
    """
    db.get_or_404(Facility, facility_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Parse times up front so the validator receives time objects (it type-checks them)
    try:
        start_time = datetime.strptime(data["start_time"], "%H:%M").time() if "start_time" in data else None
        end_time   = datetime.strptime(data["end_time"],   "%H:%M").time() if "end_time"   in data else None
    except ValueError:
        return jsonify({"error": "Times must be in HH:MM format"}), 400

    if start_time and end_time and end_time <= start_time:
        return jsonify({"error": "end_time must be after start_time"}), 400

    # schedule_id=0 is a sentinel — the validator only checks type (int), the DB assigns the real PK.
    # note defaults to "" because the validator requires type str (None would fail the type check);
    # the model stores data.get("note") after validation so the DB column can still be NULL.
    schedule_dict = {
        "schedule_id": 0,
        "facility_id": facility_id,
        "day_of_week": data.get("day_of_week"),
        "start_time":  start_time,
        "end_time":    end_time,
        "status":      data.get("status"),
        "note":        data.get("note", "")
    }
    # validate_schedule internally calls schedule_conflict when update_schedule=False,
    # so no separate conflict check is needed here.
    if not validate_schedule(schedule_dict, update_schedule=False):
        return jsonify({"error": "Invalid or conflicting schedule data — check all fields are present, correctly typed, and the slot doesn't overlap an existing non-open slot"}), 400

    slot = Schedule(
        facility_id = facility_id,
        day_of_week = data["day_of_week"],
        start_time  = start_time,
        end_time    = end_time,
        status      = data["status"],
        note        = data.get("note")
    )
    db.session.add(slot)
    db.session.flush()  # assign slot.schedule_id before committing
    if slot.status != "open":
        cancel_conflicting_checkins(facility_id, data["day_of_week"], start_time, end_time, data["status"])
    db.session.commit()
    return jsonify({"message": "Schedule slot added", "schedule_id": slot.schedule_id}), 201

# Admin: update a schedule slot
@api.route("/admin/facilities/<facility_id>/schedule/<int:schedule_id>", methods=["PUT"])
def update_schedule(facility_id, schedule_id):
    """
    PUT /api/admin/facilities/<facility_id>/schedule/<schedule_id>

    Update an existing schedule slot.  Only the fields present in the request
    body are changed; omitted fields fall back to their current database values.
    The slot's own ID is excluded from the conflict check so it can be updated
    without conflicting with itself.

    Args:
        facility_id (str): The 8-character facility ID — used to verify that
                           the slot belongs to this facility.
        schedule_id (int): The integer ID of the schedule slot to update.

    Request body (JSON, all fields optional):
        day_of_week (str): Day name (e.g. "Monday"), case-insensitive.
        start_time  (str): Slot start in "HH:MM" format on a 15-min boundary.
        end_time    (str): Slot end in "HH:MM" format, must be after start_time.
        status      (str): Slot type, ≤ 20 characters.
        note        (str): Free-text note.

    Returns:
        200: JSON confirmation message.
        400: If the request body is missing, times are not in "HH:MM" format,
             end_time ≤ start_time, or the updated slot conflicts with another
             non-open slot.
        404: If the schedule slot does not exist or does not belong to the
             given facility.
    """
    slot = db.get_or_404(Schedule, schedule_id)
    if slot.facility_id != facility_id:
        return jsonify({"error": f"Schedule slot {schedule_id} does not belong to facility {facility_id}"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Fall back to the existing DB value for any field not included in the request
    try:
        start_time = datetime.strptime(data["start_time"], "%H:%M").time() if "start_time" in data else slot.start_time
        end_time   = datetime.strptime(data["end_time"],   "%H:%M").time() if "end_time"   in data else slot.end_time
    except ValueError:
        return jsonify({"error": "Times must be in HH:MM format"}), 400

    if end_time <= start_time:
        return jsonify({"error": "end_time must be after start_time"}), 400

    # Use the real schedule_id (not a sentinel) — validate_schedule(update_schedule=True)
    # passes it to schedule_conflict as exclude_id so the slot isn't flagged against itself.
    # slot.note can be None (DB NULL), so "or ''" normalises it to str for the validator.
    schedule_dict = {
        "schedule_id": schedule_id,
        "facility_id": facility_id,
        "day_of_week": data.get("day_of_week", slot.day_of_week),
        "start_time":  start_time,
        "end_time":    end_time,
        "status":      data.get("status", slot.status),
        "note":        data.get("note", slot.note or "")
    }
    if not validate_schedule(schedule_dict, update_schedule=True):
        return jsonify({"error": "Invalid or conflicting schedule data — check all fields are correctly typed and the updated slot doesn't overlap an existing non-open slot"}), 400

    slot.day_of_week = schedule_dict["day_of_week"]
    slot.start_time  = start_time
    slot.end_time    = end_time
    slot.status      = schedule_dict["status"]
    slot.note        = data.get("note", slot.note)

    if slot.status != "open":
        cancel_conflicting_checkins(facility_id, schedule_dict["day_of_week"], start_time, end_time, schedule_dict["status"])
    db.session.commit()
    return jsonify({"message": f"Schedule slot {schedule_id} updated"})

# Admin: delete a schedule slot
@api.route("/admin/facilities/<facility_id>/schedule/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(facility_id, schedule_id):
    """
    DELETE /api/admin/facilities/<facility_id>/schedule/<schedule_id>

    Permanently remove a schedule slot from the database.

    Args:
        facility_id (str): The 8-character facility ID — used to verify that
                           the slot belongs to this facility.
        schedule_id (int): The integer ID of the schedule slot to delete.

    Returns:
        200: JSON confirmation message.
        404: If the schedule slot does not exist or does not belong to the
             given facility.
    """
    slot = db.get_or_404(Schedule, schedule_id)
    if slot.facility_id != facility_id:
        return jsonify({"error": f"Schedule slot {schedule_id} does not belong to facility {facility_id}"}), 404

    db.session.delete(slot)
    db.session.commit()
    return jsonify({"message": f"Schedule slot {schedule_id} deleted"})

# Admin: cancel any check-in
@api.route("/admin/checkins/<int:checkin_id>", methods=["DELETE"])
def admin_cancel_checkin(checkin_id):
    """
    DELETE /api/admin/checkins/<checkin_id>

    Cancel any check-in regardless of owner.  This is an admin-only action
    and requires no user_id verification.

    Args:
        checkin_id (int): The integer ID of the check-in to cancel.

    Returns:
        200: JSON confirmation message.
        404: If no check-in with that ID exists.
    """
    checkin        = db.get_or_404(CheckIn, checkin_id)
    checkin.status = "cancelled"
    db.session.commit()
    return jsonify({"message": "Check-in cancelled by admin"})
