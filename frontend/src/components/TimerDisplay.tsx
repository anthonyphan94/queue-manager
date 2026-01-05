/**
 * TimerDisplay - Reusable timer component for showing elapsed time.
 * Used for queue waiting time, working time, and break time displays.
 */

import { useStatusTimer, formatDuration } from '../hooks/useStatusTimer';

interface TimerDisplayProps {
    statusStartTime?: string | null;
    label: string;
    className?: string;
}

export const TimerDisplay = ({
    statusStartTime,
    label,
    className = "text-[11px] text-orange-600 font-medium"
}: TimerDisplayProps) => {
    const elapsedSeconds = useStatusTimer(statusStartTime);

    return (
        <span className={className}>
            {label}: {formatDuration(elapsedSeconds)}
        </span>
    );
};

export default TimerDisplay;
