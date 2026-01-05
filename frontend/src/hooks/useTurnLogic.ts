/**
 * useTurnLogic - Custom hook for turn management logic.
 * 
 * This hook encapsulates all API calls, WebSocket listeners, and state management.
 * Components can simply destructure the values and actions they need.
 */

import { useEffect, useCallback, useMemo } from 'react';
import { useTechStore } from '../store/techStore';
import type { Technician } from '../types';

interface UseTurnLogicReturn {
    // State
    technicians: Technician[];
    queue: Technician[];
    working: Technician[];
    onBreak: Technician[];
    isConnected: boolean;

    // Actions
    connect: () => void;
    nextTurn: (clientName?: string) => Promise<void>;
    finish: (techId: number) => Promise<void>;
    request: (techId: number, clientName: string) => Promise<void>;
    skip: (techId: number) => Promise<void>;
    toggleActive: (techId: number) => Promise<void>;
    addTech: (name: string) => Promise<void>;
    removeTech: (techId: number) => Promise<void>;
    reorderQueue: (techIds: number[]) => Promise<void>;
    takeBreak: (techId: number) => Promise<void>;
    returnFromBreak: (techId: number) => Promise<void>;
}

export const useTurnLogic = (): UseTurnLogicReturn => {
    const {
        technicians,
        firestoreConnected,
        connect,
        disconnect,
        assignNext,
        completeTurn,
        requestTech,
        skipTurn,
        toggleActive: storeToggleActive,
        addTech: storeAddTech,
        removeTech: storeRemoveTech,
        reorderQueue: storeReorderQueue,
        takeBreak: storeTakeBreak,
        returnFromBreak: storeReturnFromBreak,
    } = useTechStore();

    // Memoized derived state: Queue (available and active technicians)
    const queue = useMemo(() =>
        technicians
            .filter((t: Technician) => t.status === 'AVAILABLE' && t.is_active)
            .sort((a: Technician, b: Technician) => a.queue_position - b.queue_position),
        [technicians]
    );

    // Memoized derived state: Working (busy technicians)
    const working = useMemo(() =>
        technicians
            .filter((t: Technician) => t.status === 'BUSY' && t.is_active)
            .sort((a: Technician, b: Technician) => a.id - b.id),
        [technicians]
    );

    // Memoized derived state: On Break
    const onBreak = useMemo(() =>
        technicians
            .filter((t: Technician) => t.status === 'ON_BREAK' && t.is_active)
            .sort((a: Technician, b: Technician) => a.id - b.id),
        [technicians]
    );

    // Connect on mount, cleanup on unmount
    useEffect(() => {
        // Connect is now async (lazy loads Firebase)
        connect();
        // Cleanup: unsubscribe from Firestore when component unmounts
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    // Action wrappers with error handling
    const nextTurn = useCallback(async (clientName: string = 'Walk-in') => {
        try {
            await assignNext(clientName);
        } catch (error) {
            console.error('Failed to assign next turn:', error);
            throw error;
        }
    }, [assignNext]);

    const finish = useCallback(async (techId: number) => {
        try {
            await completeTurn(techId, false);
        } catch (error) {
            console.error('Failed to complete turn:', error);
            throw error;
        }
    }, [completeTurn]);

    const request = useCallback(async (techId: number, clientName: string) => {
        try {
            await requestTech(techId, clientName);
        } catch (error) {
            console.error('Failed to request technician:', error);
            throw error;
        }
    }, [requestTech]);

    const skip = useCallback(async (techId: number) => {
        try {
            await skipTurn(techId);
        } catch (error) {
            console.error('Failed to skip turn:', error);
            throw error;
        }
    }, [skipTurn]);

    const toggleActive = useCallback(async (techId: number) => {
        try {
            await storeToggleActive(techId);
        } catch (error) {
            console.error('Failed to toggle active status:', error);
            throw error;
        }
    }, [storeToggleActive]);

    const addTech = useCallback(async (name: string) => {
        try {
            await storeAddTech(name);
        } catch (error) {
            console.error('Failed to add technician:', error);
            throw error;
        }
    }, [storeAddTech]);

    const removeTech = useCallback(async (techId: number) => {
        try {
            await storeRemoveTech(techId);
        } catch (error) {
            console.error('Failed to remove technician:', error);
            throw error;
        }
    }, [storeRemoveTech]);

    const reorderQueue = useCallback(async (techIds: number[]) => {
        try {
            await storeReorderQueue(techIds);
        } catch (error) {
            console.error('Failed to reorder queue:', error);
            throw error;
        }
    }, [storeReorderQueue]);

    const takeBreak = useCallback(async (techId: number) => {
        try {
            await storeTakeBreak(techId);
        } catch (error) {
            console.error('Failed to take break:', error);
            throw error;
        }
    }, [storeTakeBreak]);

    const returnFromBreak = useCallback(async (techId: number) => {
        try {
            await storeReturnFromBreak(techId);
        } catch (error) {
            console.error('Failed to return from break:', error);
            throw error;
        }
    }, [storeReturnFromBreak]);

    return {
        technicians,
        queue,
        working,
        onBreak,
        isConnected: firestoreConnected,
        connect,
        nextTurn,
        finish,
        request,
        skip,
        toggleActive,
        addTech,
        removeTech,
        reorderQueue,
        takeBreak,
        returnFromBreak,
    };
};

export default useTurnLogic;
