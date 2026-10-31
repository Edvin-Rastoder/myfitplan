class Signup{
    constructor(form){
        this.form = form;
        this.email = document.querySelector("#email");
        this.phone = document.querySelector("#phone");
        this.password = document.querySelector("#password");
        this.confirm = document.querySelector("#confirm-password");
        this.sms = document.querySelector("#sms-reminders");
        this.formError = document.querySelector("#form-error");
        this.button = form.querySelector(".button");
        this.validateonSubmit();
    }

    validateonSubmit(){
        this.form.addEventListener("submit", (e) => {
            e.preventDefault();
            if(this.validateFields()){
                this.signup();
            }
        });
    }

    validateFields(){
        const email = this.email.value.trim();
        const phone = this.phone.value.trim();
        let valid = true;

        [this.email, this.phone, this.password, this.confirm].forEach((field) => {
            this.setStatus(field, null, "success");
        });
        this.formError.innerText = "";

        // prevents from reachign backend's error
        if(email == "" && phone == ""){
            this.setStatus(this.email, "Enter an email or a phone number", "error");
            this.setStatus(this.phone, "Enter an email or a phone number", "error");
            valid = false;
        }

        if(email != "" && !/^\S+@\S+$/.test(email)){
            this.setStatus(this.email, "Enter a valid email address", "error");
            valid = false;
        }

        // regex check for the format the users table accepts: + then 7 to 15 digits, no leading 0
        if(phone != "" && !/^\+[1-9]\d{6,14}$/.test(phone)){
            this.setStatus(this.phone, "Use the format +14085551234", "error");
            valid = false;
        }

        if(this.sms.checked && phone == ""){
            this.setStatus(this.phone, "Add a phone number to get text reminders", "error");
            valid = false;
        }

        if(this.password.value == ""){
            this.setStatus(this.password, "Password cannot be blank", "error");
            valid = false;
        }

        if(this.confirm.value != this.password.value){
            this.setStatus(this.confirm, "Passwords do not match", "error");
            valid = false;
        }

        return valid;
    }

    async signup(){
        const body = {
            email: this.email.value.trim(),
            phone: this.phone.value.trim(),
            sms_reminders_enabled: this.sms.checked ? "true" : "false"
        };

        this.button.disabled = true; // prevents double submits while waiting

        try{
            body.password_hash = await hashPassword(this.password.value);
            const response = await fetch("http://127.0.0.1:5000/create-user", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include", // backend logs the new user in with a session cookie
                body: JSON.stringify(body)
            });

            if(response.ok){
                window.location.href = this.form.action;
                return;
            }

            const data = await response.json().catch(() => ({}));
            this.formError.innerText = data.error || "Something went wrong, please try again";
        }catch(error){
            this.formError.innerText = "Could not reach the server";
        }finally{
            this.button.disabled = false;
        }
    }

    setStatus(field, message, status){
        const errMessage = field.parentElement.querySelector(".error-message");
        if(status == "error"){
            errMessage.innerText = message;
            field.classList.add("input-error");
        }
        else if(status == "success"){
            errMessage.innerText = "";
            field.classList.remove("input-error");
        }
    }
}

const signupForm = document.querySelector(".signupForm");

if(signupForm){
    const signup = new Signup(signupForm);
}
