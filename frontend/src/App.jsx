import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import DocumentUpload from './components/DocumentUpload';
import DocumentList from './components/DocumentList';
import SemanticSearch from './components/SemanticSearch';
import SystemArchitecture from './components/SystemArchitecture';
import { getHealth, listDocuments, getArchitecture } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [isHealthy, setIsHealthy] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [architectureInfo, setArchitectureInfo] = useState(null);

  const fetchBackendData = async () => {
    try {
      const health = await getHealth();
      setIsHealthy(health.status === 'healthy');

      const docs = await listDocuments();
      setDocuments(docs);

      const arch = await getArchitecture();
      setArchitectureInfo(arch);
    } catch (err) {
      console.warn('Backend connection failed:', err);
      setIsHealthy(false);
    }
  };

  useEffect(() => {
    fetchBackendData();
    const interval = setInterval(fetchBackendData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <Header
        isHealthy={isHealthy}
        documentCount={documents.length}
        architectureInfo={architectureInfo}
      />

      {/* Navigation Tabs */}
      <nav className="nav-tabs">
        <button
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <span className="tab-icon">📥</span> Ingestion & Upload
        </button>
        <button
          className={`tab-btn ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          <span className="tab-icon">📚</span> Document Repository ({documents.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          <span className="tab-icon">🔍</span> Semantic RAG Search
        </button>
        <button
          className={`tab-btn ${activeTab === 'architecture' ? 'active' : ''}`}
          onClick={() => setActiveTab('architecture')}
        >
          <span className="tab-icon">⚙️</span> Architecture & Blueprint
        </button>
      </nav>

      {/* Active Tab View */}
      <main>
        {activeTab === 'upload' && (
          <DocumentUpload onUploadSuccess={fetchBackendData} />
        )}
        {activeTab === 'list' && (
          <DocumentList documents={documents} onDocumentDeleted={fetchBackendData} />
        )}
        {activeTab === 'search' && (
          <SemanticSearch documents={documents} />
        )}
        {activeTab === 'architecture' && (
          <SystemArchitecture architectureInfo={architectureInfo} />
        )}
      </main>
    </div>
  );
}
