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


@app.route("/exercises", methods=["GET"])
def get_exercises():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    return jsonify(exercises)


@app.route("/swap-exercise", methods=["POST"])
def swap_exercise():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    data = request.get_json(silent=True) or {}
    workout_exercise_id = data.get("workout_exercise_id")
    new_exercise_name = data.get("new_exercise_name")

    if type(workout_exercise_id) is not int or not isinstance(new_exercise_name, str):
        return jsonify({"error": "Invalid exercise selection"}), 400

    new_exercise = next(
        (exercise for exercise in exercises if exercise["name"] == new_exercise_name),
        None
    )

    if new_exercise is None:
        return jsonify({"error": "Replacement exercise not found"}), 404

    with connect() as conn:
        current = conn.execute("""
            SELECT we.exercise_name
            FROM workout_exercises we
            JOIN workout_days wd ON we.workout_day_id = wd.workout_day_id
            JOIN workout_plans wp ON wd.plan_id = wp.plan_id
            WHERE we.workout_exercise_id = ?
            AND wp.user_id = ?
            AND wp.plan_id = (
                SELECT MAX(plan_id)
                FROM workout_plans
                WHERE user_id = ?
            )
        """, (workout_exercise_id, user_id, user_id)).fetchone()

        if current is None:
            return jsonify({"error": "Workout exercise not found"}), 404

        old_exercise = next(
            (exercise for exercise in exercises if exercise["name"] == current["exercise_name"]),
            None
        )

        if old_exercise is None:
            return jsonify({"error": "Original exercise not found"}), 404

        if not set(old_exercise.get("primaryMuscles", [])) & set(new_exercise.get("primaryMuscles", [])):
            return jsonify({"error": "Exercises must target the same muscle"}), 400

        conn.execute("""
            UPDATE workout_exercises
            SET exercise_name = ?
            WHERE workout_exercise_id = ?
        """, (new_exercise_name, workout_exercise_id))

    return jsonify({"message": "Exercise swapped successfully"})



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


    if goal == "muscle_gain":
        sets_count = 3
        repetitions_count = 10
    elif goal == "weight_loss":
        sets_count = 3
        repetitions_count = 12
    elif goal == "endurance":
        sets_count = 2
        repetitions_count = 15
    else:
        sets_count = 3
        repetitions_count = 10


    
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
                "INSERT INTO workout_plans (user_id, start_date, end_date, duration_minutes) VALUES (?, ?, ?, ?)",
                (user_id, start_date.isoformat(), end_date.isoformat(), duration)
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
                        (day_id, exercise["name"], sets_count, repetitions_count)
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

    name = (data.get("name") or "").strip() or None
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
                INSERT INTO users (name, email, phone, password_hash, sms_reminders_enabled, sms_consent_at)
                VALUES (?, ?, ?, ?, ?, ?) """, 
                [name, email, phone, password_hash, sms_reminders_enabled, sms_consent_at]).lastrowid
            
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


@app.route("/me", methods=["GET"])
def get_current_user():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    with connect() as conn:
        user = conn.execute(
            "SELECT name FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"name": user["name"]})

@app.route("/my-workouts", methods=["GET"])
def get_my_workouts():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    with connect() as conn:
        plan = conn.execute("""
            SELECT plan_id, start_date, end_date, duration_minutes
            FROM workout_plans
            WHERE user_id = ?
            ORDER BY plan_id DESC
            LIMIT 1
        """, (user_id,)).fetchone()

        if plan is None:
            return jsonify({"workouts": []})

        days = conn.execute("""
            SELECT workout_day_id, weekday
            FROM workout_days
            WHERE plan_id = ?
            ORDER BY weekday
        """, (plan["plan_id"],)).fetchall()

        workouts = []

        for day in days:
            exercises = conn.execute("""
                SELECT workout_exercise_id, exercise_name, sets_count, repetitions_count
                FROM workout_exercises
                WHERE workout_day_id = ?
                ORDER BY workout_exercise_id
            """, (day["workout_day_id"],)).fetchall()

            workouts.append({
                "workout_day_id": day["workout_day_id"],
                "weekday": day["weekday"],
                "exercises": [dict(exercise) for exercise in exercises]
            })

    return jsonify({
        "plan_id": plan["plan_id"],
        "start_date": plan["start_date"],
        "end_date": plan["end_date"],
        "duration_minutes": plan["duration_minutes"],
        "workouts": workouts
    })


@app.route("/update-schedule", methods=["POST"])
def update_schedule():
    user_id = check_auth()

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    weekdays = data.get("weekdays")

    if (
        not isinstance(weekdays, list)
        or not weekdays
        or any(type(day) is not int or day < 1 or day > 7 for day in weekdays)
        or len(weekdays) != len(set(weekdays))
    ):
        return jsonify({"error": "Invalid workout days"}), 400

    try:
        with connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT plan_id
                FROM workout_plans
                WHERE user_id = ?
                ORDER BY plan_id DESC
                LIMIT 1
            """, (user_id,))

            plan = cursor.fetchone()

            if not plan:
                return jsonify({"error": "No workout plan found"}), 404

            cursor.execute("""
                SELECT workout_day_id
                FROM workout_days
                WHERE plan_id = ?
                AND workout_day_id IN (
                    SELECT workout_day_id
                    FROM workout_exercises
                )
                ORDER BY weekday
            """, (plan[0],))

            workout_days = cursor.fetchall()

            if len(weekdays) != len(workout_days):
                return jsonify({
                    "error": f"Please select exactly {len(workout_days)} workout days"
                }), 400

            weekdays.sort()

            for workout_day, weekday in zip(workout_days, weekdays):
                cursor.execute("""
                    UPDATE workout_days
                    SET weekday = ?
                    WHERE workout_day_id = ?
                """, (weekday, workout_day[0]))

            conn.commit()

        return jsonify({"message": "Schedule updated successfully"}), 200

    except Exception as error:
        print("Schedule update error:", error)
        return jsonify({"error": "Failed to update schedule"}), 500



