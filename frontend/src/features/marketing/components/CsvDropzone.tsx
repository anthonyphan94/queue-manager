import { useState, useCallback, type DragEvent, type ChangeEvent } from 'react';

interface CsvDropzoneProps {
    isUploading: boolean;
    onFileSelect: (file: File) => Promise<void>;
}

/**
 * CsvDropzone - File upload dropzone for CSV files
 * 
 * Handles drag & drop and file browse functionality.
 */
export function CsvDropzone({ isUploading, onFileSelect }: CsvDropzoneProps) {
    const [isDragOver, setIsDragOver] = useState(false);

    const handleDragOver = useCallback((e: DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    }, []);

    const handleDrop = useCallback(async (e: DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) await onFileSelect(file);
    }, [onFileSelect]);

    const handleFileChange = useCallback(async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) await onFileSelect(file);
    }, [onFileSelect]);

    return (
        <div
            className={`dropzone ${isDragOver ? 'active' : ''} ${isUploading ? 'uploading' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            <div className="dropzone-content">
                <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <p className="dropzone-text">
                    {isUploading ? 'Processing...' : 'Drag & drop your CSV file here'}
                </p>
                <p className="dropzone-hint">or</p>
                <label className="file-select-button">
                    Browse Files
                    <input
                        type="file"
                        accept=".csv"
                        onChange={handleFileChange}
                        disabled={isUploading}
                        hidden
                    />
                </label>
                <p className="format-hint">Column A: Name, Column B: Phone Number</p>
            </div>
        </div>
    );
}
