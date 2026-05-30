"""
Tests for conflict detection and the cancel_conflicting_checkins helper.

Covers:
  - schedule_conflict() and checkin_conflict() directly
  - cancel_conflicting_checkins() in isolation
  - Route-level cancellation triggered by POST/PUT to the schedule endpoints
"""
import pytest
from datetime import time
from models import Schedule, CheckIn
from insertion_validation import schedule_conflict, checkin_conflict
from routes import cancel_conflicting_checkins


# ── schedule_conflict ──────────────────────────────────────────────────────────

class TestScheduleConflict:
    def test_no_conflict_when_no_slots_exist(self, facility):
        assert schedule_conflict("REC00001", "Monday", time(10, 0), time(12, 0)) is False

    def test_no_conflict_different_day(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        ))
        db.session.commit()
        assert schedule_conflict("REC00001", "Tuesday", time(10, 0), time(12, 0)) is False

    def test_no_conflict_times_do_not_overlap(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        ))
        db.session.commit()
        assert schedule_conflict("REC00001", "Monday", time(12, 0), time(14, 0)) is False

    def test_conflict_overlapping(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        ))
        db.session.commit()
        assert schedule_conflict("REC00001", "Monday", time(11, 0), time(13, 0)) is True

    def test_conflict_contained_within(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(14, 0),
            status="class", note="",
        ))
        db.session.commit()
        assert schedule_conflict("REC00001", "Monday", time(11, 0), time(12, 0)) is True

    def test_no_conflict_open_status_ignored(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="open", note="",
        ))
        db.session.commit()
        assert schedule_conflict("REC00001", "Monday", time(11, 0), time(13, 0)) is False

    def test_update_exclude_id_prevents_self_conflict(self, facility, db):
        slot = Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        )
        db.session.add(slot)
        db.session.commit()
        assert schedule_conflict(
            "REC00001", "Monday", time(10, 0), time(12, 0),
            exclude_id=slot.schedule_id,
        ) is False

    def test_no_conflict_different_facility(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        ))
        db.session.commit()
        assert schedule_conflict("REC00002", "Monday", time(10, 0), time(12, 0)) is False


# ── checkin_conflict ───────────────────────────────────────────────────────────

