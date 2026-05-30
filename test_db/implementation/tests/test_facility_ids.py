"""
Tests for facility ID uniqueness and FK connections to rules, schedules, and check-ins.
"""
import pytest
from datetime import time
from sqlalchemy.exc import IntegrityError
from models import Facility, Rule, Schedule, CheckIn


# Reusable second facility data
SECOND_FACILITY = dict(
    facility_id="REC00002",
    name="Pool",
    location="Aquatic Center",
    facility_type="pool",
    managing_office="Rec Sports",
    description="Olympic pool",
    map_x=2.0,
    map_y=3.0,
)


# ── Unique Facility IDs ────────────────────────────────────────────────────────

class TestFacilityIdUniqueness:
    def test_duplicate_id_raises_integrity_error(self, db, facility):
        """Inserting a Facility with an already-used primary key raises IntegrityError."""
        duplicate = Facility(
            facility_id="REC00001",
            name="Duplicate Gym",
            location="Elsewhere",
            facility_type="court",
            managing_office="Rec Sports",
            description="Duplicate",
            map_x=0.0,
            map_y=0.0,
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_two_facilities_with_unique_ids_coexist(self, db):
        """Two facilities with different IDs can both be inserted and retrieved."""
        f1 = Facility(
            facility_id="REC00001", name="Gym", location="Building 1",
            facility_type="court", managing_office="Rec", description="",
            map_x=1.0, map_y=1.0,
        )
        f2 = Facility(**SECOND_FACILITY)
        db.session.add_all([f1, f2])
        db.session.commit()
        assert Facility.query.count() == 2
        assert db.session.get(Facility, "REC00001") is not None
        assert db.session.get(Facility, "REC00002") is not None

    def test_all_inserted_ids_remain_distinct(self, db):
        """Each inserted facility ID is unique — no duplicates in the query result."""
        ids = ["REC00001", "REC00002", "REC00003"]
        for fid in ids:
            db.session.add(Facility(
                facility_id=fid, name=f"Facility {fid}", location="Campus",
                facility_type="court", managing_office="Rec", description="",
                map_x=0.0, map_y=0.0,
            ))
        db.session.commit()
        queried_ids = [f.facility_id for f in Facility.query.all()]
        assert len(queried_ids) == len(set(queried_ids))
        assert set(queried_ids) == set(ids)

    def test_route_rejects_duplicate_facility_id(self, client, facility):
        """POST /api/admin/facilities returns 409 when the facility_id is already in use."""
        r = client.post("/api/admin/facilities", json={
            "facility_id":     "REC00001",
            "name":            "Another Gym",
            "location":        "Somewhere",
            "facility_type":   "court",
            "managing_office": "Rec Sports",
            "description":     "Duplicate attempt",
            "map_x":           1.0,
            "map_y":           1.0,
        })
        assert r.status_code == 409

    def test_route_accepts_unique_facility_id(self, client, facility):
        """POST /api/admin/facilities succeeds when the facility_id has not been used before."""
        r = client.post("/api/admin/facilities", json={**SECOND_FACILITY})
        assert r.status_code == 201
        assert r.get_json()["facility_id"] == "REC00002"
        assert Facility.query.count() == 2


# ── Rules FK connection ────────────────────────────────────────────────────────

class TestFacilityRuleConnection:
    def test_rule_facility_id_matches_facility(self, facility, rule):
        """rule.facility_id is identical to the parent facility's facility_id."""
        assert rule.facility_id == facility.facility_id

    def test_facility_orm_relationship_returns_rule(self, facility, rule):
        """The facility.rules backref resolves to the Rule object linked to it."""
        assert facility.rules is not None
        assert facility.rules.rule_id == rule.rule_id

    def test_second_facility_has_no_rule(self, db, rule):
        """A facility with no rule record has facility.rules == None."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.commit()
        assert other.rules is None

    def test_rule_query_returns_only_matching_facility(self, db, facility, rule):
        """Querying Rule by facility_id excludes records belonging to other facilities."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.add(Rule(
            facility_id="REC00002", cost_status="paid", cost_notes="Fee applies",
            reservation_type="reservable", group_size_limit=5,
            restrictions="None", rule_notes="Contact front desk",
        ))
        db.session.commit()
        results = Rule.query.filter_by(facility_id="REC00001").all()
        assert len(results) == 1
        assert results[0].rule_id == rule.rule_id

    def test_route_returns_rule_only_for_correct_facility(self, client, rule):
        """GET /api/facilities/<id>/rules returns data for the queried facility."""
        r = client.get("/api/facilities/REC00001/rules")
        assert r.status_code == 200
        assert r.get_json()["cost_status"] == rule.cost_status

    def test_route_404_when_facility_has_no_rule(self, client, facility):
        """GET /api/facilities/<id>/rules returns 404 when no rule exists for that facility."""
        r = client.get("/api/facilities/REC00001/rules")
        assert r.status_code == 404

    def test_route_404_when_creating_rule_for_missing_facility(self, client):
        """POST /api/admin/facilities/<id>/rules returns 404 for a non-existent facility."""
        r = client.post("/api/admin/facilities/XXXXXXXX/rules", json={
            "cost_status":      "free",
            "cost_notes":       "None",
            "reservation_type": "first-come",
            "group_size_limit": 10,
            "restrictions":     "None",
            "rule_notes":       "N/A",
        })
        assert r.status_code == 404


