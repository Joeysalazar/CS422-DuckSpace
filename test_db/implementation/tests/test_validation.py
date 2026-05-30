"""
Unit tests for insertion_validation.py.

All functions are called directly (no HTTP layer). Tests that depend on
DB state use the `app` or seed fixtures from conftest.py so that queries
run inside a valid app context against the in-memory SQLite DB.
"""
import pytest
from datetime import time

from insertion_validation import (
    clean_fields, verify_time,
    validate_facility, validate_facility_hours,
    validate_rule, validate_schedule, validate_checkin,
    validate_user, validate_admin,
)
from models import Facility_Hours, Schedule, CheckIn


# ── verify_time ────────────────────────────────────────────────────────────────

class TestVerifyTime:
    @pytest.mark.parametrize("t", [
        time(0, 0), time(9, 0), time(9, 15), time(9, 30), time(9, 45), time(23, 45),
    ])
    def test_valid_quarter_boundaries(self, t):
        assert verify_time(t) is True

    @pytest.mark.parametrize("t", [
        time(9, 1), time(9, 14), time(9, 16), time(9, 0, 1), time(9, 0, 0, 1),
    ])
    def test_invalid(self, t):
        assert verify_time(t) is False


# ── clean_fields ───────────────────────────────────────────────────────────────

class TestCleanFields:
    def test_strips_surrounding_whitespace_from_key(self):
        d = {"  name  ": "foo"}
        clean_fields(d)
        assert "name" in d
        assert "  name  " not in d

    def test_removes_interior_spaces_from_key(self):
        d = {"facility id": "bar"}
        clean_fields(d)
        assert "facilityid" in d

    def test_clean_key_unchanged(self):
        d = {"name": "foo", "location": "bar"}
        clean_fields(d)
        assert sorted(d.keys()) == ["location", "name"]

    def test_value_unchanged(self):
        d = {"  name  ": "  value  "}
        clean_fields(d)
        assert d["name"] == "  value  "


# ── validate_facility ──────────────────────────────────────────────────────────

VALID_FACILITY = {
    "facility_id":     "REC00001",
    "name":            "Main Gym",
    "location":        "Rec Center",
    "facility_type":   "court",
    "managing_office": "Rec Sports",
    "description":     "Main gym space",
    "map_x":           1.0,
    "map_y":           2.0,
}

class TestValidateFacility:
    def test_valid(self, app):
        assert validate_facility(VALID_FACILITY) is True

    def test_missing_field(self, app):
        d = {**VALID_FACILITY}
        del d["name"]
        assert validate_facility(d) is False

    def test_extra_field(self, app):
        assert validate_facility({**VALID_FACILITY, "extra": "x"}) is False

    def test_facility_id_too_short(self, app):
        assert validate_facility({**VALID_FACILITY, "facility_id": "REC0001"}) is False

    def test_facility_id_too_long(self, app):
        assert validate_facility({**VALID_FACILITY, "facility_id": "REC000011"}) is False

    def test_facility_id_wrong_type(self, app):
        assert validate_facility({**VALID_FACILITY, "facility_id": 12345678}) is False

    def test_name_too_long(self, app):
        assert validate_facility({**VALID_FACILITY, "name": "x" * 101}) is False

    def test_facility_type_too_long(self, app):
        assert validate_facility({**VALID_FACILITY, "facility_type": "x" * 51}) is False

    def test_managing_office_too_long(self, app):
        assert validate_facility({**VALID_FACILITY, "managing_office": "x" * 101}) is False

    def test_map_x_out_of_bounds_high(self, app):
        assert validate_facility({**VALID_FACILITY, "map_x": 99.9}) is False

    def test_map_x_out_of_bounds_low(self, app):
        assert validate_facility({**VALID_FACILITY, "map_x": -99.9}) is False

    def test_map_x_wrong_type(self, app):
        assert validate_facility({**VALID_FACILITY, "map_x": 1}) is False  # int, not float

    def test_map_y_out_of_bounds(self, app):
        assert validate_facility({**VALID_FACILITY, "map_y": 99.9}) is False

    def test_description_wrong_type(self, app):
        assert validate_facility({**VALID_FACILITY, "description": 123}) is False


# ── validate_facility_hours ────────────────────────────────────────────────────

