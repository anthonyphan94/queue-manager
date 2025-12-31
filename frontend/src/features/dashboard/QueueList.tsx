/**
 * QueueList - Handles the drag-and-drop queue list.
 */

import { useState, useEffect } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
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
import { RequestIcon, SkipIcon, ClockOutIcon, CoffeeIcon } from './Icons';
import NextTurnHero from './NextTurnHero';
import { useStatusTimer, formatDuration } from '../../hooks/useStatusTimer';

// --- Reusable Timer Display Component ---
interface TechTimerProps {
    statusStartTime?: string | null;
    label: string;
}

const TechTimer = ({ statusStartTime, label }: TechTimerProps) => {
    const elapsedSeconds = useStatusTimer(statusStartTime);
    return (
        <span className="text-xs text-slate-400 font-medium">
            {label}: {formatDuration(elapsedSeconds)}
        </span>
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
                group relative flex items-center justify-between p-3 md:p-4 rounded-2xl transition-all duration-200 bg-white
                ${isDragging ? 'shadow-xl scale-105 z-50 ring-2 ring-rose-300' : 'shadow-sm border border-rose-100/50'}
                ${isFirst ? 'border-l-4 md:border-l-8 border-rose-500' : 'hover:border-rose-200'}
            `}
        >
            {/* Position & Name */}
            <div className="flex items-center gap-2 md:gap-4 pointer-events-none min-w-0">
                <div className={`
                    w-7 h-7 md:w-10 md:h-10 flex items-center justify-center rounded-full font-bold text-xs md:text-lg shrink-0
                    ${isFirst ? 'bg-rose-500 text-white' : 'bg-slate-100 text-slate-500'}
                `}>
                    {index + 1}
                </div>
                <div className="flex flex-col min-w-0">
                    <span className={`font-bold truncate ${isFirst ? 'text-lg md:text-3xl text-slate-800' : 'text-sm md:text-xl text-slate-800'}`}>
                        {tech.name}
                    </span>
                    <TechTimer statusStartTime={tech.status_start_time} label="Waiting" />
                </div>
            </div>

            {/* Action Buttons - Always visible on mobile for touch */}
            <div
                className={`flex gap-1 md:gap-2 transition-opacity shrink-0 ${isDragging ? 'opacity-0' : 'opacity-100'}`}
                onPointerDown={(e) => e.stopPropagation()}
            >
                <button
                    onClick={() => onClockOut(tech.id)}
                    title="Clock Out"
                    className="p-1 md:p-2 bg-white text-slate-400 rounded-lg border border-rose-200 hover:bg-rose-50 hover:text-rose-500 shadow-sm transition-colors cursor-pointer h-7 w-7 md:h-11 md:w-11 flex items-center justify-center"
                >
                    <ClockOutIcon />
                </button>
                <button
                    onClick={() => onRequest(tech.id)}
                    title="Request Assign"
                    className="p-1 md:p-2 bg-white text-rose-500 rounded-lg border border-rose-200 hover:bg-rose-50 shadow-sm transition-colors cursor-pointer h-7 w-7 md:h-11 md:w-11 flex items-center justify-center"
                >
                    <RequestIcon />
                </button>
                <button
                    onClick={() => onSkip(tech.id)}
                    title="Skip to Bottom"
                    className="p-1 md:p-2 bg-white text-slate-400 rounded-lg border border-rose-200 hover:bg-slate-50 hover:text-slate-600 shadow-sm transition-colors cursor-pointer h-7 w-7 md:h-11 md:w-11 flex items-center justify-center"
                >
                    <SkipIcon />
                </button>
                <button
                    onClick={() => onTakeBreak(tech.id)}
                    title="Take Break"
                    className="p-1 md:p-2 bg-white text-orange-400 rounded-lg border border-orange-200 hover:bg-orange-50 hover:text-orange-500 shadow-sm transition-colors cursor-pointer h-7 w-7 md:h-11 md:w-11 flex items-center justify-center"
                >
                    <CoffeeIcon />
                </button>
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
    const [queueItems, setQueueItems] = useState<Technician[]>([]);

    // Sync queueItems with props
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

    const handleDragEnd = (event: any) => {
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
        <div className="w-full flex flex-col bg-white rounded-3xl shadow-sm border border-rose-100/50 overflow-hidden">
            {/* Header: NEXT TURN Button */}
            <NextTurnHero queueLength={queueItems.length} onNextTurn={onNextTurn} />

            {/* Queue List with Drag and Drop */}
            <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-2 md:space-y-3">
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
                    <div className="text-center py-20 text-rose-300 italic">
                        No technicians available. Please add technicians to the queue.
                    </div>
                )}
            </div>
        </div>
    );
};

export default QueueList;
