/**
 * StaffCheckInModal - Modal for selecting working technicians.
 */

import { useState } from 'react';
import type { Technician } from '../../types';
import { CheckIcon, PlusIcon } from './Icons';

interface StaffCheckInModalProps {
    isOpen: boolean;
    onClose: () => void;
    technicians: Technician[];
    onToggle: (techId: number) => void;
    onAddTech: (name: string) => void;
    onRemove: (techId: number) => void;
}

export const StaffCheckInModal = ({
    isOpen,
    onClose,
    technicians,
    onToggle,
    onAddTech,
    onRemove,
}: StaffCheckInModalProps) => {
    const [showAddInput, setShowAddInput] = useState(false);
    const [newTechName, setNewTechName] = useState('');

    const handleAddTech = (e: React.FormEvent) => {
        e.preventDefault();
        if (newTechName.trim()) {
            onAddTech(newTechName.trim());
            setNewTechName('');
            setShowAddInput(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-end md:items-center justify-center z-50 p-0 md:p-4" onClick={onClose}>
            {/* Modal Container: Flex Column with space-y-6 for automatic 24px gaps */}
            <div
                className="flex flex-col p-4 md:p-8 space-y-4 md:space-y-6 bg-white rounded-t-3xl md:rounded-3xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto pb-safe"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Grabber Handle for Mobile Sheet Look */}
                <div className="w-12 h-1.5 bg-slate-300 rounded-full mx-auto md:hidden mb-2"></div>

                {/* Child 1: Header */}
                <h2 className="text-xl md:text-2xl font-bold text-slate-800 text-center">Select Working Technicians</h2>

                {/* Child 2: Input Section */}
                <div>
                    {showAddInput ? (
                        <form onSubmit={handleAddTech} className="flex gap-3">
                            <input
                                type="text"
                                value={newTechName}
                                onChange={(e) => setNewTechName(e.target.value)}
                                placeholder="Enter technician name..."
                                autoFocus
                                className="flex-1 px-4 py-3 border border-rose-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-400 focus:border-transparent text-slate-800 text-base min-h-[44px]"
                            />
                            <button
                                type="submit"
                                className="px-6 py-3 bg-rose-500 text-white font-semibold rounded-xl hover:bg-rose-600 transition-colors min-h-[44px]"
                            >
                                Add
                            </button>
                            <button
                                type="button"
                                onClick={() => { setShowAddInput(false); setNewTechName(''); }}
                                className="px-6 py-3 bg-slate-100 text-slate-500 font-semibold rounded-xl hover:bg-slate-200 transition-colors min-h-[44px]"
                            >
                                Cancel
                            </button>
                        </form>
                    ) : (
                        <button
                            onClick={() => setShowAddInput(true)}
                            className="flex items-center justify-center w-full gap-2 px-4 py-4 bg-rose-50 text-rose-500 font-semibold rounded-xl hover:bg-rose-100 transition-colors border-2 border-rose-200 border-dashed min-h-[44px]"
                        >
                            <PlusIcon />
                            Add New Technician
                        </button>
                    )}
                </div>

                {/* Child 3: The List (Grid of Name Chips) */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 md:gap-4">
                    {technicians.map((tech) => (
                        <div key={tech.id} className="relative group">
                            <button
                                onClick={() => onToggle(tech.id)}
                                className={`
                                    w-full px-4 py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-200 shadow-sm text-center whitespace-normal break-words min-h-[44px]
                                    ${tech.is_active
                                        ? 'bg-rose-500 text-white hover:bg-rose-600 shadow-rose-200'
                                        : 'bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700'
                                    }
                                `}
                            >
                                {tech.is_active && <CheckIcon />}
                                <span>{tech.name}</span>
                            </button>
                            {/* Remove Button */}
                            <button
                                onClick={(e) => { e.stopPropagation(); onRemove(tech.id); }}
                                className="absolute -top-2 -right-2 bg-white text-rose-500 rounded-full p-1.5 shadow-md border border-rose-100 hover:bg-rose-50 opacity-0 group-hover:opacity-100 transition-opacity z-10"
                                title="Remove Technician"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    ))}
                    {technicians.length === 0 && (
                        <div className="col-span-3 text-center text-slate-400 py-8">No technicians added yet.</div>
                    )}
                </div>

                {/* Child 4: Footer (Done Button) */}
                <div className="pt-4 flex justify-center">
                    <button
                        onClick={onClose}
                        className="px-16 py-4 bg-rose-500 text-white font-bold rounded-xl hover:bg-rose-600 transition-all duration-200 shadow-lg shadow-rose-200 text-lg min-h-[44px]"
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
};

export default StaffCheckInModal;
