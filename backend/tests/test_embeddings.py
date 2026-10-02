from app.rag.embeddings import embedding_generator

def test_single_embedding_generation():
    text = "Database query latency increased to 450ms."
    vector = embedding_generator.generate_embedding(text)
    
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert any(val != 0.0 for val in vector)

def test_batch_embedding_generation():
    texts = [
        "Database migration timeout.",
        "Sprint velocity fell from 42 points to 28 points.",
        "Security compliance specs require local vector store."
    ]
    vectors = embedding_generator.generate_embeddings_batch(texts)
    
    assert len(vectors) == 3
    for vec in vectors:
        assert isinstance(vec, list)
        assert len(vec) == 384
