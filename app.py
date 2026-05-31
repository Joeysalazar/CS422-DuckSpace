"""
File: app.py
Purpose:
    Main Flask application for Duck Space.

    This file connects the frontend UI to the backend database/API work.
    The homepage still uses the existing card layout, but the facility data
    now comes from the SQLite database instead of the old hardcoded mock list.

System:
    Duck Space is a CS 422 student project that helps users compare campus
    spaces by rules, schedule notes, group-size limits, and next steps.

Authors:
    Initial UI: Joey Salazar
    Backend/API files: Kai Hogan/team backend work
    Integration update: Joey Salazar

Last updated:
    May 2026
"""

from pathlib import Path
import os
import sys
import threading
import webbrowser

from flask import Flask, render_template, abort


# ---------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------

# BASE_DIR points to the main project folder: duck-space/
BASE_DIR = Path(__file__).resolve().parent

# BACKEND_DIR points to Kai's backend/API folder.
# This lets the root app reuse the backend models and routes.
BACKEND_DIR = BASE_DIR / "test_db" / "implementation"

# DB_PATH points to the working local SQLite demo database.
# For now, we are using SQLite because the Neon database is not seeded yet.
DB_PATH = BACKEND_DIR / "instance" / "duckspace_demo.db"


# ---------------------------------------------------------------------
# Backend imports
# ---------------------------------------------------------------------

# Add the backend folder to Python's import path.
# Without this, the root app would not know where models.py and routes.py are.
sys.path.insert(0, str(BACKEND_DIR))

# Import the database object, database tables, and API routes from the backend.
from models import db, Facility, Rule, Schedule, Facility_Hours, CheckIn
from routes import api


# ---------------------------------------------------------------------
# Flask app setup
# ---------------------------------------------------------------------

# Create the Flask application.
app = Flask(__name__)

# Tell Flask-SQLAlchemy to use the local SQLite database.
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH.as_posix()}"

# Disable a Flask-SQLAlchemy tracking feature that is not needed for this project.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect the database object to this Flask app.
db.init_app(app)

# Register Kai's API routes under /api.
# Example: /api/facilities
app.register_blueprint(api, url_prefix="/api")


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def format_time(value):
    """
    Convert a database time value into a cleaner display string.

    Example:
        06:00:00.000000 becomes 6:00 AM
        22:45:00.000000 becomes 10:45 PM
    """

    # If the database has no time value, show a safe message.
    if value is None:
        return "Unknown"

    # Convert the database value to text so it can be cleaned up.
    text = str(value)

    # Remove microseconds if they are included.
    # Example: 06:00:00.000000 becomes 06:00:00
    if "." in text:
        text = text.split(".")[0]

    # Split the time into hour/minute/second pieces.
    parts = text.split(":")

    # If the time has at least hour and minute values, format it nicely.
    if len(parts) >= 2:
        hour = int(parts[0])
        minute = int(parts[1])

        # Decide whether the time is AM or PM.
        suffix = "AM" if hour < 12 else "PM"

        # Convert 24-hour time to 12-hour time.
        display_hour = hour % 12

        # In 12-hour time, 0 should display as 12.
        if display_hour == 0:
            display_hour = 12

        return f"{display_hour}:{minute:02d} {suffix}"

    # If the value was not in the expected format, return it as-is.
    return text


def get_noise_level(facility_type):
    """
    Estimate the noise level for a facility.

    The current backend database does not store noise_level yet.
    This keeps the UI working without changing the schema right now.
    """

    # Rec courts and studios are usually moderate noise spaces.
    if facility_type == "Studio":
        return "Moderate"

    if facility_type == "Court":
        return "Moderate"

    # This is included for future study-space data.
    if facility_type == "Study Space":
        return "Quiet"

    # If the facility type is unknown, avoid guessing too strongly.
    return "Unknown"


def get_category(facility_type):
    """
    Estimate the category for a facility.

    The current backend database does not store category yet.
    The existing UI needs category for filtering, so this function derives it
    from facility_type for now.
    """

    # Current demo backend data is mainly PE and Rec spaces.
    if facility_type in ["Court", "Studio"]:
        return "Recreation"

    # These are included for future facility types.
    if facility_type == "Study Space":
        return "Study"

    if facility_type == "Room":
        return "Meeting"

    # Use a general category when there is no better match.
    return "Other"


