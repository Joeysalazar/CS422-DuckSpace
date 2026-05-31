"""
utils/
======
Business-logic layer for DuckSpace.
 
This package sits between Kai's database/API routes and the raw SQL —
import from here instead of reaching into individual modules directly.
 
Quick reference
---------------
from utils import (
    # Check-in lifecycle
    create_checkin,
    cancel_checkin,
    get_checkin,
    get_active_checkins,
 
    # Occupancy
    get_current_occupancy,
    expire_old_checkins,
 
    # Facility status
    get_group_size_limit,
    is_at_capacity,
    get_busyness_label,
    is_open_now,
    get_todays_hours,
    get_facility_status_snapshot,
)
"""
 
from checkin_manager import (
    create_checkin,
    cancel_checkin,
    get_checkin,
    get_active_checkins,
)
 
from occupancy_manager import (
    get_current_occupancy,
    expire_old_checkins,
)
 
from facility_manager import (
    get_group_size_limit,
    is_at_capacity,
    get_busyness_label,
    is_open_now,
    get_todays_hours,
    get_facility_status_snapshot,
)
 
__all__ = [
    # checkin_manager
    "create_checkin",
    "cancel_checkin",
    "get_checkin",
    "get_active_checkins",
    # occupancy_manager
    "get_current_occupancy",
    "expire_old_checkins",
    # facility_manager
    "get_group_size_limit",
    "is_at_capacity",
    "get_busyness_label",
    "is_open_now",
    "get_todays_hours",
    "get_facility_status_snapshot",
]