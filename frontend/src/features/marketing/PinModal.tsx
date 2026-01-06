import { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../../store/authStore';
import './PinModal.css';

/**
 * PinModal - PIN entry modal for Marketing authentication
 * 
 * Shows a 4-digit PIN entry form when user is not authenticated.
 */
export function PinModal() {
    const { verifyPin, isVerifying, error } = useAuthStore();
    const [pin, setPin] = useState(['', '', '', '']);
    const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

    // Focus first input on mount
    useEffect(() => {
        inputRefs.current[0]?.focus();
    }, []);

    const handleChange = (index: number, value: string) => {
        // Only allow digits
        if (value && !/^\d$/.test(value)) return;

        const newPin = [...pin];
        newPin[index] = value;
        setPin(newPin);

        // Auto-focus next input
        if (value && index < 3) {
            inputRefs.current[index + 1]?.focus();
        }

        // Auto-submit when all 4 digits entered
        if (value && index === 3) {
            const fullPin = newPin.join('');
            if (fullPin.length === 4) {
                verifyPin(fullPin);
            }
        }
    };

    const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
        // Handle backspace - go to previous input
        if (e.key === 'Backspace' && !pin[index] && index > 0) {
            inputRefs.current[index - 1]?.focus();
        }
    };

    const handlePaste = (e: React.ClipboardEvent) => {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text').slice(0, 4);
        if (/^\d{1,4}$/.test(pastedData)) {
            const newPin = pastedData.split('').concat(['', '', '', '']).slice(0, 4);
            setPin(newPin);

            // Focus appropriate input
            const filledCount = pastedData.length;
            if (filledCount < 4) {
                inputRefs.current[filledCount]?.focus();
            }

            // Auto-submit if 4 digits
            if (pastedData.length === 4) {
                verifyPin(pastedData);
            }
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const fullPin = pin.join('');
        if (fullPin.length === 4) {
            verifyPin(fullPin);
        }
    };

    return (
        <div className="pin-modal-backdrop">
            <div className="pin-modal">
                <div className="pin-modal-icon">🔐</div>
                <h2 className="pin-modal-title">Enter PIN</h2>
                <p className="pin-modal-subtitle">
                    Enter your 4-digit PIN to access Marketing
                </p>

                <form onSubmit={handleSubmit}>
                    <div className="pin-inputs" onPaste={handlePaste}>
                        {pin.map((digit, index) => (
                            <input
                                key={index}
                                ref={(el) => { inputRefs.current[index] = el }}
                                type="text"
                                inputMode="numeric"
                                maxLength={1}
                                value={digit}
                                onChange={(e) => handleChange(index, e.target.value)}
                                onKeyDown={(e) => handleKeyDown(index, e)}
                                className="pin-input"
                                disabled={isVerifying}
                                aria-label={`PIN digit ${index + 1}`}
                            />
                        ))}
                    </div>

                    {error && (
                        <div className="pin-error">{error}</div>
                    )}

                    <button
                        type="submit"
                        className="pin-submit-btn"
                        disabled={pin.join('').length !== 4 || isVerifying}
                    >
                        {isVerifying ? 'Verifying...' : 'Unlock'}
                    </button>
                </form>

                <a href="/" className="pin-back-link">
                    ← Back to Dashboard
                </a>
            </div>
        </div>
    );
}
