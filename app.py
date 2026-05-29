from flask import Flask, render_template

app = Flask(__name__)

spaces = [
    {
        "facility_id": "REC00001",
        "name": "Oldtown Court 1",
        "location": "Student Recreation Center",
        "category": "Recreation",
        "facility_type": "Court",
        "noise_level": "Moderate",
        "description": "Court space used for open recreation activities.",
        "reservation_type": "First-come, first-served",
        "cost_status": "Free for casual use",
        "group_size_limit": 5,
        "current_count": 4,
        "restrictions": "Open rec has lower priority than classes, clubs, and scheduled programs.",
        "rule_notes": "Groups over 5 may need staff approval or rental guidance.",
        "next_step": "Drop in during open rec hours and check posted schedules before using.",
        "schedule": [
            {"day": "Monday", "time": "6:00 AM - 10:45 PM", "status": "Open Rec"},
            {"day": "Tuesday", "time": "10:30 AM - 12:00 PM", "status": "Class/Reserved"}
        ]
    },
    {
        "facility_id": "REC00002",
        "name": "Studio 283",
        "location": "Student Recreation Center",
        "category": "Recreation",
        "facility_type": "Studio",
        "noise_level": "Moderate",
        "description": "Studio space with limited open recreation use.",
        "reservation_type": "Limited drop-in",
        "cost_status": "Depends on use",
        "group_size_limit": 5,
        "current_count": 2,
        "restrictions": "Student org practices and sound system use may not be allowed during open use.",
        "rule_notes": "PE and Rec programs have priority.",
        "next_step": "Check the posted room schedule or ask staff before using.",
        "schedule": [
            {"day": "Monday", "time": "8:30 PM - 10:45 PM", "status": "Open Rec"},
            {"day": "Thursday", "time": "6:30 PM - 10:45 PM", "status": "Open Rec"}
        ]
    },
    {
        "facility_id": "REC00003",
        "name": "Student Tennis Center",
        "location": "Student Recreation Center",
        "category": "Recreation",
        "facility_type": "Court",
        "noise_level": "Moderate",
        "description": "Tennis court space with open recreation and reservation options.",
        "reservation_type": "Reservable",
        "cost_status": "Free/Depends",
        "group_size_limit": 5,
        "current_count": 8,
        "restrictions": "Courts should be used for tennis. Non-marking shoes may be required.",
        "rule_notes": "This is one of the Rec spaces with a reservation option.",
        "next_step": "Check RecWeb or use during posted open recreation hours.",
        "schedule": [
            {"day": "Monday", "time": "5:30 PM - 8:30 PM", "status": "Open/Reservable"},
            {"day": "Friday", "time": "Closed", "status": "Closed"}
        ]
    },
    {
        "facility_id": "STUDY001",
        "name": "EMU Study Lounge",
        "location": "Erb Memorial Union",
        "category": "Study",
        "facility_type": "Study Space",
        "noise_level": "Moderate",
        "description": "Open study area for individual studying, casual work, or meeting between classes.",
        "reservation_type": "Drop-in",
        "cost_status": "Free",
        "group_size_limit": 6,
        "current_count": 12,
        "restrictions": "Shared space. Large groups should avoid taking over seating during busy times.",
        "rule_notes": "Good for students who do not need a completely quiet space.",
        "next_step": "Use as a drop-in study spot. For quieter work, choose a library-style space instead.",
        "schedule": [
            {"day": "Monday", "time": "Morning - Evening", "status": "Usually Available"},
            {"day": "Tuesday", "time": "Morning - Evening", "status": "Usually Available"},
            {"day": "Friday", "time": "Morning - Afternoon", "status": "Usually Available"}
        ]
    },
    {
        "facility_id": "STUDY002",
        "name": "Library Quiet Study Area",
        "location": "Campus Library",
        "category": "Study",
        "facility_type": "Study Space",
        "noise_level": "Quiet",
        "description": "Quiet study area for focused individual work.",
        "reservation_type": "Drop-in",
        "cost_status": "Free",
        "group_size_limit": 2,
        "current_count": 6,
        "restrictions": "Keep noise low. Group conversations should move to a group study room.",
        "rule_notes": "Best for students who want a quiet study environment.",
        "next_step": "Use this space for quiet work. If studying with friends, look for a group study room.",
        "schedule": [
            {"day": "Monday", "time": "Morning - Evening", "status": "Usually Available"},
            {"day": "Wednesday", "time": "Morning - Evening", "status": "Usually Available"},
            {"day": "Friday", "time": "Morning - Afternoon", "status": "Usually Available"}
        ]
    },
    {
        "facility_id": "STUDY003",
        "name": "Dining Hall Study Tables",
        "location": "Campus Dining Area",
        "category": "Study",
        "facility_type": "Dining / Social",
        "noise_level": "Loud",
        "description": "Casual tables that can be used for studying, eating, or group work.",
        "reservation_type": "Drop-in",
        "cost_status": "Free/Depends",
        "group_size_limit": 8,
        "current_count": 18,
        "restrictions": "Can be noisy during meal times. Seating may be limited when dining traffic is high.",
        "rule_notes": "Better for social studying than quiet focused work.",
        "next_step": "Use this space if you are okay with background noise and a casual environment.",
        "schedule": [
            {"day": "Monday", "time": "Lunch - Evening", "status": "Busy"},
            {"day": "Tuesday", "time": "Lunch - Evening", "status": "Busy"},
            {"day": "Thursday", "time": "Afternoon - Evening", "status": "Usually Available"}
        ]
    },
    {
        "facility_id": "MEET001",
        "name": "Small Group Meeting Room",
        "location": "Campus Building",
        "category": "Meeting",
        "facility_type": "Room",
        "noise_level": "Quiet",
        "description": "Small room for group work, project meetings, or club planning.",
        "reservation_type": "May require reservation",
        "cost_status": "Free/Depends",
        "group_size_limit": 6,
        "current_count": 0,
        "restrictions": "May require reservation depending on the building or department.",
        "rule_notes": "Good fit for teams that need a quieter shared workspace.",
        "next_step": "Check the managing office or reservation page before relying on this room.",
        "schedule": [
            {"day": "Monday", "time": "Afternoon", "status": "Sample Available"},
            {"day": "Wednesday", "time": "Afternoon", "status": "Sample Available"}
        ]
    }
]

@app.route("/")
def index():
    return render_template("index.html", spaces=spaces)

if __name__ == "__main__":
    import os
    import threading
    import webbrowser

    url = "http://127.0.0.1:5000"

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(debug=True)