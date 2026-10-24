const auth = new Authenticate();

document.querySelector(".logout").addEventListener("click", (e) => {
    auth.logout();
})

const person = null;