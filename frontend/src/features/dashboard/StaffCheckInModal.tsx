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
                                    className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-400 focus:border-transparent text-slate-800 text-base min-h-[44px]"
                                    style={{ borderColor: 'var(--color-border)' }}
                                />
                                <button
                                    type="submit"
                                    className="px-4 py-2 font-semibold rounded-lg transition-colors min-h-[44px] border-2"
                                    style={{
                                        backgroundColor: 'var(--color-surface)',
                                        borderColor: 'var(--color-primary)',
                                        color: 'var(--color-primary)'
                                    }}
                                >
                                    Add
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { setShowAddInput(false); setNewTechName(''); }}
                                    className="px-4 py-2 font-semibold rounded-lg transition-colors min-h-[44px]"
                                    style={{
                                        backgroundColor: 'transparent',
                                        color: 'var(--color-text-secondary)'
                                    }}
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
                            <div
                                key={tech.id}
                                className={`
                                    relative flex items-center justify-between p-0 overflow-hidden rounded-2xl border transition-all duration-200
                                    ${tech.is_active
                                        ? 'bg-rose-100 border-rose-200 active:bg-rose-200'
                                        : 'bg-white border-slate-200 active:bg-slate-50'
                                    }
                                `}
                                onClick={() => onToggle(tech.id)}
                            >
                                {/* Main Click Area for Toggling */}
                                <div className="flex-1 flex items-center h-14 pl-4 cursor-pointer">
                                    {/* Left Indicator (Selected only) */}
                                    {tech.is_active && (
                                        <div className="absolute left-0 top-3 bottom-3 w-1 bg-rose-600 rounded-r shadow-sm" />
                                    )}

                                    <span className={`text-base font-semibold truncate ${tech.is_active ? 'text-slate-900' : 'text-slate-700'}`}>
                                        {tech.name}
                                    </span>
                                </div>

                                {/* Right Actions Area */}
                                <div className="flex items-center pr-4 gap-3">
                                    {/* Selected Checkmark */}
                                    {tech.is_active && (
                                        <CheckIcon className="w-6 h-6 text-rose-600" />
                                    )}

                                    {/* Remove Button (Subtle Text) */}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onRemove(tech.id);
                                        }}
                                        className="text-red-600 text-xs font-semibold px-2 py-1 rounded hover:bg-red-50 active:bg-red-100 transition-colors"
                                        title="Remove Technician"
                                        aria-label={`Remove ${tech.name}`}
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        ))}

                        {technicians.length === 0 && (
                            <div className="text-center text-slate-400 py-8 text-sm">
                                No technicians added yet.
                            </div>
                        )}
                    </div>
                </div>

                <div className="bottom-sheet-footer">
                    <button
                        onClick={onClose}
                        className="w-full min-h-[48px] font-bold rounded-xl transition-all duration-200 shadow-md text-base"
                        style={{
                            backgroundColor: 'var(--color-primary)',
                            color: 'var(--color-text-inverse)'
                        }}
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
};

export default StaffCheckInModal;
