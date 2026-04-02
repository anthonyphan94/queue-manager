import { create } from 'zustand';
import { API_BASE } from '../utils/api';

/**
 * Auth store for Marketing module PIN authentication.
 *
 * PIN is kept only in Zustand memory (not persisted to sessionStorage).
 * Page refresh requires re-entering the PIN — this is intentional for security.
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
                set({ pin: newPin });
            }

            return { success: data.success, message: data.message };
        } catch {
            return { success: false, message: 'Connection error. Please try again.' };
        }
    },

    logout: () => {
        set({ isAuthenticated: false, pin: null, error: null });
    },

    checkStoredAuth: () => {
        // PIN is only kept in memory. Page refresh requires re-authentication.
        // This is intentional for security.
    },

    getAuthHeader: () => {
        const state = get();
        if (state.pin) {
            return { 'X-Marketing-Pin': state.pin };
        }
        return {};
    },
}));
