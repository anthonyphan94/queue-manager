import { create } from 'zustand';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const AUTH_KEY = 'marketing_authenticated';

/**
 * Auth store for Marketing module PIN authentication.
 * 
 * Stores PIN in sessionStorage (cleared when browser closes).
 */
interface AuthState {
    isAuthenticated: boolean;
    pin: string | null;
    isVerifying: boolean;
    error: string | null;

    // Actions
    verifyPin: (pin: string) => Promise<boolean>;
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
