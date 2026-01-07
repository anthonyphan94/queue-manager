import { create } from 'zustand';

// Use relative URLs in production (served from same origin), localhost in development
const isDev = import.meta.env.DEV;
const API_BASE = isDev ? 'http://localhost:8080' : '';
const AUTH_KEY = 'marketing_authenticated';

/**
 * Auth store for Marketing module PIN authentication.
 * 
 * Stores PIN in sessionStorage (cleared when browser closes).
 */
interface ChangePinResult {
    success: boolean;
    message: string;
}

interface AuthState {
    isAuthenticated: boolean;
    pin: string | null;
    isVerifying: boolean;
    error: string | null;

    // Actions
    verifyPin: (pin: string) => Promise<boolean>;
    changePin: (currentPin: string, newPin: string) => Promise<ChangePinResult>;
    logout: () => void;
    checkStoredAuth: () => void;
    getAuthHeader: () => { 'X-Marketing-Pin': string } | {};
}

export const useAuthStore = create<AuthState>((set, get) => ({
    isAuthenticated: false,
    pin: null,
    isVerifying: false,
    error: null,

    verifyPin: async (pin: string) => {
        set({ isVerifying: true, error: null });

        try {
            const response = await fetch(`${API_BASE}/marketing/verify-pin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pin }),
            });

            const data = await response.json();

            if (data.valid) {
                // Store in sessionStorage (cleared when browser closes)
                sessionStorage.setItem(AUTH_KEY, pin);
                set({ isAuthenticated: true, pin, isVerifying: false, error: null });
                return true;
            } else {
                set({ isVerifying: false, error: 'Invalid PIN' });
                return false;
            }
        } catch (err) {
            set({ isVerifying: false, error: 'Connection error. Please try again.' });
            return false;
        }
    },

    changePin: async (currentPin: string, newPin: string): Promise<ChangePinResult> => {
        try {
            const response = await fetch(`${API_BASE}/marketing/change-pin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
            });

            const data = await response.json();

            if (data.success) {
                // Update stored PIN to the new one
                sessionStorage.setItem(AUTH_KEY, newPin);
                set({ pin: newPin });
            }

            return { success: data.success, message: data.message };
        } catch {
            return { success: false, message: 'Connection error. Please try again.' };
        }
    },

    logout: () => {
        sessionStorage.removeItem(AUTH_KEY);
        set({ isAuthenticated: false, pin: null, error: null });
    },

    checkStoredAuth: () => {
        const storedPin = sessionStorage.getItem(AUTH_KEY);
        if (storedPin) {
            set({ isAuthenticated: true, pin: storedPin });
        }
    },

    getAuthHeader: () => {
        const state = get();
        if (state.pin) {
            return { 'X-Marketing-Pin': state.pin };
        }
        return {};
    },
}));
