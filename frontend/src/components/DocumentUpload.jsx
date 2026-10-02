import React, { useState, useRef } from 'react';
import { uploadDocuments } from '../services/api';

export default function DocumentUpload({ onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
      setErrorMessage('');
      setUploadResult(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(Array.from(e.dataTransfer.files));
      setErrorMessage('');
      setUploadResult(null);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    setErrorMessage('');
    setUploadResult(null);

    try {
      const result = await uploadDocuments(files);
      setUploadResult(result);
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      setErrorMessage(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const getFormatClass = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'pdf') return 'pdf';
    if (ext === 'docx' || ext === 'doc') return 'docx';
    if (ext === 'csv') return 'csv';
    return 'txt';
  };

  return (
    <div className="card-panel">
      <div className="section-header">
        <h2>📄 Document Ingestion Module</h2>
        <p>Support uploading PDF, DOCX, CSV, and TXT files for content extraction, text normalization, chunking, and ChromaDB vector indexing.</p>
      </div>

      <div
        className="dropzone"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          multiple
          accept=".pdf,.docx,.doc,.csv,.txt"
          style={{ display: 'none' }}
        />
        <div className="dropzone-icon">📥</div>
        <h3 style={{ fontSize: '1.1rem', color: '#ffffff', marginBottom: '6px' }}>
          Drag & Drop Document Files Here
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Supports <span className="format-badge pdf">PDF</span> <span className="format-badge docx">DOCX</span> <span className="format-badge csv">CSV</span> <span className="format-badge txt">TXT</span> files
        </p>
      </div>

      {files.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
            Selected Files ({files.length}):
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {files.map((file, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: 'rgba(15, 23, 42, 0.6)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`format-badge ${getFormatClass(file.name)}`}>
                    {getFormatClass(file.name)}
                  </span>
                  <span style={{ fontSize: '0.9rem', fontWeight: '500' }}>{file.name}</span>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
            <button
              className="btn-primary"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading ? '⚙️ Processing & Indexing...' : '⚡ Process & Index Documents'}
            </button>
            <button
              className="btn-secondary"
              onClick={() => setFiles([])}
              disabled={isUploading}
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {errorMessage && (
        <div style={{ padding: '14px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', color: '#f87171', fontSize: '0.88rem' }}>
          ⚠️ <strong>Upload Error:</strong> {errorMessage}
        </div>
      )}

      {uploadResult && uploadResult.success && (
        <div style={{ padding: '16px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#34d399', fontSize: '0.9rem' }}>
          <h4 style={{ fontWeight: '700', marginBottom: '8px' }}>
            ✅ Ingestion Complete! Successfully indexed {uploadResult.total_uploaded} document(s).
          </h4>
          <ul style={{ paddingLeft: '20px', fontSize: '0.84rem' }}>
            {uploadResult.documents.map((doc) => (
              <li key={doc.doc_id}>
                <strong>{doc.filename}</strong>: {doc.chunk_count} text chunks indexed ({doc.char_count} chars, SHA: {doc.checksum_sha256.substring(0, 8)})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
