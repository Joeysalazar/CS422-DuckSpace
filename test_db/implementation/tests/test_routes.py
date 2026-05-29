"""
Integration tests for every HTTP route in routes.py.
Uses the Flask test client — each test makes real HTTP calls against
the in-memory SQLite DB spun up in conftest.py.
"""
from datetime import time
from models import Facility_Hours, CheckIn


# ── Facilities ─────────────────────────────────────────────────────────────────

class TestGetFacilities:
    def test_empty_list(self, client):
        r = client.get("/api/facilities")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_returns_all_facilities(self, client, facility):
        r = client.get("/api/facilities")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["facility_id"] == "REC00001"
        assert data[0]["name"] == "Main Gym"

    def test_response_shape(self, client, facility):
        data = client.get("/api/facilities").get_json()
        keys = set(data[0].keys())
        assert keys == {"facility_id", "name", "location", "facility_type",
                        "managing_office", "description", "map_x", "map_y"}

    def test_get_one_facility(self, client, facility):
        r = client.get("/api/facilities/REC00001")
        assert r.status_code == 200
        assert r.get_json()["name"] == "Main Gym"

    def test_get_one_not_found(self, client):
        assert client.get("/api/facilities/XXXXXXXX").status_code == 404

    def test_filter_by_type_match(self, client, facility):
        r = client.get("/api/facilities/type/court")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["facility_id"] == "REC00001"

    def test_filter_by_type_no_match(self, client, facility):
        r = client.get("/api/facilities/type/pool")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_filter_by_type_response_shape(self, client, facility):
        data = client.get("/api/facilities/type/court").get_json()
        assert set(data[0].keys()) == {"facility_id", "name", "location"}


# ── Facility Hours ─────────────────────────────────────────────────────────────

class TestFacilityHoursRoutes:
    def test_get_hours_empty(self, client, facility):
        r = client.get("/api/facilities/REC00001/hours")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_get_hours_not_found_facility(self, client):
        assert client.get("/api/facilities/XXXXXXXX/hours").status_code == 404

    def test_add_hours(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/hours", json={
            "day_of_week": "Monday",
            "open_time":   "08:00",
            "close_time":  "22:00",
        })
        assert r.status_code == 201
        assert "hours_id" in r.get_json()

    def test_add_hours_returns_in_get(self, client, facility):
        client.post("/api/admin/facilities/REC00001/hours", json={
            "day_of_week": "Monday",
            "open_time":   "08:00",
            "close_time":  "22:00",
        })
        r = client.get("/api/facilities/REC00001/hours")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["day_of_week"] == "Monday"

    def test_add_hours_invalid_time_format(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/hours", json={
            "day_of_week": "Monday",
            "open_time":   "not-a-time",
            "close_time":  "22:00",
        })
        assert r.status_code == 400

    def test_add_hours_close_before_open(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/hours", json={
            "day_of_week": "Monday",
            "open_time":   "22:00",
            "close_time":  "08:00",
        })
        assert r.status_code == 400

    def test_add_hours_not_on_15min_boundary(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/hours", json={
            "day_of_week": "Monday",
            "open_time":   "08:07",
            "close_time":  "22:00",
        })
        assert r.status_code == 400

    def test_add_hours_facility_not_found(self, client):
        r = client.post("/api/admin/facilities/XXXXXXXX/hours", json={
            "day_of_week": "Monday",
            "open_time":   "08:00",
            "close_time":  "22:00",
        })
        assert r.status_code == 404

    def test_update_hours(self, client, facility, db):
        h = Facility_Hours(
            facility_id="REC00001", day_of_week="Tuesday",
            open_time=time(8, 0), close_time=time(20, 0),
        )
        db.session.add(h)
        db.session.commit()
        r = client.put(f"/api/admin/facilities/REC00001/hours/{h.hours_id}", json={
            "close_time": "22:00",
        })
        assert r.status_code == 200

    def test_update_hours_wrong_facility(self, client, facility, db):
        h = Facility_Hours(
            facility_id="REC00001", day_of_week="Tuesday",
            open_time=time(8, 0), close_time=time(20, 0),
        )
        db.session.add(h)
        db.session.commit()
        r = client.put(f"/api/admin/facilities/XXXXXXXX/hours/{h.hours_id}", json={
            "close_time": "22:00",
        })
        assert r.status_code == 404

    def test_update_hours_not_found(self, client, facility):
        r = client.put("/api/admin/facilities/REC00001/hours/9999", json={
            "close_time": "22:00",
        })
        assert r.status_code == 404


# ── Rules ──────────────────────────────────────────────────────────────────────

