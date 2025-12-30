import { create } from 'zustand';

// Use relative URLs in production (served from same origin), localhost in development
const isDev = import.meta.env.DEV;
const API_URL = isDev ? 'http://localhost:8000' : '';
const WS_URL = isDev ? 'ws://localhost:8000/ws' : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

export const useTechStore = create((set, get) => ({
    technicians: [],
    wsConnected: false,
    ws: null,

    // Connect to WebSocket
    connect: () => {
        if (get().ws) return;

        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('WebSocket connected');
            set({ wsConnected: true });
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'init' || data.type === 'update') {
                set({ technicians: data.technicians });
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            set({ wsConnected: false, ws: null });
            // Reconnect after 2 seconds
            setTimeout(() => get().connect(), 2000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        set({ ws });
    },

    // Add technician
    addTech: async (name) => {
        const res = await fetch(`${API_URL}/techs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        return res.json();
    },

    // Assign next available tech
    assignNext: async (clientName) => {
        const res = await fetch(`${API_URL}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: clientName }),
        });
        return res.json();
    },

    // Request specific tech
    requestTech: async (techId, clientName) => {
        const res = await fetch(`${API_URL}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: clientName, request_tech_id: techId }),
        });
        return res.json();
    },

    // Complete turn
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

    // Skip turn (alias for completeTurn with isRequest=false, effectively moving to bottom)
    skipTurn: async (techId) => {
        return get().completeTurn(techId, false);
    },

    // Toggle technician active/inactive (for daily check-in roster)
    toggleActive: async (techId) => {
        const res = await fetch(`${API_URL}/techs/toggle-active`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        return res.json();
    },

    // Reorder queue
    reorderQueue: async (techIds) => {
        const res = await fetch(`${API_URL}/techs/reorder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_ids: techIds }),
        });
        return res.json();
    },

    // Remove technician
    removeTech: async (techId) => {
        const res = await fetch(`${API_URL}/techs/${techId}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to remove technician');
        return res.json();
    },

    // Take break
    takeBreak: async (techId) => {
        const res = await fetch(`${API_URL}/techs/break`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tech_id: techId }),
        });
        if (!res.ok) throw new Error('Failed to take break');
        return res.json();
    },

    // Return from break
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
