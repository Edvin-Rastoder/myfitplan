
document.addEventListener("DOMContentLoaded", async () => {
    const searchInput = document.querySelector(".searchbar input");
    const exerciseList = document.querySelector(".listOfExercise");
    const exerciseTitle = document.querySelector(".exerciseTitle h2");
    const stepsContainer = document.querySelector(".steps");
    const alternativesContainer = document.querySelector(".diffChoice");    
    const workoutExerciseSelect = document.querySelector("#workout-exercise-select");
    const swapMessage = document.querySelector("#swap-message");


    let exercises = [];

    
    async function loadWorkoutExercises() {
    const response = await fetch("http://127.0.0.1:5000/my-workouts", {
        credentials: "include"
    });

    if (!response.ok) {
        throw new Error("Failed to load workout plan");
    }

    const data = await response.json();
    const dayNames = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ];

    workoutExerciseSelect.innerHTML =
        '<option value="">Select a workout exercise</option>';

    (data.workouts || []).forEach(workout => {
        workout.exercises.forEach(exercise => {
            const option = document.createElement("option");
            option.value = exercise.workout_exercise_id;
            option.textContent =
                `${dayNames[workout.weekday - 1]} - ${exercise.exercise_name}`;
            workoutExerciseSelect.appendChild(option);
        });
    });
}



    function showAlternatives(exercise) {
        alternativesContainer.innerHTML = "";


    const primaryMuscles = exercise.primaryMuscles || [];

    const alternatives = exercises.filter(other => {
        if (other.name === exercise.name) {
            return false;
        }

        const sameMuscle = (other.primaryMuscles || []).some(muscle =>
            primaryMuscles.includes(muscle)
        );

        const sameCategory = other.category === exercise.category;

        return sameMuscle && sameCategory;
    }).slice(0, 5);


    if (alternatives.length === 0) {
        alternativesContainer.textContent = "No alternatives available.";
        return;
    }

    alternatives.forEach(alternative => {
        const option = document.createElement("div");
        option.className = "alternative-option";

        const info = document.createElement("div");

        const name = document.createElement("h4");
        name.textContent = alternative.name;

        const equipment = document.createElement("p");
        equipment.textContent = alternative.equipment || "No equipment";

        const button = document.createElement("button");
        button.className = "swap";
        button.textContent = "Swap";

        button.addEventListener("click", async () => {
            const workoutExerciseId = Number(workoutExerciseSelect.value);

            if (!workoutExerciseId) {
                swapMessage.textContent = "Please select a workout exercise first.";
                return;
            }

            button.disabled = true;
            swapMessage.textContent = "Swapping exercise...";

            try {
                const response = await fetch("http://127.0.0.1:5000/swap-exercise", {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        workout_exercise_id: workoutExerciseId,
                        new_exercise_name: alternative.name
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || "Unable to swap exercise");
                }

                swapMessage.textContent = "Exercise swapped successfully!";
                await loadWorkoutExercises();

            } catch (error) {
                swapMessage.textContent = error.message;
            } finally {
                button.disabled = false;
            }
        });


        info.appendChild(name);
        info.appendChild(equipment);

        option.appendChild(info);
        option.appendChild(button);

        alternativesContainer.appendChild(option);
    });
}   

    workoutExerciseSelect.addEventListener("change", () => {
        const selectedOption = workoutExerciseSelect.options[workoutExerciseSelect.selectedIndex];

        if (!selectedOption.value) {
            return;
        }

        const exerciseName = selectedOption.textContent.split(" - ").slice(1).join(" - ");

        const selectedExercise = exercises.find(exercise =>
            exercise.name === exerciseName
        );

        if (selectedExercise) {
            showDetails(selectedExercise);
            searchInput.value = selectedExercise.name;
            displayExercises([selectedExercise]);
            swapMessage.textContent = "";
        }
    });



    function showDetails(exercise) {
        exerciseTitle.textContent = exercise.name;
        showAlternatives(exercise);

        stepsContainer.innerHTML = "";

        const instructions = exercise.instructions || [];

        if (instructions.length === 0) {
            stepsContainer.textContent = "No instructions available.";
            return;
        }

        instructions.forEach((instruction, index) => {
            const step = document.createElement("p");
            step.textContent = `${index + 1}. ${instruction}`;
            stepsContainer.appendChild(step);
        });
    }

    function displayExercises(filteredExercises) {
        exerciseList.innerHTML = "";

        filteredExercises.forEach(exercise => {
            const card = document.createElement("div");
            card.className = "exercise";

            const name = document.createElement("h2");
            name.textContent = exercise.name;

            const muscle = document.createElement("p");
            muscle.textContent =
                "Targeted Muscle: " +
                (exercise.primaryMuscles || []).join(", ");

            const equipment = document.createElement("p");
            equipment.textContent =
                "Equipment Needed: " +
                (exercise.equipment || "None");

            card.appendChild(name);
            card.appendChild(muscle);
            card.appendChild(equipment);

            card.addEventListener("click", () => {
                showDetails(exercise);
            });

            exerciseList.appendChild(card);
        });
    }

    try {
        const response = await fetch("http://127.0.0.1:5000/exercises", {
            credentials: "include"
        });

        if (!response.ok) {
            throw new Error("Failed to load exercises");
        }

        const data = await response.json();

        exercises = Array.isArray(data) ? data : data.exercises || [];
        await loadWorkoutExercises();

        displayExercises(exercises);

        if (exercises.length > 0) {
            showDetails(exercises[0]);
        }

        searchInput.addEventListener("input", () => {
            const search = searchInput.value.toLowerCase();

            const filtered = exercises.filter(exercise =>
                exercise.name.toLowerCase().includes(search)
            );

            displayExercises(filtered);
        });

    } catch (error) {
        console.error("Error loading exercises:", error);
        exerciseList.textContent = "Unable to load exercises.";
    }
});
