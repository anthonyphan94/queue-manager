import { create } from 'zustand';
import { API_BASE } from '../utils/api';

const AUTH_KEY = 'marketing_auth';
const SESSION_TTL = 2 * 60 * 60 * 1000; // 2 hours in ms

/**
 * Auth store for Marketing module PIN authentication.
 *
 * PIN + expiry stored in sessionStorage. Session lasts 2 hours
 * or until the browser is closed (whichever comes first).
 */

function saveSession(pin: string) {
    sessionStorage.setItem(AUTH_KEY, JSON.stringify({
        pin,
        expires: Date.now() + SESSION_TTL,
    }));
}

function loadSession(): string | null {
    try {
        const raw = sessionStorage.getItem(AUTH_KEY);
        if (!raw) return null;
        const { pin, expires } = JSON.parse(raw);
        if (Date.now() > expires) {
            sessionStorage.removeItem(AUTH_KEY);
            return null;
        }
        return pin;
    } catch {
        sessionStorage.removeItem(AUTH_KEY);
        return null;
    }
}

function clearSession() {
    sessionStorage.removeItem(AUTH_KEY);
}

interface ChangePinResult {
    success: boolean;
    message: string;
}

interface AuthState {
    isAuthenticated: boolean;
    pin: string | null;
    isVerifying: boolean;
    error: string | null;

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
                saveSession(pin);
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
                saveSession(newPin);
                set({ pin: newPin });
            }

            return { success: data.success, message: data.message };
        } catch {
            return { success: false, message: 'Connection error. Please try again.' };
        }
    },

    logout: () => {
        clearSession();
        set({ isAuthenticated: false, pin: null, error: null });
    },

    checkStoredAuth: () => {
        const storedPin = loadSession();
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
