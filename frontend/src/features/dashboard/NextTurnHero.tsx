/**
 * NextTurnHero - The giant "NEXT TURN" button area.
 */

import { NextTurnIcon } from './Icons';

interface NextTurnHeroProps {
    queueLength: number;
    onNextTurn: () => void;
}

export const NextTurnHero = ({ queueLength, onNextTurn }: NextTurnHeroProps) => {
    const isDisabled = queueLength === 0;

    return (
        <div className="p-3 md:p-4 border-b border-rose-100 z-10 shrink-0">
            <button
                onClick={onNextTurn}
                disabled={isDisabled}
                className={`w-full h-24 bg-rose-500 text-white text-3xl font-bold rounded-2xl flex items-center justify-center gap-3 shadow-lg hover:bg-rose-600 active:scale-95 transition-all
                    ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'shadow-rose-200'}
                `}
            >
                <span>NEXT TURN</span>
                <NextTurnIcon />
            </button>
            <div className="mt-4 flex justify-between items-center text-rose-400 text-sm">
                <span className="font-semibold uppercase tracking-wider">Queue ({queueLength})</span>
                <span className="text-xs text-rose-300">Drag to reorder</span>
            </div>
        </div>
    );
};

export default NextTurnHero;
