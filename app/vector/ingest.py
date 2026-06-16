import os
import sys
from app.vector.chroma import VectorStore

def ingest_directory(path: str):
    store = VectorStore()
    docs = []
    metas = []
    ids = []
    
    valid_extensions = ('.py', '.js', '.ts', '.astro', '.md', '.json', '.yml')
    
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(valid_extensions) and "node_modules" not in root and ".git" not in root:
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # For a 7B model context, chunking by function/class is ideal, 
                    # but file-level chunking is used here for brevity
                    docs.append(content)
                    metas.append({"source": filepath})
                    ids.append(filepath)
                except Exception as e:
                    print(f"Skipping {filepath}: {e}")
                    
    if docs:
        store.collection.add(documents=docs, metadatas=metas, ids=ids)
        print(f"Successfully ingested {len(docs)} files into ChromaDB.")
    else:
        print("No valid files found to ingest.")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Ingesting repository from {target_dir}...")
    ingest_directory(target_dir)