class TestRulesRoutes:
    RULE_PAYLOAD = {
        "cost_status":      "free",
        "cost_notes":       "No charge",
        "reservation_type": "first-come",
        "group_size_limit": 10,
        "restrictions":     "None",
        "rule_notes":       "See front desk",
    }

    def test_get_rules(self, client, rule):
        r = client.get("/api/facilities/REC00001/rules")
        assert r.status_code == 200
        assert r.get_json()["cost_status"] == "free"

    def test_get_rules_not_found(self, client, facility):
        assert client.get("/api/facilities/REC00001/rules").status_code == 404

    def test_check_group_eligible(self, client, rule):
        r = client.get("/api/facilities/REC00001/check-group?size=5")
        assert r.status_code == 200
        assert r.get_json()["eligible"] is True

    def test_check_group_ineligible(self, client, rule):
        r = client.get("/api/facilities/REC00001/check-group?size=10")
        assert r.status_code == 200
        assert r.get_json()["eligible"] is False

    def test_check_group_missing_size_param(self, client, rule):
        assert client.get("/api/facilities/REC00001/check-group").status_code == 400

    def test_create_rules(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/rules", json=self.RULE_PAYLOAD)
        assert r.status_code == 201
        assert "rule_id" in r.get_json()

    def test_create_rules_duplicate(self, client, rule):
        r = client.post("/api/admin/facilities/REC00001/rules", json=self.RULE_PAYLOAD)
        assert r.status_code == 409

    def test_create_rules_facility_not_found(self, client):
        r = client.post("/api/admin/facilities/XXXXXXXX/rules", json=self.RULE_PAYLOAD)
        assert r.status_code == 404

    def test_create_rules_missing_field(self, client, facility):
        payload = {**self.RULE_PAYLOAD}
        del payload["cost_status"]
        r = client.post("/api/admin/facilities/REC00001/rules", json=payload)
        assert r.status_code == 400

    def test_update_rules(self, client, rule):
        r = client.put("/api/admin/facilities/REC00001/rules", json={"cost_status": "paid"})
        assert r.status_code == 200

    def test_update_rules_not_found(self, client, facility):
        r = client.put("/api/admin/facilities/REC00001/rules", json={"cost_status": "paid"})
        assert r.status_code == 404


# ── Schedule ───────────────────────────────────────────────────────────────────

class TestScheduleRoutes:
    def test_get_schedule_empty(self, client, facility):
        r = client.get("/api/facilities/REC00001/schedule")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_get_schedule_with_data(self, client, schedule_slot):
        r = client.get("/api/facilities/REC00001/schedule")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["status"] == "class"

    def test_get_schedule_filter_by_day(self, client, schedule_slot):
        r = client.get("/api/facilities/REC00001/schedule?day=Monday")
        assert len(r.get_json()) == 1

    def test_get_schedule_filter_no_match(self, client, schedule_slot):
        r = client.get("/api/facilities/REC00001/schedule?day=Tuesday")
        assert r.get_json() == []

    def test_add_schedule(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/schedule", json={
            "day_of_week": "Tuesday",
            "start_time":  "09:00",
            "end_time":    "10:00",
            "status":      "class",
            "note":        "Yoga",
        })
        assert r.status_code == 201
        assert "schedule_id" in r.get_json()

    def test_add_schedule_conflict(self, client, schedule_slot):
        r = client.post("/api/admin/facilities/REC00001/schedule", json={
            "day_of_week": "Monday",
            "start_time":  "11:00",
            "end_time":    "13:00",
            "status":      "class",
            "note":        "",
        })
        assert r.status_code == 400

    def test_add_schedule_end_before_start(self, client, facility):
        r = client.post("/api/admin/facilities/REC00001/schedule", json={
            "day_of_week": "Tuesday",
            "start_time":  "10:00",
            "end_time":    "09:00",
            "status":      "class",
            "note":        "",
        })
        assert r.status_code == 400

    def test_add_schedule_facility_not_found(self, client):
        r = client.post("/api/admin/facilities/XXXXXXXX/schedule", json={
            "day_of_week": "Tuesday",
            "start_time":  "09:00",
            "end_time":    "10:00",
            "status":      "class",
            "note":        "",
        })
        assert r.status_code == 404

    def test_update_schedule(self, client, schedule_slot):
        r = client.put(
            f"/api/admin/facilities/REC00001/schedule/{schedule_slot.schedule_id}",
            json={"note": "Updated note"},
        )
        assert r.status_code == 200

    def test_update_schedule_wrong_facility(self, client, schedule_slot):
        r = client.put(
            f"/api/admin/facilities/XXXXXXXX/schedule/{schedule_slot.schedule_id}",
            json={"note": "Updated"},
        )
        assert r.status_code == 404

    def test_update_schedule_not_found(self, client, facility):
        r = client.put(
            "/api/admin/facilities/REC00001/schedule/9999",
            json={"note": "Updated"},
        )
        assert r.status_code == 404

    def test_delete_schedule(self, client, schedule_slot):
        r = client.delete(
            f"/api/admin/facilities/REC00001/schedule/{schedule_slot.schedule_id}"
        )
        assert r.status_code == 200
        r2 = client.get("/api/facilities/REC00001/schedule?day=Monday")
        assert r2.get_json() == []

    def test_delete_schedule_wrong_facility(self, client, schedule_slot):
        r = client.delete(
            f"/api/admin/facilities/XXXXXXXX/schedule/{schedule_slot.schedule_id}"
        )
        assert r.status_code == 404

    def test_delete_schedule_not_found(self, client, facility):
        r = client.delete("/api/admin/facilities/REC00001/schedule/9999")
        assert r.status_code == 404


