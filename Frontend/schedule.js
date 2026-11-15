// Loads the logged-in user's most recent saved plan and shows one card per day.
// Values from the API are added with textContent, never as HTML.
const statusText = document.querySelector("#schedule-status");
const planDates = document.querySelector("#plan-dates");
const week = document.querySelector("#schedule-week");

// "YYYY-MM-DD" -> local date. new Date("YYYY-MM-DD") is read as UTC and can shift by a day.
function parseDate(text){
    const [year, month, day] = text.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function toIsoDate(value){
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${value.getFullYear()}-${month}-${day}`;
}

function formatDate(value, options){
    return value.toLocaleDateString(undefined, options);
}

function describeExercise(exercise){
    let text = `${exercise.exercise_name} - ${exercise.sets_count} x ${exercise.repetitions_count}`;
    if(exercise.suggested_weight !== null){
        text += ` @ ${exercise.suggested_weight} lb`;
    }
    if(exercise.rest_time !== null){
        text += `, rest ${exercise.rest_time}s`;
    }
    return text;
}

function createDayCard(heading, typeText, lines){
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
    lines.forEach((line) => {
        const item = document.createElement("li");
        item.textContent = line;
        list.appendChild(item);
    });
    card.appendChild(list);
    return card;
}

function savedDayCard(heading, day){
    const lines = day.exercises.length > 0 ? day.exercises.map(describeExercise) : ["No exercises prescribed"];
    // older plans were saved without a workout type
    return createDayCard(heading, day.workout_type || "Workout type not recorded", lines);
}

function showPlan(plan){
    const start = parseDate(plan.start_date);
    const end = parseDate(plan.end_date);
    const longDate = { month: "short", day: "numeric", year: "numeric" };
    const cardDate = { weekday: "long", month: "short", day: "numeric" };
    planDates.textContent = `${formatDate(start, longDate)} - ${formatDate(end, longDate)}`;
    statusText.hidden = true;

    const daysByDate = new Map();
    plan.days.forEach((day) => {
        if(day.date !== null){
            daysByDate.set(day.date, day);
        }
    });

    // one card per calendar date, starting on whatever weekday the plan starts
    const shown = new Set();
    for(let current = start; current <= end;
        current = new Date(current.getFullYear(), current.getMonth(), current.getDate() + 1)){
        const heading = formatDate(current, cardDate);
        const day = daysByDate.get(toIsoDate(current));
        if(day){
            week.appendChild(savedDayCard(heading, day));
            shown.add(day.workout_day_id);
        }else{
            week.appendChild(createDayCard(heading, "No workout scheduled", []));
        }
    }

    // saved days outside the date range, or without a weekday
    plan.days.filter((day) => !shown.has(day.workout_day_id)).forEach((day) => {
        const heading = day.date !== null ? formatDate(parseDate(day.date), cardDate) : "Not scheduled yet";
        week.appendChild(savedDayCard(heading, day));
    });
}

function showMessage(message, link){
    statusText.textContent = message;
    if(link){
        const anchor = document.createElement("a");
        anchor.href = link.href;
        anchor.textContent = link.text;
        statusText.append(" ", anchor);
    }
    statusText.hidden = false;
}

// `auth` is the shared Authenticate helper from initialize.js, which loads before this file
async function loadSchedule(){
    try{
        const response = await auth.apiFetch("/workout-plans/latest");

        if(response.status == 401){
            return; // apiFetch is already sending the user to the login page
        }
        if(response.status == 404){
            showMessage("You don't have a saved workout plan yet.", { href: "questionnaire.html", text: "Build a plan" });
            return;
        }
        if(!response.ok){
            showMessage("Could not load your schedule. Please try again later.");
            return;
        }

        showPlan(await response.json());
    }catch(error){
        showMessage("Could not load your schedule. Please try again later.");
    }
}

loadSchedule();
