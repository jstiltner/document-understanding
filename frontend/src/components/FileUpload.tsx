import React, { useState, useRef } from 'react';
import { Button, Form, Alert, ProgressBar } from 'react-bootstrap';
import { documentApi } from '../services/api';

interface FileUploadProps {
  onSuccess: (message: string) => void;
  onError: (error: string) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onSuccess, onError }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      onError('Please select a PDF file');
      return;
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    if (file.size > maxSize) {
      onError('File size must be less than 50MB');
      return;
    }

    setSelectedFile(file);
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      onError('Please select a file first');
      return;
    }

    setUploading(true);

    try {
      const result = await documentApi.uploadDocument(selectedFile);
      onSuccess(`${result.filename} uploaded successfully! Processing started.`);
      setSelectedFile(null);
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="file-upload">
      <div
        className={`upload-area ${dragOver ? 'dragover' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
        style={{ cursor: 'pointer' }}
      >
        <div className="text-center">
          <div className="mb-3">
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-muted"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14,2 14,8 20,8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10,9 9,9 8,9"></polyline>
            </svg>
          </div>
          
          {selectedFile ? (
            <div>
              <h6 className="mb-2">Selected File:</h6>
              <p className="mb-1"><strong>{selectedFile.name}</strong></p>
              <p className="text-muted small mb-3">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          ) : (
            <div>
              <h6 className="mb-2">Drop PDF file here</h6>
              <p className="text-muted mb-3">or click to browse</p>
            </div>
          )}
          
          <p className="small text-muted mb-0">
            Supports PDF files up to 50MB
          </p>
        </div>
      </div>

      <Form.Control
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
      />

      {selectedFile && (
        <div className="mt-3">
          <div className="d-flex gap-2">
            <Button
              variant="primary"
              onClick={handleUpload}
              disabled={uploading}
              className="flex-grow-1"
            >
              {uploading ? 'Uploading...' : 'Upload & Process'}
            </Button>
            <Button
              variant="outline-secondary"
              onClick={() => {
                setSelectedFile(null);
                if (fileInputRef.current) {
                  fileInputRef.current.value = '';
                }
              }}
              disabled={uploading}
            >
              Clear
            </Button>
          </div>
          
          {uploading && (
            <div className="mt-2">
              <ProgressBar animated now={100} />
              <small className="text-muted">
                Uploading file and starting processing...
              </small>
            </div>
          )}
        </div>
      )}

      <div className="mt-3">
        <Alert variant="info" className="small mb-0">
          <strong>Supported formats:</strong> PDF files only<br />
          <strong>Processing:</strong> OCR extraction → LLM field extraction → Review (if needed)
        </Alert>
      </div>
    </div>
  );
};

export default FileUpload;