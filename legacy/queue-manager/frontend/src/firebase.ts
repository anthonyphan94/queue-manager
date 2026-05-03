/**
 * Firebase Configuration - Lazy Loaded
 *
 * Firebase and Firestore are initialized lazily on first access
 * to reduce initial bundle size and startup time.
 */

import type { FirebaseApp } from 'firebase/app';
import type { Firestore } from 'firebase/firestore';

interface FirebaseConfig {
    apiKey: string;
    authDomain: string;
    projectId: string;
    storageBucket: string;
    messagingSenderId: string;
    appId: string;
}

const firebaseConfig: FirebaseConfig = {
    apiKey: "AIzaSyB1FY8ssXBZSDOfxVZ0ZFNzI_wYhrQaQRo",
    authDomain: "mbl-queue-manager.firebaseapp.com",
    projectId: "mbl-queue-manager",
    storageBucket: "mbl-queue-manager.firebasestorage.app",
    messagingSenderId: "382115177008",
    appId: "1:382115177008:web:58f41146f4f433239a83f5"
};

// Lazy-loaded singletons
let app: FirebaseApp | null = null;
let db: Firestore | null = null;

/**
 * Get or initialize the Firebase app instance.
 */
export async function getApp(): Promise<FirebaseApp> {
    if (!app) {
        const { initializeApp } = await import('firebase/app');
        app = initializeApp(firebaseConfig);
    }
    return app;
}

/**
 * Get or initialize the Firestore database instance.
 * This is the primary export used by the store.
 */
export async function getDB(): Promise<Firestore> {
    if (!db) {
        const [{ getFirestore }, firebaseApp] = await Promise.all([
            import('firebase/firestore'),
            getApp()
        ]);
        db = getFirestore(firebaseApp);
    }
    return db;
}

// For backwards compatibility - synchronous access (use getDB() for new code)
// This will be undefined until getDB() is called
export { db };
