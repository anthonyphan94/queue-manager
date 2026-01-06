import { create } from 'zustand';

// ============================================
// DATA MODEL - Mail-Style CSV Import
// ============================================

/**
 * Row - A single imported CSV row with validation status
 * 
 * INVARIANTS:
 * - status === "excluded" if and only if errors.length > 0
 * - "ready" rows can be included/excluded from sending
 * - "excluded" rows are never includable
 */
export interface Row {
    id: string;              // Stable unique identifier
    rowIndex: number;        // 1-based CSV row number for display
    name: string;
    phone: string;
    status: 'ready' | 'excluded';
    errors: string[];        // Non-empty only when status === "excluded"
}

/**
 * SmsResult - Result of sending an SMS
 */
export interface SmsResult {
    rowId: string;
    name: string;
    phone: string;
    status: 'sent' | 'failed' | 'pending';
    sid?: string;
    error?: string;
}

/**
 * UndoSnapshot - State saved for Undo functionality
 */
interface UndoSnapshot {
    rows: Row[];
    includedIdsSnapshot: string[];
    positions: number[];  // Original positions of removed rows
}

/**
 * MarketingState - Complete state with mail-style semantics
 * 
 * COUNTS INVARIANTS:
 * - Imported = rows.length
 * - Ready = rows.filter(r => r.status === 'ready').length
 * - Excluded = rows.filter(r => r.status === 'excluded').length
 * - Included = includedIds.size (only ready rows)
 * - Imported = Ready + Excluded (always)
 * - Included <= Ready (always)
 */
interface MarketingState {
    // === Tab State ===
    activeTab: 'manual' | 'csv';
    setActiveTab: (tab: 'manual' | 'csv') => void;

    // === ROW STATE ===
    rows: Row[];

    // === INCLUSION STATE ===
    // IDs of rows currently selected to send (ready rows only)
    includedIds: Set<string>;

    // === UNDO STATE ===
    lastRemoved: UndoSnapshot | null;

    // === TOAST STATE ===
    toast: { message: string; showUndo: boolean } | null;

    // === SENDING STATE ===
    isSending: boolean;
    sendResults: SmsResult[];

    // === MESSAGE STATE ===
    messageDraft: string;
    setMessageDraft: (message: string) => void;

    // === ERROR STATE ===
    error: string | null;
    setError: (error: string | null) => void;

    // === COMPUTED HELPERS ===
    getCounts: () => {
        imported: number;
        ready: number;
        excluded: number;
        included: number;
    };
    getReadyRows: () => Row[];
    getExcludedRows: () => Row[];
    getIncludedRows: () => Row[];

    // === IMPORT ACTIONS ===
    setImportData: (rows: Row[]) => void;
    clearAllData: () => void;

    // === INCLUSION ACTIONS ===
    includeAllReady: () => void;
    includeNone: () => void;
    toggleInclusion: (rowId: string) => void;

    // === REMOVAL ACTIONS ===
    removeRow: (rowId: string) => void;
    removeSelected: () => void;
    undoRemove: () => void;

    // === TOAST ACTIONS ===
    dismissToast: () => void;

    // === SENDING ACTIONS ===
    setSending: (sending: boolean) => void;
    setSendResults: (results: SmsResult[]) => void;
    clearResults: () => void;
}

/**
 * Marketing Store - Mail-Style Implementation
 */
