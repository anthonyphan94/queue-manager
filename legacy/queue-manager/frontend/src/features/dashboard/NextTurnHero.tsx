/**
 * NextTurnHero - The "NEXT TURN" button area.
 * iOS HIG compliant: compact on mobile, proper touch target.
 */

import { NextTurnIcon } from './Icons';

interface NextTurnHeroProps {
    queueLength: number;
    onNextTurn: () => void;
}

export const NextTurnHero = ({ queueLength, onNextTurn }: NextTurnHeroProps) => {
    const isDisabled = queueLength === 0;

    return (
        <div className="p-2 md:p-4 border-b border-rose-100 z-10 shrink-0">
            <button
                onClick={onNextTurn}
                disabled={isDisabled}
                className={`w-full h-12 md:h-16 bg-rose-500 text-white text-base md:text-xl font-bold rounded-xl flex items-center justify-center gap-2 shadow-md hover:bg-rose-600 active:scale-[0.98] transition-all
                    ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'shadow-rose-200'}
                `}
            >
                <span>NEXT TURN</span>
                <NextTurnIcon />
            </button>
            <div className="mt-1.5 flex justify-between items-center text-rose-400 text-[11px]">
                <span className="font-semibold uppercase tracking-wider">Queue ({queueLength})</span>
                <span className="text-rose-300">Drag to reorder</span>
            </div>
        </div>
    );
};

export default NextTurnHero;
