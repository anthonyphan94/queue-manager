import { create } from 'zustand';
import { db } from '../firebase';
import { collection, query, orderBy, onSnapshot } from 'firebase/firestore';

// Use relative URLs in production (served from same origin), localhost in development
const isDev = import.meta.env.DEV;
const API_URL = isDev ? 'http://localhost:8000' : '';

export const useTechStore = create((set, get) => ({
    technicians: [],
    firestoreConnected: false,
    unsubscribe: null,

    // Connect to Firestore real-time listener
    connect: () => {
        // Prevent duplicate subscriptions
        if (get().unsubscribe) {
            console.log('Firestore already connected');
            return;
        }

        console.log('🔥 Connecting to Firestore...');

        // Create query ordered by queue_position
        const techniciansRef = collection(db, 'technicians');
        const q = query(techniciansRef, orderBy('queue_position'));

        // Subscribe to real-time updates
        const unsubscribe = onSnapshot(
            q,
            (snapshot) => {
                const techs = snapshot.docs.map((doc) => ({
                    id: parseInt(doc.id, 10),
                    ...doc.data(),
                    // Convert Firestore Timestamp to ISO string for consistency
                    status_start_time: doc.data().status_start_time?.toDate?.()?.toISOString() || null
                }));

                console.log(`📦 Firestore update: ${techs.length} technicians`);
                set({ technicians: techs, firestoreConnected: true });
            },
            (error) => {
                console.error('❌ Firestore error:', error);
                set({ firestoreConnected: false });
            }
        );

        set({ unsubscribe });
    },

    // Disconnect from Firestore (cleanup)
    disconnect: () => {
        const { unsubscribe } = get();
        if (unsubscribe) {
            console.log('🔌 Disconnecting from Firestore');
            unsubscribe();
            set({ unsubscribe: null, firestoreConnected: false });
        }
    },

    // Add technician (via Python API)
    addTech: async (name) => {
        const res = await fetch(`${API_URL}/techs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        return res.json();
    },

    // Assign next available tech (via Python API)
    assignNext: async (clientName) => {
        const res = await fetch(`${API_URL}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: clientName }),
        });
        return res.json();
    },

    // Request specific tech (via Python API)
    requestTech: async (techId, clientName) => {
        const res = await fetch(`${API_URL}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: clientName, request_tech_id: techId }),
        });
        return res.json();
    },

    // Complete turn (via Python API)
    completeTurn: async (techId, isRequest = false) => {
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
    skipTurn: async (techId) => {
        return get().completeTurn(techId, false);
    },

    // Toggle technician active/inactive (via Python API)
    toggleActive: async (techId) => {
        const res = await fetch(`${API_URL}/techs/toggle-active`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        return res.json();
    },

    // Reorder queue (via Python API)
    reorderQueue: async (techIds) => {
        const res = await fetch(`${API_URL}/techs/reorder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_ids: techIds }),
        });
        return res.json();
    },

    // Remove technician (via Python API)
    removeTech: async (techId) => {
        const res = await fetch(`${API_URL}/techs/${techId}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to remove technician');
        return res.json();
    },

    // Take break (via Python API)
    takeBreak: async (techId) => {
        const res = await fetch(`${API_URL}/techs/break`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        if (!res.ok) throw new Error('Failed to take break');
        return res.json();
    },

    // Return from break (via Python API)
    returnFromBreak: async (techId) => {
        const res = await fetch(`${API_URL}/techs/return`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        if (!res.ok) throw new Error('Failed to return from break');
        return res.json();
    },
}));
