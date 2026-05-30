import sys
import os
import pytest
import bcrypt
from datetime import time
from flask import Flask

# Put the implementation directory on the path so tests can import models, routes, etc.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import db as _db, Facility, Rule, Facility_Hours, Schedule, User, CheckIn, Admin


# ── App & client ───────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    """
    Minimal test Flask app built directly from models + routes,
    bypassing app.py (which has its own issues — see the issues list).
    Uses SQLite in-memory so every test gets a clean slate.
    """
    from routes import api

    test_app = Flask(__name__)
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    _db.init_app(test_app)
    test_app.register_blueprint(api, url_prefix="/api")

    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


# ── Seed fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def facility(db):
    f = Facility(
        facility_id="REC00001", name="Main Gym", location="Rec Center",
        facility_type="court", managing_office="Rec Sports",
        description="Main gym space", map_x=1.0, map_y=2.0,
    )
    db.session.add(f)
    db.session.commit()
    return f


@pytest.fixture
def rule(db, facility):
    r = Rule(
        facility_id="REC00001", cost_status="free", cost_notes="No cost",
        reservation_type="first-come", group_size_limit=10,
        restrictions="None", rule_notes="See front desk",
    )
    db.session.add(r)
    db.session.commit()
    return r


@pytest.fixture
def user(db):
    u = User(name="Test User", email="test@uoregon.edu")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin_user(db):
    pw_hash = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    a = Admin(username="admin", password_hash=pw_hash)
    db.session.add(a)
    db.session.commit()
    return a


@pytest.fixture
def schedule_slot(db, facility):
    s = Schedule(
        facility_id="REC00001", day_of_week="Monday",
        start_time=time(10, 0), end_time=time(12, 0),
        status="class", note="Yoga",
    )
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def checkin(db, facility, user):
    c = CheckIn(
        facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
        start_time=time(14, 0), end_time=time(15, 0),
        group_size=2, status="active", note="",
    )
    db.session.add(c)
    db.session.commit()
    return c
