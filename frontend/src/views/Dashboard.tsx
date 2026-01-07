/**
 * Dashboard - Main dashboard view for the Salon Turn Manager.
 * iOS HIG compliant: single page scroll, safe areas, compact sections.
 * 
 * This component uses the useTurnLogic hook for all business logic
 * and composes the UI from atomic feature components.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
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
        resetAllTechnicians,
    } = useTurnLogic();

    // Modal States
    const [isModalOpen, setIsModalOpen] = useState(false);

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
        <div className="flex flex-col min-h-screen font-sans text-slate-800 pt-safe" style={{ backgroundColor: '#f3dadc' }}>
            {/* --- TOP BAR --- */}
            <header className="h-12 md:h-14 bg-white shadow-sm z-30 flex items-center justify-between px-3 md:px-6 shrink-0 sticky top-0">
                <div className="flex items-center gap-2">
                    <img src={logo} alt="Marilyn's Beauty Lounge" className="h-8 md:h-10 w-auto" />
                    <h1 className="text-base md:text-xl font-brand text-slate-800 hidden sm:block">MARILYN BEAUTY LOUNGE</h1>
                </div>
                <div className="flex items-center gap-2">
                    <Link
                        to="/marketing"
                        className="min-h-[44px] min-w-[44px] px-3 bg-purple-50 hover:bg-purple-100 text-purple-600 rounded-lg transition-colors flex items-center gap-2 font-semibold text-sm"
                    >
                        <span>📱</span>
                        <span className="hidden sm:inline">Marketing</span>
                    </Link>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="min-h-[44px] min-w-[44px] px-2 bg-rose-50 hover:bg-rose-100 text-rose-500 rounded-lg transition-colors flex items-center gap-2 font-semibold text-sm"
                    >
                        <TechniciansIcon />
                        <span className="hidden sm:inline">Technicians</span>
                    </button>
                </div>
            </header>


            {/* --- MODALS --- */}
            <StaffCheckInModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                technicians={technicians}
                onToggle={toggleActive}
                onAddTech={handleAddTech}
                onRemove={handleRemoveTech}
                onResetAll={async () => {
                    await resetAllTechnicians();
                    setIsModalOpen(false);
                }}
            />

            {/* --- MAIN CONTENT --- Single page scroll on mobile */}
            <main className="flex-1 p-2 md:p-4 pb-safe px-safe">
                {/* Mobile: Stack vertically, Desktop: Two columns */}
                <div className="flex flex-col lg:flex-row gap-3 md:gap-4">

                    {/* Left Panel: Queue + On Break */}
                    <div className="w-full lg:w-[40%] flex flex-col gap-2 md:gap-3">
                        {/* Queue Section - Primary focus */}
                        <div className="min-h-[50vh] lg:min-h-0 lg:flex-1">
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

                        {/* On Break Section - Compact carousel (only if people on break) */}
                        {onBreak.length > 0 && (
                            <RestingSection
                                onBreak={onBreak}
                                onReturn={handleReturnFromBreak}
                            />
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
