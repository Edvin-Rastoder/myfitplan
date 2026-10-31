class Authenticate{
    // Sends a request to the backend with the session cookie; 401 if cookie is missing or expired
    async apiFetch(path, options = {}){
        const response = await fetch("http://127.0.0.1:5000" + path, { ...options, credentials: "include" });
        if(response.status == 401){
            window.location.replace("loginpage.html");
        }
        return response;
    }

    async logout(){
        try{
            await fetch("http://127.0.0.1:5000/logout", { method: "POST", credentials: "include" });
        }finally{
            window.location.replace("index.html");
        }
    }
}