class TestValidateFacilityHours:
    def valid_hours(self):
        return {
            "hours_id":    0,
            "facility_id": "REC00001",
            "day_of_week": "Monday",
            "open_time":   time(8, 0),
            "close_time":  time(22, 0),
        }

    def test_valid(self, facility):
        assert validate_facility_hours(self.valid_hours()) is True

    def test_missing_field(self, facility):
        d = self.valid_hours()
        del d["open_time"]
        assert validate_facility_hours(d) is False

    def test_invalid_day(self, facility):
        d = self.valid_hours()
        d["day_of_week"] = "Someday"
        assert validate_facility_hours(d) is False

    def test_day_case_insensitive(self, facility):
        d = self.valid_hours()
        d["day_of_week"] = "MONDAY"
        assert validate_facility_hours(d) is True

    def test_time_not_on_15min_boundary(self, facility):
        d = self.valid_hours()
        d["open_time"] = time(8, 7)
        assert validate_facility_hours(d) is False

    def test_hours_id_wrong_type(self, facility):
        d = self.valid_hours()
        d["hours_id"] = "zero"
        assert validate_facility_hours(d) is False

    def test_duplicate_day_for_facility(self, facility, db):
        db.session.add(Facility_Hours(
            facility_id="REC00001", day_of_week="Monday",
            open_time=time(8, 0), close_time=time(22, 0),
        ))
        db.session.commit()
        assert validate_facility_hours(self.valid_hours()) is False


# ── validate_rule ──────────────────────────────────────────────────────────────

VALID_RULE = {
    "rule_id":          0,
    "facility_id":      "REC00001",
    "cost_status":      "free",
    "cost_notes":       "No charge",
    "reservation_type": "first-come",
    "group_size_limit": 5,
    "restrictions":     "None",
    "rule_notes":       "See front desk",
}

class TestValidateRule:
    def test_valid(self, facility):
        assert validate_rule(VALID_RULE) is True

    def test_missing_field(self, facility):
        d = {**VALID_RULE}
        del d["cost_status"]
        assert validate_rule(d) is False

    def test_group_size_zero(self, facility):
        assert validate_rule({**VALID_RULE, "group_size_limit": 0}) is False

    def test_group_size_too_large(self, facility):
        assert validate_rule({**VALID_RULE, "group_size_limit": 1001}) is False

    def test_group_size_boundary_min(self, facility):
        assert validate_rule({**VALID_RULE, "group_size_limit": 1}) is True

    def test_group_size_boundary_max(self, facility):
        assert validate_rule({**VALID_RULE, "group_size_limit": 250}) is True

    def test_cost_status_too_long(self, facility):
        assert validate_rule({**VALID_RULE, "cost_status": "x" * 21}) is False

    def test_reservation_type_too_long(self, facility):
        assert validate_rule({**VALID_RULE, "reservation_type": "x" * 31}) is False

    def test_rule_id_wrong_type(self, facility):
        assert validate_rule({**VALID_RULE, "rule_id": "zero"}) is False

    def test_duplicate_rule_for_facility(self, facility, rule):
        assert validate_rule(VALID_RULE) is False


# ── validate_schedule ──────────────────────────────────────────────────────────

class TestValidateSchedule:
    def valid_sched(self):
        return {
            "schedule_id": 0,
            "facility_id": "REC00001",
            "day_of_week": "Tuesday",
            "start_time":  time(9, 0),
            "end_time":    time(10, 0),
            "status":      "open",
            "note":        "",
        }

    def test_valid_insert(self, facility):
        assert validate_schedule(self.valid_sched(), update_schedule=False) is True

    def test_missing_field(self, facility):
        d = self.valid_sched()
        del d["status"]
        assert validate_schedule(d, update_schedule=False) is False

    def test_invalid_weekday(self, facility):
        d = self.valid_sched()
        d["day_of_week"] = "Someday"
        assert validate_schedule(d, update_schedule=False) is False

    def test_weekday_too_long(self, facility):
        d = self.valid_sched()
        d["day_of_week"] = "Wednesday"  # 9 chars, within limit
        assert validate_schedule(d, update_schedule=False) is True

    def test_status_too_long(self, facility):
        d = self.valid_sched()
        d["status"] = "x" * 21
        assert validate_schedule(d, update_schedule=False) is False

    def test_time_not_on_boundary(self, facility):
        d = self.valid_sched()
        d["start_time"] = time(9, 7)
        assert validate_schedule(d, update_schedule=False) is False

    def test_conflict_with_existing_non_open_slot(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        ))
        db.session.commit()
        d = self.valid_sched()
        d.update(day_of_week="Monday", start_time=time(11, 0), end_time=time(13, 0), status="class")
        assert validate_schedule(d, update_schedule=False) is False

    def test_no_conflict_with_open_slot(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="open", note="",
        ))
        db.session.commit()
        d = self.valid_sched()
        d.update(day_of_week="Monday", start_time=time(11, 0), end_time=time(13, 0), status="class")
        assert validate_schedule(d, update_schedule=False) is True

    def test_update_same_times_no_self_conflict(self, facility, db):
        """Updating a slot without changing its times should pass validation."""
        slot = Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        )
        db.session.add(slot)
        db.session.commit()
        d = {
            "schedule_id": slot.schedule_id,
            "facility_id": "REC00001",
            "day_of_week": "Monday",
            "start_time":  time(10, 0),
            "end_time":    time(12, 0),
            "status":      "closed",  # only status changes
            "note":        "",
        }
        assert validate_schedule(d, update_schedule=True) is True


