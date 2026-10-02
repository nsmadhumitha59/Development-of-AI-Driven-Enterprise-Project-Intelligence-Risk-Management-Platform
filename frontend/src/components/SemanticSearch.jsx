import React, { useState } from 'react';
import { searchRAG } from '../services/api';

const EXAMPLE_QUERIES = [
  "What caused the sprint velocity drop?",
  "Why is the API Gateway slow or lagging?",
  "What are the security and compliance requirements?",
  "Why is the cloud migration project delayed?"
];

export default function SemanticSearch({ documents }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [selectedFileType, setSelectedFileType] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSearch = async (overrideQuery = null) => {
    const q = overrideQuery || query;
    if (!q.trim()) return;

    setIsSearching(true);
    setErrorMessage('');
    try {
      const res = await searchRAG(q, topK, selectedDocId, selectedFileType);
      setSearchResults(res);
    } catch (err) {
      setErrorMessage(err.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleExampleClick = (example) => {
    setQuery(example);
    handleSearch(example);
  };

  const getFormatBadge = (type) => {
    const ext = type.toLowerCase();
    return <span className={`format-badge ${ext}`}>{ext}</span>;
  };

  return (
    <div className="card-panel">
      <div className="section-header">
        <h2>🔍 Semantic Vector Retrieval Playground</h2>
        <p>Test real-time vector similarity search across indexed document text chunks using 384-dimensional SentenceTransformer embeddings and ChromaDB.</p>
      </div>

      {/* Query Bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '14px' }}>
        <input
          type="text"
          className="input-field"
          placeholder="Enter natural language query (e.g. 'project schedule delays', 'database bottleneck')..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          className="btn-primary"
          onClick={() => handleSearch()}
          disabled={isSearching || !query.trim()}
          style={{ minWidth: '130px' }}
        >
          {isSearching ? '🔎 Searching...' : '🚀 Retrieve'}
        </button>
      </div>

      {/* Quick Example Chips */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '600' }}>Sample Queries:</span>
        {EXAMPLE_QUERIES.map((example, idx) => (
          <button
            key={idx}
            className="btn-secondary"
            onClick={() => handleExampleClick(example)}
            style={{ fontSize: '0.76rem', padding: '4px 10px', borderRadius: '20px' }}
          >
            💡 {example}
          </button>
        ))}
      </div>

      {/* Search Filters */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center', background: 'rgba(15, 23, 42, 0.4)', padding: '14px', borderRadius: '10px', marginBottom: '24px', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '600' }}>Top-K Matches:</label>
          <input
            type="range"
            min="1"
            max="15"
            value={topK}
            onChange={(e) => setTopK(e.target.value)}
            style={{ accentColor: 'var(--primary)', cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--primary)', minWidth: '24px' }}>{topK}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '600' }}>Doc Filter:</label>
          <select
            className="input-field"
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            style={{ padding: '6px 12px', fontSize: '0.82rem' }}
          >
            <option value="">All Documents ({documents.length})</option>
            {documents.map((doc) => (
              <option key={doc.doc_id} value={doc.doc_id}>
                {doc.filename} ({doc.file_type})
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '600' }}>File Format:</label>
          <select
            className="input-field"
            value={selectedFileType}
            onChange={(e) => setSelectedFileType(e.target.value)}
            style={{ padding: '6px 12px', fontSize: '0.82rem' }}
          >
            <option value="">All Formats</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="csv">CSV</option>
            <option value="txt">TXT</option>
          </select>
        </div>
      </div>

      {errorMessage && (
        <div style={{ padding: '14px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', color: '#f87171', fontSize: '0.88rem' }}>
          ⚠️ {errorMessage}
        </div>
      )}

      {/* Results Listing */}
      {searchResults && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1rem', color: '#ffffff' }}>
              Retrieval Results for <span style={{ color: 'var(--primary)' }}>"{searchResults.query}"</span>
            </h3>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Found {searchResults.total_hits} matching chunk(s)
            </span>
          </div>

          {searchResults.hits.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No matching chunks found for this query or filter criteria.
            </div>
          ) : (
            searchResults.hits.map((hit) => (
              <div key={hit.chunk_id} className="search-hit-card">
                <div className="search-hit-header">
                  <div className="hit-title">
                    {getFormatBadge(hit.file_type)}
                    <span style={{ color: '#ffffff' }}>{hit.filename}</span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                      Chunk #{hit.chunk_index}
                    </span>
                  </div>
                  <span className="score-badge">
                    🎯 {(hit.similarity_score * 100).toFixed(1)}% Match
                  </span>
                </div>
                <div className="chunk-text-box">{hit.text}</div>
                <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  <span>Chunk ID: <code>{hit.chunk_id}</code></span>
                  <span>Cosine Distance: {hit.distance}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
