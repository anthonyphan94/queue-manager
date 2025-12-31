/**
 * Firebase Configuration
 * 
 * Initializes Firebase and exports the Firestore database instance.
 * Used for real-time synchronization with onSnapshot listeners.
 */

import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
    apiKey: "AIzaSyB1FY8ssXBZSDOfxVZ0ZFNzI_wYhrQaQRo",
    authDomain: "mbl-queue-manager.firebaseapp.com",
    projectId: "mbl-queue-manager",
    storageBucket: "mbl-queue-manager.firebasestorage.app",
    messagingSenderId: "382115177008",
    appId: "1:382115177008:web:58f41146f4f433239a83f5"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize and export Firestore
export const db = getFirestore(app);
export default app;
