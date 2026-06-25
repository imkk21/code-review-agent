import os
import hashlib
import numpy as np
from typing import List

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class CodeEmbedder:
    def __init__(self, model_name: str = "gemini-embedding-001"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini GenAI Client for embeddings: {e}")

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates embedding for a single text.
        """
        embeddings = self.get_embeddings_batch([text])
        return embeddings[0] if embeddings else self._generate_mock_vector(text)

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of texts in a batch.
        """
        if not texts:
            return []
            
        if not self.client:
            # Fall back to mock vectors
            return [self._generate_mock_vector(t) for t in texts]

        try:
            # Call Gemini embeddings endpoint
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=texts
            )
            
            # Extract list of embedding vectors
            if response.embeddings:
                return [emb.values for emb in response.embeddings]
                
            return [self._generate_mock_vector(t) for t in texts]
        except Exception as e:
            print(f"Embedding API call failed: {e}. Falling back to mock embeddings.")
            return [self._generate_mock_vector(t) for t in texts]

    def _generate_mock_vector(self, text: str, dimensions: int = 768) -> List[float]:
        """
        Generates a deterministic normalized mock vector based on the SHA-256 hash of the text.
        Allows offline/key-free testing of vector index matching.
        """
        sha = hashlib.sha256(text.encode('utf-8')).digest()
        seed = int.from_bytes(sha[:4], 'big')
        rng = np.random.default_rng(seed)
        
        # Generate random normal vector
        vec = rng.standard_normal(dimensions)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        return vec.tolist()
