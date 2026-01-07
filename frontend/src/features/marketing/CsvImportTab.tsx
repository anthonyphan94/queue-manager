import { useState, useRef } from 'react';
import { useMarketingStore, type Row } from '../../store/marketingStore';
import { useAuthStore } from '../../store/authStore';
import { API_BASE } from '../../utils/api';
import { CsvDropzone, SendResultsPanel, ConfirmModal, UndoToast } from './components';

/**
 * CsvImportTab - Mail-style CSV import with bulk selection and removal
 * 
 * KEY TERMINOLOGY:
 * - Imported: total rows in current session
 * - Ready: valid rows that can be sent
 * - Excluded: invalid rows that cannot be sent  
 * - Included: rows currently selected to send (Ready only)
 * 
 * INVARIANTS:
 * - Imported = Ready + Excluded
 * - Included <= Ready
 * - Excluded rows are never includable
 */
export function CsvImportTab() {
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

    const [isUploading, setIsUploading] = useState(false);
    const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
    const [highlightedRowId, setHighlightedRowId] = useState<string | null>(null);
    const tableContainerRef = useRef<HTMLDivElement>(null);

    // Computed values
    const counts = getCounts();
    const excludedRows = getExcludedRows();

    // === UPLOAD HANDLER ===
    const uploadFile = async (file: File) => {
        if (!file.name.toLowerCase().endsWith('.csv')) {
            setError('Please upload a .csv file');
            return;
        }

        setIsUploading(true);
        setError(null);
        clearResults();

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_BASE}/marketing/preview-csv`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to parse CSV');
            }

            const data = await response.json();

            // Transform API response to Row model
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
                    name: '—',
                    phone: '—',
                    status: 'excluded',
                    errors: [errMsg],
                });
            });

            importedRows.sort((a, b) => a.rowIndex - b.rowIndex);
            setImportData(importedRows);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to upload file');
        } finally {
            setIsUploading(false);
        }
    };

    // === BROADCAST HANDLER ===
    const handleBroadcast = async () => {
        const includedRows = getIncludedRows();
        if (includedRows.length === 0 || !messageDraft.trim()) return;

        setSending(true);
        setError(null);

        try {
            const authHeader = useAuthStore.getState().getAuthHeader();
            const response = await fetch(`${API_BASE}/marketing/send-batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader },
                body: JSON.stringify({
                    recipients: includedRows.map(r => ({ name: r.name, phone: r.phone })),
                    message: messageDraft,
                }),
            });

            const data = await response.json();
            setSendResults(data.results);
        } catch (err) {
            setError('Network error. Please check your connection.');
            setSending(false);
        }
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

    // === RENDER STATES ===
    const isReady = counts.included > 0 && messageDraft.trim().length > 0;
    const hasData = rows.length > 0;
    const hasResults = sendResults.length > 0;

    return (
        <div className="csv-tab">
            {/* === UPLOAD AREA === */}
            {!hasData && !hasResults && (
                <CsvDropzone isUploading={isUploading} onFileSelect={uploadFile} />
            )}

            {/* === PREVIEW TABLE === */}
            {hasData && !hasResults && (
                <div className="preview-section">
                    {/* A) STICKY SUMMARY BAR */}
                    <div className="import-summary-bar">
                        <span className="summary-item">
                            <strong>Imported:</strong> {counts.imported}
                        </span>
                        <span className="summary-divider">|</span>
                        <span className="summary-item ready">
                            <strong>Ready:</strong> {counts.ready}
                        </span>
                        <span className="summary-divider">|</span>
                        <span className="summary-item excluded">
                            <strong>Excluded:</strong> {counts.excluded}
                        </span>
                        <span className="summary-divider">|</span>
                        <span className="summary-item included">
                            <strong>Included:</strong> {counts.included}
                        </span>
                    </div>

                    {/* B) EXCLUDED ALERT */}
                    {counts.excluded > 0 && (
                        <div className="excluded-alert">
                            <div className="excluded-alert-header">
                                <span className="excluded-icon">⚠️</span>
                                <strong>Excluded ({counts.excluded})</strong>
                            </div>
                            <ul className="excluded-error-list">
                                {excludedRows.slice(0, 5).map((row) => (
                                    <li key={row.id}>
                                        <span className="error-text">
                                            Row {row.rowIndex} — {row.errors[0]}
                                        </span>
                                        <button
                                            className="jump-row-btn"
                                            onClick={() => jumpToRow(row.id)}
                                            type="button"
                                            aria-label={`Jump to row ${row.rowIndex}`}
                                        >
                                            Jump to row {row.rowIndex}
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

                    {/* C) MAIL-STYLE BULK ACTION BAR */}
                    <div className="bulk-action-bar">
                        <button
                            className="bulk-action-btn remove-selected-btn"
                            onClick={removeSelected}
                            disabled={counts.included === 0}
                            type="button"
                            aria-label="Remove selected"
                        >
                            🗑️ Remove selected
                        </button>
                        <span className="action-divider" />
                        <button
                            className="bulk-action-btn"
                            onClick={includeAllReady}
                            disabled={counts.included === counts.ready}
                            type="button"
                        >
                            Include all ready ({counts.ready})
                        </button>
                        <button
                            className="bulk-action-btn"
                            onClick={includeNone}
                            disabled={counts.included === 0}
                            type="button"
                        >
                            Include none
                        </button>
                        <div className="bulk-action-spacer" />
                        <button
                            className="remove-csv-btn"
                            onClick={() => setShowRemoveConfirm(true)}
                            type="button"
                        >
                            Remove CSV
                        </button>
                    </div>

                    {/* D) TABLE */}
                    <div className="preview-table-container" ref={tableContainerRef}>
                        <table className="preview-table" role="grid">
                            <thead>
                                <tr>
                                    <th className="checkbox-col">Include</th>
                                    <th className="name-col">Name</th>
                                    <th className="phone-col">Phone</th>
                                    <th className="action-col">Action</th>
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
                                                    🗑️
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {/* MESSAGE INPUT */}
                    <div className="form-group">
                        <label htmlFor="broadcast-message">Broadcast Message</label>
                        <textarea
                            id="broadcast-message"
                            value={messageDraft}
                            onChange={(e) => setMessageDraft(e.target.value)}
                            placeholder="Hi [name], don't miss our 20% off sale this weekend!"
                            rows={4}
                            disabled={isSending}
                        />
                        <span className="hint">Use [name] to personalize each message.</span>
                        <span className="char-count">{messageDraft.length}/1600</span>
                    </div>

                    {/* BROADCAST BUTTON */}
                    <button
                        className="broadcast-button"
                        onClick={handleBroadcast}
                        disabled={!isReady || isSending}
                    >
                        {isSending
                            ? `Sending to ${counts.included} recipients...`
                            : `Send to ${counts.included} included recipient${counts.included !== 1 ? 's' : ''}`
                        }
                    </button>
                </div>
            )}

            {/* === RESULTS === */}
            {hasResults && (
                <SendResultsPanel results={sendResults} onNewBroadcast={clearAllData} />
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

            {/* === REMOVE CSV CONFIRMATION MODAL === */}
            {showRemoveConfirm && (
                <ConfirmModal
                    title="Remove CSV?"
                    message={`This will clear all imported data, including ${counts.imported} rows and ${counts.included} included selections.`}
                    confirmLabel="Remove CSV"
                    cancelLabel="Cancel"
                    onConfirm={() => {
                        clearAllData();
                        setShowRemoveConfirm(false);
                    }}
                    onCancel={() => setShowRemoveConfirm(false)}
                />
            )}
        </div>
    );
}
