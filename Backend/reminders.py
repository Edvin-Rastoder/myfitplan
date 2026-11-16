# Constraints on the twilio and resend:
# 
#   Since both are free trial, they only support linked developer emails and phone numbers
#   I will purchase tokens if needed later, according to our demonstration plan
#   Otherwise, if you want to test it out, use your RESEND and TWILIO API informaiton
#   or contact me on Discord

import os
from datetime import date
from pathlib import Path

import resend
from twilio.rest import Client

from database.db import connect

ENV_PATH = Path(__file__).resolve().parent / ".env"

# Default account for development in Resend
DEFAULT_FROM_EMAIL = "MyFitPlan <onboarding@resend.dev>"
EMAIL_SUBJECT = "Your MyFitPlan workout is today"


def load_env_file(path=ENV_PATH):
    # Copy KEY=value lines from Backend/.env into the environment
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def send_email(to, subject, text):
    resend.api_key = os.environ["RESEND_API_KEY"]
    params: resend.Emails.SendParams = {
        "from": os.environ.get("RESEND_FROM_EMAIL") or DEFAULT_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    
    resend.Emails.send(params)


def send_sms(to, body):
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    client.messages.create(to=to, from_=os.environ["TWILIO_FROM_NUMBER"], body=body)


def get_todays_exercises(conn, user_id, today):
    # retrieves user exercises for today (if not a workout day -> empty)
    rows = conn.execute("""
        SELECT we.exercise_name
        FROM workout_exercises we
        JOIN workout_days wd ON wd.workout_day_id = we.workout_day_id
        WHERE wd.plan_id = (SELECT MAX(plan_id) FROM workout_plans WHERE user_id = ?)
        AND wd.weekday = ?
        ORDER BY we.workout_exercise_id
    """, (user_id, today.isoweekday())).fetchall() # specifies the type for later .join


    exercises = []
    for row in rows:
        exercises.append(row["exercise_name"])
    
    return exercises


def build_message(name, exercises):
    greeting = f"Hi {name}" if name else "Hi there"
    return f"{greeting}, you have a following workout planned for today: {', '.join(exercises)}. Open MyFitPlan to get started!"


def send_workout_reminders():

    with connect() as conn:
        email_users = conn.execute("""
            SELECT user_id, name, email FROM users
            WHERE email_reminders_enabled = 1 AND email IS NOT NULL
        """).fetchall()
        
        sms_users = conn.execute("""
            SELECT user_id, name, phone FROM users
            WHERE sms_reminders_enabled = 1 AND phone IS NOT NULL
        """).fetchall()

        # collecting tuples (user + their workout) for each of the methods to go over
        email_reminders = []
        sms_reminders = []
        
        for user in email_users:
          email_reminders.append((user, get_todays_exercises(conn, user["user_id"], date.today())))
        
        for user in sms_users:
          sms_reminders.append((user, get_todays_exercises(conn, user["user_id"], date.today())))

    # first pass: emails
    for user, exercises in email_reminders:
        if not exercises:
            continue  # no workout today
        try:
            send_email(user["email"], EMAIL_SUBJECT, build_message(user["name"], exercises))
            print("Emailed", user["email"])
        except Exception as error:
            print(f"Could not email {user['email']}: {error}")

    # second pass: texts
    for user, exercises in sms_reminders:
        if not exercises:
            continue  # no workout today
        try:
            send_sms(user["phone"], build_message(user["name"], exercises))
            print("Texted", user["phone"])
        except Exception as error:
            print(f"Could not text {user['phone']}: {error}")

# sends out the workout reminders 
if __name__ == "__main__":
    load_env_file()
    send_workout_reminders()
