import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import './ChangePinModal.css';

interface ChangePinModalProps {
    onClose: () => void;
}

/**
 * ChangePinModal - Modal for changing the marketing PIN
 */
export function ChangePinModal({ onClose }: ChangePinModalProps) {
    const { changePin } = useAuthStore();
    const [currentPin, setCurrentPin] = useState('');
    const [newPin, setNewPin] = useState('');
    const [confirmPin, setConfirmPin] = useState('');
    const [isChanging, setIsChanging] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate new PIN
        if (newPin.length < 4) {
            setError('New PIN must be at least 4 characters');
            return;
        }

        if (newPin !== confirmPin) {
            setError('New PINs do not match');
            return;
        }

        setIsChanging(true);

        try {
            const result = await changePin(currentPin, newPin);
            if (result.success) {
                setSuccess(true);
                // Auto-close after 2 seconds
                setTimeout(() => {
                    onClose();
                }, 2000);
            } else {
                setError(result.message);
            }
        } catch {
            setError('Failed to change PIN. Please try again.');
        } finally {
            setIsChanging(false);
        }
    };

    if (success) {
        return (
            <div className="change-pin-modal-backdrop" onClick={onClose}>
                <div className="change-pin-modal" onClick={(e) => e.stopPropagation()}>
                    <div className="change-pin-success">
                        <div className="success-icon">&#10003;</div>
                        <h2>PIN Changed!</h2>
                        <p>Your marketing PIN has been updated successfully.</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="change-pin-modal-backdrop" onClick={onClose}>
            <div className="change-pin-modal" onClick={(e) => e.stopPropagation()}>
                <div className="change-pin-header">
                    <h2>Change PIN</h2>
                    <button className="close-btn" onClick={onClose} aria-label="Close">
                        &times;
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="change-pin-field">
                        <label htmlFor="currentPin">Current PIN</label>
                        <input
                            id="currentPin"
                            type="password"
                            value={currentPin}
                            onChange={(e) => setCurrentPin(e.target.value)}
                            placeholder="Enter current PIN"
                            disabled={isChanging}
                            autoComplete="current-password"
                        />
                    </div>

                    <div className="change-pin-field">
                        <label htmlFor="newPin">New PIN</label>
                        <input
                            id="newPin"
                            type="password"
                            value={newPin}
                            onChange={(e) => setNewPin(e.target.value)}
                            placeholder="Enter new PIN (4-20 chars)"
                            minLength={4}
                            maxLength={20}
                            disabled={isChanging}
                            autoComplete="new-password"
                        />
                    </div>

                    <div className="change-pin-field">
                        <label htmlFor="confirmPin">Confirm New PIN</label>
                        <input
                            id="confirmPin"
                            type="password"
                            value={confirmPin}
                            onChange={(e) => setConfirmPin(e.target.value)}
                            placeholder="Confirm new PIN"
                            minLength={4}
                            maxLength={20}
                            disabled={isChanging}
                            autoComplete="new-password"
                        />
                    </div>

                    {error && <div className="change-pin-error">{error}</div>}

                    <div className="change-pin-actions">
                        <button
                            type="button"
                            className="cancel-btn"
                            onClick={onClose}
                            disabled={isChanging}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="submit-btn"
                            disabled={isChanging || !currentPin || !newPin || !confirmPin}
                        >
                            {isChanging ? 'Changing...' : 'Change PIN'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
