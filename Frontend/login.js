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
                    if(user.value == "admin" && pass.value == "admin123"){
                        localStorage.setItem("auth", 1);
                        this.form.submit();
                    }else{
                        this.setStatus(user, "","error");
                        this.setStatus(pass, "The Password OR Username May Be Wrong", "error")
                    }
                
                }
        });
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