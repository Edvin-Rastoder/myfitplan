
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={
    r"/generate-workout": {
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


if __name__ == "__main__":
    app.run(debug=True)
