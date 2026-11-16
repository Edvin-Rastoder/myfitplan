

document.addEventListener("DOMContentLoaded", async () => {
   const group = document.querySelector(".group");
   const summary = document.querySelector(".summary");
   const cardioNames = [
   "Treadmill Walking",
   "Stationary Cycling",
   "Jump Rope",
   "Jogging",
   "Elliptical"
   ]; 

const startButton = document.querySelector("#start-workout");
const doneButton = summary.querySelector(".done");
const timerDisplay = document.querySelector("#workout-timer");

let startTime = null;
let timerInterval = null;

function getElapsedSeconds() {
   if (startTime === null) return 0;
   return Math.floor((Date.now() - startTime) / 1000);
}

function updateTimer() {
   const elapsed = getElapsedSeconds();
   const minutes = Math.floor(elapsed / 60);
   const seconds = elapsed % 60;

   timerDisplay.textContent =
       String(minutes).padStart(2, "0") + ":" +
       String(seconds).padStart(2, "0");
}

startButton.addEventListener("click", () => {
   if (startTime !== null) return;

   startTime = Date.now();
   startButton.disabled = true;
   startButton.textContent = "Workout In Progress";
   doneButton.disabled = false;

   updateTimer();
   timerInterval = setInterval(updateTimer, 1000);
});


   try {
       const response = await fetch("http://127.0.0.1:5000/my-workouts", {
           credentials: "include"
       });

       if (!response.ok) {
           throw new Error("Failed to load workouts: " + response.status);
       }

       const data = await response.json();
       const workouts = data.workouts || [];

       const today = (new Date().getDay() + 6) % 7 + 1;

       const workout = workouts.find(w =>
           w.weekday === today && w.exercises.length > 0
       ) || workouts.find(w => w.exercises.length > 0);

       group.querySelectorAll(".exercise").forEach(el => el.remove());

       if (!workout) {
           const message = document.createElement("p");
           message.textContent = "No workout plan found. Generate a plan first.";
           group.insertBefore(message, summary);
           summary.querySelector(".done").disabled = true;
           startButton.disabled = true;
           return;
       }

       let totalSets = 0;
       let totalCardio = 0;

       workout.exercises.forEach(exercise => {
           const card = document.createElement("div");
           card.className = "exercise";
           card.dataset.exerciseId = exercise.workout_exercise_id;

           const title = document.createElement("div");
           title.className = "title";

           const heading = document.createElement("h3");
           heading.textContent = "Exercise: " + exercise.exercise_name;
           title.appendChild(heading);
           card.appendChild(title);

           if (cardioNames.includes(exercise.exercise_name)) {
               totalCardio++;
               card.classList.add("cardio");

               const checkbox = document.createElement("input");
               checkbox.type = "checkbox";
               checkbox.className = "cardio-check";

               const label = document.createElement("label");
               label.textContent = " Completed";
               label.prepend(checkbox);

               card.appendChild(label);
               group.insertBefore(card, summary);
               return;
           }

           const list = document.createElement("div");
           const headers = document.createElement("div");
           headers.className = "list-titles";

           ["Set", "Target", "Reps Done", "Weight", "Done"].forEach(text => {
               const p = document.createElement("p");
               p.textContent = text;
               headers.appendChild(p);
           });

           list.appendChild(headers);

           for (let i = 1; i <= exercise.sets_count; i++) {
               totalSets++;

               const row = document.createElement("div");
               row.className = "list-row";
               row.dataset.setNumber = i;

               const number = document.createElement("p");
               number.textContent = i;

               const target = document.createElement("p");
               target.textContent = exercise.repetitions_count;

              
               const reps = document.createElement("select");
               reps.className = "list-in reps";

               for (let r = 0; r <= 50; r++) {
                   const option = document.createElement("option");
                   option.value = r;
                   option.textContent = r;
                   reps.appendChild(option);
               }

               reps.value = exercise.repetitions_count;

               const weight = document.createElement("select");
               weight.className = "list-in weight";

               const noWeight = document.createElement("option");
               noWeight.value = "";
               noWeight.textContent = "Bodyweight";
               weight.appendChild(noWeight);

               for (let w = 0; w <= 500; w += 5) {
                   const option = document.createElement("option");
                   option.value = w;
                   option.textContent = w + " lb";
                   weight.appendChild(option);
               }


               const checkbox = document.createElement("input");
               checkbox.type = "checkbox";
               checkbox.className = "check";

               row.append(number, target, reps, weight, checkbox);
               list.appendChild(row);
           }

           card.appendChild(list);
           group.insertBefore(card, summary);
       });

       const setsDone = summary.querySelector(".sum-info p:last-child");

       function updateSummary() {
           const completedSets = group.querySelectorAll(".check:checked").length;
           const completedCardio = group.querySelectorAll(".cardio-check:checked").length;

           setsDone.textContent =
               `${completedSets + completedCardio} / ${totalSets + totalCardio}`;
       }

       group.addEventListener("change", event => {
           if (event.target.matches(".check, .cardio-check")) {
               updateSummary();
           }
       });

       updateSummary();

       summary.querySelector(".done").addEventListener("click", async () => {
           const exercises = [];

           for (const card of group.querySelectorAll(".exercise")) {
               const sets = [];

               if (card.classList.contains("cardio")) {
               const checkbox = card.querySelector(".cardio-check");

               if (checkbox.checked) {
                   exercises.push({
                       workout_exercise_id: Number(card.dataset.exerciseId),
                       sets: [{
                           set_number: 1,
                           repetitions: 0,
                           weight: null
                       }]
                   });
               }

               continue;
           }

               for (const row of card.querySelectorAll(".list-row")) {
                   if (!row.querySelector(".check").checked) continue;

                   const repsValue = row.querySelector(".reps").value;
                   const weightValue = row.querySelector(".weight").value;

                   if (repsValue === "" || !Number.isInteger(Number(repsValue)) ||
                       Number(repsValue) < 0) {
                       alert("Enter valid reps for every completed set.");
                       return;
                   }

                   if (weightValue !== "" &&
                       (!Number.isFinite(Number(weightValue)) ||
                        Number(weightValue) < 0)) {
                       alert("Enter a valid weight.");
                       return;
                   }

                   sets.push({
                       set_number: Number(row.dataset.setNumber),
                       repetitions: Number(repsValue),
                       weight: weightValue === "" ? null : Number(weightValue)
                   });
               }

               if (sets.length > 0) {
                   exercises.push({
                       workout_exercise_id: Number(card.dataset.exerciseId),
                       sets: sets
                   });
               }
           }

           if (exercises.length === 0) {
               alert("Complete at least one exercise before saving.");
               return;
           }

           const button = summary.querySelector(".done");
           button.disabled = true;

           try {
               const saveResponse = await fetch(
                   "http://127.0.0.1:5000/complete-workout",
                   {
                       method: "POST",
                       credentials: "include",
                       headers: {
                           "Content-Type": "application/json"
                       },
                       body: JSON.stringify({
                           workout_day_id: workout.workout_day_id,
                           exercises: exercises,
                           duration_seconds: getElapsedSeconds()
                       })
                   }
               );

               const result = await saveResponse.json();

               if (!saveResponse.ok) {
                   throw new Error(result.error || "Could not save workout");
               }

               clearInterval(timerInterval);
               updateTimer();

               alert("Workout saved successfully!");
               window.location.href = "history.html";


           } catch (error) {
               alert(error.message);
               button.disabled = false;
           }
       });

   } catch (error) {
       console.error("Error loading workout:", error);
       alert("Could not load workout. Check your Flask server.");
   }
});



