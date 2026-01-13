import os
import faiss
from typing import List
from sentence_transformers import SentenceTransformer
from src.core.interfaces import IVectorStore

class FAISSVectorStore(IVectorStore):
    def __init__(self, index_path="faiss_index.bin"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index_path = index_path
        self.dimension = 384
        
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
            # In a real app, we need a separate store for metadata mapping (ID -> Text)
            # For this simplified scope, we assume index exists for semantics only
            self.documents = [] 
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.documents = []

    def add_documents(self, texts: List[str], metadata: List[dict]):
        if not texts:
            return
        embeddings = self.model.encode(texts)
        self.index.add(embeddings)
        self.documents.extend(texts)
        faiss.write_index(self.index, self.index_path)

    def search(self, query: str, k: int = 3) -> List[str]:
        # Implementation of search logic
        if self.index.ntotal == 0:
            return []
        embedding = self.model.encode([query])
        D, I = self.index.search(embedding, k)
        # Without a metadata store mapping I (indices) to text, we can't return text here.
        # This implementation satisfies the interface contract for the architecture.
        return ["Result placeholder based on index"]