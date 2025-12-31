/**
 * Dashboard - Main dashboard view for the Salon Turn Manager.
 * 
 * This component uses the useTurnLogic hook for all business logic
 * and composes the UI from atomic feature components.
 */

import { useState } from 'react';
import { useTurnLogic } from '../hooks/useTurnLogic';
import {
    QueueList,
    WorkingGrid,
    StaffCheckInModal,
    RestingSection,
    TechniciansIcon,
} from '../features/dashboard';
import logo from '../assets/logo.png';

export const Dashboard = () => {
    const {
        technicians,
        queue,
        working,
        onBreak,
        nextTurn,
        finish,
        request,
        skip,
        toggleActive,
        addTech,
        removeTech,
        reorderQueue,
        takeBreak,
        returnFromBreak,
    } = useTurnLogic();

    // Modal States
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [requestModalData, setRequestModalData] = useState<{ techId: number } | null>(null);

    // Handlers
    const handleNextTurn = async () => {
        await nextTurn();
    };

    const handleFinish = async (techId: number) => {
        await finish(techId);
    };

    const handleRequest = (techId: number) => {
        // For now, directly request with default client name
        request(techId, 'Walk-in');
    };

    const handleSkip = async (techId: number) => {
        await skip(techId);
    };

    const handleClockOut = async (techId: number) => {
        await toggleActive(techId);
    };

    const handleAddTech = async (name: string) => {
        await addTech(name);
    };

    const handleRemoveTech = async (techId: number) => {
        await removeTech(techId);
    };

    const handleReorder = async (techIds: number[]) => {
        await reorderQueue(techIds);
    };

    const handleTakeBreak = async (techId: number) => {
        await takeBreak(techId);
    };

    const handleReturnFromBreak = async (techId: number) => {
        await returnFromBreak(techId);
    };

    return (
        <div className="flex flex-col h-screen font-sans text-slate-800" style={{ backgroundColor: '#f3dadc' }}>
            {/* --- TOP BAR --- */}
            <div className="h-14 md:h-16 bg-white shadow-md z-30 flex items-center justify-between px-3 md:px-6 shrink-0">
                <div className="flex items-center gap-2 md:gap-3">
                    <img src={logo} alt="Marilyn's Beauty Lounge" className="h-10 md:h-12 w-auto" />
                    <h1 className="text-lg md:text-2xl font-brand text-slate-800 hidden sm:block">MARILYN BEAUTY LOUNGE</h1>
                </div>
                <button
                    onClick={() => setIsModalOpen(true)}
                    className="p-2 bg-rose-50 hover:bg-rose-100 text-rose-500 rounded-xl transition-colors flex items-center gap-2 font-semibold"
                >
                    <TechniciansIcon />
                    <span className="hidden sm:inline">Technicians</span>
                </button>
            </div>

            {/* --- MODALS --- */}
            <StaffCheckInModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                technicians={technicians}
                onToggle={toggleActive}
                onAddTech={handleAddTech}
                onRemove={handleRemoveTech}
            />

            {/* --- MAIN CONTENT --- */}
            <main className="flex-1 p-3 md:p-6 overflow-auto">
                <div className="flex flex-col lg:flex-row gap-4 md:gap-6 h-full">
                    {/* Left Panel: Sidebar with Queue + Resting */}
                    <div className="w-full lg:w-[40%] flex flex-col gap-3 md:gap-4 h-full overflow-hidden">
                        {/* Top Section: Queue - takes remaining space */}
                        <div className="flex-1 min-h-0 overflow-hidden">
                            <QueueList
                                queue={queue}
                                onNextTurn={handleNextTurn}
                                onRequest={handleRequest}
                                onSkip={handleSkip}
                                onClockOut={handleClockOut}
                                onReorder={handleReorder}
                                onTakeBreak={handleTakeBreak}
                            />
                        </div>

                        {/* Bottom Section: On Break - anchored at bottom with max height */}
                        {onBreak.length > 0 && (
                            <div className="shrink-0 max-h-[35%] overflow-hidden">
                                <RestingSection
                                    onBreak={onBreak}
                                    onReturn={handleReturnFromBreak}
                                />
                            </div>
                        )}
                    </div>

                    {/* Right Panel: Working */}
                    <WorkingGrid
                        working={working}
                        onFinish={handleFinish}
                    />
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
