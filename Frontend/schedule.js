
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await fetch("http://127.0.0.1:5000/my-workouts", {
            credentials: "include"
        });

        if (!response.ok) {
            throw new Error("Failed to load workouts: " + response.status);
        }

        const data = await response.json();
        const workouts = data.workouts || [];

const dayOptions = document.querySelectorAll(".day-options input");
const saveButton = document.querySelector("#save-schedule");
const scheduleMessage = document.querySelector("#schedule-message");

const scheduledWorkouts = workouts
    .filter(workout => workout.exercises.length > 0)
    .sort((a, b) => a.weekday - b.weekday);

const requiredDays = scheduledWorkouts.length;

dayOptions.forEach(option => {
    option.checked = scheduledWorkouts.some(
        workout => workout.weekday === Number(option.value)
    );
});

saveButton.addEventListener("click", async () => {
    const selectedDays = Array.from(dayOptions)
        .filter(option => option.checked)
        .map(option => Number(option.value))
        .sort((a, b) => a - b);

    if (selectedDays.length !== requiredDays) {
        scheduleMessage.textContent =
            `Please select exactly ${requiredDays} workout days.`;
        return;
    }

    saveButton.disabled = true;
    scheduleMessage.textContent = "Saving schedule...";

    try {
        const response = await fetch("http://127.0.0.1:5000/update-schedule", {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                weekdays: selectedDays
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not save schedule");
        }

        scheduleMessage.textContent = "Schedule saved successfully!";
        window.location.reload();

    } catch (error) {
        scheduleMessage.textContent = error.message;
    } finally {
        saveButton.disabled = false;
    }
});


        const days = document.querySelectorAll(".week .day");
        const weekInfo = document.querySelector(".header p");

        const dayNames = [
            "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"
        ];

        if (data.start_date && data.end_date) {
            const start = new Date(data.start_date + "T12:00:00");
            const end = new Date(data.end_date + "T12:00:00");

            const formatDate = date =>
                date.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric"
                });

            weekInfo.textContent =
                formatDate(start) + " - " + formatDate(end);
        } else {
            weekInfo.textContent = "No workout plan generated yet";
        }

        days.forEach((dayElement, index) => {
            const workout = workouts.find(w => w.weekday === index + 1);

            const typeElement = dayElement.querySelector("p");
            const exerciseList = dayElement.querySelector(".exercise-list");

            exerciseList.innerHTML = "";

            if (!workout) {
                typeElement.textContent = "No workout scheduled";
                return;
            }

            if (workout.exercises.length === 0) {
                typeElement.textContent = "Rest Day";
                return;
            }

            typeElement.textContent =
                workout.exercises.length + " Exercises";

            workout.exercises.forEach(exercise => {
                const item = document.createElement("li");
                const exerciseText = document.createElement("a");

                
                const cardioExercises = [
                    "Treadmill Walking",
                    "Stationary Cycling",
                    "Jump Rope",
                    "Jogging",
                    "Elliptical"
                ];

                if (cardioExercises.includes(exercise.exercise_name)) {
                    exerciseText.textContent = exercise.exercise_name;
                } else {
                    exerciseText.textContent =
                        exercise.exercise_name + " - " +
                        exercise.sets_count + " x " +
                        exercise.repetitions_count;
                }


                item.appendChild(exerciseText);
                exerciseList.appendChild(item);
            });
        });

    } catch (error) {
        console.error("Error loading schedule:", error);
    }
});
