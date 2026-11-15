
document.addEventListener("DOMContentLoaded", async () => {
    const workoutList = document.querySelector(".workouthist");
    const details = document.querySelector(".detailList");
    const filter = document.querySelector(".filterTime");

    try {
        const response = await fetch("http://127.0.0.1:5000/workout-history", {
            credentials: "include"
        });

        if (!response.ok) {
            throw new Error("Failed to load workout history");
        }

        const data = await response.json();
        const history = data.history || [];

        const listContainer = document.createElement("div");
        listContainer.className = "history-list";
        workoutList.appendChild(listContainer);

        function showDetails(workout) {
            const stats = details.querySelectorAll(".statsInfo .info h2");

            stats[0].textContent = workout.total_sets + " Sets";
            stats[1].textContent = workout.total_weight + " lb";

            if (workout.duration_seconds === null ||
                workout.duration_seconds === undefined) {
                
            if (workout.duration_seconds === null ||
                workout.duration_seconds === undefined) {
                stats[2].textContent = "--";
} else {
    const minutes = Math.floor(workout.duration_seconds / 60);
    const seconds = workout.duration_seconds % 60;

    stats[2].textContent =
        `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

            } else {
                const minutes = Math.floor(workout.duration_seconds / 60);
                const seconds = workout.duration_seconds % 60;

                stats[2].textContent =
                    `${minutes}m ${String(seconds).padStart(2, "0")}s`;
            }

            const rows = details.querySelector(".workoutSpecificData");
            rows.replaceChildren();

            
workout.exercises.forEach(exercise => {
    exercise.sets.forEach((set, index) => {
        const row = document.createElement("div");
        row.className = "history-row";

        if (index === 0) {
            row.classList.add("exercise-start");
        }

        const values = [
            index === 0 ? exercise.exercise_name : "",
            set.set_number,
            set.repetitions,
            set.weight === null ? "Bodyweight" : set.weight + " lb"
        ];

        values.forEach(value => {
            const p = document.createElement("p");
            p.textContent = value;
            row.appendChild(p);
        });

        rows.appendChild(row);
    });
});

        }

        function renderHistory() {
            listContainer.replaceChildren();

            const now = new Date();
            const startOfWeek = new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate() - ((now.getDay() + 6) % 7)
            );

            const filtered = history.filter(workout => {
                const date = new Date(workout.completed_on + "T00:00:00");

                if (filter.value === "week") {
                    return date >= startOfWeek && date <= now;
                }

                if (filter.value === "month") {
                    return date.getFullYear() === now.getFullYear() &&
                           date.getMonth() === now.getMonth();
                }

                return true;
            });

            if (filtered.length === 0) {
                const message = document.createElement("p");
                message.textContent = "No completed workouts found.";
                listContainer.appendChild(message);
                details.style.display = "none";
                return;
            }

            details.style.display = "";

            filtered.forEach(workout => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "history-item";

                button.textContent =
                    workout.completed_on + " - " +
                    workout.total_sets + " Sets Completed";

                button.addEventListener("click", () => {
                    showDetails(workout);
                });

                listContainer.appendChild(button);
            });

            showDetails(filtered[0]);
        }

        filter.addEventListener("change", renderHistory);
        renderHistory();

    } catch (error) {
        console.error("Error loading history:", error);
        alert("Could not load workout history.");
    }
});
