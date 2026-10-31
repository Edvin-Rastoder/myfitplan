const auth = new Authenticate();

document.querySelector(".logout").addEventListener("click", (e) => {
    e.preventDefault(); 
    auth.logout();
})

const person = null;