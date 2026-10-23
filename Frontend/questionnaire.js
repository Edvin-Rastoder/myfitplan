const form = document.getElementById("fitness-form");
form.addEventListener("submit", function(event) {
    event.preventDefault();

    const goal = document.getElementById("fitness-goal").value;
    const experience = document.getElementById("experience-level").value;
    const days = document.getElementById("workout-days").value;
    const duration = document.getElementById("workout-duration").value;

    console.log("Fitness Goal:", goal);
    console.log("Experience Level:", experience);
    console.log("Workout Days:", days);
    console.log("Workout Duration:", duration);

    console.log("Form submitted!");


    const userSettings = {
    goal: goal,
    experience :experience,
    days: Number(days),
    duration: Number(duration)
    }


    fetch("http://127.0.0.1:5000/generate-workout", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(userSettings)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Response from Flask:", data);
    })
    .catch(error => {
        console.error("Error:", error);
    });

    console.log("User Settings:", userSettings);
});

