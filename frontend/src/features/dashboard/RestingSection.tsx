/**
 * RestingSection - Displays technicians on break in a compact grid layout.
 */

import type { Technician } from '../../types';
import { useStatusTimer, formatDuration } from '../../hooks/useStatusTimer';

interface RestingSectionProps {
    onBreak: Technician[];
    onReturn: (techId: number) => void;
}

// Compact tile for technician on break
const BreakTile = ({ tech, onReturn }: { tech: Technician; onReturn: (techId: number) => void }) => {
    const elapsedSeconds = useStatusTimer(tech.status_start_time);

    return (
        <button
            onClick={() => onReturn(tech.id)}
            title={`Click to return ${tech.name} from break`}
            className="bg-orange-50 p-3 rounded-xl border border-orange-200 hover:bg-orange-100 hover:border-orange-300 transition-all duration-200 cursor-pointer flex flex-col items-center gap-1 shadow-sm"
        >
            <span className="font-bold text-sm text-slate-800 truncate w-full text-center">
                {tech.name}
            </span>
            <span className="text-xs text-orange-600 font-mono font-semibold">
                {formatDuration(elapsedSeconds)}
            </span>
        </button>
    );
};

export const RestingSection = ({ onBreak, onReturn }: RestingSectionProps) => {
    if (onBreak.length === 0) return null;

    return (
        <div className="flex flex-col h-full bg-white border-t-2 border-orange-200">
            {/* Header - Static, doesn't scroll */}
            <div className="shrink-0 px-3 md:px-4 py-2 md:py-3 bg-orange-50 border-b border-orange-100">
                <h2 className="text-sm md:text-base font-bold text-orange-700">
                    🍴 On Break ({onBreak.length})
                </h2>
            </div>

            {/* Scrollable Grid */}
            <div className="flex-1 overflow-y-auto p-2 md:p-3">
                <div className="grid grid-cols-2 gap-2">
                    {onBreak.map((tech) => (
                        <BreakTile key={tech.id} tech={tech} onReturn={onReturn} />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default RestingSection;
