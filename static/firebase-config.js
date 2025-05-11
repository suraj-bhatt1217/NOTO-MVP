import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, 
         GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-firestore.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCQtLJnMfV-L0-PXCHCHGLoIRe2RtgG3xM",
  authDomain: "noto-firebase-auth.firebaseapp.com",
  projectId: "noto-firebase-auth",
  storageBucket: "noto-firebase-auth.firebasestorage.app",
  messagingSenderId: "663797937929",
  appId: "1:663797937929:web:f753a53f4e9789002985d8",
  measurementId: "G-W7ZS3DBYQL"
};

  // Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

const db = getFirestore(app);

export { auth, provider, db };