@app.route("/complete-workout", methods=["POST"])
def complete_workout():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid workout data"}), 400

    workout_day_id = data.get("workout_day_id")
    exercises = data.get("exercises")

    duration_seconds = data.get("duration_seconds")

    if type(duration_seconds) is not int or duration_seconds < 0:
        return jsonify({"error": "Invalid workout duration"}), 400


    if type(workout_day_id) is not int or workout_day_id < 1:
        return jsonify({"error": "Invalid workout day"}), 400

    if not isinstance(exercises, list) or not exercises:
        return jsonify({"error": "No completed exercises"}), 400

    try:
        with connect() as conn:
            workout = conn.execute("""
                SELECT wd.workout_day_id
                FROM workout_days wd
                JOIN workout_plans wp ON wd.plan_id = wp.plan_id
                WHERE wd.workout_day_id = ? AND wp.user_id = ?
            """, (workout_day_id, user_id)).fetchone()

            if workout is None:
                return jsonify({"error": "Workout not found"}), 404

            completed_exercises = []
            seen_exercises = set()

            for exercise in exercises:
                if not isinstance(exercise, dict):
                    raise ValueError("Invalid exercise data")

                exercise_id = exercise.get("workout_exercise_id")
                sets = exercise.get("sets")

                if type(exercise_id) is not int or exercise_id < 1:
                    raise ValueError("Invalid exercise ID")

                if exercise_id in seen_exercises:
                    raise ValueError("Duplicate exercise")

                seen_exercises.add(exercise_id)

                if not isinstance(sets, list) or not sets:
                    raise ValueError("No completed sets")

                saved_exercise = conn.execute("""
                    SELECT workout_exercise_id, exercise_name, sets_count
                    FROM workout_exercises
                    WHERE workout_exercise_id = ?
                    AND workout_day_id = ?
                """, (exercise_id, workout_day_id)).fetchone()

                if saved_exercise is None:
                    raise ValueError("Exercise does not belong to this workout")

                completed_sets = []
                seen_sets = set()

                for workout_set in sets:
                    if not isinstance(workout_set, dict):
                        raise ValueError("Invalid set data")

                    set_number = workout_set.get("set_number")
                    reps = workout_set.get("repetitions")
                    weight = workout_set.get("weight")

                    if (type(set_number) is not int or
                            not 1 <= set_number <= saved_exercise["sets_count"]):
                        raise ValueError("Invalid set number")

                    if set_number in seen_sets:
                        raise ValueError("Duplicate set number")

                    seen_sets.add(set_number)

                    if type(reps) is not int or reps < 0:
                        raise ValueError("Invalid repetitions")

                    if weight is not None:
                        if (type(weight) not in (int, float) or
                                not 0 <= weight < float("inf")):
                            raise ValueError("Invalid weight")

                    completed_sets.append((set_number, reps, weight))

                completed_exercises.append(
                    (saved_exercise, completed_sets)
                )

            completed_on = datetime.now().date().isoformat()

            workout_log_id = conn.execute("""
                INSERT INTO workout_logs
                (user_id, workout_day_id, completed_on, duration_seconds)
                VALUES (?, ?, ?, ?)
            """, (user_id, workout_day_id, completed_on, duration_seconds)).lastrowid


            for exercise, sets in completed_exercises:
                exercise_log_id = conn.execute("""
                    INSERT INTO exercise_logs
                    (workout_log_id, workout_exercise_id, exercise_name)
                    VALUES (?, ?, ?)
                """, (
                    workout_log_id,
                    exercise["workout_exercise_id"],
                    exercise["exercise_name"]
                )).lastrowid

                for set_number, reps, weight in sets:
                    conn.execute("""
                        INSERT INTO set_logs
                        (exercise_log_id, set_number, repetitions, weight)
                        VALUES (?, ?, ?, ?)
                    """, (exercise_log_id, set_number, reps, weight))

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({
        "message": "Workout saved successfully!",
        "workout_log_id": workout_log_id
    }), 201


