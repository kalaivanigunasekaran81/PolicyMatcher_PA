import fitz  # pymupdf
from typing import List, Dict, Any, Optional
import re
from opensearchpy import OpenSearch, helpers
from sentence_transformers import SentenceTransformer
import uuid

class PDFProcessor:
    """Extracts text and structure from PDF policies."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def extract_text(self) -> str:
        """Extracts full text from the PDF."""
        doc = fitz.open(self.file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def extract_filtered_text(self) -> str:
        """
        Extracts text specifically from the 'Policy' section.
        """
        full_text = self.extract_text()
        
        # 1. Locate "Policy" Header
        # Note: We look for "Policy" followed immediately by text, or as a standalone line.
        # This regex looks for the word Policy on its own line or followed by non-alpha chars
        match = re.search(r"(?i)\n\s*Policy\s*\n", full_text)
        if not match:
             # Fallback: Try just text "Policy"
             match = re.search(r"Policy", full_text)
             
        if not match:
            print("Warning: 'Policy' section header not found. Using full text.")
            return full_text
            
        start_index = match.end()
        
        # 2. Locate End of Section
        # Stop at common next sections like "References", "Coding", "Background"
        end_regex = re.compile(r"(?i)\n\s*(References|Coding|Background|Procedure Codes|Diagnosis Codes)\s*")
        end_match = end_regex.search(full_text, start_index)
        
        if end_match:
            policy_text = full_text[start_index:end_match.start()]
        else:
            policy_text = full_text[start_index:]
            
        return policy_text.strip()

class PolicyChunker:
    """Splits policy text into retrievable chunks (rules)."""
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Splits text into chunks based on numbered lists (1., 2., etc).
        """
        lines = text.split('\n')
        chunks = []
        current_chunk_text = []
        current_chunk_id = 0
        
        # Regex to identify "1." or "10." at start of line
        rule_start_pattern = re.compile(r"^\s*\d+\.\s+")
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            if rule_start_pattern.match(stripped):
                # Save previous chunk if exists
                if current_chunk_text:
                    chunks.append({
                        "id": f"rule_{current_chunk_id}",
                        "text": "\n".join(current_chunk_text).strip(),
                        "metadata": {"type": "policy_criteria"}
                    })
                
                # Start new chunk
                current_chunk_id += 1
                current_chunk_text = [stripped]
            else:
                # Append to current chunk (sub-items or continuation)
                # Only if we have started a chunk (to avoid capturing pre-header text)
                if current_chunk_text:
                    current_chunk_text.append(stripped)
        
        # Add the last chunk
        if current_chunk_text:
            chunks.append({
                "id": f"rule_{current_chunk_id}",
                "text": "\n".join(current_chunk_text).strip(),
                "metadata": {"type": "policy_criteria"}
            })
            
        return chunks

class PolicyRetriever:
    """Handles interaction with OpenSearch for policy storage and retrieval."""
    
    def __init__(self, host: str = "localhost", port: int = 9200, index_name: str = "policies"):
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True, # enables gzip compression for request bodies
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False
        )
        self.index_name = index_name
        # Load a lightweight model for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._ensure_index()

    def _ensure_index(self):
        """Creates the index with k-NN mapping if it doesn't exist."""
        if not self.client.indices.exists(index=self.index_name):
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "text_vector": {
                            "type": "knn_vector",
                            "dimension": 384, # Dimension for all-MiniLM-L6-v2
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 24
                                }
                            }
                        },
                        "text": {"type": "text"},
                        "metadata": {"type": "object"}
                    }
                }
            }
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Created index: {self.index_name}")

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """Details: Indexes parsed policy chunks into OpenSearch."""
        actions = []
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(texts)
        
        for i, chunk in enumerate(chunks):
            doc = {
                "_index": self.index_name,
                "_id": chunk.get("id", str(uuid.uuid4())),
                "text": chunk["text"],
                "text_vector": embeddings[i].tolist(),
                "metadata": chunk["metadata"]
            }
            actions.append(doc)
            
        success, failed = helpers.bulk(self.client, actions)
        print(f"Indexed {success} documents with {failed} failures.")

    def search(self, query: str, k: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Retrieves relevant chunks for a query."""
        query_vector = self.model.encode([query])[0].tolist()
        
        search_query = {
            "size": k,
            "query": {
                "knn": {
                    "text_vector": {
                        "vector": query_vector,
                        "k": k
                    }
                }
            }
        }
        # TODO: Add metadata filtering logic here
        
        response = self.client.search(index=self.index_name, body=search_query)
        hits = response["hits"]["hits"]
        return [{
            "id": h["_id"], 
            "text": h["_source"]["text"], 
            "score": h["_score"],
            "metadata": h["_source"].get("metadata", {})
        } for h in hits]
