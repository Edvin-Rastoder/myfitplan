from database.db import connect
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlite3 import IntegrityError
import secrets
import json
from pathlib import Path

exercise_file = Path(__file__).parent / "exercises.json"

with open(exercise_file, "r", encoding="utf-8") as file:
    exercises = json.load(file)

print("Loaded", len(exercises), "exercises")
print(exercises[0])
beginner_exercises = [
    exercise for exercise in exercises
    if exercise["level"] == "beginner"
]

print("Beginner exercises:", len(beginner_exercises))

app = Flask(__name__)

CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": ["http://127.0.0.1:5500", "http://localhost:5500"]
    }
})

@app.route("/")
def home():
    return "Hello! Connected to myfitplan!"


@app.route("/generate-workout", methods=["POST"])
def generate_workout():
    user_preferences = request.get_json()

    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in to generate a workout"}), 401


    print("Received preferences:", user_preferences)

    goal = user_preferences["goal"]
    experience = user_preferences["experience"]
    workout_days = user_preferences["days"]
    duration = user_preferences["duration"]

    
    if experience == "advanced":
        allowed_levels = ["intermediate", "expert"]
    else:
        allowed_levels = [experience]

    matching_exercises = [
        exercise for exercise in exercises
        if exercise["level"] in allowed_levels
        and exercise["category"] == "strength"
    ]



    for muscle in ["quadriceps", "hamstrings", "chest", "lats"]:
        count = sum(
            1 for exercise in matching_exercises
            if muscle in exercise["primaryMuscles"]
        )
        print(muscle, count)


    muscle_groups_by_workout = {
        "Full Body": ["quadriceps", "hamstrings", "chest", "lats"],
        "Upper": ["chest", "lats", "shoulders", "biceps", "triceps"],
        "Lower": ["quadriceps", "quadriceps", "hamstrings", "glutes", "calves"],
        "Push": ["chest", "chest", "shoulders", "shoulders", "triceps"],
        "Pull": ["lats", "lats", "shoulders", "biceps", "biceps"],
        "Legs": ["quadriceps", "quadriceps", "hamstrings", "glutes", "calves"]
    }
    print("Full Body muscles:", muscle_groups_by_workout["Full Body"])


    print("Matching exercises:", len(matching_exercises))

    workout_plan = []

    if goal == "muscle_gain":
        if workout_days == 3:
            if experience == "beginner":
                workout_plan = ["Full Body", "Full Body", "Full Body"]
            else:
                workout_plan = ["Upper", "Lower", "Full Body"]

        elif workout_days == 5:
            if experience == "beginner":
                workout_plan = ["Upper", "Lower", "Upper", "Lower", "Full Body"]
            else:
                workout_plan = ["Push", "Pull", "Legs", "Upper", "Lower"]

        elif workout_days == 7:
            if experience == "beginner":
                workout_plan = [
                    "Upper", "Lower", "Active Recovery",
                    "Upper", "Lower", "Active Recovery", "Rest"
                ]
            elif experience == "intermediate":
                workout_plan = [
                    "Push", "Pull", "Legs", "Active Recovery",
                    "Upper", "Lower", "Rest"
                ]
            elif experience == "advanced":
                workout_plan = [
                    "Push", "Pull", "Legs",
                    "Push", "Pull", "Legs", "Rest"
                ]
    elif goal == "weight_loss":
        if workout_days == 3:
            workout_plan = ["Full Body", "Cardio", "Full Body"]
        elif workout_days == 5:
            workout_plan = ["Upper", "Lower", "Cardio", "Full Body", "Cardio"]
        elif workout_days == 7:
            workout_plan = [
                "Upper", "Cardio", "Lower",
                "Cardio", "Full Body", "Active Recovery", "Rest"
            ]

    elif goal == "endurance":
        if workout_days == 3:
            workout_plan = ["Cardio", "Full Body", "Cardio"]
        elif workout_days == 5:
            workout_plan = [
                "Cardio", "Full Body", "Cardio",
                "Active Recovery", "Cardio"
            ]
        elif workout_days == 7:
            workout_plan = [
                "Cardio", "Full Body", "Cardio",
                "Active Recovery", "Cardio", "Cardio", "Rest"
            ]
                    

    cardio_exercises = [
        {"name": "Treadmill Walking"},
        {"name": "Stationary Cycling"},
        {"name": "Jump Rope"},
        {"name": "Jogging"},
        {"name": "Elliptical"}
    ]

    weekly_workouts = []

    for day_number, workout_type in enumerate(workout_plan, start=1):
        print("Day:", day_number, "Workout:", workout_type)

        daily_workout = {
            "day": day_number,
            "type": workout_type,
            "exercises": []
        }
        if workout_type in muscle_groups_by_workout:
            daily_workout["muscle_groups"] = muscle_groups_by_workout[workout_type]
        else:
            daily_workout["muscle_groups"] = []

        if workout_type == "Cardio":
            daily_workout["exercises"] = cardio_exercises

        
        for muscle in daily_workout["muscle_groups"]:
            for exercise in matching_exercises:
                if muscle in exercise["primaryMuscles"]:
                    if exercise not in daily_workout["exercises"]:
                        daily_workout["exercises"].append(exercise)
                        break

        if workout_type not in ["Rest", "Active Recovery"]:
            if duration == 15:
                exercise_count = 2
            elif duration == 30:
                exercise_count = 3
            elif duration == 45:
                exercise_count = 4
            else:
                exercise_count = 5

            daily_workout["exercises"] = daily_workout["exercises"][:exercise_count]

        weekly_workouts.append(daily_workout)
        print("Selected duration:", duration)

    for day in weekly_workouts:
        print(
            day["day"],
            day["type"],
            "Exercises:",
            len(day["exercises"])
        )
        


    selected_exercises = []


    # Determine workout type
    if goal == "muscle_gain":
        workout_type = "Strength Training"
    elif goal == "weight_loss":
        workout_type = "Cardio and Strength Training"
    elif goal == "endurance":
        workout_type = "Endurance Training"
    else:
        workout_type = "General Fitness"

    # Determine workout level
    if experience == "beginner":
        workout_level = "Beginner Level"
    elif experience == "intermediate":
        workout_level = "Intermediate Level"
    elif experience == "advanced":
        workout_level = "Advanced Level"
    else:
        workout_level = "General Level"


    if workout_plan:
        from datetime import timedelta

        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=6)

        with connect() as conn:
            plan_id = conn.execute(
                "INSERT INTO workout_plans (user_id, start_date, end_date) VALUES (?, ?, ?)",
                (user_id, start_date.isoformat(), end_date.isoformat())
            ).lastrowid

            print("Saved workout plan ID:", plan_id)

            for day in weekly_workouts:
                day_id = conn.execute(
                    "INSERT INTO workout_days (plan_id, weekday) VALUES (?, ?)",
                    (plan_id, ((start_date.weekday() + day["day"] - 1) % 7) + 1)
                ).lastrowid

                for exercise in day["exercises"]:
                    conn.execute(
                        """
                        INSERT INTO workout_exercises
                        (workout_day_id, exercise_name, sets_count, repetitions_count)
                        VALUES (?, ?, ?, ?)
                        """,
                        (day_id, exercise["name"], 3, 10)
                    )



    return jsonify({
        "message": "Workout generated successfully!",
        "workout_plan": workout_plan,
        "weekly_workouts": weekly_workouts,
        "workout_type": workout_type,
        "workout_level": workout_level
    })



