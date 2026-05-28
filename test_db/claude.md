# Duck Space — Project Context for Claude Code

## Project Overview
Duck Space is a web application for the University of Oregon that helps students, clubs, and small groups find and understand campus recreational facilities. It is **not** an official reservation system — it acts as a guide that centralizes fragmented information about spaces, rules, hours, and next steps for using them.

## Tech Stack
- **Frontend:** To be determined (list/map view, mobile responsive)
- **Backend:** Python, Flask (MVC pattern)
- **Database:** PostgreSQL hosted on Neon (serverless)
- **ORM:** SQLAlchemy (via Flask-SQLAlchemy)
- **Deployment:** Vercel
- **Environment:** python-dotenv for environment variables

## Project Structure
```
duck-space/
├── app.py           # Flask app entry point, registers blueprint, initializes db
├── models.py        # SQLAlchemy models (database schema)
├── routes.py        # Flask API routes
├── create_tables.py # Run once to create all tables in Neon
├── .env             # DATABASE_URL (never commit this)
├── .gitignore       # Must include .env
└── vercel.json      # Vercel deployment config
```

## Environment Variables
```
DATABASE_URL=postgresql://user:password@host/dbname
```

## Database Schema

### Table Creation Order (respect foreign key dependencies)
1. facilities
2. rules
3. facility_hours
4. schedules
5. admins
6. users
7. checkins

### facilities
```sql
CREATE TABLE facilities (
    facility_id     CHAR(8) PRIMARY KEY,   -- always 8 chars e.g. REC00001
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(100),
    facility_type   VARCHAR(50),           -- court, room, studio, outdoor
    managing_office VARCHAR(100),
    description     TEXT,
    map_x           FLOAT,
    map_y           FLOAT
);
```

### facility_hours
Hours are stored per day because facilities have different hours on different days.
```sql
CREATE TABLE facility_hours (
    hours_id    SERIAL PRIMARY KEY,
    facility_id CHAR(8) REFERENCES facilities(facility_id),
    day_of_week VARCHAR(10),
    open_time   TIME,
    close_time  TIME
);
```

### rules
One rule record per facility.
```sql
CREATE TABLE rules (
    rule_id          SERIAL PRIMARY KEY,
    facility_id      CHAR(8) REFERENCES facilities(facility_id),
    cost_status      VARCHAR(20),   -- free, paid, depends
    cost_notes       TEXT,
    reservation_type VARCHAR(30),   -- reservable, first-come, drop-in
    group_size_limit INT,           -- groups of 5+ must rent per UO policy
    restrictions     TEXT,
    rule_notes       TEXT
);
```

### schedules
Recurring weekly schedule slots (classes, closures, open rec).
```sql
CREATE TABLE schedules (
    schedule_id SERIAL PRIMARY KEY,
    facility_id CHAR(8) REFERENCES facilities(facility_id),
    day_of_week VARCHAR(10),
    start_time  TIME,
    end_time    TIME,
    status      VARCHAR(20),   -- open, reserved, class, closed
    note        TEXT
);
CREATE INDEX idx_schedules_facility_day ON schedules(facility_id, day_of_week);
```

### admins
```sql
CREATE TABLE admins (
    admin_id      SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL       -- use bcrypt, never plain text
);
```

### users
```sql
CREATE TABLE users (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    duck_id VARCHAR(50) UNIQUE NOT NULL,   -- UO DuckID
    name    VARCHAR(100),
    email   VARCHAR(100)
);
```

### checkins
Students cannot officially reserve rooms. This table records informal check-ins only.
```sql
CREATE TABLE checkins (
    checkin_id  SERIAL PRIMARY KEY,
    facility_id CHAR(8) REFERENCES facilities(facility_id),
    user_id     INTEGER REFERENCES users(user_id),
    day_of_week VARCHAR(10),
    start_time  TIMESTAMP,
    end_time    TIMESTAMP,
    group_size  INTEGER,
    status      VARCHAR(20) DEFAULT 'active',  -- active, completed, cancelled
    note        TEXT
);
CREATE INDEX idx_checkins_facility_day ON checkins(facility_id, day_of_week);
```

## SQLAlchemy Models (models.py)

All models inherit from `db.Model`. Key relationships:
- `Facility` has one `Rule` (uselist=False), many `Schedule` slots, many `FacilityHours`, many `CheckIn`
- `Rule`, `Schedule`, `FacilityHours`, `CheckIn` all have a `facility_id` ForeignKey back to `Facility`
- `CheckIn` also has a `user_id` ForeignKey to `User`
- All models should have a `to_dict()` method for clean JSON serialization

## API Routes (routes.py)

All routes are registered under the `api` Blueprint with prefix `/api`.

### Facility Routes
| Method | Route | Purpose |
|---|---|---|
| GET | `/facilities` | Get all facilities |
| GET | `/facilities/<id>` | Get one facility |
| GET | `/facilities/type/<type>` | Filter by type |
| GET | `/facilities/<id>/rules` | Get rules for a facility |
| GET | `/facilities/<id>/schedule?day=Monday` | Get schedule slots |
| GET | `/facilities/<id>/checkins?day=Monday` | Get active check-ins |
| GET | `/facilities/<id>/hours` | Get hours by day |

### Check-in Routes
| Method | Route | Purpose |
|---|---|---|
| POST | `/checkins` | Record a check-in |
| GET | `/users/<id>/checkins` | View a user's check-ins |
| PUT | `/checkins/<id>/complete` | Mark check-in as completed |
| DELETE | `/checkins/<id>` | Cancel a check-in |

### Group Size Check
| Method | Route | Purpose |
|---|---|---|
| GET | `/facilities/<id>/check-group?size=6` | Check if group size is allowed |

### Admin Routes
| Method | Route | Purpose |
|---|---|---|
| POST | `/admin/login` | Admin login |
| PUT | `/admin/facilities/<id>` | Update facility info |
| PUT | `/admin/facilities/<id>/rules` | Update facility rules |
| POST | `/admin/facilities/<id>/schedule` | Add a schedule slot |
| DELETE | `/admin/checkins/<id>` | Cancel any check-in |

## Key Business Rules
- Groups of 5 or more technically require rental (per interview with Chantelle Russell, Associate Director for Physical Education) but this is not strictly enforced
- Most spaces are first-come first-served — the check-in system is informal, not an official reservation
- Priority of use: open rec < clubs < classes
- The rec center internal schedule is not publicly accessible — Duck Space uses manually entered data
- Admin mode requires password authentication (bcrypt hashed, never plain text)
- All facility IDs are exactly 8 characters (CHAR(8)), e.g. REC00001

## Conflict Checking Logic
When a check-in is created, validate against:
1. Facility hours (start/end must be within open_time and close_time for that day)
2. Schedule table (cannot overlap a class or closure slot)
3. Existing active check-ins (cannot overlap another active check-in)

## Important Notes
- Never store plain text passwords — use bcrypt
- Never commit .env to git
- The DATABASE_URL lives only on the server; users never see it
- Users talk to Flask routes only — they never access the database directly
- Time fields in schedules use TIME; check-in timestamps use TIMESTAMP
- db.create_all() will create tables in the correct dependency order automatically
- Admin routes currently have no auth guard beyond the login route — session/token auth needs to be added