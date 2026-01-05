/**
 * useBodyScrollLock - Custom hook to lock body scroll when a modal is open.
 * Preserves scroll position and restores it when unlocked.
 */

import { useEffect } from 'react';

export const useBodyScrollLock = (isLocked: boolean): void => {
    useEffect(() => {
        if (isLocked) {
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
    }, [isLocked]);
};

export default useBodyScrollLock;
