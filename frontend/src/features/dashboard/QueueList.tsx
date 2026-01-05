/**
 * QueueList - Handles the drag-and-drop queue list.
 * iOS HIG compliant: compact rows, 44px touch targets, optimized for mobile.
 */

import { useState, useEffect } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    type DragEndEvent,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Technician } from '../../types';
import { RequestIcon, SkipIcon, ClockOutIcon } from './Icons';
import NextTurnHero from './NextTurnHero';
import { TimerDisplay } from '../../components/TimerDisplay';

// --- Compact Action Button ---
interface ActionButtonProps {
    onClick: () => void;
    title: string;
    children: React.ReactNode;
    variant?: 'default' | 'lunch' | 'assign';
}

const ActionButton = ({ onClick, title, children, variant = 'default' }: ActionButtonProps) => {
    const baseClasses = "min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg transition-colors cursor-pointer";

    const variantClasses =
        variant === 'lunch'
            ? "px-3 bg-white text-orange-500 border-2 border-orange-300 hover:bg-orange-50 hover:border-orange-400 font-bold text-xs"
            : variant === 'assign'
                ? "px-3 bg-white text-emerald-500 border-2 border-emerald-300 hover:bg-emerald-50 hover:border-emerald-400 font-bold text-xs"
                : "w-9 h-9 bg-white text-slate-400 border border-rose-200 hover:bg-rose-50 hover:text-rose-500";

    return (
        <button
            onClick={onClick}
            title={title}
            className={`${baseClasses} ${variantClasses}`}
        >
            {children}
        </button>
    );
};

// --- Sortable Item Component ---
interface SortableQueueItemProps {
    id: number;
    tech: Technician;
    index: number;
    onRequest: (techId: number) => void;
    onSkip: (techId: number) => void;
    onClockOut: (techId: number) => void;
    onTakeBreak: (techId: number) => void;
}

const SortableQueueItem = ({ id, tech, index, onRequest, onSkip, onClockOut, onTakeBreak }: SortableQueueItemProps) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 50 : 'auto',
    };

    const isFirst = index === 0;

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`
                group relative flex items-center justify-between p-2 rounded-xl transition-all duration-200 bg-white gap-2
                ${isDragging ? 'shadow-xl scale-[1.02] z-50 ring-2 ring-rose-300' : 'shadow-sm border border-rose-100/50'}
                ${isFirst ? 'border-l-4 border-rose-500' : 'hover:border-rose-200'}
            `}
        >
            {/* Left: Position Badge + Name + Timer */}
            <div className="flex items-center gap-2 pointer-events-none min-w-0 flex-1">
                {/* Order badge - compact */}
                <div className={`
                    w-6 h-6 flex items-center justify-center rounded-full font-bold text-xs shrink-0
                    ${isFirst ? 'bg-rose-500 text-white' : 'bg-slate-100 text-slate-500'}
                `}>
                    {index + 1}
                </div>

                {/* Name and timer */}
                <div className="flex flex-col min-w-0">
                    <span className={`font-semibold truncate leading-tight ${isFirst ? 'text-base text-slate-800' : 'text-sm text-slate-700'}`}>
                        {tech.name}
                    </span>
                    <TimerDisplay statusStartTime={tech.status_start_time} label="Waiting" />
                </div>
            </div>

            {/* Right: Action Buttons */}
            <div
                className={`flex items-center gap-1 shrink-0 ${isDragging ? 'opacity-0' : 'opacity-100'}`}
                onPointerDown={(e) => e.stopPropagation()}
            >
                <ActionButton onClick={() => onClockOut(tech.id)} title="Clock Out">
                    <ClockOutIcon />
                </ActionButton>
                <ActionButton onClick={() => onRequest(tech.id)} title="Request Assign" variant="assign">
                    Assign
                </ActionButton>
                <ActionButton onClick={() => onTakeBreak(tech.id)} title="Lunch Break" variant="lunch">
                    LUNCH
                </ActionButton>
            </div>
        </div>
    );
};

// --- Main QueueList Component ---
interface QueueListProps {
    queue: Technician[];
    onNextTurn: () => void;
    onRequest: (techId: number) => void;
    onSkip: (techId: number) => void;
    onClockOut: (techId: number) => void;
    onReorder: (techIds: number[]) => void;
    onTakeBreak: (techId: number) => void;
}

export const QueueList = ({ queue, onNextTurn, onRequest, onSkip, onClockOut, onReorder, onTakeBreak }: QueueListProps) => {
    // Local state for optimistic drag-drop updates, initialized with prop value
    const [queueItems, setQueueItems] = useState<Technician[]>(queue);

    // Sync with prop when external updates occur (e.g., backend sync)
    useEffect(() => {
        setQueueItems(queue);
    }, [queue]);

    // Dnd Sensors
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;

        if (active.id !== over?.id) {
            setQueueItems((items) => {
                const oldIndex = items.findIndex((item) => item.id === active.id);
                const newIndex = items.findIndex((item) => item.id === over.id);

                const newItems = arrayMove(items, oldIndex, newIndex);

                // Trigger Backend Update
                const newOrderIds = newItems.map(t => t.id);
                onReorder(newOrderIds);

                return newItems;
            });
        }
    };

    return (
        <div className="w-full h-full flex flex-col bg-white rounded-2xl shadow-sm border border-rose-200/60 overflow-hidden">
            {/* Header: NEXT TURN Button */}
            <NextTurnHero queueLength={queueItems.length} onNextTurn={onNextTurn} />

            {/* Queue List with Drag and Drop */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                >
                    <SortableContext
                        items={queueItems.map(t => t.id)}
                        strategy={verticalListSortingStrategy}
                    >
                        {queueItems.map((tech, index) => (
                            <SortableQueueItem
                                key={tech.id}
                                id={tech.id}
                                tech={tech}
                                index={index}
                                onRequest={onRequest}
                                onSkip={onSkip}
                                onClockOut={onClockOut}
                                onTakeBreak={onTakeBreak}
                            />
                        ))}
                    </SortableContext>
                </DndContext>

                {queueItems.length === 0 && (
                    <div className="text-center py-12 text-rose-300 italic text-sm">
                        No technicians available. Please add technicians to the queue.
                    </div>
                )}
            </div>
        </div>
    );
};

export default QueueList;
