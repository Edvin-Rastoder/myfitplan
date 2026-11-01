from database.db import connect
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlite3 import IntegrityError
import secrets

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

    print("Received preferences:", user_preferences)

    goal = user_preferences["goal"]
    experience = user_preferences["experience"]
    workout_days = user_preferences["days"]
    duration = user_preferences["duration"]

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

    if workout_days == 3:
        workout_days = 3  
    elif workout_days == 5:
        workout_days = 5
    elif workout_days == 7:
        workout_days = 7

    return jsonify({
    "message": "Workout generated successfully!",
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

    password_hash = generate_password_hash(password_hash)
    
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
