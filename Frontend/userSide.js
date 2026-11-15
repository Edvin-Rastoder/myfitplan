
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


        const nextWorkoutTime = document.querySelector("#next-workout-time");

        if (nextWorkoutTime) {
            nextWorkoutTime.textContent = data.duration_minutes
                ? data.duration_minutes + " min"
                : "--";
        }

        const timePerSession = document.querySelector("#time-per-session");

        if (timePerSession) {
            timePerSession.textContent = data.duration_minutes
                ? data.duration_minutes + " min"
                : "--";
        }

        const days = document.querySelectorAll(".card2 .week .day");
        const stats = document.querySelectorAll(".card2 .spec-info h3");
        const workoutName = document.querySelector(".card3 h4");
        const exerciseList = document.querySelector(".card3 .exercise-list");

        days.forEach(day => {
            day.querySelector(".workout-type").textContent = "--";
        });

        if (workouts.length === 0) {
            workoutName.textContent = "No workout plan yet";
            exerciseList.innerHTML = "";
            stats[0].textContent = "0";
            stats[1].textContent = "0";
            return;
        }

        let totalExercises = 0;
        let totalSets = 0;

        workouts.forEach(workout => {
            const dayIndex = workout.weekday - 1;

            if (dayIndex >= 0 && dayIndex < days.length) {
                const dayElement = days[dayIndex];

                dayElement.querySelector(".workout-type").textContent =
                    workout.exercises.length > 0
                        ? workout.exercises.length + " exercises"
                        : "Rest";
            }

            totalExercises += workout.exercises.length;

            workout.exercises.forEach(exercise => {
                totalSets += exercise.sets_count;
            });
        });

        stats[0].textContent = totalExercises;
        stats[1].textContent = totalSets;

        const today = new Date();
        const todayIndex = (today.getDay() + 6) % 7;


        const todaysWorkout = workouts.find(workout =>
            workout.weekday === todayIndex + 1 &&
            workout.exercises.length > 0
        );

        const reminder = document.querySelector("#workout-reminder");

        if (reminder) {
            if (todaysWorkout) {
                reminder.hidden = false;
                reminder.innerHTML = `
                <div class="reminder-content">
                    <span class="reminder-icon">🔔</span>
                    <div>
                        <strong>Workout Reminder</strong>
                        <p>You have a ${data.duration_minutes ? data.duration_minutes + "-minute " : ""}workout scheduled today! 💪</p>
                    </div>
                </div>
            `;
            } else {
                reminder.hidden = true;
            }
        }


        const upcomingWorkout = workouts
            .filter(workout =>
                workout.weekday - 1 >= todayIndex &&
                workout.exercises.length > 0
            )
            .sort((a, b) => a.weekday - b.weekday)[0];

        const nextWorkout = upcomingWorkout ||
            workouts.find(workout => workout.exercises.length > 0);

        if (nextWorkout) {
            const dayNames = [
                "Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday", "Sunday"
            ];

            workoutName.textContent =
                "Workout: " + dayNames[nextWorkout.weekday - 1];

            exerciseList.innerHTML = "";

            nextWorkout.exercises.forEach(exercise => {
                const item = document.createElement("li");

                const name = document.createElement("span");
                name.className = "exercise-name";
                name.textContent = exercise.exercise_name;

                const reps = document.createElement("span");
                reps.className = "exercise-reps";
                reps.textContent =
                    exercise.sets_count + " sets × " +
                    exercise.repetitions_count + " reps";

                item.appendChild(name);
                item.appendChild(reps);

                exerciseList.appendChild(item);
            });

        }

    } catch (error) {
        console.error("Error loading workouts:", error);
    }
});





document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await fetch("http://127.0.0.1:5000/workout-stats", {
            credentials: "include"
        });

        if (!response.ok) {
            throw new Error("Failed to load workout statistics");
        }

        const data = await response.json();

        const progress = document.querySelector(".card1");
        const lastWorkout = document.querySelector(".card4");

        const workoutsCompleted = progress.querySelector(".chart");
        workoutsCompleted.textContent = data.total_workouts + " Workouts Completed";

        const consistency = progress.querySelectorAll(".data-area")[0];
        consistency.textContent = data.weekly_completed + " Workouts This Week";

        const weeklyGoal = progress.querySelectorAll(".data-area")[1];

        const planResponse = await fetch("http://127.0.0.1:5000/my-workouts", {
            credentials: "include"
        });

        if (planResponse.ok) {
            const planData = await planResponse.json();

            const weeklyTarget = (planData.workouts || []).filter(
                workout => workout.exercises.length > 0
            ).length;

            weeklyGoal.replaceChildren();

            const goalText = document.createElement("p");
            goalText.textContent =
                data.weekly_completed + " / " + weeklyTarget + " Workouts";

            const progressBar = document.createElement("div");
            progressBar.className = "weekly-progress";

            const progressFill = document.createElement("div");
            progressFill.className = "weekly-progress-fill";

            const percentage = weeklyTarget > 0
                ? Math.min((data.weekly_completed / weeklyTarget) * 100, 100)
                : 0;

            progressFill.style.width = percentage + "%";

            progressBar.appendChild(progressFill);
            weeklyGoal.append(goalText, progressBar);

        }

        if (data.last_workout) {
            const completed = data.last_workout.sets_completed;
            const planned = data.last_workout.sets_planned;

            lastWorkout.querySelector(".data-area").textContent =
                "Workout Completed";

            lastWorkout.querySelector("p").innerHTML =
                completed + "/" + planned + "<span> Sets Completed</span>";

            const lastWorkoutInfo = lastWorkout.querySelector(".spec-info p:last-child");
            lastWorkoutInfo.textContent = data.last_workout.date;
        }

    } catch (error) {
        console.error("Error loading workout statistics:", error);
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await fetch("http://127.0.0.1:5000/me", {
            credentials: "include"
        });

        if (!response.ok) {
            throw new Error("Failed to load user");
        }

        const data = await response.json();
        const welcome = document.querySelector("#welcome-message");

        if (welcome && data.name) {
            welcome.textContent = "Welcome, " + data.name.split(" ")[0] + "!";
        }
    } catch (error) {
        console.error("Error loading user:", error);
    }
});

