"""
DuckSpace seed script — reads CSVs from data/ and inserts into the database.

Usage:
    python seed_data.py
    (DATABASE_URL must be set in .env or environment)

To add or update facilities: edit the CSV files in data/, then rerun this script.
Reruns are safe — existing rows for known facility IDs are cleared first.

Schedule rows marked [SAMPLE] in data/schedules.csv are placeholder demo data.
All other data is sourced from rec.uoregon.edu (public information).
"""

import csv
import os
from datetime import time
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

try:
    from models import db, Facility, Facility_Hours, Rule, Schedule
except ImportError:
    from test_db.models import db, Facility, Facility_Hours, Rule, Schedule

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

DATA_DIR = Path(__file__).parent / "data"


def load_csv(filename: str) -> list[dict]:
    with open(DATA_DIR / filename, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_time(value: str) -> time | None:
    if not value:
        return None
    h, m = value.strip().split(":")
    return time(int(h), int(m))


def parse_int(value: str) -> int | None:
    return int(value) if value.strip() else None


def parse_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def parse_str(value: str) -> str | None:
    stripped = value.strip()
    return stripped if stripped else None


def build_facilities(rows: list[dict]) -> list[Facility]:
    return [
        Facility(
            facility_id=r["facility_id"],
            name=r["name"],
            location=parse_str(r["location"]),
            category=parse_str(r["category"]),
            facility_type=parse_str(r["facility_type"]),
            noise_level=parse_str(r["noise_level"]),
            managing_office=parse_str(r["managing_office"]),
            description=parse_str(r["description"]),
            next_step=parse_str(r["next_step"]),
            map_x=parse_float(r["map_x"]),
            map_y=parse_float(r["map_y"]),
        )
        for r in rows
    ]


def build_rules(rows: list[dict]) -> list[Rule]:
    return [
        Rule(
            facility_id=r["facility_id"],
            cost_status=parse_str(r["cost_status"]),
            cost_notes=parse_str(r["cost_notes"]),
            reservation_type=parse_str(r["reservation_type"]),
            group_size_limit=parse_int(r["group_size_limit"]),
            restrictions=parse_str(r["restrictions"]),
            rule_notes=parse_str(r["rule_notes"]),
        )
        for r in rows
    ]


def build_facility_hours(rows: list[dict]) -> list[Facility_Hours]:
    return [
        Facility_Hours(
            facility_id=r["facility_id"],
            day_of_week=r["day_of_week"],
            open_time=parse_time(r["open_time"]),
            close_time=parse_time(r["close_time"]),
        )
        for r in rows
    ]


def build_schedules(rows: list[dict]) -> list[Schedule]:
    return [
        Schedule(
            facility_id=r["facility_id"],
            day_of_week=r["day_of_week"],
            start_time=parse_time(r["start_time"]),
            end_time=parse_time(r["end_time"]),
            status=r["status"],
            note=parse_str(r["note"]),
        )
        for r in rows
    ]


def seed():
    facility_rows = load_csv("facilities.csv")
    facility_ids = [r["facility_id"] for r in facility_rows]

    # Clear existing data for these facility IDs so reruns are safe
    Schedule.query.filter(Schedule.facility_id.in_(facility_ids)).delete(synchronize_session=False)
    Facility_Hours.query.filter(Facility_Hours.facility_id.in_(facility_ids)).delete(synchronize_session=False)
    Rule.query.filter(Rule.facility_id.in_(facility_ids)).delete(synchronize_session=False)
    Facility.query.filter(Facility.facility_id.in_(facility_ids)).delete(synchronize_session=False)
    db.session.flush()

    facilities = build_facilities(facility_rows)
    rules = build_rules(load_csv("rules.csv"))
    hours = build_facility_hours(load_csv("facility_hours.csv"))
    schedules = build_schedules(load_csv("schedules.csv"))

    db.session.add_all(facilities)
    db.session.flush()
    db.session.add_all(rules)
    db.session.add_all(hours)
    db.session.add_all(schedules)
    db.session.commit()

    print(
        f"Seeded {len(facilities)} facilities, {len(rules)} rule sets, "
        f"{len(hours)} hour entries, {len(schedules)} schedule blocks."
    )


if __name__ == "__main__":
    with app.app_context():
        seed()
