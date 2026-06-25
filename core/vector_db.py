import sqlite3
import struct
import numpy as np
from typing import List, Tuple
from core.models import CodeChunk, SearchResult

class LocalVectorDB:
    def __init__(self, db_path: str = "code_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Initializes the SQLite database and creates the chunks table if it doesn't exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    chunk_type TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
            """)
            conn.commit()

    def clear(self):
        """
        Clears all stored chunks.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS chunks")
            conn.commit()
        self._init_db()

    def delete_file_chunks(self, file_path: str):
        """
        Deletes existing chunks for a specific file (used before re-indexing a file).
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chunks WHERE file_path = ?", (file_path,))
            conn.commit()

    def add_chunks(self, chunks: List[CodeChunk], embeddings: List[List[float]]):
        """
        Saves chunks and their corresponding embeddings into the database.
        """
        if not chunks or not embeddings:
            return
            
        assert len(chunks) == len(embeddings), "Number of chunks must match number of embeddings."
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            insert_data = []
            
            for chunk, emb in zip(chunks, embeddings):
                # Convert float list to binary representation using numpy
                emb_bytes = np.array(emb, dtype=np.float32).tobytes()
                
                insert_data.append((
                    chunk.file_path,
                    chunk.content,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.chunk_type,
                    emb_bytes
                ))
                
            cursor.executemany("""
                INSERT INTO chunks (file_path, content, start_line, end_line, chunk_type, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
            """, insert_data)
            conn.commit()

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[SearchResult]:
        """
        Queries the database and computes cosine similarity with NumPy.
        Returns the top_k closest search results.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path, content, start_line, end_line, chunk_type, embedding FROM chunks")
            rows = cursor.fetchall()
            
        if not rows:
            return []
            
        # Parse query embedding
        query_vec = np.array(query_embedding, dtype=np.float32)
        # Ensure query is normalized
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec /= query_norm

        # Extract embeddings matrix and metadata
        embeddings_list = []
        metadata = []
        
        for row in rows:
            file_path, content, start_line, end_line, chunk_type, emb_bytes = row
            emb = np.frombuffer(emb_bytes, dtype=np.float32)
            
            embeddings_list.append(emb)
            metadata.append((file_path, content, start_line, end_line, chunk_type))
            
        # Stack embeddings into a 2D matrix
        embeddings_matrix = np.vstack(embeddings_list)
        
        # Normalize each row in the matrix
        row_norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
        # Avoid division by zero
        row_norms[row_norms == 0] = 1.0
        normalized_matrix = embeddings_matrix / row_norms
        
        # Calculate cosine similarity (dot product of normalized vectors)
        similarities = np.dot(normalized_matrix, query_vec)
        
        # Rank matches
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            file_path, content, start_line, end_line, chunk_type = metadata[idx]
            
            chunk = CodeChunk(
                file_path=file_path,
                content=content,
                start_line=start_line,
                end_line=end_line,
                chunk_type=chunk_type
            )
            
            results.append(SearchResult(
                chunk=chunk,
                similarity=score
            ))
            
        return results
