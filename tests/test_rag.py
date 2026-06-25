import os
import shutil
import tempfile
import numpy as np
from core.chunker import chunk_file
from core.embeddings import CodeEmbedder
from core.vector_db import LocalVectorDB
from core.rag_orchestrator import RAGOrchestrator
from core.models import CodeChunk

def test_chunker_python():
    # Create a temporary python file
    content = """
class DataProcessor:
    def process(self, x):
        return x * 2

def helper_func():
    pass
"""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name
        
    try:
        chunks = chunk_file(temp_path)
        # Should detect class DataProcessor, function process, and function helper_func
        chunk_types = [c.chunk_type for c in chunks]
        assert "class" in chunk_types
        assert "function" in chunk_types
        assert len(chunks) >= 3
    finally:
        os.remove(temp_path)

def test_deterministic_embeddings():
    embedder = CodeEmbedder()
    vec1 = embedder.get_embedding("import os")
    vec2 = embedder.get_embedding("import os")
    vec3 = embedder.get_embedding("def test(): pass")
    
    expected_dim = 3072 if embedder.client is not None else 768
    assert len(vec1) == expected_dim
    assert vec1 == vec2  # Must be deterministic
    assert vec1 != vec3  # Different inputs should result in different vectors

def test_vector_db_search():
    temp_db_path = tempfile.mktemp(suffix=".db")
    db = LocalVectorDB(db_path=temp_db_path)
    
    try:
        # Create vectors
        emb1 = [1.0] + [0.0] * 767  # matches query perfectly
        emb2 = [0.0, 1.0] + [0.0] * 766
        
        chunk1 = CodeChunk(file_path="a.py", content="content a", start_line=1, end_line=5, chunk_type="function")
        chunk2 = CodeChunk(file_path="b.py", content="content b", start_line=10, end_line=15, chunk_type="class")
        
        db.add_chunks([chunk1, chunk2], [emb1, emb2])
        
        # Query with vector matching emb1
        query_vec = [1.0] + [0.0] * 767
        results = db.search(query_vec, top_k=2)
        
        assert len(results) == 2
        assert results[0].chunk.file_path == "a.py"
        assert results[0].similarity > 0.99  # perfect match
        assert results[1].chunk.file_path == "b.py"
        assert abs(results[1].similarity) < 0.01  # orthogonal
    finally:
        del db
        import gc
        gc.collect()
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

def test_rag_orchestrator():
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_memory.db")
    
    # Create a couple of mock files
    file1_path = os.path.join(temp_dir, "utils.py")
    with open(file1_path, "w", encoding="utf-8") as f:
        f.write("def calculate_hash(data):\n    return data.strip()\n")
        
    file2_path = os.path.join(temp_dir, "main.py")
    with open(file2_path, "w", encoding="utf-8") as f:
        f.write("def run():\n    calculate_hash('hello')\n")

    try:
        orchestrator = RAGOrchestrator(db_path=temp_db_path, workspace_root=temp_dir)
        stats = orchestrator.index_directory(temp_dir)
        
        assert stats["indexed_files"] == 2
        assert stats["total_chunks"] >= 2
        
        # Verify context retrieval for code change
        # A code change referencing calculate_hash
        context = orchestrator.get_context_for_changes(file2_path, added_lines=[2])
        
        # Should retrieve the chunk from utils.py containing calculate_hash
        assert len(context) > 0
        retrieved_paths = [res.chunk.file_path for res in context]
        assert "utils.py" in retrieved_paths
    finally:
        del orchestrator
        import gc
        gc.collect()
        shutil.rmtree(temp_dir)
