/**
 * WorkingGrid - Displays the technicians currently working.
 * iOS HIG compliant: 1-column on mobile, compact cards, 44px touch targets.
 */

import { memo } from 'react';
import type { Technician } from '../../types';
import { FinishIcon, EmptyStateIcon } from './Icons';
import { TimerDisplay } from '../../components/TimerDisplay';

interface WorkingGridProps {
    working: Technician[];
    onFinish: (techId: number) => void;
}

export const WorkingGrid = memo(({ working, onFinish }: WorkingGridProps) => {
    return (
        <div className="w-full lg:w-[60%] flex flex-col bg-white rounded-2xl shadow-sm border border-rose-200/60 overflow-hidden min-h-[30vh] lg:min-h-0">
            {/* Header */}
            <div className="p-3 md:p-4 border-b border-rose-100 z-10 shrink-0">
                <h2 className="text-sm md:text-base font-bold text-slate-800 flex items-center gap-2">
                    <span className="w-2 h-2 md:w-2.5 md:h-2.5 rounded-full bg-green-500 animate-pulse"></span>
                    Currently Working
                </h2>
            </div>

            {/* Active Grid - 1 column on mobile, 2-3 on larger screens */}
            <div className="flex-1 overflow-y-auto p-2 md:p-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 md:gap-3">
                    {working.map((tech) => (
                        <div
                            key={tech.id}
                            className="bg-white p-2.5 md:p-3 rounded-xl shadow-sm border border-rose-100 flex items-center gap-2 md:gap-3 hover:shadow-md transition-all duration-200"
                        >
                            {/* Left: Name and Timer */}
                            <div className="flex flex-col min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-semibold text-sm md:text-base text-slate-800 truncate">{tech.name}</span>
                                    <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded-full uppercase tracking-wide shrink-0">
                                        Busy
                                    </span>
                                </div>
                                <TimerDisplay
                                    statusStartTime={tech.status_start_time}
                                    label="Working"
                                    className="text-[11px] md:text-xs text-orange-600 font-medium"
                                />
                            </div>

                            {/* Right: Finish Button */}
                            <button
                                onClick={() => onFinish(tech.id)}
                                className="min-h-[44px] min-w-[44px] px-3 bg-white border border-rose-200 text-rose-500 font-semibold text-xs rounded-lg hover:bg-rose-50 transition-all duration-200 flex items-center justify-center gap-1 shrink-0"
                            >
                                <FinishIcon />
                                <span className="hidden sm:inline">FINISH</span>
                            </button>
                        </div>
                    ))}
                </div>
                {working.length === 0 && (
                    <div className="h-full min-h-[100px] flex flex-col items-center justify-center text-rose-300">
                        <EmptyStateIcon />
                        <p className="text-sm mt-2">No one is currently working.</p>
                    </div>
                )}
            </div>
        </div>
    );
});

WorkingGrid.displayName = 'WorkingGrid';

export default WorkingGrid;
