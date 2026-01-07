interface UndoToastProps {
    message: string;
    showUndo: boolean;
    onUndo: () => void;
    onDismiss: () => void;
}

/**
 * UndoToast - Toast notification with optional undo action
 */
export function UndoToast({ message, showUndo, onUndo, onDismiss }: UndoToastProps) {
    return (
        <div className="undo-toast">
            <span className="toast-message">{message}</span>
            {showUndo && (
                <button className="toast-undo-btn" onClick={onUndo} type="button">
                    Undo
                </button>
            )}
            <button className="toast-close-btn" onClick={onDismiss} type="button" aria-label="Dismiss">
                ✕
            </button>
        </div>
    );
}
