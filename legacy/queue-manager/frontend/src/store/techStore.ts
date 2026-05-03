/**
 * Zustand store for technician state management.
 * Connects to Firestore for real-time updates and provides API methods.
 */

import { create } from 'zustand';
import { getDB } from '../firebase';
import { collection, query, orderBy, onSnapshot, type Unsubscribe, type Firestore } from 'firebase/firestore';
import type {
    Technician,
    AssignResponse,
    CompleteResponse,
    ToggleActiveResponse,
    ReorderResponse,
    RemoveResponse,
} from '../types';
import { API_BASE as API_URL } from '../utils/api';

interface BreakResponse {
    tech_id: number;
    status: string;
    status_start_time: string | null;
}

interface ResetResponse {
    success: boolean;
    deleted_from_firestore: number;
    message: string;
}

interface TechStore {
    technicians: Technician[];
    firestoreConnected: boolean;
    unsubscribe: Unsubscribe | null;

    // Connection methods
    connect: () => Promise<void>;
    disconnect: () => void;

    // API methods
    addTech: (name: string) => Promise<Technician>;
    assignNext: (clientName: string) => Promise<AssignResponse>;
    requestTech: (techId: number, clientName: string) => Promise<AssignResponse>;
    completeTurn: (techId: number, isRequest?: boolean) => Promise<CompleteResponse>;
    skipTurn: (techId: number) => Promise<CompleteResponse>;
    toggleActive: (techId: number) => Promise<ToggleActiveResponse>;
    reorderQueue: (techIds: number[]) => Promise<ReorderResponse>;
    removeTech: (techId: number) => Promise<RemoveResponse>;
    takeBreak: (techId: number) => Promise<BreakResponse>;
    returnFromBreak: (techId: number) => Promise<BreakResponse>;
    resetAllTechnicians: () => Promise<ResetResponse>;
}

export const useTechStore = create<TechStore>((set, get) => ({
    technicians: [],
    firestoreConnected: false,
    unsubscribe: null,

    // Connect to Firestore real-time listener (lazy loads Firebase)
    connect: async () => {
        // Prevent duplicate subscriptions
        if (get().unsubscribe) {
            console.log('Firestore already connected');
            return;
        }

        console.log('Connecting to Firestore...');

        // Lazy load Firestore
        const db: Firestore = await getDB();

        // Create query ordered by queue_position
        const techniciansRef = collection(db, 'technicians');
        const q = query(techniciansRef, orderBy('queue_position'));

        // Subscribe to real-time updates
        const unsubscribe = onSnapshot(
            q,
            (snapshot) => {
                const techs: Technician[] = snapshot.docs.map((doc) => ({
                    id: parseInt(doc.id, 10),
                    name: doc.data().name,
                    status: doc.data().status,
                    queue_position: doc.data().queue_position,
                    is_active: doc.data().is_active,
                    // Convert Firestore Timestamp to ISO string for consistency
                    status_start_time: doc.data().status_start_time?.toDate?.()?.toISOString() || undefined
                }));

                console.log(`Firestore update: ${techs.length} technicians`);
                set({ technicians: techs, firestoreConnected: true });
            },
            (error) => {
                console.error('Firestore error:', error);
                set({ firestoreConnected: false });
            }
        );

        set({ unsubscribe });
    },

    // Disconnect from Firestore (cleanup)
    disconnect: () => {
        const { unsubscribe } = get();
        if (unsubscribe) {
            console.log('Disconnecting from Firestore');
            unsubscribe();
            set({ unsubscribe: null, firestoreConnected: false });
        }
    },

    // Add technician (via Python API)
    addTech: async (name: string): Promise<Technician> => {
        const res = await fetch(`${API_URL}/techs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        if (!res.ok) throw new Error('Failed to add technician');
        return res.json();
    },

    // Assign next available tech (via Python API)
    assignNext: async (clientName: string): Promise<AssignResponse> => {
        const res = await fetch(`${API_URL}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: clientName }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to assign technician');
        }
        return res.json();
    },

    // Request specific tech (via Python API)
    requestTech: async (techId: number, clientName: string): Promise<AssignResponse> => {
        const res = await fetch(`${API_URL}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: clientName, request_tech_id: techId }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to request technician');
        }
        return res.json();
    },

    // Complete turn (via Python API)
    completeTurn: async (techId: number, isRequest: boolean = false): Promise<CompleteResponse> => {
        console.log(`Sending complete turn for techId: ${techId}, isRequest: ${isRequest}`);
        const res = await fetch(`${API_URL}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId, is_request: isRequest }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to complete turn');
        }
        return res.json();
    },

    // Skip turn (alias for completeTurn)
    skipTurn: async (techId: number): Promise<CompleteResponse> => {
        return get().completeTurn(techId, false);
    },

    // Toggle technician active/inactive (via Python API)
    toggleActive: async (techId: number): Promise<ToggleActiveResponse> => {
        const res = await fetch(`${API_URL}/techs/toggle-active`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        if (!res.ok) throw new Error('Failed to toggle active status');
        return res.json();
    },

    // Reorder queue (via Python API)
    reorderQueue: async (techIds: number[]): Promise<ReorderResponse> => {
        const res = await fetch(`${API_URL}/techs/reorder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_ids: techIds }),
        });
        if (!res.ok) throw new Error('Failed to reorder queue');
        return res.json();
    },

    // Remove technician (via Python API)
    removeTech: async (techId: number): Promise<RemoveResponse> => {
        const res = await fetch(`${API_URL}/techs/${techId}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to remove technician');
        return res.json();
    },

    // Take break (via Python API)
    takeBreak: async (techId: number): Promise<BreakResponse> => {
        const res = await fetch(`${API_URL}/techs/break`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        if (!res.ok) throw new Error('Failed to take break');
        return res.json();
    },

    // Return from break (via Python API)
    returnFromBreak: async (techId: number): Promise<BreakResponse> => {
        const res = await fetch(`${API_URL}/techs/return`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        if (!res.ok) throw new Error('Failed to return from break');
        return res.json();
    },

    // Reset all technicians (admin - clears Firestore)
    resetAllTechnicians: async (): Promise<ResetResponse> => {
        const res = await fetch(`${API_URL}/admin/reset-technicians`, {
            method: 'POST',
        });
        if (!res.ok) throw new Error('Failed to reset technicians');
        return res.json();
    },
}));