# ── Users ──────────────────────────────────────────────────────────────────────

class TestUserRoutes:
    def test_create_user(self, client):
        r = client.post("/api/users", json={
            "name":  "Jane Duck",
            "email": "jane@uoregon.edu",
        })
        assert r.status_code == 201
        assert "user_id" in r.get_json()

    def test_create_user_duplicate_name_and_email(self, client, user):
        r = client.post("/api/users", json={
            "name":  "Test User",
            "email": "test@uoregon.edu",
        })
        assert r.status_code == 400

    def test_create_user_missing_field(self, client):
        r = client.post("/api/users", json={"name": "No Email"})
        assert r.status_code == 400

    def test_create_user_no_body(self, client):
        r = client.post("/api/users")
        assert r.status_code in (400, 415)

    def test_get_user_checkins_empty(self, client, user):
        r = client.get(f"/api/users/{user.user_id}/checkins")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_get_user_checkins_returns_active_only(self, client, checkin, user, db):
        cancelled = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Tuesday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="cancelled", note="",
        )
        db.session.add(cancelled)
        db.session.commit()
        r = client.get(f"/api/users/{user.user_id}/checkins")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["checkin_id"] == checkin.checkin_id


# ── Check-ins ──────────────────────────────────────────────────────────────────

class TestCheckinRoutes:
    PAYLOAD = {
        "facility_id": "REC00001",
        "day_of_week": "Monday",
        "start_time":  "14:00",
        "end_time":    "15:00",
        "group_size":  2,
        "note":        "",
    }

    def test_create_checkin(self, client, facility, rule, user):
        r = client.post("/api/checkins", json={**self.PAYLOAD, "user_id": user.user_id})
        assert r.status_code == 201
        assert "checkin_id" in r.get_json()

    def test_create_checkin_group_too_large(self, client, facility, rule, user):
        r = client.post("/api/checkins", json={
            **self.PAYLOAD, "user_id": user.user_id, "group_size": 10,
        })
        assert r.status_code == 400

    def test_create_checkin_facility_not_found(self, client, user):
        r = client.post("/api/checkins", json={
            **self.PAYLOAD, "user_id": user.user_id, "facility_id": "XXXXXXXX",
        })
        assert r.status_code == 404

    def test_create_checkin_invalid_time_format(self, client, facility, rule, user):
        r = client.post("/api/checkins", json={
            **self.PAYLOAD, "user_id": user.user_id, "start_time": "bad",
        })
        assert r.status_code == 400

    def test_create_checkin_no_body(self, client):
        r = client.post("/api/checkins")
        assert r.status_code in (400, 415)

    def test_complete_checkin(self, client, checkin, user):
        r = client.put(
            f"/api/checkins/{checkin.checkin_id}/complete",
            json={"user_id": user.user_id},
        )
        assert r.status_code == 200

    def test_complete_checkin_wrong_user(self, client, checkin):
        r = client.put(
            f"/api/checkins/{checkin.checkin_id}/complete",
            json={"user_id": 9999},
        )
        assert r.status_code == 403

    def test_complete_checkin_missing_user_id(self, client, checkin):
        r = client.put(f"/api/checkins/{checkin.checkin_id}/complete", json={})
        assert r.status_code == 400

    def test_complete_checkin_not_found(self, client):
        r = client.put("/api/checkins/9999/complete", json={"user_id": 1})
        assert r.status_code == 404

    def test_cancel_checkin(self, client, checkin, user):
        r = client.delete(
            f"/api/checkins/{checkin.checkin_id}",
            json={"user_id": user.user_id},
        )
        assert r.status_code == 200

    def test_cancel_checkin_wrong_user(self, client, checkin):
        r = client.delete(
            f"/api/checkins/{checkin.checkin_id}",
            json={"user_id": 9999},
        )
        assert r.status_code == 403

    def test_cancel_checkin_missing_user_id(self, client, checkin):
        r = client.delete(f"/api/checkins/{checkin.checkin_id}", json={})
        assert r.status_code == 400

    def test_cancel_checkin_not_found(self, client):
        r = client.delete("/api/checkins/9999", json={"user_id": 1})
        assert r.status_code == 404

    def test_get_facility_checkins(self, client, checkin):
        r = client.get("/api/facilities/REC00001/checkins")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["checkin_id"] == checkin.checkin_id

    def test_get_facility_checkins_filter_by_day(self, client, checkin):
        r = client.get("/api/facilities/REC00001/checkins?day=Monday")
        assert len(r.get_json()) == 1

    def test_get_facility_checkins_filter_no_match(self, client, checkin):
        r = client.get("/api/facilities/REC00001/checkins?day=Tuesday")
        assert r.get_json() == []


