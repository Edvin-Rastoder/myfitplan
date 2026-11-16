// Schedule page: shows the latest saved plan as one card per date, and lets the user
// choose which weekdays the workouts fall on (POST /update-schedule).
// `auth` is the shared Authenticate helper from initialize.js, which loads before this file.
// Values from the API are added with textContent, never as HTML.

const CARDIO_EXERCISES = ["Treadmill Walking", "Stationary Cycling", "Jump Rope", "Jogging", "Elliptical"];

// "YYYY-MM-DD" -> local date, without the UTC shift of new Date("YYYY-MM-DD")
function parseDate(text) {
    const [year, month, day] = text.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function toIsoDate(value) {
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${value.getFullYear()}-${month}-${day}`;
}

function formatDate(value, options) {
    return value.toLocaleDateString("en-US", options);
}

function exerciseText(exercise) {
    if (CARDIO_EXERCISES.includes(exercise.exercise_name)) {
        return exercise.exercise_name;
    }
    return `${exercise.exercise_name} - ${exercise.sets_count} x ${exercise.repetitions_count}`;
}

function dayCard(heading, typeText, lines) {
    const card = document.createElement("div");
    card.className = "day";

    const title = document.createElement("div");
    title.className = "title";
    const h3 = document.createElement("h3");
    h3.textContent = heading;
    title.appendChild(h3);
    card.appendChild(title);

    const type = document.createElement("p");
    type.textContent = typeText;
    card.appendChild(type);

    const list = document.createElement("ul");
    list.className = "exercise-list";
    lines.forEach(line => {
        const item = document.createElement("li");
        const text = document.createElement("a");
        text.textContent = line;
        item.appendChild(text);
        list.appendChild(item);
    });
    card.appendChild(list);
    return card;
}

function workoutCard(heading, workout) {
    const lines = workout.exercises.length > 0 ? workout.exercises.map(exerciseText) : ["No exercises"];
    // plans saved before workout types were stored have no type
    return dayCard(heading, workout.workout_type || "Workout type not recorded", lines);
}

function showStatus(message, link) {
    const status = document.querySelector("#schedule-status");
    status.textContent = message;
    if (link) {
        const anchor = document.createElement("a");
        anchor.href = link.href;
        anchor.textContent = link.text;
        status.append(" ", anchor);
    }
    status.hidden = false;
}

function renderPlan(data) {
    const start = parseDate(data.start_date);
    const end = parseDate(data.end_date);
    document.querySelector("#plan-dates").textContent =
        formatDate(start, { month: "short", day: "numeric" }) + " - " +
        formatDate(end, { month: "short", day: "numeric", year: "numeric" });

    const workoutsByDate = new Map(data.workouts.filter(w => w.date).map(w => [w.date, w]));
    const week = document.querySelector("#schedule-week");
    week.replaceChildren();

    // one card per calendar date, starting on whatever weekday the plan starts
    for (let current = start; current <= end;
         current = new Date(current.getFullYear(), current.getMonth(), current.getDate() + 1)) {
        const heading = formatDate(current, { weekday: "long", month: "short", day: "numeric" });
        const workout = workoutsByDate.get(toIsoDate(current));
        week.appendChild(workout ? workoutCard(heading, workout) : dayCard(heading, "No workout scheduled", []));
    }

    data.workouts.filter(w => !w.date).forEach(w => week.appendChild(workoutCard("Not scheduled yet", w)));
}

function disablePicker(message) {
    document.querySelectorAll(".day-options input").forEach(option => { option.disabled = true; });
    document.querySelector("#save-schedule").disabled = true;
    document.querySelector("#schedule-message").textContent = message;
}

function setUpPicker(workouts) {
    const dayOptions = document.querySelectorAll(".day-options input");
    const saveButton = document.querySelector("#save-schedule");
    const scheduleMessage = document.querySelector("#schedule-message");

    // only days with exercises are moved; Rest and Active Recovery days fill the remaining days
    const scheduledWorkouts = workouts.filter(workout => workout.exercises.length > 0);
    const requiredDays = scheduledWorkouts.length;

    dayOptions.forEach(option => {
        option.checked = scheduledWorkouts.some(workout => workout.weekday === Number(option.value));
    });

    saveButton.addEventListener("click", async () => {
        const selectedDays = Array.from(dayOptions)
            .filter(option => option.checked)
            .map(option => Number(option.value))
            .sort((a, b) => a - b);

        if (selectedDays.length !== requiredDays) {
            scheduleMessage.textContent = `Please select exactly ${requiredDays} workout days.`;
            return;
        }

        saveButton.disabled = true;
        scheduleMessage.textContent = "Saving schedule...";

        try {
            const response = await auth.apiFetch("/update-schedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ weekdays: selectedDays })
            });
            const result = await response.json().catch(() => ({}));

            if (response.ok) {
                scheduleMessage.textContent = "Schedule saved successfully!";
                window.location.reload();
                return;
            }
            scheduleMessage.textContent = result.error || "Could not save schedule. Please try again.";
        } catch (error) {
            scheduleMessage.textContent = "Could not reach the server. Please try again.";
        }
        saveButton.disabled = false;
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await auth.apiFetch("/my-workouts");

        if (response.status === 401) {
            return; // apiFetch is already sending the user to the login page
        }
        if (!response.ok) {
            throw new Error("Failed to load workouts: " + response.status);
        }

        const data = await response.json();

        if (!data.plan_id) {
            showStatus("You don't have a saved workout plan yet.", { href: "questionnaire.html", text: "Build a plan" });
            disablePicker("Build a plan first to choose your workout days.");
            return;
        }

        renderPlan(data);
        setUpPicker(data.workouts);
        document.querySelector("#schedule-status").hidden = true;
    } catch (error) {
        console.error("Error loading schedule:", error);
        showStatus("Could not load your schedule. Please try again later.");
        disablePicker("Your schedule could not be loaded.");
    }
});
