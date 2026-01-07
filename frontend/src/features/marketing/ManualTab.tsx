import { useState } from 'react';
import { useMarketingStore } from '../../store/marketingStore';
import { useAuthStore } from '../../store/authStore';

// Use relative URLs in production, localhost in development
const isDev = import.meta.env.DEV;
const API_BASE = isDev ? 'http://localhost:8080' : '';

/**
 * ManualTab - Single SMS send form
 */
export function ManualTab() {
    const { isSending, setSending, setError, error } = useMarketingStore();

    const [name, setName] = useState('');
    const [phone, setPhone] = useState('');
    const [message, setMessage] = useState('');
    const [success, setSuccess] = useState<string | null>(null);

    const isValid = name.trim() && phone.trim().length >= 10 && message.trim();

    const handleSend = async () => {
        if (!isValid) return;

        setSending(true);
        setError(null);
        setSuccess(null);

        try {
            const authHeader = useAuthStore.getState().getAuthHeader();
            const response = await fetch(`${API_BASE}/marketing/send-single`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader },
                body: JSON.stringify({ name, phone, message }),
            });

            const data = await response.json();

            if (data.success) {
                setSuccess('SMS sent successfully.');
                // Clear form
                setName('');
                setPhone('');
                setMessage('');
            } else {
                setError(data.error || 'Failed to send SMS');
            }
        } catch (err) {
            setError('Network error. Please check your connection.');
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="manual-tab">
            <div className="form-group">
                <label htmlFor="customer-name">Customer Name</label>
                <input
                    id="customer-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="John Doe"
                    disabled={isSending}
                />
            </div>

            <div className="form-group">
                <label htmlFor="phone-number">Phone Number</label>
                <input
                    id="phone-number"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="(555) 123-4567"
                    disabled={isSending}
                />
                <span className="hint">US numbers only. Will be formatted to E.164.</span>
            </div>

            <div className="form-group">
                <label htmlFor="message-content">Message</label>
                <textarea
                    id="message-content"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Hi [name], don't miss our 20% off sale this weekend!"
                    rows={4}
                    disabled={isSending}
                />
                <span className="hint">Use [name] to personalize the message.</span>
                <span className="char-count">{message.length}/1600</span>
            </div>

            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}

            <button
                className="send-button"
                onClick={handleSend}
                disabled={!isValid || isSending}
            >
                {isSending ? 'Sending...' : 'Send SMS'}
            </button>
        </div>
    );
}
