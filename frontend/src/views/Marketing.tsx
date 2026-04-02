import { useEffect, useState, useRef } from 'react';
import { useMarketingStore, type Row } from '../store/marketingStore';
import { useAuthStore } from '../store/authStore';
import { API_BASE } from '../utils/api';
import { PinModal } from '../features/marketing/PinModal';
import { ChangePinModal } from '../features/marketing/ChangePinModal';
import { SendResultsPanel, ConfirmModal, UndoToast, SmsCostEstimate } from '../features/marketing/components';
import '../features/marketing/Marketing.css';

/**
 * Marketing Page - SMS Marketing Module
 *
 * Single-page layout with two panels:
 * - LEFT: Recipients (fetch from Google Sheets, recipient table)
 * - RIGHT: Message composer (textarea, cost estimate, send)
 *
 * AUTHENTICATION:
 * - Requires PIN authentication before accessing
 * - PIN is verified against backend and stored in sessionStorage
 */
function Spinner() {
    return (
        <svg className="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>
    );
}

export default function Marketing() {
    const {
        rows,
        includedIds,
        toast,
        messageDraft,
        setMessageDraft,
        isSending,
        sendResults,
        error,
        setError,
        getCounts,
        getIncludedRows,
        getExcludedRows,
        setImportData,
        clearAllData,
        includeAllReady,
        includeNone,
        toggleInclusion,
        removeRow,
        removeSelected,
        undoRemove,
        dismissToast,
        setSending,
        setSendResults,
        clearResults,
    } = useMarketingStore();

    const { isAuthenticated, checkStoredAuth, logout } = useAuthStore();
    const [showChangePinModal, setShowChangePinModal] = useState(false);
    const [isFetchingSheets, setIsFetchingSheets] = useState(false);
    const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
    const [showSendConfirm, setShowSendConfirm] = useState(false);
    const [highlightedRowId, setHighlightedRowId] = useState<string | null>(null);
    const tableContainerRef = useRef<HTMLDivElement>(null);

    // Single SMS state
    const [singleName, setSingleName] = useState('');
    const [singlePhone, setSinglePhone] = useState('');
    const [singleMessage, setSingleMessage] = useState('');
    const [singleSending, setSingleSending] = useState(false);
    const [singleSuccess, setSingleSuccess] = useState<string | null>(null);
    const [singleError, setSingleError] = useState<string | null>(null);

    // Batch progress state
    const [batchId, setBatchId] = useState<string | null>(null);
    const [progress, setProgress] = useState<{
        current: number;
        total: number;
        sent: number;
        failed: number;
        lastPhone: string;
        lastStatus: string;
    } | null>(null);

    // Check for stored auth on mount
    useEffect(() => {
        checkStoredAuth();
    }, [checkStoredAuth]);

    // Computed values
    const counts = getCounts();
    const excludedRows = getExcludedRows();
    const isReady = counts.included > 0 && messageDraft.trim().length > 0;
    const hasData = rows.length > 0;
    const hasResults = sendResults.length > 0;

    // === FETCH FROM GOOGLE SHEETS HANDLER ===
    const fetchFromSheets = async () => {
        console.log('[fetchFromSheets] Step 1: Button clicked, setting loading state');
        setIsFetchingSheets(true);
        setError(null);
        clearResults();

        try {
            console.log('[fetchFromSheets] Step 2: Getting auth header from store');
            const authHeader = useAuthStore.getState().getAuthHeader();
            console.log('[fetchFromSheets] Step 3: Auth header present:', Object.keys(authHeader).length > 0);

            console.log('[fetchFromSheets] Step 4: Calling POST /marketing/prepare');
            const response = await fetch(`${API_BASE}/marketing/prepare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader },
            });
            console.log('[fetchFromSheets] Step 5: Response received, status:', response.status);

            if (!response.ok) {
                const errorData = await response.json();
                console.error('[fetchFromSheets] Step 5a: Error response:', errorData);
                throw new Error(errorData.detail || 'Failed to fetch from Google Sheets');
            }

            const data = await response.json();
            console.log('[fetchFromSheets] Step 6: Data parsed —', {
                contacts: data.contacts?.length ?? 0,
                errors: data.errors?.length ?? 0,
                total_count: data.total_count,
                valid_count: data.valid_count,
                invalid_count: data.invalid_count,
            });

            const importedRows: Row[] = [];

            data.contacts.forEach((c: any, idx: number) => {
                importedRows.push({
                    id: `row-${idx}`,
                    rowIndex: idx + 1,
                    name: c.name,
                    phone: c.phone,
                    status: 'ready',
                    errors: [],
                });
            });

            data.errors.forEach((errMsg: string, idx: number) => {
                const match = errMsg.match(/Row (\d+)/);
                const rowNum = match ? parseInt(match[1]) : importedRows.length + idx + 1;
                importedRows.push({
                    id: `error-${idx}`,
                    rowIndex: rowNum,
                    name: '\u2014',
                    phone: '\u2014',
                    status: 'excluded',
                    errors: [errMsg],
                });
            });

            importedRows.sort((a, b) => a.rowIndex - b.rowIndex);
            console.log('[fetchFromSheets] Step 7: Rows built — ready:', importedRows.filter(r => r.status === 'ready').length, ', excluded:', importedRows.filter(r => r.status === 'excluded').length);

            setImportData(importedRows);
            console.log('[fetchFromSheets] Step 8: Store updated, UI should render recipients');
        } catch (err) {
            console.error('[fetchFromSheets] ERROR:', err);
            setError(err instanceof Error ? err.message : 'Failed to fetch from Google Sheets');
        } finally {
            setIsFetchingSheets(false);
            console.log('[fetchFromSheets] Done: loading state cleared');
        }
    };

    // === BROADCAST HANDLER (SSE streaming) ===
    const handleBroadcast = async () => {
        const includedRows = getIncludedRows();
        if (includedRows.length === 0 || !messageDraft.trim()) return;

        setSending(true);
        setError(null);
        setProgress(null);
        setBatchId(null);

        try {
            const authHeader = useAuthStore.getState().getAuthHeader();
            const response = await fetch(`${API_BASE}/marketing/send-batch-stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader },
                body: JSON.stringify({
                    recipients: includedRows.map(r => ({ name: r.name, phone: r.phone })),
                    message: messageDraft,
                }),
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({ detail: 'Send failed' }));
                throw new Error(err.detail || 'Send failed');
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error('Streaming not supported');

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const event = JSON.parse(line.slice(6));

                        if (event.type === 'start') {
                            setBatchId(event.batch_id);
                            setProgress({ current: 0, total: event.total, sent: 0, failed: 0, lastPhone: '', lastStatus: '' });
                        } else if (event.type === 'progress') {
                            setProgress({
                                current: event.current,
                                total: event.total,
                                sent: event.sent,
                                failed: event.failed,
                                lastPhone: event.last_phone,
                                lastStatus: event.last_status,
                            });
                        } else if (event.type === 'complete') {
                            setSendResults(event.results);
                            setProgress(null);
                            setBatchId(null);
                        } else if (event.type === 'cancelled') {
                            setError(`Cancelled. Sent: ${event.sent}, Failed: ${event.failed}, Remaining: ${event.remaining}`);
                            setProgress(null);
                            setBatchId(null);
                        }
                    } catch { /* skip malformed events */ }
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Network error. Please check your connection.');
        } finally {
            setSending(false);
        }
    };

    // === CANCEL HANDLER ===
    const handleCancel = async () => {
        if (!batchId) return;
        try {
            const authHeader = useAuthStore.getState().getAuthHeader();
            await fetch(`${API_BASE}/marketing/cancel-batch/${batchId}`, {
                method: 'POST',
                headers: { ...authHeader },
            });
        } catch { /* best effort */ }
    };

    // === JUMP TO ROW HANDLER ===
    const jumpToRow = (rowId: string) => {
        setHighlightedRowId(rowId);
        const rowElement = document.getElementById(`row-${rowId}`);
        if (rowElement && tableContainerRef.current) {
            rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        setTimeout(() => setHighlightedRowId(null), 2000);
    };

    // === SINGLE SMS HANDLER ===
    const handleSingleSend = async () => {
        if (!singleName.trim() || !singlePhone.trim() || !singleMessage.trim()) return;

        setSingleSending(true);
        setSingleError(null);
        setSingleSuccess(null);

        try {
            const authHeader = useAuthStore.getState().getAuthHeader();
            const response = await fetch(`${API_BASE}/marketing/send-single`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader },
                body: JSON.stringify({ name: singleName, phone: singlePhone, message: singleMessage }),
            });

            const data = await response.json();

            if (data.success) {
                setSingleSuccess('SMS sent successfully.');
                setSingleName('');
                setSinglePhone('');
                setSingleMessage('');
            } else {
                setSingleError(data.error || 'Failed to send SMS');
            }
        } catch {
            setSingleError('Network error. Please check your connection.');
        } finally {
            setSingleSending(false);
        }
    };

    const singleIsValid = singleName.trim() && singlePhone.replace(/\D/g, '').length >= 10 && singleMessage.trim();

    // Show PIN modal if not authenticated
    if (!isAuthenticated) {
        return <PinModal />;
    }

    return (
        <div className="marketing-page">
            {/* === TOP BAR === */}
            <div className="marketing-top-bar">
                <div />
                <div className="top-bar-actions">
                    <button
                        onClick={() => setShowChangePinModal(true)}
                        className="btn-secondary btn-sm"
                        title="Change PIN"
                    >
                        Change PIN
                    </button>
                    <button onClick={logout} className="btn-secondary btn-sm btn-lock" title="Lock Marketing">
                        Lock
                    </button>
                </div>
            </div>

            {showChangePinModal && (
                <ChangePinModal onClose={() => setShowChangePinModal(false)} />
            )}

            {/* === HEADER === */}
            <header className="marketing-header">
                <h1>SMS Marketing</h1>
                <p className="subtitle">Send promotional messages to your customers</p>
            </header>

            {/* === RESULTS VIEW (full width, replaces everything) === */}
            {hasResults && (
                <div className="marketing-card results-card">
                    <SendResultsPanel results={sendResults} onNewBroadcast={clearAllData} />
                </div>
            )}

            {/* === MAIN CONTENT (two-column layout) === */}
            {!hasResults && (
                <div className="marketing-grid">
                    {/* LEFT PANEL: Recipients */}
                    <div className="marketing-card recipients-panel">
                        <div className="panel-header">
                            <h2 className="panel-title">Recipients</h2>
                            {hasData && (
                                <button
                                    className="btn-danger btn-sm"
                                    onClick={() => setShowRemoveConfirm(true)}
                                    type="button"
                                >
                                    Clear List
                                </button>
                            )}
                        </div>

                        {/* Empty state: Load recipients */}
                        {!hasData && (
                            <div className="empty-state">
                                <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                                    <circle cx="9" cy="7" r="4" />
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                                </svg>
                                <p className="empty-state-text">No recipients loaded</p>
                                <p className="empty-state-hint">
                                    Pull contacts from Google Sheets. Opt-outs, failures, and duplicates are automatically filtered.
                                </p>
                                <button
                                    className="btn-primary load-recipients-btn"
                                    onClick={fetchFromSheets}
                                    disabled={isFetchingSheets}
                                >
                                    {isFetchingSheets ? <><Spinner /> Loading recipients...</> : 'Load Recipients'}
                                </button>
                            </div>
                        )}

                        {/* Data loaded: Summary + table */}
                        {hasData && (
                            <>
                                {/* Summary stats */}
                                <div className="summary-stats">
                                    <div className="stat">
                                        <span className="stat-value">{counts.imported}</span>
                                        <span className="stat-label">Imported</span>
                                    </div>
                                    <div className="stat">
                                        <span className="stat-value stat-ready">{counts.ready}</span>
                                        <span className="stat-label">Ready</span>
                                    </div>
                                    <div className="stat">
                                        <span className="stat-value stat-excluded">{counts.excluded}</span>
                                        <span className="stat-label">Excluded</span>
                                    </div>
                                    <div className="stat">
                                        <span className="stat-value stat-included">{counts.included}</span>
                                        <span className="stat-label">Included</span>
                                    </div>
                                </div>

                                {/* Excluded alert */}
                                {counts.excluded > 0 && (
                                    <div className="excluded-alert">
                                        <div className="excluded-alert-header">
                                            <strong>Excluded ({counts.excluded})</strong>
                                        </div>
                                        <ul className="excluded-error-list">
                                            {excludedRows.slice(0, 5).map((row) => (
                                                <li key={row.id}>
                                                    <span className="error-text">
                                                        Row {row.rowIndex} -- {row.errors[0]}
                                                    </span>
                                                    <button
                                                        className="jump-row-btn"
                                                        onClick={() => jumpToRow(row.id)}
                                                        type="button"
                                                        aria-label={`Jump to row ${row.rowIndex}`}
                                                    >
                                                        Jump
                                                    </button>
                                                </li>
                                            ))}
                                            {counts.excluded > 5 && (
                                                <li className="more-errors">...and {counts.excluded - 5} more</li>
                                            )}
                                        </ul>
                                        <p className="excluded-note">Excluded rows will not receive SMS.</p>
                                    </div>
                                )}

                                {/* Bulk action bar */}
                                <div className="bulk-action-bar">
                                    <button
                                        className="bulk-action-btn remove-selected-btn"
                                        onClick={removeSelected}
                                        disabled={counts.included === 0}
                                        type="button"
                                        aria-label="Remove selected"
                                    >
                                        Remove selected
                                    </button>
                                    <span className="action-divider" />
                                    <button
                                        className="bulk-action-btn"
                                        onClick={includeAllReady}
                                        disabled={counts.included === counts.ready}
                                        type="button"
                                    >
                                        Include all ({counts.ready})
                                    </button>
                                    <button
                                        className="bulk-action-btn"
                                        onClick={includeNone}
                                        disabled={counts.included === 0}
                                        type="button"
                                    >
                                        Include none
                                    </button>
                                </div>

                                {/* Recipient table */}
                                <div className="recipient-table-container" ref={tableContainerRef}>
                                    <table className="recipient-table" role="grid">
                                        <thead>
                                            <tr>
                                                <th className="checkbox-col">Include</th>
                                                <th className="name-col">Name</th>
                                                <th className="phone-col">Phone</th>
                                                <th className="action-col"></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {rows.map((row) => {
                                                const isExcluded = row.status === 'excluded';
                                                const isIncluded = includedIds.has(row.id);

                                                return (
                                                    <tr
                                                        key={row.id}
                                                        id={`row-${row.id}`}
                                                        className={`
                                                            ${isExcluded ? 'row-excluded' : ''}
                                                            ${isIncluded && !isExcluded ? 'row-included' : ''}
                                                            ${highlightedRowId === row.id ? 'row-highlighted' : ''}
                                                        `}
                                                        role="row"
                                                    >
                                                        <td className="checkbox-col">
                                                            <input
                                                                type="checkbox"
                                                                checked={isIncluded && !isExcluded}
                                                                disabled={isExcluded}
                                                                onChange={() => toggleInclusion(row.id)}
                                                                aria-label={`Include row ${row.rowIndex}`}
                                                            />
                                                        </td>
                                                        <td className="name-col">
                                                            <span className="name-text">{row.name}</span>
                                                            {isExcluded && (
                                                                <>
                                                                    <span className="excluded-badge">Excluded</span>
                                                                    <span
                                                                        className="error-indicator"
                                                                        title={row.errors.join(', ')}
                                                                    >
                                                                        {row.errors[0]}
                                                                    </span>
                                                                </>
                                                            )}
                                                        </td>
                                                        <td className="phone-col">{row.phone}</td>
                                                        <td className="action-col">
                                                            <button
                                                                className="row-remove-btn"
                                                                onClick={() => removeRow(row.id)}
                                                                type="button"
                                                                aria-label={`Remove row ${row.rowIndex}`}
                                                            >
                                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                    <polyline points="3 6 5 6 21 6" />
                                                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                                                                </svg>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </>
                        )}
                    </div>

                    {/* RIGHT COLUMN */}
                    <div className="right-column">
                        {/* Broadcast Composer */}
                        <div className="marketing-card composer-panel">
                            <div className="panel-header">
                                <h2 className="panel-title">Broadcast Message</h2>
                            </div>

                            <div className="composer-body">
                                <div className="form-group">
                                    <label htmlFor="broadcast-message">Message</label>
                                    <textarea
                                        id="broadcast-message"
                                        value={messageDraft}
                                        onChange={(e) => setMessageDraft(e.target.value)}
                                        placeholder="Hi [name], don't miss our 20% off sale this weekend!"
                                        rows={5}
                                        disabled={isSending}
                                    />
                                    <div className="textarea-meta">
                                        <span className="hint">Use [name] to personalize each message.</span>
                                        <span className="char-count">{messageDraft.length}/1600</span>
                                    </div>
                                    <SmsCostEstimate message={messageDraft} recipientCount={counts.included || 1} />
                                </div>

                                {/* Progress bar during sending */}
                                {isSending && progress && (
                                    <div className="send-progress">
                                        <div className="progress-header">
                                            <span className="progress-label">
                                                Sending {progress.current} of {progress.total}
                                            </span>
                                            <span className="progress-percent">
                                                {Math.round((progress.current / progress.total) * 100)}%
                                            </span>
                                        </div>
                                        <div className="progress-bar-track">
                                            <div
                                                className="progress-bar-fill"
                                                style={{ width: `${(progress.current / progress.total) * 100}%` }}
                                            />
                                        </div>
                                        <div className="progress-stats">
                                            <span className="progress-sent">{progress.sent} sent</span>
                                            <span className="progress-divider">/</span>
                                            <span className="progress-failed">{progress.failed} failed</span>
                                            {progress.lastPhone && (
                                                <span className="progress-last">
                                                    Last: ...{progress.lastPhone} ({progress.lastStatus})
                                                </span>
                                            )}
                                        </div>
                                        <button
                                            className="btn-danger cancel-btn"
                                            onClick={handleCancel}
                                            type="button"
                                        >
                                            Cancel Send
                                        </button>
                                    </div>
                                )}

                                {/* Send button (hidden during sending) */}
                                {!isSending && (
                                    <button
                                        className="btn-primary broadcast-btn"
                                        onClick={() => setShowSendConfirm(true)}
                                        disabled={!isReady}
                                    >
                                        Send to {counts.included} recipient{counts.included !== 1 ? 's' : ''}
                                    </button>
                                )}

                                {!hasData && !isSending && (
                                    <p className="composer-hint">Load recipients to enable broadcasting.</p>
                                )}
                            </div>
                        </div>

                        {/* Quick Send - Single SMS */}
                        <div className="marketing-card quick-send-panel">
                            <div className="panel-header">
                                <h2 className="panel-title">Quick Send</h2>
                            </div>

                            <div className="composer-body">
                                <div className="form-row">
                                    <div className="form-group">
                                        <label htmlFor="single-name">Name</label>
                                        <input
                                            id="single-name"
                                            type="text"
                                            value={singleName}
                                            onChange={(e) => setSingleName(e.target.value)}
                                            placeholder="Jane Doe"
                                            disabled={singleSending}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label htmlFor="single-phone">Phone</label>
                                        <input
                                            id="single-phone"
                                            type="tel"
                                            value={singlePhone}
                                            onChange={(e) => setSinglePhone(e.target.value)}
                                            placeholder="(901) 555-1234"
                                            disabled={singleSending}
                                        />
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label htmlFor="single-message">Message</label>
                                    <textarea
                                        id="single-message"
                                        value={singleMessage}
                                        onChange={(e) => setSingleMessage(e.target.value)}
                                        placeholder="Hi [name], just wanted to let you know..."
                                        rows={3}
                                        disabled={singleSending}
                                    />
                                    <div className="textarea-meta">
                                        <span className="hint">Use [name] to personalize.</span>
                                        <span className="char-count">{singleMessage.length}/1600</span>
                                    </div>
                                    <SmsCostEstimate message={singleMessage} />
                                </div>

                                {singleError && <div className="error-message">{singleError}</div>}
                                {singleSuccess && <div className="success-message">{singleSuccess}</div>}

                                <button
                                    className="btn-primary broadcast-btn"
                                    onClick={handleSingleSend}
                                    disabled={!singleIsValid || singleSending}
                                >
                                    {singleSending ? <><Spinner /> Sending...</> : 'Send SMS'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* === ERROR MESSAGE === */}
            {error && <div className="error-message">{error}</div>}

            {/* === UNDO TOAST === */}
            {toast && (
                <UndoToast
                    message={toast.message}
                    showUndo={toast.showUndo}
                    onUndo={undoRemove}
                    onDismiss={dismissToast}
                />
            )}

            {/* === CLEAR LIST CONFIRMATION MODAL === */}
            {showRemoveConfirm && (
                <ConfirmModal
                    title="Clear recipient list?"
                    message={`This will clear all imported data, including ${counts.imported} rows and ${counts.included} included selections.`}
                    confirmLabel="Clear List"
                    cancelLabel="Cancel"
                    onConfirm={() => {
                        clearAllData();
                        setShowRemoveConfirm(false);
                    }}
                    onCancel={() => setShowRemoveConfirm(false)}
                />
            )}

            {/* === SEND CONFIRMATION MODAL === */}
            {showSendConfirm && (
                <ConfirmModal
                    title="Send SMS?"
                    message={`You are about to send ${counts.included} SMS message${counts.included !== 1 ? 's' : ''}. This will use your Twilio credits and cannot be undone.`}
                    confirmLabel="Send Now"
                    cancelLabel="Cancel"
                    onConfirm={() => {
                        setShowSendConfirm(false);
                        handleBroadcast();
                    }}
                    onCancel={() => setShowSendConfirm(false)}
                />
            )}
        </div>
    );
}
