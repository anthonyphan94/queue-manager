/**
 * StaffCheckInModal - iOS HIG-compliant bottom sheet for selecting working technicians.
 * Features: body scroll lock, sticky header/footer, list-based selection, safe areas.
 */

import { useState, useEffect } from 'react';
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

    // Body scroll lock
    useEffect(() => {
        if (isOpen) {
            // Lock body scroll
            document.body.classList.add('modal-open');
            // Save current scroll position
            const scrollY = window.scrollY;
            document.body.style.top = `-${scrollY}px`;
        } else {
            // Unlock body scroll
            document.body.classList.remove('modal-open');
            // Restore scroll position
            const scrollY = document.body.style.top;
            document.body.style.top = '';
            window.scrollTo(0, parseInt(scrollY || '0') * -1);
        }

        return () => {
            document.body.classList.remove('modal-open');
            document.body.style.top = '';
        };
    }, [isOpen]);

    const handleAddTech = (e: React.FormEvent) => {
        e.preventDefault();
        if (newTechName.trim()) {
            onAddTech(newTechName.trim());
            setNewTechName('');
            setShowAddInput(false);
        }
    };

    const selectedCount = technicians.filter(t => t.is_active).length;

    if (!isOpen) return null;

    return (
        <div
            className="bottom-sheet-backdrop"
            onClick={onClose}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
        >
            {/* Sheet Container */}
            <div
                className="bottom-sheet-container"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Sticky Header */}
                <div className="bottom-sheet-header">
                    {/* Drag Handle */}
                    <div className="bottom-sheet-handle md:hidden"></div>

                    {/* Title and Selection Count */}
                    <div className="flex items-center justify-between">
                        <h2 id="modal-title" className="text-lg font-bold text-slate-800">
                            Select Working Technicians
                        </h2>
                        <span className="text-sm font-medium text-slate-500">
                            {selectedCount} selected
                        </span>
                    </div>
                </div>

                {/* Scrollable Content */}
                <div className="bottom-sheet-content">
                    {/* Add New Technician Section */}
                    <div className="mb-4">
                        {showAddInput ? (
                            <form onSubmit={handleAddTech} className="flex gap-2">
                                <input
                                    type="text"
                                    value={newTechName}
                                    onChange={(e) => setNewTechName(e.target.value)}
                                    placeholder="Enter technician name..."
                                    autoFocus
                                    className="flex-1 px-3 py-2 border border-rose-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-400 focus:border-transparent text-slate-800 text-base min-h-[44px]"
                                />
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-rose-500 text-white font-semibold rounded-lg hover:bg-rose-600 transition-colors min-h-[44px]"
                                >
                                    Add
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { setShowAddInput(false); setNewTechName(''); }}
                                    className="px-4 py-2 bg-slate-100 text-slate-500 font-semibold rounded-lg hover:bg-slate-200 transition-colors min-h-[44px]"
                                >
                                    Cancel
                                </button>
                            </form>
                        ) : (
                            <button
                                onClick={() => setShowAddInput(true)}
                                className="action-row w-full"
                            >
                                <PlusIcon className="action-row-icon" />
                                <span className="action-row-text">Add New Technician</span>
                            </button>
                        )}
                    </div>

                    {/* Technician List */}
                    <div className="space-y-1">
                        {technicians.map((tech) => (
                            <div key={tech.id} className="selection-row-container">
                                <button
                                    onClick={() => onToggle(tech.id)}
                                    className={`selection-row flex-1 ${tech.is_active ? 'selected' : ''}`}
                                >
                                    <span className="selection-row-name">{tech.name}</span>
                                    {tech.is_active && (
                                        <CheckIcon className="selection-row-check" />
                                    )}
                                </button>

                                {/* Remove Button - always visible, HIG compliant */}
                                <button
                                    onClick={() => onRemove(tech.id)}
                                    className="min-h-[44px] min-w-[44px] px-3 text-rose-500 bg-white border-2 border-rose-200 hover:text-rose-600 hover:bg-rose-50 hover:border-rose-300 rounded-lg transition-colors flex items-center justify-center text-xs font-semibold"
                                    title="Remove Technician"
                                    aria-label={`Remove ${tech.name}`}
                                >
                                    Remove
                                </button>
                            </div>
                        ))}

                        {technicians.length === 0 && (
                            <div className="text-center text-slate-400 py-8 text-sm">
                                No technicians added yet.
                            </div>
                        )}
                    </div>
                </div>

                {/* Sticky Footer */}
                <div className="bottom-sheet-footer">
                    <button
                        onClick={onClose}
                        className="w-full min-h-[48px] bg-rose-500 text-white font-bold rounded-xl hover:bg-rose-600 transition-all duration-200 shadow-md text-base"
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
};

export default StaffCheckInModal;
