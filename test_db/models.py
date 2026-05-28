from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Facility(db.Model):
    __tablename__ = "facilities"
    
    facility_id     = db.Column(db.CHAR(8), primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    location        = db.Column(db.String(100))
    facility_type   = db.Column(db.String(50))
    managing_office = db.Column(db.String(100))
    description     = db.Column(db.Text)
    map_x           = db.Column(db.Float)
    map_y           = db.Column(db.Float)
    
    # Relationships
    rules     = db.relationship("Rule", backref="facility", uselist=False)
    schedules = db.relationship("Schedule", backref="facility")
    hours = db.relationship("facility_hours", backref="facility")

class Rule(db.Model):
    __tablename__ = "rules"
    
    rule_id          = db.Column(db.Integer, primary_key=True)
    facility_id      = db.Column(db.CHAR(8), db.ForeignKey("facilities.facility_id"))
    cost_status      = db.Column(db.String(20))
    cost_notes       = db.Column(db.Text)
    reservation_type = db.Column(db.String(30))
    group_size_limit = db.Column(db.Integer)
    restrictions     = db.Column(db.Text)
    rule_notes       = db.Column(db.Text)

class Facility_Hours(db.Model):
    __tablename__ = "facility_hours"

    hours_id  = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.CHAR(8), db.ForeignKey("facilities.facility_id"))
    day_of_week = db.Column(db.CHAR(10))
    open_time = db.Column(db.Time)
    close_time = db.Column(db.Time)

class Schedule(db.Model):
    __tablename__ = "schedules"
    __table_args__ = (
        db.Index("idx_schedules_facility_day", "facility_id", "day_of_week"),
    )
    
    schedule_id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.CHAR(8), db.ForeignKey("facilities.facility_id"))
    day_of_week = db.Column(db.String(10))
    start_time  = db.Column(db.Time)
    end_time    = db.Column(db.Time)
    status      = db.Column(db.String(20))  # open, reserved, class, closed
    note        = db.Column(db.Text)

class Admin(db.Model):
    __tablename__ = "admins"
    
    admin_id      = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)

class User(db.Model):
    __tablename__ = "users"
    
    user_id    = db.Column(db.Integer, primary_key=True)
    duck_id    = db.Column(db.String(50), unique=True, nullable=False)  # UO DuckID
    name       = db.Column(db.String(100))
    email      = db.Column(db.String(100))
    
    reservations = db.relationship("Reservation", backref="user")

class CheckIn(db.Model):
    __tablename__ = "checkins"
    __table_args__ = (
        db.Index("idx_checkins_facility_day", "facility_id", "day_of_week"),
    )
    
    checkin_id  = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.CHAR(8), db.ForeignKey("facilities.facility_id"))
    user_id     = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    day_of_week = db.Column(db.String(10))
    start_time  = db.Column(db.Time)
    end_time    = db.Column(db.Time)
    group_size  = db.Column(db.Integer)
    status      = db.Column(db.String(20), default="active")  # active, completed, cancelled
    note        = db.Column(db.Text)