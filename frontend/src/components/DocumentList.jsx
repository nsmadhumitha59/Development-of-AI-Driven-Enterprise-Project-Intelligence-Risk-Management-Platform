import React, { useState } from 'react';
import { deleteDocument } from '../services/api';

export default function DocumentList({ documents, onDocumentDeleted }) {
  const [filterText, setFilterText] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}" and purge all its vector chunks?`)) return;

    setDeletingId(docId);
    try {
      await deleteDocument(docId);
      if (onDocumentDeleted) onDocumentDeleted();
    } catch (err) {
      alert(`Error deleting document: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(filterText.toLowerCase()) ||
    doc.file_type.toLowerCase().includes(filterText.toLowerCase()) ||
    doc.doc_id.toLowerCase().includes(filterText.toLowerCase())
  );

  const getFormatBadge = (type) => {
    const ext = type.toLowerCase();
    return <span className={`format-badge ${ext}`}>{ext}</span>;
  };

  return (
    <div className="card-panel">
      <div className="section-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2>📚 Indexed Document Repository</h2>
          <p>Browse metadata records for all extracted, normalized, and vector-indexed project files.</p>
        </div>

        <input
          type="text"
          className="input-field"
          placeholder="🔍 Filter documents..."
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          style={{ maxWidth: '260px' }}
        />
      </div>

      {documents.length === 0 ? (
        <div style={{ padding: '40px', textAlignment: 'center', textAlign: 'center', color: 'var(--text-muted)' }}>
          <p style={{ fontSize: '1rem', marginBottom: '8px' }}>No documents uploaded yet.</p>
          <p style={{ fontSize: '0.84rem' }}>Upload PDF, DOCX, CSV, or TXT documents to populate the vector knowledge base.</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Format</th>
                <th>Filename</th>
                <th>Doc ID</th>
                <th>Size</th>
                <th>Chunks</th>
                <th>Word Count</th>
                <th>SHA-256</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.map((doc) => (
                <tr key={doc.doc_id}>
                  <td>{getFormatBadge(doc.file_type)}</td>
                  <td>
                    <strong style={{ color: '#ffffff' }}>{doc.filename}</strong>
                  </td>
                  <td>
                    <code style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)' }}>{doc.doc_id}</code>
                  </td>
                  <td>{(doc.file_size_bytes / 1024).toFixed(1)} KB</td>
                  <td>
                    <span style={{ fontWeight: '700', color: 'var(--primary)' }}>{doc.chunk_count}</span>
                  </td>
                  <td>{doc.word_count.toLocaleString()} words</td>
                  <td>
                    <code style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {doc.checksum_sha256.substring(0, 10)}...
                    </code>
                  </td>
                  <td>
                    <button
                      className="btn-danger"
                      onClick={() => handleDelete(doc.doc_id, doc.filename)}
                      disabled={deletingId === doc.doc_id}
                    >
                      {deletingId === doc.doc_id ? 'Deleting...' : '🗑️ Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
