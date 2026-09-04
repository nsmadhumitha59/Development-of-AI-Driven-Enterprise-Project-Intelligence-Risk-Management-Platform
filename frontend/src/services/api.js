const API_BASE = '/api/v1';

export async function getHealth() {
  const res = await fetch(`${API_BASE}/system/health`);
  if (!res.ok) throw new Error('Backend offline');
  return res.json();
}

export async function getArchitecture() {
  const res = await fetch(`${API_BASE}/system/architecture`);
  if (!res.ok) throw new Error('Failed to fetch architecture info');
  return res.json();
}

export async function uploadDocuments(fileList) {
  const formData = new FormData();
  for (let i = 0; i < fileList.length; i++) {
    formData.append('files', fileList[i]);
  }

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload documents');
  }

  return res.json();
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to load documents');
  return res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete document ${docId}`);
  return res.json();
}

export async function searchRAG(query, topK = 5, docId = null, fileType = null) {
  const res = await fetch(`${API_BASE}/rag/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      top_k: parseInt(topK, 10),
      doc_id: docId || undefined,
      file_type: fileType || undefined,
    }),
  });

  if (!res.ok) throw new Error('Semantic search failed');
  return res.json();
}