export const useMarketingStore = create<MarketingState>((set, get) => ({
    // === Tab State ===
    activeTab: 'manual',
    setActiveTab: (tab) => set({ activeTab: tab }),

    // === ROW STATE ===
    rows: [],

    // === INCLUSION STATE ===
    includedIds: new Set(),

    // === UNDO STATE ===
    lastRemoved: null,

    // === TOAST STATE ===
    toast: null,

    // === SENDING STATE ===
    isSending: false,
    sendResults: [],

    // === MESSAGE STATE ===
    messageDraft: '',
    setMessageDraft: (message) => set({ messageDraft: message }),

    // === ERROR STATE ===
    error: null,
    setError: (error) => set({ error }),

    // === COMPUTED HELPERS ===
    getCounts: () => {
        const state = get();
        const ready = state.rows.filter(r => r.status === 'ready').length;
        const excluded = state.rows.filter(r => r.status === 'excluded').length;
        return {
            imported: state.rows.length,
            ready,
            excluded,
            included: state.includedIds.size,
        };
    },

    getReadyRows: () => get().rows.filter(r => r.status === 'ready'),
    getExcludedRows: () => get().rows.filter(r => r.status === 'excluded'),
    getIncludedRows: () => {
        const state = get();
        return state.rows.filter(r =>
            r.status === 'ready' && state.includedIds.has(r.id)
        );
    },

    // === IMPORT ACTIONS ===
    setImportData: (rows) => {
        set({
            rows,
            // Start with nothing included - user must explicitly include
            includedIds: new Set(),
            sendResults: [],
            error: null,
            lastRemoved: null,
            toast: null,
        });
    },

    clearAllData: () => {
        set({
            rows: [],
            includedIds: new Set(),
            sendResults: [],
            error: null,
            lastRemoved: null,
            toast: null,
        });
    },

    // === INCLUSION ACTIONS ===
    includeAllReady: () => {
        const readyIds = get().rows
            .filter(r => r.status === 'ready')
            .map(r => r.id);
        set({ includedIds: new Set(readyIds) });
    },

    includeNone: () => {
        set({ includedIds: new Set() });
    },

    toggleInclusion: (rowId: string) => {
        const state = get();
        const row = state.rows.find(r => r.id === rowId);

        // GUARD: Cannot include excluded rows
        if (!row || row.status === 'excluded') return;

        const newIncluded = new Set(state.includedIds);
        if (newIncluded.has(rowId)) {
            newIncluded.delete(rowId);
        } else {
            newIncluded.add(rowId);
        }
        set({ includedIds: newIncluded });
    },

    // === REMOVAL ACTIONS ===
    removeRow: (rowId: string) => {
        const state = get();
        const rowIndex = state.rows.findIndex(r => r.id === rowId);
        if (rowIndex === -1) return;

        const row = state.rows[rowIndex];
        const newRows = [...state.rows];
        newRows.splice(rowIndex, 1);

        const newIncluded = new Set(state.includedIds);
        newIncluded.delete(rowId);

        // Save for Undo
        const snapshot: UndoSnapshot = {
            rows: [row],
            includedIdsSnapshot: state.includedIds.has(rowId) ? [rowId] : [],
            positions: [rowIndex],
        };

        set({
            rows: newRows,
            includedIds: newIncluded,
            lastRemoved: snapshot,
            toast: { message: 'Removed 1 recipient', showUndo: true },
        });

        // Auto-dismiss toast after 6 seconds
        setTimeout(() => {
            const current = get();
            if (current.toast?.message === 'Removed 1 recipient') {
                set({ toast: null, lastRemoved: null });
            }
        }, 6000);
    },

    removeSelected: () => {
        const state = get();
        if (state.includedIds.size === 0) return;

        const removedRows: Row[] = [];
        const positions: number[] = [];
        const includedSnapshot = Array.from(state.includedIds);

        // Find rows to remove and their positions
        state.rows.forEach((row, index) => {
            if (state.includedIds.has(row.id)) {
                removedRows.push(row);
                positions.push(index);
            }
        });

        // Remove the rows
        const newRows = state.rows.filter(r => !state.includedIds.has(r.id));

        // Save for Undo
        const snapshot: UndoSnapshot = {
            rows: removedRows,
            includedIdsSnapshot: includedSnapshot,
            positions,
        };

        const count = removedRows.length;
        set({
            rows: newRows,
            includedIds: new Set(),
            lastRemoved: snapshot,
            toast: { message: `Removed ${count} recipient${count !== 1 ? 's' : ''}`, showUndo: true },
        });

        // Auto-dismiss toast after 6 seconds
        setTimeout(() => {
            const current = get();
            if (current.toast?.message.startsWith('Removed ')) {
                set({ toast: null, lastRemoved: null });
            }
        }, 6000);
    },

    undoRemove: () => {
        const state = get();
        if (!state.lastRemoved) return;

        const { rows: removedRows, includedIdsSnapshot, positions } = state.lastRemoved;

        // Restore rows to their original positions
        const newRows = [...state.rows];
        removedRows.forEach((row, i) => {
            const pos = positions[i];
            // Insert at original position (or end if position is now beyond array)
            const insertPos = Math.min(pos, newRows.length);
            newRows.splice(insertPos, 0, row);
        });

        // Restore included IDs
        const newIncluded = new Set(state.includedIds);
        includedIdsSnapshot.forEach(id => newIncluded.add(id));

        set({
            rows: newRows,
            includedIds: newIncluded,
            lastRemoved: null,
            toast: null,
        });
    },

    // === TOAST ACTIONS ===
    dismissToast: () => set({ toast: null }),

    // === SENDING ACTIONS ===
    setSending: (sending) => set({ isSending: sending }),
    setSendResults: (results) => set({ sendResults: results, isSending: false }),
    clearResults: () => set({ sendResults: [] }),
}));
