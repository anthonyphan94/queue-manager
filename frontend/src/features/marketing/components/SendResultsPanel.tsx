import type { SmsResult } from '../../../store/marketingStore';

interface SendResultsPanelProps {
    results: SmsResult[];
    onNewBroadcast: () => void;
}

/**
 * SendResultsPanel - Displays SMS send results after broadcast
 * 
 * Shows success/failure counts and detailed results table.
 */
export function SendResultsPanel({ results, onNewBroadcast }: SendResultsPanelProps) {
    const sentCount = results.filter(r => r.status === 'sent').length;
    const failedCount = results.filter(r => r.status === 'failed').length;

    return (
        <div className="results-section">
            <div className="results-summary">
                <div className="result-stat sent">
                    <span className="count">{sentCount}</span>
                    <span className="label">Sent</span>
                </div>
                <div className="result-stat failed">
                    <span className="count">{failedCount}</span>
                    <span className="label">Failed</span>
                </div>
            </div>

            <div className="results-table-container">
                <table className="results-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Phone</th>
                            <th>Status</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results.map((result, i) => (
                            <tr key={i} className={result.status}>
                                <td>{result.name}</td>
                                <td>{result.phone}</td>
                                <td>
                                    <span className={`status-badge ${result.status}`}>
                                        {result.status === 'sent' ? '✓' : '✗'}
                                    </span>
                                </td>
                                <td className="details">
                                    {result.status === 'sent' ? 'Sent successfully' : result.error}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <button className="new-broadcast-button" onClick={onNewBroadcast}>
                New Broadcast
            </button>
        </div>
    );
}
