const form = document.getElementById("fitness-form");
const submitButton = form.querySelector('button[type="submit"]');
const buttonLabel = submitButton.textContent;
const planError = document.getElementById("plan-error");

function showPlanError(message, link) {
    planError.textContent = message;
    if (link) {
        const anchor = document.createElement("a");
        anchor.href = link.href;
        anchor.className = "alert-link";
        anchor.textContent = link.text;
        planError.append(" ", anchor);
    }
    planError.hidden = false;

    submitButton.disabled = false;
    submitButton.textContent = buttonLabel;
}

form.addEventListener("submit", async function(event) {
    event.preventDefault();

    // ignore repeat clicks while a plan is being built
    if (submitButton.disabled) {
        return;
    }
    submitButton.disabled = true;
    submitButton.textContent = "Building your plan...";
    planError.hidden = true;

    const userSettings = {
        goal: document.getElementById("fitness-goal").value,
        experience: document.getElementById("experience-level").value,
        days: Number(document.getElementById("workout-days").value),
        duration: Number(document.getElementById("workout-duration").value)
    };

    try {
        const response = await fetch("http://127.0.0.1:5000/generate-workout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "include",
            body: JSON.stringify(userSettings)
        });
        const data = await response.json().catch(() => ({}));

        if (response.status === 401) {
            showPlanError("Your session has expired. Please log in again.", { href: "loginpage.html", text: "Log in" });
            return;
        }
        if (!response.ok) {
            showPlanError(data.error || "Could not build your plan. Please try again.");
            return;
        }
        if (!Array.isArray(data.workout_plan) || data.workout_plan.length === 0) {
            showPlanError("No plan could be built for these choices. Please try different options.");
            return;
        }

        // the plan is saved; show it on the Schedule page (the button stays disabled while leaving)
        window.location.href = "schedule.html";
    } catch (error) {
        showPlanError("Could not reach the server. Please try again.");
    }
});