# ── Admin auth ─────────────────────────────────────────────────────────────────

class TestAdminAuth:
    def test_register(self, client):
        r = client.post("/api/admin/register", json={
            "username": "newadmin", "password": "secret",
        })
        assert r.status_code == 201
        assert "admin_id" in r.get_json()

    def test_register_duplicate_username(self, client, admin_user):
        r = client.post("/api/admin/register", json={
            "username": "admin", "password": "other",
        })
        assert r.status_code == 409

    def test_register_no_body(self, client):
        r = client.post("/api/admin/register")
        assert r.status_code in (400, 415)

    def test_login_success(self, client, admin_user):
        r = client.post("/api/admin/login", json={
            "username": "admin", "password": "testpass",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["message"] == "Login successful"
        assert "admin_id" in data

    def test_login_wrong_password(self, client, admin_user):
        r = client.post("/api/admin/login", json={
            "username": "admin", "password": "wrong",
        })
        assert r.status_code == 401

    def test_login_unknown_user(self, client):
        r = client.post("/api/admin/login", json={
            "username": "ghost", "password": "pass",
        })
        assert r.status_code == 401

    def test_login_missing_fields(self, client):
        r = client.post("/api/admin/login", json={"username": "admin"})
        assert r.status_code == 400


# ── Admin facility management ──────────────────────────────────────────────────

class TestAdminFacilityMgmt:
    PAYLOAD = {
        "facility_id":     "REC00002",
        "name":            "Pool",
        "location":        "Aquatic Center",
        "facility_type":   "pool",
        "managing_office": "Rec Sports",
        "description":     "Olympic pool",
        "map_x":           2.0,
        "map_y":           3.0,
    }

    def test_create_facility(self, client):
        r = client.post("/api/admin/facilities", json=self.PAYLOAD)
        assert r.status_code == 201
        assert r.get_json()["facility_id"] == "REC00002"

    def test_create_facility_duplicate(self, client, facility):
        r = client.post("/api/admin/facilities", json={
            **self.PAYLOAD, "facility_id": "REC00001",
        })
        assert r.status_code == 409

    def test_create_facility_id_wrong_length(self, client):
        r = client.post("/api/admin/facilities", json={
            **self.PAYLOAD, "facility_id": "SHORT",
        })
        assert r.status_code == 400

    def test_create_facility_map_out_of_bounds(self, client):
        r = client.post("/api/admin/facilities", json={
            **self.PAYLOAD, "map_x": 999.0,
        })
        assert r.status_code == 400

    def test_create_facility_no_body(self, client):
        r = client.post("/api/admin/facilities")
        assert r.status_code in (400, 415)

    def test_update_facility(self, client, facility):
        r = client.put("/api/admin/facilities/REC00001", json={"name": "Updated Gym"})
        assert r.status_code == 200

    def test_update_facility_not_found(self, client):
        r = client.put("/api/admin/facilities/XXXXXXXX", json={"name": "Ghost"})
        assert r.status_code == 404

    def test_update_facility_no_body(self, client, facility):
        r = client.put("/api/admin/facilities/REC00001")
        assert r.status_code in (400, 415)

    def test_admin_cancel_any_checkin(self, client, checkin):
        r = client.delete(f"/api/admin/checkins/{checkin.checkin_id}")
        assert r.status_code == 200

    def test_admin_cancel_checkin_not_found(self, client):
        r = client.delete("/api/admin/checkins/9999")
        assert r.status_code == 404