class TestCheckinConflict:
    def test_no_conflict_when_empty(self, facility):
        assert checkin_conflict("REC00001", "Monday", time(10, 0), time(12, 0)) is False

    def test_conflict_with_non_open_schedule(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="class", note="",
        ))
        db.session.commit()
        assert checkin_conflict("REC00001", "Monday", time(11, 0), time(13, 0)) is True

    def test_no_conflict_with_open_schedule(self, facility, db):
        db.session.add(Schedule(
            facility_id="REC00001", day_of_week="Monday",
            start_time=time(10, 0), end_time=time(12, 0),
            status="open", note="",
        ))
        db.session.commit()
        assert checkin_conflict("REC00001", "Monday", time(11, 0), time(13, 0)) is False

    def test_conflict_with_active_checkin(self, facility, user, db):
        db.session.add(CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(16, 0),
            group_size=1, status="active", note="",
        ))
        db.session.commit()
        assert checkin_conflict("REC00001", "Monday", time(15, 0), time(17, 0)) is True

    def test_no_conflict_with_cancelled_checkin(self, facility, user, db):
        db.session.add(CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(16, 0),
            group_size=1, status="cancelled", note="",
        ))
        db.session.commit()
        assert checkin_conflict("REC00001", "Monday", time(15, 0), time(17, 0)) is False

    def test_no_conflict_different_day(self, facility, user, db):
        db.session.add(CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(16, 0),
            group_size=1, status="active", note="",
        ))
        db.session.commit()
        assert checkin_conflict("REC00001", "Tuesday", time(14, 0), time(16, 0)) is False

    def test_update_exclude_id_prevents_self_conflict(self, facility, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(16, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        assert checkin_conflict(
            "REC00001", "Monday", time(14, 0), time(16, 0),
            exclude_id=ci.checkin_id,
        ) is False


# ── cancel_conflicting_checkins ────────────────────────────────────────────────

class TestCancelConflictingCheckins:
    def test_deletes_overlapping_active_checkin(self, facility, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        cancel_conflicting_checkins("REC00001", "Monday", time(9, 0), time(12, 0), "class")
        db.session.commit()

        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is None

    def test_leaves_non_overlapping_checkin(self, facility, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(14, 0), end_time=time(15, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        cancel_conflicting_checkins("REC00001", "Monday", time(9, 0), time(12, 0), "class")
        db.session.commit()

        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is not None

    def test_no_op_for_open_status(self, facility, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        cancel_conflicting_checkins("REC00001", "Monday", time(9, 0), time(12, 0), "open")
        db.session.commit()

        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is not None

    def test_leaves_cancelled_checkin_alone(self, facility, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="cancelled", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        cancel_conflicting_checkins("REC00001", "Monday", time(9, 0), time(12, 0), "class")
        db.session.commit()

        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is not None

    def test_deletes_multiple_overlapping_checkins(self, facility, user, db):
        ids = []
        for start, end in [(time(9, 30), time(10, 30)), (time(10, 45), time(11, 30))]:
            ci = CheckIn(
                facility_id="REC00001", user_id=user.user_id, day_of_week="Monday",
                start_time=start, end_time=end,
                group_size=1, status="active", note="",
            )
            db.session.add(ci)
            db.session.flush()
            ids.append(ci.checkin_id)
        db.session.commit()

        cancel_conflicting_checkins("REC00001", "Monday", time(9, 0), time(12, 0), "class")
        db.session.commit()

        for ci_id in ids:
            assert CheckIn.query.filter_by(checkin_id=ci_id).first() is None


# ── Route-level cancellation ───────────────────────────────────────────────────

class TestCancelViaRoutes:
    def test_add_schedule_cancels_overlapping_checkin(self, client, facility, rule, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Wednesday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        r = client.post("/api/admin/facilities/REC00001/schedule", json={
            "day_of_week": "Wednesday",
            "start_time":  "09:00",
            "end_time":    "12:00",
            "status":      "class",
            "note":        "",
        })
        assert r.status_code == 201
        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is None

    def test_add_open_schedule_does_not_cancel_checkins(self, client, facility, rule, user, db):
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Wednesday",
            start_time=time(10, 0), end_time=time(11, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        r = client.post("/api/admin/facilities/REC00001/schedule", json={
            "day_of_week": "Wednesday",
            "start_time":  "09:00",
            "end_time":    "12:00",
            "status":      "open",
            "note":        "",
        })
        assert r.status_code == 201
        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is not None

    def test_update_schedule_to_non_open_cancels_checkin(self, client, facility, rule, user, db):
        slot = Schedule(
            facility_id="REC00001", day_of_week="Thursday",
            start_time=time(9, 0), end_time=time(11, 0),
            status="open", note="",
        )
        db.session.add(slot)
        db.session.commit()

        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Thursday",
            start_time=time(9, 30), end_time=time(10, 30),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        # Expand time range slightly so duplicate_schedule doesn't flag it as a duplicate
        r = client.put(
            f"/api/admin/facilities/REC00001/schedule/{slot.schedule_id}",
            json={"end_time": "12:00", "status": "class"},
        )
        assert r.status_code == 200
        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is None

    def test_update_schedule_to_open_does_not_cancel_checkins(self, client, facility, rule, user, db):
        slot = Schedule(
            facility_id="REC00001", day_of_week="Friday",
            start_time=time(9, 0), end_time=time(11, 0),
            status="class", note="",
        )
        db.session.add(slot)
        db.session.commit()

        # Checkin OUTSIDE the original slot time — won't be cancelled regardless
        ci = CheckIn(
            facility_id="REC00001", user_id=user.user_id, day_of_week="Friday",
            start_time=time(12, 0), end_time=time(13, 0),
            group_size=1, status="active", note="",
        )
        db.session.add(ci)
        db.session.commit()
        ci_id = ci.checkin_id

        # Update Schedule to open and make it conflict with Checkin
        r = client.put(
            f"/api/admin/facilities/REC00001/schedule/{slot.schedule_id}",
            json={"status": "open", "end_time": "13:00"},
        )
        assert r.status_code == 200
        assert CheckIn.query.filter_by(checkin_id=ci_id).first() is not None
