import chromadb
import os

class VectorStore:
    def __init__(self, path="./chroma_data"):
        # CPU-bound embeddings keep GPU VRAM free for the 7B LLM inference
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection("agentern_codebase")
        
    def search(self, query: str, n_results=3) -> str:
        if self.collection.count() == 0:
            return "No codebase context available."
        results = self.collection.query(query_texts=[query], n_results=n_results)
        if not results["documents"]:
            return ""
        return "\n---\n".join(results["documents"][0])
