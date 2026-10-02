import React from 'react';

export default function SystemArchitecture({ architectureInfo }) {
  if (!architectureInfo) return null;

  const { rag_pipeline, multi_agent_framework } = architectureInfo;

  return (
    <div>
      {/* RAG Pipeline Spec Card */}
      <div className="card-panel">
        <div className="section-header">
          <h2>🧩 System Architecture & RAG Flow Specification</h2>
          <p>Overall system architectural design and pipeline flow for document ingestion, text normalization, vector embedding, and ChromaDB indexing.</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Formats Supported</div>
            <div style={{ fontSize: '0.95rem', fontWeight: '700', color: '#ffffff' }}>PDF, DOCX, CSV, TXT</div>
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Embedding Model</div>
            <div style={{ fontSize: '0.95rem', fontWeight: '700', color: 'var(--accent-cyan)' }}>{rag_pipeline.embedding_model}</div>
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Vector Dimensions</div>
            <div style={{ fontSize: '0.95rem', fontWeight: '700', color: 'var(--primary)' }}>384 Dimensions</div>
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Vector Storage</div>
            <div style={{ fontSize: '0.95rem', fontWeight: '700', color: '#34d399' }}>ChromaDB (Local Persistent)</div>
          </div>
        </div>

        {/* Visual Pipeline Flow Diagram */}
        <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <h3 style={{ fontSize: '0.95rem', color: 'var(--text-muted)', marginBottom: '16px', textAlign: 'center' }}>
            🔄 End-to-End Milestone 1 RAG Data Flow
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ flex: '1', minWidth: '140px', background: 'rgba(99, 102, 241, 0.12)', border: '1px solid rgba(99, 102, 241, 0.3)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>📁 Upload</div>
              <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: '600' }}>PDF / DOCX / CSV / TXT</div>
            </div>
            <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>➔</span>
            <div style={{ flex: '1', minWidth: '140px', background: 'rgba(6, 182, 212, 0.12)', border: '1px solid rgba(6, 182, 212, 0.3)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>⚙️ Extraction</div>
              <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: '600' }}>Text Normalization</div>
            </div>
            <span style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>➔</span>
            <div style={{ flex: '1', minWidth: '140px', background: 'rgba(139, 92, 246, 0.12)', border: '1px solid rgba(139, 92, 246, 0.3)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>✂️ Chunker</div>
              <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: '600' }}>Recursive Splitter</div>
            </div>
            <span style={{ color: 'var(--accent-purple)', fontWeight: 'bold' }}>➔</span>
            <div style={{ flex: '1', minWidth: '140px', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>🧬 Embeddings</div>
              <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: '600' }}>all-MiniLM-L6-v2</div>
            </div>
            <span style={{ color: 'var(--accent-amber)', fontWeight: 'bold' }}>➔</span>
            <div style={{ flex: '1', minWidth: '140px', background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>🗄️ Vector Store</div>
              <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: '600' }}>ChromaDB Retrieval</div>
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Agent System Framework Specs */}
      <div className="card-panel">
        <div className="section-header">
          <h2>🤖 Multi-Agent Framework Architecture Specs</h2>
          <p>Extensible agent structure and contract responsibilities designed for future milestone expansion.</p>
        </div>

        <div className="agent-grid">
          {multi_agent_framework.map((agent, idx) => (
            <div
              key={idx}
              className={`agent-card ${agent.status === 'Active' ? 'active-agent' : ''}`}
            >
              <div className="agent-card-header">
                <span className="agent-title">{agent.name}</span>
                <span className={`agent-status-badge ${agent.status}`}>
                  {agent.status === 'Active' ? '● Implemented' : '⏳ ' + agent.milestone}
                </span>
              </div>

              <div style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', fontWeight: '600', marginBottom: '10px' }}>
                {agent.milestone}
              </div>

              <h4 style={{ fontSize: '0.8rem', color: '#ffffff', marginBottom: '6px' }}>Core Responsibilities:</h4>
              <ul className="responsibilities-list">
                {agent.responsibilities.map((resp, i) => (
                  <li key={i}>{resp}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
