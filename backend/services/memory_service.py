import os
import uuid
from typing import List
# pyrefly: ignore [missing-import]
from langchain_chroma import Chroma
# pyrefly: ignore [missing-import]
from langchain_huggingface import HuggingFaceEmbeddings


try:
    # pyrefly: ignore [missing-import]
    import pypdf
except ImportError:
    pypdf = None


class MemoryService:
    def __init__(self):
        # Determine the paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, "data", "chroma")
        self.knowledge_dir = os.path.join(base_dir, "knowledge")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # Create directories if they do not exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.knowledge_dir, exist_ok=True)

        self.user_memory = Chroma(
            collection_name="user_memory",
            embedding_function=self.embeddings,
            persist_directory=self.data_dir
        )
        self.documents = Chroma(
            collection_name="documents",
            embedding_function=self.embeddings,
            persist_directory=self.data_dir
        )
        
        print("[MemoryService] Online.")

    def save_memory(self, fact: str) -> bool:
        """Save a discrete fact to the user memory long-term storage."""
        if not fact or not fact.strip():
            return False
            
        doc_id = str(uuid.uuid4())
        try:
            # LangChain Chroma uses add_texts or add_documents instead of add()
            self.user_memory.add_texts(
                texts=[fact],
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
        Query both user memory and local documents using LangChain API.
        Returns a formatted context string.
        """
        if not query_text or not query_text.strip():
            return ""

        context_blocks = []

        # 1. Query User Memory using similarity_search_with_score
        try:
            mem_results = self.user_memory.similarity_search_with_score(
                query_text,
                k=n_results
            )
            valid_memories = []
            for doc, distance in mem_results:
                # Lower L2 distance is better. Limit to somewhat strict similarity (e.g. < 1.0)
                if distance < 1.0:
                    valid_memories.append(f"- {doc.page_content}")
            
            if valid_memories:
                context_blocks.append("Ingatan Masa Lalu tentang Pengguna:\n" + "\n".join(valid_memories))
        except Exception as e:
            print(f"[MemoryService] Error querying user memory: {e}")

        # 2. Query Documents (RAG) using similarity_search_with_score
        try:
            doc_results = self.documents.similarity_search_with_score(
                query_text,
                k=n_results
            )
            valid_docs = []
            for doc, distance in doc_results:
                if distance < 1.2:  # slightly more lenient for document chunks
                    source_name = doc.metadata.get('source', 'Unknown')
                    valid_docs.append(f"[Sumber: {source_name}]\n{doc.page_content}")
            
            if valid_docs:
                context_blocks.append("Konteks dari Dokumen RAG:\n" + "\n\n".join(valid_docs))
        except Exception as e:
            print(f"[MemoryService] Error querying documents: {e}")

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

                # Basic chunking
                chunks = self._chunk_text(text_content, chunk_size=500)
                
                if chunks:
                    ids = [f"{filename}_{i}" for i in range(len(chunks))]
                    metadatas = [{"source": filename} for _ in chunks]
                    
                    # LangChain Chroma uses add_texts
                    self.documents.add_texts(
                        texts=chunks,
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