def get_current_count(facility_id):
    """
    Estimate current usage from active check-ins.

    The checkins table is currently empty in the demo database, so this usually
    returns 0. Later, if check-ins are added, this will sum active group sizes.
    """

    # Get all active check-ins for this facility.
    checkIns = CheckIn.query.filter_by(
        facility_id=facility_id,
        status="active"
    ).all()

    # Start the count at 0.
    total = 0

    # Add each active check-in's group size to the total.
    for checkIn in checkIns:
        if checkIn.group_size:
            total += checkIn.group_size

    return total


def build_space_data(facility):
    """
    Build one space dictionary for the frontend.

    The old UI expects each space to have fields like category, noise_level,
    current_count, rules, and schedule. The backend database stores those
    pieces across multiple tables, so this function gathers them into one
    dictionary for the card UI.
    """

    # Get the rules row for this facility.
    rule = Rule.query.filter_by(facility_id=facility.facility_id).first()

    # Get all schedule rows for this facility.
    schedules = Schedule.query.filter_by(
        facility_id=facility.facility_id
    ).order_by(
        Schedule.day_of_week,
        Schedule.start_time
    ).all()

    # Use the database group limit if it exists.
    # If not, use 5 because Rec guidance treats 5+ as needing extra guidance.
    group_limit = rule.group_size_limit if rule and rule.group_size_limit else 5

    # Convert database schedule rows into the format the existing UI expects.
    schedule_items = []

    for item in schedules:
        start = format_time(item.start_time)
        end = format_time(item.end_time)

        schedule_items.append({
            "day": item.day_of_week,
            "time": f"{start} - {end}",
            "status": item.status.title() if item.status else "Unknown",
            "note": item.note or ""
        })

    # Pull rule values if they exist.
    # These defaults keep the page from crashing if a facility has no rule row.
    reservation_type = rule.reservation_type if rule else "Unknown"
    rule_notes = rule.rule_notes if rule else "No rule notes available."

    # Return one complete space object for the template and JavaScript.
    return {
        "facility_id": facility.facility_id,
        "name": facility.name,
        "location": facility.location,
        "category": get_category(facility.facility_type),
        "facility_type": facility.facility_type,
        "noise_level": get_noise_level(facility.facility_type),
        "description": facility.description,
        "reservation_type": reservation_type,
        "cost_status": rule.cost_status if rule else "Unknown",
        "cost_notes": rule.cost_notes if rule else "No cost notes available.",
        "group_size_limit": group_limit,
        "current_count": get_current_count(facility.facility_id),
        "restrictions": rule.restrictions if rule else "No restrictions listed.",
        "rule_notes": rule_notes,
        "next_step": f"{reservation_type}. {rule_notes}",
        "schedule": schedule_items
    }


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------

@app.route("/")
def index():
    """
    Show the main Duck Space homepage.

    The homepage displays facility cards. Each card is built from the backend
    database, then passed into the existing index.html template.
    """

    # Get all facilities from the database in alphabetical order.
    facilities = Facility.query.order_by(Facility.name).all()

    # Convert each database facility into the format the frontend expects.
    spaces = [build_space_data(facility) for facility in facilities]

    # Render the existing homepage with database-backed spaces.
    return render_template("index.html", spaces=spaces)


@app.route("/facility/<facility_id>")
def facility_detail(facility_id):
    """
    Show a detail page for one facility.

    This gives the project a working facility page instead of leaving
    templates/facility.html empty.
    """

    # Find the selected facility by its 8-character ID.
    facility = Facility.query.filter_by(facility_id=facility_id).first()

    # If the ID does not exist, return a 404 page.
    if facility is None:
        abort(404)

    # Build the same frontend-friendly space object used on the homepage.
    space = build_space_data(facility)

    # Load facility hours for the detail page.
    hours = Facility_Hours.query.filter_by(
        facility_id=facility_id
    ).order_by(
        Facility_Hours.day_of_week
    ).all()

    # Render the facility detail page.
    return render_template("facility.html", space=space, hours=hours)


@app.route("/admin")
def admin():
    """
    Show a simple admin preview page.

    This is not a full editing system yet. It shows the facilities currently
    loaded from the database so the team can verify backend data from the UI.
    """

    # Get all facilities for the admin preview list.
    facilities = Facility.query.order_by(Facility.name).all()

    # Render the admin preview page.
    return render_template("admin.html", facilities=facilities)


# ---------------------------------------------------------------------
# Run the app
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # Local address for the Flask app.
    url = "http://127.0.0.1:5000"

    # Open the browser once when Flask's debug reloader starts the real process.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    # Start the Flask development server.
    app.run(debug=True)