/**
 * useStatusTimer - Reusable hook for calculating elapsed time from status_start_time.
 * 
 * This hook handles:
 * - Live updating every second
 * - Negative value prevention (Math.max(0, diff))
 * - Null/undefined status_start_time handling
 */

import { useState, useEffect } from 'react';

/**
 * Format duration in MM:SS format
 */
export const formatDuration = (seconds: number): string => {
    // Ensure we never show negative values
    const safeSeconds = Math.max(0, seconds);
    const mins = Math.floor(safeSeconds / 60);
    const secs = safeSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Hook that returns elapsed seconds since status_start_time
 */
export const useStatusTimer = (statusStartTime?: string | null): number => {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        if (!statusStartTime) {
            setElapsed(0);
            return;
        }

        const startTime = new Date(statusStartTime).getTime();

        // Check for invalid date
        if (isNaN(startTime)) {
            setElapsed(0);
            return;
        }

        const updateElapsed = () => {
            const now = Date.now();
            // Prevent negative values
            setElapsed(Math.max(0, Math.floor((now - startTime) / 1000)));
        };

        updateElapsed();
        const interval = setInterval(updateElapsed, 1000);

        return () => clearInterval(interval);
    }, [statusStartTime]);

    return elapsed;
};

export default useStatusTimer;
