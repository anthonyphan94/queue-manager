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
        <div className="w-[60%] flex flex-col bg-white rounded-3xl shadow-sm border border-rose-100/50 overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-rose-100 z-10 shrink-0">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></span>
                    Currently Working
                </h2>
            </div>

            {/* Active Grid */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {working.map((tech) => (
                        <div key={tech.id} className="bg-white p-5 rounded-2xl shadow-sm border border-rose-100 flex flex-col gap-4 hover:shadow-md transition-all duration-200">
                            <div className="flex justify-between items-start">
                                <span className="font-bold text-xl text-slate-800 truncate">{tech.name}</span>
                                <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full uppercase tracking-wide">
                                    Busy
                                </span>
                            </div>

                            <button
                                onClick={() => onFinish(tech.id)}
                                className="mt-auto w-full min-h-[44px] bg-white border border-rose-200 text-rose-500 font-semibold rounded-xl hover:bg-rose-50 transition-all duration-200 flex items-center justify-center gap-2"
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
