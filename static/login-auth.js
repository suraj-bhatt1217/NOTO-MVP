import { auth, provider } from "./firebase-config.js";

import { createUserWithEmailAndPassword,
         signInWithEmailAndPassword,
         signInWithPopup,
         sendPasswordResetEmail } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";



/* == UI - Elements == */
const signInWithGoogleButtonEl = document.getElementById("sign-in-with-google-btn")
const signUpWithGoogleButtonEl = document.getElementById("sign-up-with-google-btn")
const emailInputEl = document.getElementById("email-input")
const passwordInputEl = document.getElementById("password-input")
const signInButtonEl = document.getElementById("sign-in-btn")
const createAccountButtonEl = document.getElementById("create-account-btn")
const emailForgotPasswordEl = document.getElementById("email-forgot-password")
const forgotPasswordButtonEl = document.getElementById("forgot-password-btn")

const errorMsgEmail = document.getElementById("email-error-message")
const errorMsgPassword = document.getElementById("password-error-message")
const errorMsgGoogleSignIn = document.getElementById("google-signin-error-message")



/* == UI - Event Listeners == */
if (signInWithGoogleButtonEl && signInButtonEl) {
    signInWithGoogleButtonEl.addEventListener("click", authSignInWithGoogle)
    signInButtonEl.addEventListener("click", authSignInWithEmail)
}

if (createAccountButtonEl) {
    createAccountButtonEl.addEventListener("click", authCreateAccountWithEmail)
}

if (signUpWithGoogleButtonEl) {
    signUpWithGoogleButtonEl.addEventListener("click", authSignUpWithGoogle)
}

if (forgotPasswordButtonEl) {
    forgotPasswordButtonEl.addEventListener("click", resetPassword)
}




/* === Main Code === */

/* = Functions - Firebase - Authentication = */

// Function to sign in with Google authentication
async function authSignInWithGoogle() {
    console.log('🔵 Google Sign-in button clicked');
    
    // Configure Google Auth provider with custom parameters
    provider.setCustomParameters({
        'prompt': 'select_account'
    });
    
    console.log('🔵 Google Auth provider configured');

    try {
        console.log('🔵 Attempting signInWithPopup...');
        // Attempt to sign in with a popup and retrieve user data
        const result = await signInWithPopup(auth, provider);
        console.log('🔵 signInWithPopup successful, result:', result);

        // Check if the result or user object is undefined or null
        if (!result || !result.user) {
            console.error('❌ No user data returned from Google Sign-in');
            throw new Error('Authentication failed: No user data returned.');
        }

        const user = result.user;
        const email = user.email;
        console.log('🔵 User data extracted:', { uid: user.uid, email: email, displayName: user.displayName });

        // Ensure the email is available in the user data
        if (!email) {
            console.error('❌ No email address returned from Google Sign-in');
            throw new Error('Authentication failed: No email address returned.');
        }

        console.log('🔵 Getting ID token...');
        // Retrieve ID token for the user
        const idToken = await user.getIdToken();
        console.log('🔵 ID token retrieved successfully, length:', idToken.length);

        // Log in the user using the obtained ID token
        console.log('🔵 Calling loginUser function...');
        loginUser(user, idToken);

    } catch (error) {
        console.error('❌ Error during Google Sign-in:', error);
        console.error('❌ Error code:', error.code);
        console.error('❌ Error message:', error.message);
        console.error('❌ Full error object:', error);
        // Handle errors by logging and potentially updating the UI
        handleLogging(error, 'Error during sign-in with Google');
    }
}



// Function to create new account with Google auth - will also sign in existing users
async function authSignUpWithGoogle() {
    console.log('🔵 Google Sign-up button clicked');
    
    provider.setCustomParameters({
        'prompt': 'select_account'
    });

    try {
        console.log('🔵 Attempting Google signup with popup...');
        const result = await signInWithPopup(auth, provider);
        console.log('🔵 Google signup successful, result:', result);
        
        const user = result.user;
        const email = user.email;
        console.log('🔵 Signup user data:', { uid: user.uid, email: email });

        // Sign in user
        console.log('🔵 Getting ID token for signup...');
        const idToken = await user.getIdToken();
        console.log('🔵 Signup ID token retrieved');
        loginUser(user, idToken);
    } catch (error) {
        // The AuthCredential type that was used or other errors.
        console.error("❌ Error during Google signup:", error);
        console.error("❌ Signup error code:", error.code);
        console.error("❌ Signup error message:", error.message);
        // Handle error appropriately here, e.g., updating UI to show an error message
    }
}




