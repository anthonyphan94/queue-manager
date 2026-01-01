/**
 * RestingSection - Displays technicians on break in a compact horizontal carousel.
 * iOS HIG compliant: compact chips, horizontal scroll, max height constraint.
 */

import { useState } from 'react';
import type { Technician } from '../../types';
import { useStatusTimer, formatDuration } from '../../hooks/useStatusTimer';

interface RestingSectionProps {
    onBreak: Technician[];
    onReturn: (techId: number) => void;
}

// Compact chip for technician on break
const BreakChip = ({ tech, onReturn }: { tech: Technician; onReturn: (techId: number) => void }) => {
    const elapsedSeconds = useStatusTimer(tech.status_start_time);

    return (
        <button
            onClick={() => onReturn(tech.id)}
            title={`Tap to return ${tech.name} from break`}
            className="break-chip"
        >
            <span className="break-chip-name">{tech.name}</span>
            <span className="break-chip-time">{formatDuration(elapsedSeconds)}</span>
        </button>
    );
};

// Expanded grid view (shown when "See all" is tapped)
const ExpandedGrid = ({
    onBreak,
    onReturn,
    onCollapse
}: {
    onBreak: Technician[];
    onReturn: (techId: number) => void;
    onCollapse: () => void;
}) => {
    return (
        <div className="p-2 md:p-3">
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {onBreak.map((tech) => (
                    <BreakChip key={tech.id} tech={tech} onReturn={onReturn} />
                ))}
            </div>
            <button
                onClick={onCollapse}
                className="mt-2 w-full text-center text-orange-600 text-xs font-medium py-2 min-h-[44px] flex items-center justify-center"
            >
                Show less
            </button>
        </div>
    );
};

export const RestingSection = ({ onBreak, onReturn }: RestingSectionProps) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (onBreak.length === 0) return null;

    return (
        <div
            className="flex flex-col bg-white rounded-2xl shadow-sm border border-orange-200 overflow-hidden"
            style={{ maxHeight: isExpanded ? 'none' : 'var(--on-break-max-height)' }}
        >
            {/* Header - Always visible */}
            <div className="shrink-0 px-3 py-2 bg-orange-50 border-b border-orange-100 flex items-center justify-between">
                <h2 className="text-sm font-bold text-orange-700 flex items-center gap-1.5">
                    <span>🍴</span>
                    <span>On Break ({onBreak.length})</span>
                </h2>
                {onBreak.length > 3 && (
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="text-xs text-orange-600 font-medium px-2 py-1 min-h-[44px] min-w-[44px] flex items-center justify-center"
                    >
                        {isExpanded ? 'Collapse' : 'See all'}
                    </button>
                )}
            </div>

            {/* Content - Carousel or Expanded Grid */}
            {isExpanded ? (
                <ExpandedGrid
                    onBreak={onBreak}
                    onReturn={onReturn}
                    onCollapse={() => setIsExpanded(false)}
                />
            ) : (
                <div className="on-break-carousel scroll-x-ios">
                    {onBreak.map((tech) => (
                        <BreakChip key={tech.id} tech={tech} onReturn={onReturn} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default RestingSection;
