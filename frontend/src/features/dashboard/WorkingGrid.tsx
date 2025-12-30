/**
 * WorkingGrid - Displays the technicians currently working.
 */

import type { Technician } from '../../types';
import { FinishIcon, EmptyStateIcon } from './Icons';

interface WorkingGridProps {
    working: Technician[];
    onFinish: (techId: number) => void;
}

export const WorkingGrid = ({ working, onFinish }: WorkingGridProps) => {
    return (
        <div className="w-full lg:w-[60%] flex flex-col bg-white rounded-3xl shadow-sm border border-rose-100/50 overflow-hidden min-h-[40vh] lg:min-h-0">
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-rose-100 z-10 shrink-0">
                <h2 className="text-lg md:text-xl font-bold text-slate-800 flex items-center gap-2">
                    <span className="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full bg-green-500 animate-pulse"></span>
                    Currently Working
                </h2>
            </div>

            {/* Active Grid */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-6">
                    {working.map((tech) => (
                        <div key={tech.id} className="bg-white p-3 md:p-5 rounded-xl md:rounded-2xl shadow-sm border border-rose-100 flex flex-col gap-3 md:gap-4 hover:shadow-md transition-all duration-200">
                            <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-1">
                                <span className="font-bold text-base md:text-xl text-slate-800 truncate">{tech.name}</span>
                                <span className="px-2 py-0.5 md:px-2.5 md:py-1 bg-green-100 text-green-700 text-[10px] md:text-xs font-bold rounded-full uppercase tracking-wide w-fit">
                                    Busy
                                </span>
                            </div>

                            <button
                                onClick={() => onFinish(tech.id)}
                                className="mt-auto w-full min-h-[40px] md:min-h-[44px] bg-white border border-rose-200 text-rose-500 font-semibold text-sm md:text-base rounded-xl hover:bg-rose-50 transition-all duration-200 flex items-center justify-center gap-1 md:gap-2"
                            >
                                <FinishIcon />
                                FINISH
                            </button>
                        </div>
                    ))}
                </div>
                {working.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-rose-300">
                        <EmptyStateIcon />
                        <p className="text-lg">No one is currently working.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default WorkingGrid;