@app.route("/workout-stats", methods=["GET"])
def workout_stats():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    with connect() as conn:
        total_workouts = conn.execute("""
            SELECT COUNT(*) AS total
            FROM workout_logs
            WHERE user_id = ?
        """, (user_id,)).fetchone()["total"]

        last_workout = conn.execute("""
            SELECT workout_log_id, workout_day_id, completed_on
            FROM workout_logs
            WHERE user_id = ?
            ORDER BY completed_on DESC, workout_log_id DESC
            LIMIT 1
        """, (user_id,)).fetchone()

        last_workout_data = None

        if last_workout:
            completed_sets = conn.execute("""
                SELECT COUNT(*) AS total
                FROM set_logs sl
                JOIN exercise_logs el
                ON sl.exercise_log_id = el.exercise_log_id
                WHERE el.workout_log_id = ?
            """, (last_workout["workout_log_id"],)).fetchone()["total"]

            planned_sets = conn.execute("""
                SELECT COALESCE(SUM(sets_count), 0) AS total
                FROM workout_exercises
                WHERE workout_day_id = ?
            """, (last_workout["workout_day_id"],)).fetchone()["total"]

            last_workout_data = {
                "date": last_workout["completed_on"],
                "sets_completed": completed_sets,
                "sets_planned": planned_sets
            }

        weekly_completed = conn.execute("""
            SELECT COUNT(*) AS total
            FROM workout_logs
            WHERE user_id = ?
            AND completed_on BETWEEN date('now', 'localtime', 'weekday 0', '-6 days')
            AND date('now', 'localtime', 'weekday 0')
        """, (user_id,)).fetchone()["total"]

    return jsonify({
        "total_workouts": total_workouts,
        "weekly_completed": weekly_completed,
        "last_workout": last_workout_data
    })


@app.route("/workout-history", methods=["GET"])
def workout_history():
    user_id = check_auth()

    if user_id is None:
        return jsonify({"error": "You must be logged in"}), 401

    with connect() as conn:
        workouts = conn.execute("""
            SELECT workout_log_id, completed_on, workout_day_id, duration_seconds
            FROM workout_logs
            WHERE user_id = ?
            ORDER BY completed_on DESC, workout_log_id DESC
        """, (user_id,)).fetchall()

        history = []

        for workout in workouts:
            exercise_rows = conn.execute("""
                SELECT exercise_log_id, exercise_name
                FROM exercise_logs
                WHERE workout_log_id = ?
                ORDER BY exercise_log_id
            """, (workout["workout_log_id"],)).fetchall()

            workout_exercises = []
            total_sets = 0
            total_weight = 0

            for exercise in exercise_rows:
                sets = conn.execute("""
                    SELECT set_number, repetitions, weight
                    FROM set_logs
                    WHERE exercise_log_id = ?
                    ORDER BY set_number
                """, (exercise["exercise_log_id"],)).fetchall()

                saved_sets = [dict(s) for s in sets]

                total_sets += len(saved_sets)
                total_weight += sum(
                    s["weight"] * s["repetitions"]
                    for s in saved_sets
                    if s["weight"] is not None
                )

                workout_exercises.append({
                    "exercise_name": exercise["exercise_name"],
                    "sets": saved_sets
                })

            history.append({
                "workout_log_id": workout["workout_log_id"],
                "completed_on": workout["completed_on"],
                "workout_day_id": workout["workout_day_id"],
                "duration_seconds": workout["duration_seconds"],
                "total_sets": total_sets,
                "total_weight": total_weight,
                "exercises": workout_exercises
            })

    return jsonify({"history": history})


if __name__ == "__main__":
    app.run(debug=True)
