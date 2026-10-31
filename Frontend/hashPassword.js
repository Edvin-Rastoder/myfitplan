// Signup and login must use these consistently
async function hashPassword(password){
    const bytes = new TextEncoder().encode("myfitplan:" + password);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}
