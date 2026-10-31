class Login{
    constructor(form,fields){
        this.form = form;
        this.fields = fields;
        this.validateonSubmit();
    }

    validateonSubmit(){
        let self = this;
        this.form.addEventListener("submit", (e) => {
            e.preventDefault();
            const whichButton = e.submitter;

            var err = 0;
            self.fields.forEach((field) => {
                const input = document.querySelector(`#${field}`);
                if(self.valdiateFields(input) == false){
                    err++;
                }
            });

            if(err == 0){
                const user = document.querySelector("#username");
                const pass = document.querySelector("#password");
                self.login(user, pass);
            }
        });
    }

    async login(user, pass){
        // backend handles empty phone or email, so can send whichever one is provided
        const username = user.value.trim();
        const body = {};

        if(username.includes("@")){
            body.email = username;
        }else{
            body.phone = username;
        }

        try{
            body.password_hash = await hashPassword(pass.value);
            const response = await fetch("http://127.0.0.1:5000/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include", // enables storing session information
                body: JSON.stringify(body)
            });

            if(response.ok){
                window.location.href = this.form.action;
            }else{
                this.setStatus(user, "", "error");
                this.setStatus(pass, "The password OR username may be incorrect", "error");
            }

        }catch(error){
            this.setStatus(pass, "Could not reach the server", "error");
        }
    }

    valdiateFields(field){

        if(field.value.trim() == ""){
            this.setStatus(
                field,
                `${field.previousElementSibling.innerText} cannot be blank`,
                 "error"
            );
            return false;
        }else{
            this.setStatus(field, null, "success");
            return true;
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

const form = document.querySelector(".loginForm");

if(form){
    const fields = ["username", "password"];
    const validator = new Login (form, fields);
}