function authSignInWithEmail() {

    const email = emailInputEl.value
    const password = passwordInputEl.value

    signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            // Signed in 
            const user = userCredential.user;

            user.getIdToken().then(function(idToken) {
                loginUser(user, idToken)
            });

            console.log("User signed in: ", user)
        })
        .catch((error) => {
            const errorCode = error.code;
            console.error("Error code: ", errorCode)
            if (errorCode === "auth/invalid-email") {
                errorMsgEmail.textContent = "Invalid email"
            } else if (errorCode === "auth/invalid-credential") {
                errorMsgPassword.textContent = "Login failed - invalid email or password"
            } 
        });
}



function authCreateAccountWithEmail() {
    // Clear previous error messages
    errorMsgEmail.textContent = ""
    errorMsgPassword.textContent = ""
    
    const email = emailInputEl.value
    const password = passwordInputEl.value
    
    // Add loading indicator to button
    if (createAccountButtonEl) {
        createAccountButtonEl.innerHTML = "Creating Account..."
        createAccountButtonEl.disabled = true
    }

    createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            // Signed in 
            const user = userCredential.user;
            
            // Show success message
            if (errorMsgEmail) {
                errorMsgEmail.textContent = "Account created successfully! Redirecting..."
                errorMsgEmail.style.color = "green"
            }
            
            // Get ID token and login user
            user.getIdToken().then(function(idToken) {
                loginUser(user, idToken)
            });
        })
        .catch((error) => {
            const errorCode = error.code;
            
            // Reset button
            if (createAccountButtonEl) {
                createAccountButtonEl.innerHTML = "Sign Up"
                createAccountButtonEl.disabled = false
            }
            
            if (errorCode === "auth/invalid-email") {
                errorMsgEmail.textContent = "Invalid email"
            } else if (errorCode === "auth/weak-password") {
                errorMsgPassword.textContent = "Invalid password - must be at least 6 characters"
            } else if (errorCode === "auth/email-already-in-use") {
                errorMsgEmail.textContent = "An account already exists for this email."
            } else {
                // Generic error message for other errors
                errorMsgEmail.textContent = "Error creating account: " + error.message
            }
        });

}



function resetPassword() {
    const emailToReset = emailForgotPasswordEl.value

    clearInputField(emailForgotPasswordEl)

    sendPasswordResetEmail(auth, emailToReset)
    .then(() => {
        // Password reset email sent!
        const resetFormView = document.getElementById("reset-password-view")
        const resetSuccessView = document.getElementById("reset-password-confirmation-page")

        resetFormView.style.display = "none"
        resetSuccessView.style.display = "block"

    })
    .catch((error) => {
        const errorCode = error.code;
        const errorMessage = error.message;
 
    });

}



function loginUser(user, idToken) {
    console.log('🔵 loginUser called with user:', { uid: user.uid, email: user.email });
    console.log('🔵 ID token length:', idToken.length);
    
    const requestData = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${idToken}`
        },
        credentials: 'same-origin'
    };
    
    console.log('🔵 Making fetch request to /auth with headers:', requestData.headers);
    
    fetch('/auth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${idToken}`
        },
        credentials: 'same-origin'  // Ensures cookies are sent with the request
    }).then(response => {
        console.log('🔵 Received response from /auth:', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
            headers: Object.fromEntries(response.headers.entries())
        });
        
        if (response.ok) {
            console.log('🔵 Login successful, redirecting to dashboard...');
            window.location.href = '/dashboard';
        } else {
            console.error('❌ Login failed with status:', response.status);
            response.text().then(text => {
                console.error('❌ Response body:', text);
            });
            // Handle errors here
        }
    }).catch(error => {
        console.error('❌ Fetch error during login:', error);
        console.error('❌ Network error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    });
}



// /* = Functions - UI = */
function clearInputField(field) {
	field.value = ""
}

function clearAuthFields() {
	clearInputField(emailInputEl)
	clearInputField(passwordInputEl)
}