@app.route("/create-user", methods=["POST"])
def create_user():
    data = request.get_json()

    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    password_hash = data.get("password_hash") or None
    sms_reminders_enabled = 1 if data.get("sms_reminders_enabled") == "true" else 0
    sms_consent_at = None
    
    if not (email or phone) or not password_hash:
        return jsonify({"error": "Email or phone, and password are required"}), 400

    if sms_reminders_enabled and not phone:
        return jsonify({"error": "Phone number is required for SMS reminders to be enabled"}), 400

    if sms_reminders_enabled:
        sms_consent_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    
    password_hash = generate_password_hash(password_hash, method="pbkdf2:sha256")

    
    # preparing a Cookie/session token for the user
    session_token = secrets.token_urlsafe(32)
    user_agent = request.headers.get("User-Agent", "")[:512] 
    
    try:
        with connect() as conn:
            user_id = conn.execute("""
                INSERT INTO users (email, phone, password_hash, sms_reminders_enabled, sms_consent_at)
                VALUES (?, ?, ?, ?, ?) """, 
                [email, phone, password_hash, sms_reminders_enabled, sms_consent_at]).lastrowid
            
            conn.execute("""INSERT INTO sessions (user_id, session_token, user_agent) 
                                    VALUES (?, ?, ?)""",
                                    [user_id, session_token, user_agent])    
    except IntegrityError as e:
        if "UNIQUE" in str(e):
            return jsonify({"error": "An account with this email or phone already exists"}), 409       
        return jsonify({"error": "Invalid email or phone format"}), 400
      
    
    resp = jsonify({"user_id": user_id})
    resp.set_cookie("session_token", session_token, httponly=True, samesite="Lax", max_age=24 * 3600)
    
    return resp, 201

@app.route("/login", methods=["POST"])
def login_user():
    data = request.get_json()
    
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    password_hash = data.get("password_hash") or None
    session_token = secrets.token_urlsafe(32)
    # in case we will want user to see their active sessions later
    user_agent = request.headers.get("User-Agent", "")[:512] 
    
    if not (email != "" or phone != "") or not password_hash:
        return jsonify({"error": "Email or phone, and password are required"}), 400
    
    with connect() as conn:
        user = conn.execute("SELECT user_id, password_hash FROM users WHERE email = ? OR phone = ?",
                            [email, phone]).fetchone()
        
        if user is None or not check_password_hash(user["password_hash"], password_hash):
            return jsonify({"error": "Incorrect email, phone, or password"}), 401
    
        conn.execute("""INSERT INTO sessions (user_id, session_token, user_agent) 
                        VALUES (?, ?, ?)""",
                        [user["user_id"], session_token, user_agent])
    
    resp = jsonify({"user_id": user["user_id"]})
    resp.set_cookie("session_token", session_token, httponly=True, samesite="Lax", max_age=24 * 3600)
    
    return resp, 200


@app.route("/logout", methods=["POST"])
def logout_user():
    session_token = request.cookies.get("session_token", "")
    
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE session_token = ? ", [session_token])

    resp = jsonify({"message": "Logged out"})
    resp.delete_cookie("session_token")
    
    return resp, 200

# helper method to quickly check user authentication
# returns user_id if authentication is valid
def check_auth():
    session_token = request.cookies.get("session_token", "")
    
    with connect() as conn:
        match = conn.execute("""SELECT user_id FROM sessions WHERE session_token = ? 
                                AND expires_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now')""",
                                [session_token]).fetchone()

    return match["user_id"] if match else None


if __name__ == "__main__":
    app.run(debug=True)
