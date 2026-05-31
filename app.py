"""
Duck Space main Flask app.

This file connects the student-facing UI to the backend database models
and API routes. It uses Neon/PostgreSQL when DATABASE_URL is set in .env.
If DATABASE_URL is missing, it falls back to the local SQLite demo database.
"""

from pathlib import Path
import os
import sys
import threading
import webbrowser

from dotenv import load_dotenv
from flask import Flask, render_template, abort


# ---------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------

# Root folder for this project.
BASE_DIR = Path(__file__).resolve().parent

# Kai's backend implementation folder.
BACKEND_DIR = BASE_DIR / "test_db" / "implementation"

# Add backend folder to Python's import path so this root app can import
# Kai's models.py and routes.py files.
sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------
# Backend imports
# ---------------------------------------------------------------------

from models import db, Facility, Rule, Schedule, Facility_Hours, CheckIn
from routes import api


# ---------------------------------------------------------------------
# App and database configuration
# ---------------------------------------------------------------------

# Load environment variables from .env.
# The main one we need is DATABASE_URL for Neon.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Local SQLite fallback. This should only be used if DATABASE_URL is missing.
DB_PATH = BACKEND_DIR / "instance" / "duckspace_demo.db"

app = Flask(__name__)

# Use Neon when DATABASE_URL exists. Otherwise, use the local demo SQLite DB.
app.config["SQLALCHEMY_DATABASE_URI"] = (
    DATABASE_URL or f"sqlite:///{DB_PATH.as_posix()}"
)

# Disable a tracking feature we do not need for this project.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect SQLAlchemy to this Flask app.
db.init_app(app)

# Register Kai's API routes under /api.
app.register_blueprint(api, url_prefix="/api")


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def format_time(value):
    """
    Convert database time values into a cleaner display format.

    The database can return time objects or strings like 06:00:00.
    This helper keeps the UI from showing messy database formatting.
    """
    if value is None:
        return ""

    text = str(value)

    # Remove microseconds if they exist.
    if "." in text:
        text = text.split(".")[0]

    # Shorten HH:MM:SS to HH:MM.
    if len(text) >= 5:
        return text[:5]

    return text


def get_category(facility):
    """
    Give each facility a simple UI category.

    This is mainly for filtering/display. The database has facility_type,
    but the UI also wants broader groups like Recreation or Study.
    """
    facility_type = (facility.facility_type or "").lower()
    location = (facility.location or "").lower()
    office = (facility.managing_office or "").lower()

    if "rec" in location or "rec" in office or facility_type in ["court", "studio"]:
        return "Recreation"

    if "study" in facility_type or "library" in location:
        return "Study"

    if "meeting" in facility_type or "room" in facility_type:
        return "Meeting"

    return "Campus Space"


def get_noise_level(facility):
    """
    Estimate a simple noise label for the UI.

    This is not official data. It helps the current UI keep its
    noise-level filter while the database data is still being expanded.
    """
    facility_type = (facility.facility_type or "").lower()

    if "study" in facility_type or "library" in facility_type:
        return "Quiet"

    if "court" in facility_type or "studio" in facility_type:
        return "Moderate"

    if "outdoor" in facility_type or "field" in facility_type:
        return "Loud"

    return "Moderate"


def get_current_count(facility_id):
    """
    Count the number of people currently checked in for a facility.

    The checkins table stores group_size, so we sum group sizes for
    active check-ins instead of just counting rows.
    """
    active_checkins = CheckIn.query.filter_by(
        facility_id=facility_id,
        status="active"
    ).all()

    total = 0

    for checkin in active_checkins:
        total += checkin.group_size or 0

    return total


def build_space_data(facility):
    """
    Convert a Facility database row into the dictionary format expected
    by the existing Duck Space UI.
    """
    rule = Rule.query.filter_by(facility_id=facility.facility_id).first()

    schedule_rows = Schedule.query.filter_by(
        facility_id=facility.facility_id
    ).all()

    schedule_data = []

    for item in schedule_rows:
        schedule_data.append({
            "day": item.day_of_week,
            "start_time": format_time(item.start_time),
            "end_time": format_time(item.end_time),
            "status": getattr(item, "status", ""),
            "note": getattr(item, "note", "")
        })

    group_size_limit = getattr(rule, "group_size_limit", 5) if rule else 5

    return {
        "facility_id": facility.facility_id,
        "name": facility.name,
        "location": facility.location,
        "facility_type": facility.facility_type,
        "managing_office": facility.managing_office,
        "description": facility.description,
        "map_x": facility.map_x,
        "map_y": facility.map_y,

        # UI fields.
        "category": get_category(facility),
        "noise_level": get_noise_level(facility),
        "current_count": get_current_count(facility.facility_id),
        "group_size_limit": group_size_limit,

        # Rules fields.
        # Neon and the older demo DB may use slightly different rule column names,
        # so getattr() keeps the UI from crashing if one field is missing.
        "fee_type": getattr(rule, "fee_type", "Unknown") if rule else "Unknown",
        "fee_description": getattr(rule, "fee_description", "No fee information listed.") if rule else "No fee information listed.",
        "access_type": getattr(rule, "access_type", "Unknown") if rule else "Unknown",
        "restrictions": getattr(rule, "restrictions", "No restrictions listed.") if rule else "No restrictions listed.",
        "rule_notes": getattr(rule, "rule_notes", "No rule notes listed.") if rule else "No rule notes listed.",

        # Schedule fields.
        "schedule": schedule_data
    }


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------

@app.route("/")
def index():
    """
    Homepage.

    Loads all facilities from the active database and renders them as cards.
    If Neon has more facilities, they should appear here automatically.
    """
    facilities = Facility.query.order_by(Facility.name).all()
    spaces = [build_space_data(facility) for facility in facilities]

    return render_template("index.html", spaces=spaces)


@app.route("/facility/<facility_id>")
def facility_detail(facility_id):
    """
    Facility details page.

    Shows one facility with its rules, hours, schedule, and usage information.
    """
    facility = Facility.query.filter_by(facility_id=facility_id).first()

    if not facility:
        abort(404)

    space = build_space_data(facility)

    hours = Facility_Hours.query.filter_by(
        facility_id=facility_id
    ).order_by(Facility_Hours.day_of_week).all()

    schedules = Schedule.query.filter_by(
        facility_id=facility_id
    ).order_by(Schedule.day_of_week, Schedule.start_time).all()

    rule = Rule.query.filter_by(facility_id=facility_id).first()

    return render_template(
        "facility.html",
        space=space,
        hours=hours,
        schedules=schedules,
        rule=rule,
        format_time=format_time
    )


@app.route("/admin")
def admin():
    """
    Admin preview page.

    This page is currently read-only. It proves that the app can read
    facility records from the backend database.
    """
    facilities = Facility.query.order_by(Facility.name).all()
    spaces = [build_space_data(facility) for facility in facilities]

    return render_template("admin.html", spaces=spaces)


# ---------------------------------------------------------------------
# Run app
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Duck Space starting...")
    print("Database:", "Neon/PostgreSQL" if DATABASE_URL else "Local SQLite demo DB")

    # Flask debug mode starts the app twice because of the reloader.
    # This check makes sure the browser only opens in the real running process.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()

    app.run(debug=True)