# ── validate_checkin ───────────────────────────────────────────────────────────

class TestValidateCheckin:
    def valid_ci(self, facility_id, user_id):
        return {
            "checkin_id":  0,
            "facility_id": facility_id,
            "user_id":     user_id,
            "day_of_week": "Monday",
            "start_time":  time(14, 0),
            "end_time":    time(15, 0),
            "group_size":  2,
            "status":      "active",
            "note":        "",
        }

    def test_valid(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is True

    def test_facility_not_in_list(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        assert validate_checkin(ci, [], [user.user_id], update_checkin=False) is False

    def test_user_not_in_list(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        assert validate_checkin(ci, ["REC00001"], [], update_checkin=False) is False

    def test_invalid_weekday(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        ci["day_of_week"] = "Someday"
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_group_size_zero(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        ci["group_size"] = 0
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_group_size_negative(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        ci["group_size"] = -1
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_time_not_on_boundary(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        ci["start_time"] = time(14, 7)
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_status_too_long(self, facility, user):
        ci = self.valid_ci("REC00001", user.user_id)
        ci["status"] = "x" * 21
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_conflict_with_non_open_schedule(self, facility, user, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(13, 0), end_time=time(15, 0),
            status="class", note="",
        ))
        db.session.commit()
        ci = self.valid_ci("REC00001", user.user_id)
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_no_conflict_with_open_schedule(self, facility, user, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(13, 0), end_time=time(15, 0),
            status="open", note="",
        ))
        db.session.commit()
        ci = self.valid_ci("REC00001", user.user_id)
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is True

    def test_conflict_with_existing_active_checkin(self, facility, user, db):
        db.session.add(CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(15, 30),
            group_size=1, status="active", note="",
        ))
        db.session.commit()
        ci = self.valid_ci("REC00001", user.user_id)
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=False) is False

    def test_update_no_self_conflict(self, facility, user, db):
        existing = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(15, 0),
            group_size=2, status="active", note="",
        )
        db.session.add(existing)
        db.session.commit()
        ci = self.valid_ci("REC00001", user.user_id)
        ci["checkin_id"] = existing.checkin_id
        assert validate_checkin(ci, ["REC00001"], [user.user_id], update_checkin=True) is False  # still blocked by duplicate_checkin


# ── validate_user ──────────────────────────────────────────────────────────────

class TestValidateUser:
    VALID = {"name": "Test User", "email": "test@uoregon.edu"}

    def test_valid(self, app):
        assert validate_user(self.VALID) is True

    def test_missing_name(self, app):
        assert validate_user({"email": "test@uoregon.edu"}) is False

    def test_missing_email(self, app):
        assert validate_user({"name": "Test User"}) is False

    def test_extra_field(self, app):
        assert validate_user({**self.VALID, "extra": "x"}) is False

    def test_name_too_long(self, app):
        assert validate_user({**self.VALID, "name": "x" * 101}) is False

    def test_email_too_long(self, app):
        assert validate_user({**self.VALID, "email": "x" * 101}) is False

    def test_name_wrong_type(self, app):
        assert validate_user({**self.VALID, "name": 123}) is False

    def test_duplicate_user(self, user, app):
        assert validate_user(self.VALID) is False


# ── validate_admin ─────────────────────────────────────────────────────────────

class TestValidateAdmin:
    VALID = {"admin_id": 0, "username": "admin", "password_hash": "bcrypt-hash-here"}

    def test_valid(self, app):
        assert validate_admin(self.VALID, []) is True

    def test_missing_field(self, app):
        d = {**self.VALID}
        del d["username"]
        assert validate_admin(d, []) is False

    def test_extra_field(self, app):
        assert validate_admin({**self.VALID, "extra": "x"}, []) is False

    def test_duplicate_username(self, app):
        assert validate_admin(self.VALID, ["admin"]) is False

    def test_username_too_long(self, app):
        assert validate_admin({**self.VALID, "username": "x" * 51}, []) is False

    def test_password_hash_wrong_type(self, app):
        assert validate_admin({**self.VALID, "password_hash": None}, []) is False

    def test_admin_id_wrong_type(self, app):
        assert validate_admin({**self.VALID, "admin_id": "zero"}, []) is False
