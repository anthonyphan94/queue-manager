/**
 * RestingSection - Displays technicians on break with a live timer.
 */

import type { Technician } from '../../types';
import { BackIcon, CoffeeIcon } from './Icons';
import { useStatusTimer, formatDuration } from '../../hooks/useStatusTimer';

interface RestingSectionProps {
    onBreak: Technician[];
    onReturn: (techId: number) => void;
}

// Individual break card with timer
const BreakCard = ({ tech, onReturn }: { tech: Technician; onReturn: (techId: number) => void }) => {
    const elapsedSeconds = useStatusTimer(tech.status_start_time);

    return (
        <div className="bg-orange-50 p-3 md:p-4 rounded-xl border-2 border-orange-300 flex items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-full bg-orange-200 text-orange-600">
                    <CoffeeIcon />
                </div>
                <div>
                    <span className="font-bold text-base md:text-lg text-slate-800">{tech.name}</span>
                    <div className="text-sm text-orange-600 font-mono font-semibold">
                        Break: {formatDuration(elapsedSeconds)}
                    </div>
                </div>
            </div>
            <button
                onClick={() => onReturn(tech.id)}
                title="Return from Break"
                className="p-2 md:p-3 bg-white text-orange-500 rounded-lg border border-orange-300 hover:bg-orange-100 shadow-sm transition-colors cursor-pointer flex items-center gap-2 font-semibold"
            >
                <BackIcon />
                <span className="hidden md:inline">Back</span>
            </button>
        </div>
    );
};

export const RestingSection = ({ onBreak, onReturn }: RestingSectionProps) => {
    if (onBreak.length === 0) return null;

    return (
        <div className="w-full flex flex-col bg-white rounded-3xl shadow-sm border border-orange-200 overflow-hidden">
            {/* Header */}
            <div className="p-3 md:p-4 border-b border-orange-100 bg-orange-50">
                <h2 className="text-base md:text-lg font-bold text-orange-700 flex items-center gap-2">
                    <CoffeeIcon />
                    On Break ({onBreak.length})
                </h2>
            </div>

            {/* Break Cards */}
            <div className="p-3 md:p-4 space-y-2 md:space-y-3">
                {onBreak.map((tech) => (
                    <BreakCard key={tech.id} tech={tech} onReturn={onReturn} />
                ))}
            </div>
        </div>
    );
};

export default RestingSection;