# ── Schedules FK connection ────────────────────────────────────────────────────

class TestFacilityScheduleConnection:
    def test_schedule_facility_id_matches_facility(self, facility, schedule_slot):
        """schedule.facility_id is identical to the parent facility's facility_id."""
        assert schedule_slot.facility_id == facility.facility_id

    def test_facility_orm_relationship_returns_schedules(self, facility, schedule_slot):
        """facility.schedules list contains the Schedule object linked to it."""
        assert len(facility.schedules) == 1
        assert facility.schedules[0].schedule_id == schedule_slot.schedule_id

    def test_second_facility_has_no_schedules(self, db, schedule_slot):
        """A facility with no schedules has an empty facility.schedules list."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.commit()
        assert other.schedules == []

    def test_schedule_query_returns_only_matching_facility(self, db, facility, schedule_slot):
        """Querying Schedule by facility_id excludes records belonging to other facilities."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.add(Schedule(
            facility_id="REC00002", day_of_week="Wednesday",
            start_time=time(9, 0), end_time=time(10, 0),
            status="open", note="",
        ))
        db.session.commit()
        results = Schedule.query.filter_by(facility_id="REC00001").all()
        assert len(results) == 1
        assert results[0].schedule_id == schedule_slot.schedule_id

    def test_route_returns_empty_schedule_for_different_facility(self, client, db, schedule_slot):
        """GET /api/facilities/<other_id>/schedule returns [] when that facility has no slots."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.commit()
        r = client.get("/api/facilities/REC00002/schedule")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_route_does_not_mix_schedules_between_facilities(self, client, db, facility, schedule_slot):
        """GET /api/facilities/<id>/schedule returns only that facility's slots."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.add(Schedule(
            facility_id="REC00002", day_of_week="Tuesday",
            start_time=time(9, 0), end_time=time(10, 0),
            status="class", note="",
        ))
        db.session.commit()
        r1 = client.get("/api/facilities/REC00001/schedule")
        r2 = client.get("/api/facilities/REC00002/schedule")
        assert len(r1.get_json()) == 1
        assert len(r2.get_json()) == 1
        assert r1.get_json()[0]["day_of_week"] == "Monday"
        assert r2.get_json()[0]["day_of_week"] == "Tuesday"

    def test_route_404_when_adding_schedule_to_missing_facility(self, client):
        """POST /api/admin/facilities/<id>/schedule returns 404 for a non-existent facility."""
        r = client.post("/api/admin/facilities/XXXXXXXX/schedule", json={
            "day_of_week": "Tuesday",
            "start_time":  "09:00",
            "end_time":    "10:00",
            "status":      "open",
            "note":        "",
        })
        assert r.status_code == 404


# ── Check-ins FK connection ────────────────────────────────────────────────────

class TestFacilityCheckinConnection:
    def test_checkin_facility_id_matches_facility(self, facility, checkin):
        """checkin.facility_id is identical to the parent facility's facility_id."""
        assert checkin.facility_id == facility.facility_id

    def test_second_facility_has_no_checkins(self, db, checkin):
        """A facility with no check-ins returns an empty list from a direct DB query."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.commit()
        assert CheckIn.query.filter_by(facility_id="REC00002").all() == []

    def test_checkin_query_returns_only_matching_facility(self, db, facility, user, checkin):
        """Querying CheckIn by facility_id excludes records belonging to other facilities."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.add(CheckIn(
            facility_id="REC00002", user_id=user.user_id, day_of_week="Tuesday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="active", note="",
        ))
        db.session.commit()
        results = CheckIn.query.filter_by(facility_id="REC00001").all()
        assert len(results) == 1
        assert results[0].checkin_id == checkin.checkin_id

    def test_route_returns_empty_checkins_for_different_facility(self, client, db, checkin):
        """GET /api/facilities/<other_id>/checkins returns [] when that facility has no check-ins."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.commit()
        r = client.get("/api/facilities/REC00002/checkins")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_route_does_not_mix_checkins_between_facilities(self, client, db, facility, user, checkin):
        """GET /api/facilities/<id>/checkins returns only that facility's active check-ins."""
        other = Facility(**SECOND_FACILITY)
        db.session.add(other)
        db.session.add(CheckIn(
            facility_id="REC00002", user_id=user.user_id, day_of_week="Tuesday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="active", note="",
        ))
        db.session.commit()
        r1 = client.get("/api/facilities/REC00001/checkins")
        r2 = client.get("/api/facilities/REC00002/checkins")
        assert len(r1.get_json()) == 1
        assert len(r2.get_json()) == 1
        assert r1.get_json()[0]["checkin_id"] == checkin.checkin_id

    def test_route_404_when_creating_checkin_for_missing_facility(self, client, user):
        """POST /api/checkins returns 404 when the facility_id does not exist."""
        r = client.post("/api/checkins", json={
            "facility_id": "XXXXXXXX",
            "user_id":     user.user_id,
            "day_of_week": "Monday",
            "start_time":  "14:00",
            "end_time":    "15:00",
            "group_size":  1,
            "note":        "",
        })
        assert r.status_code == 404
