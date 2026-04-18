import os
import uuid
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions

# Optional PyPDF for future extension if needed, but for now we focus on txt/md
try:
    import pypdf
except ImportError:
    pypdf = None


class MemoryService:
    def __init__(self):
        # Determine the paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, "data", "chroma")
        self.knowledge_dir = os.path.join(base_dir, "knowledge")

        # Create directories if they do not exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.knowledge_dir, exist_ok=True)

        # Initialize ChromaDB persistent client
        print("[MemoryService] Initializing ChromaDB (this may take a moment to download models on first run)...")
        self.client = chromadb.PersistentClient(path=self.data_dir)
        
        # Use sentence-transformers all-MiniLM-L6-v2 as the embedding function
        # Note: chromadb default is all-MiniLM-L6-v2 anyway, but we explicitly specify for clarity
        self.ef = embedding_functions.DefaultEmbeddingFunction()

        # Get or create the collections
        # 'user_memory' for long term conceptual facts the user expressly tells Rei
        # 'documents' for local file RAG
        self.user_memory = self.client.get_or_create_collection(
            name="user_memory", 
            embedding_function=self.ef
        )
        self.documents = self.client.get_or_create_collection(
            name="documents", 
            embedding_function=self.ef
        )
        
        print("[MemoryService] Online.")

    def save_memory(self, fact: str) -> bool:
        """Save a discrete fact to the user memory long-term storage."""
        if not fact or not fact.strip():
            return False
            
        doc_id = str(uuid.uuid4())
        try:
            self.user_memory.add(
                documents=[fact],
                metadatas=[{"type": "user_fact"}],
                ids=[doc_id]
            )
            print(f"[MemoryService] Saved new memory: {fact}")
            return True
        except Exception as e:
            print(f"[MemoryService] Error saving memory: {e}")
            return False

    def query_context(self, query_text: str, n_results: int = 3) -> str:
        """
        Query both user memory and local documents.
        Returns a formatted context string.
        """
        if not query_text or not query_text.strip():
            return ""

        context_blocks = []

        # 1. Query User Memory
        try:
            mem_results = self.user_memory.query(
                query_texts=[query_text],
                n_results=n_results
            )
            if mem_results and mem_results['documents'] and len(mem_results['documents'][0]) > 0:
                # Filter by distance if available
                distances = mem_results['distances'][0]
                docs = mem_results['documents'][0]
                
                valid_memories = []
                for doc, dist in zip(docs, distances):
                    # Lower distance is better. Limit to somewhat strict similarity (e.g. < 1.0 depending on embedding space)
                    if dist < 1.0: 
                        valid_memories.append(f"- {doc}")
                
                if valid_memories:
                    context_blocks.append("Ingatan Masa Lalu tentang Pengguna:\n" + "\n".join(valid_memories))
        except Exception as e:
            pass

        # 2. Query Documents (RAG)
        try:
            doc_results = self.documents.query(
                query_texts=[query_text],
                n_results=n_results
            )
            if doc_results and doc_results['documents'] and len(doc_results['documents'][0]) > 0:
                distances = doc_results['distances'][0]
                docs = doc_results['documents'][0]
                sources = doc_results['metadatas'][0]
                
                valid_docs = []
                for doc, meta, dist in zip(docs, sources, distances):
                    if dist < 1.2:  # slightly more lenient for document chunks
                        source_name = meta.get('source', 'Unknown')
                        valid_docs.append(f"[Sumber: {source_name}]\n{doc}")
                
                if valid_docs:
                    context_blocks.append("Konteks dari Dokumen RAG:\n" + "\n\n".join(valid_docs))
        except Exception as e:
            pass

        if not context_blocks:
            return ""
            
        return "\n\n".join(context_blocks)

    def ingest_documents(self):
        """Read files from knowledge_dir and store them in the documents collection."""
        print("[MemoryService] Checking for documents to ingest...")
        
        # Keep track of what we have already ingested
        existing_metadatas = self.documents.get(include=['metadatas'])['metadatas']
        ingested_sources = set(meta.get('source') for meta in existing_metadatas if meta and 'source' in meta)
        
        files_to_process = []
        for filename in os.listdir(self.knowledge_dir):
            if filename.endswith(".txt") or filename.endswith(".md"):
                if filename not in ingested_sources:
                    files_to_process.append(filename)
            elif filename.endswith(".pdf") and pypdf:
                if filename not in ingested_sources:
                    files_to_process.append(filename)

        if not files_to_process:
            print("[MemoryService] No new documents to ingest.")
            return

        for filename in files_to_process:
            filepath = os.path.join(self.knowledge_dir, filename)
            print(f"[MemoryService] Ingesting {filename}...")
            
            text_content = ""
            
            try:
                if filename.endswith(".pdf") and pypdf:
                    with open(filepath, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        for page in reader.pages:
                            text_content += page.extract_text() + "\n"
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        text_content = f.read()

                # Basic chunking (overlap not implemented for simplicity, just chunk by ~500 chars keeping words)
                chunks = self._chunk_text(text_content, chunk_size=500)
                
                if chunks:
                    ids = [f"{filename}_{i}" for i in range(len(chunks))]
                    metadatas = [{"source": filename} for _ in chunks]
                    
                    self.documents.add(
                        documents=chunks,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"[MemoryService] Successfully ingested {filename} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"[MemoryService] Failed to ingest {filename}: {e}")

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into rough chunks."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_len = 0
        
        for word in words:
            if current_len + len(word) > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_len = len(word)
            else:
                current_chunk.append(word)
                current_len += len(word) + 1  # +1 for space
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
