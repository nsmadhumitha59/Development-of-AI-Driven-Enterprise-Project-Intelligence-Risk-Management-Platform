from app.rag.chunker import RecursiveCharacterChunker
from app.schemas import DocumentMetadata

def test_recursive_chunker():
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
    text = (
        "Paragraph 1: Project Alpha is currently behind schedule due to database latency issues. "
        "Engineers are actively working to add missing indices.\n\n"
        "Paragraph 2: Sprint velocity dropped significantly from 45 points to 28 points. "
        "The primary risk factor is the unassigned payment vendor dependency."
    )
    meta = DocumentMetadata(
        doc_id="doc_test123",
        filename="test.txt",
        file_type="txt",
        file_size_bytes=len(text),
        char_count=len(text),
        word_count=len(text.split()),
        checksum_sha256="abc123hash",
        uploaded_at="2026-09-04T00:00:00Z"
    )
    chunks = chunker.chunk_document(text, meta)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doc_id == "doc_test123"
        assert chunk.filename == "test.txt"
        assert chunk.file_type == "txt"
        assert chunk.chunk_id.startswith("doc_test123_chk_")
        assert len(chunk.text) > 0
        assert chunk.char_length == len(chunk.text)
