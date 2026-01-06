import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useMarketingStore } from '../store/marketingStore';
import { useAuthStore } from '../store/authStore';
import { ManualTab } from '../features/marketing/ManualTab';
import { CsvImportTab } from '../features/marketing/CsvImportTab';
import { PinModal } from '../features/marketing/PinModal';
import '../features/marketing/Marketing.css';

/**
 * Marketing Page - SMS Marketing Module
 * 
 * AUTHENTICATION:
 * - Requires PIN authentication before accessing
 * - PIN is verified against backend and stored in sessionStorage
 * - User can logout to re-enter PIN
 * 
 * Two modes of operation:
 * 1. Manual Entry - Send single SMS
 * 2. CSV Import - Bulk send via file upload
 */
export default function Marketing() {
    const { activeTab, setActiveTab } = useMarketingStore();
    const { isAuthenticated, checkStoredAuth, logout } = useAuthStore();

    // Check for stored auth on mount
    useEffect(() => {
        checkStoredAuth();
    }, [checkStoredAuth]);

    // Show PIN modal if not authenticated
    if (!isAuthenticated) {
        return <PinModal />;
    }

    return (
        <div className="marketing-page">
            <div className="marketing-top-bar">
                <Link to="/" className="back-link">← Back to Dashboard</Link>
                <button onClick={logout} className="logout-btn" title="Lock Marketing">
                    🔒 Lock
                </button>
            </div>

            <header className="marketing-header">
                <h1>📱 SMS Marketing</h1>
                <p className="subtitle">Send promotional messages to your customers</p>
            </header>

            <div className="tab-navigation">
                <button
                    className={`tab-button ${activeTab === 'manual' ? 'active' : ''}`}
                    onClick={() => setActiveTab('manual')}
                >
                    ✉️ Single SMS
                </button>
                <button
                    className={`tab-button ${activeTab === 'csv' ? 'active' : ''}`}
                    onClick={() => setActiveTab('csv')}
                >
                    📄 CSV Import
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'manual' ? <ManualTab /> : <CsvImportTab />}
            </div>
        </div>
    );
}
