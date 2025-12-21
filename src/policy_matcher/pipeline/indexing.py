from opensearchpy import OpenSearch, helpers
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from ..rules import Rule

class RuleIndexer:
    """Handles interaction with OpenSearch for Rule storage and retrieval."""
    
    def __init__(self, host: str = "localhost", port: int = 9200, index_name: str = "clinical_rules"):
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False
        )
        self.index_name = index_name
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
                            "dimension": 384,
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
                        "description": {"type": "text"},
                        "logic": {"type": "text"},
                        "rule_type": {"type": "keyword"},
                        "policy_id": {"type": "keyword"},
                        "rule_id": {"type": "keyword"}
                    }
                }
            }
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Created index: {self.index_name}")

    def index_rules(self, rules: List[Rule]):
        """Indexes approved Rule objects."""
        actions = []
        # Encode descriptions as the primary search vector
        texts = [r.description for r in rules]
        if not texts:
            print("No rules to index.")
            return

        embeddings = self.model.encode(texts)
        
        for i, rule in enumerate(rules):
            doc = {
                "_index": self.index_name,
                "_id": rule.id,
                "description": rule.description,
                "text_vector": embeddings[i].tolist(),
                "logic": rule.logic_expression,
                "rule_type": rule.type,
                "policy_id": rule.parent_policy_id,
                "rule_id": rule.id,
                "metadata": {
                    "required": rule.required
                }
            }
            actions.append(doc)
            
        success, failed = helpers.bulk(self.client, actions)
        print(f"Indexed {success} rules with {failed} failures.")

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieves relevant rules."""
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
        
        response = self.client.search(index=self.index_name, body=search_query)
        hits = response["hits"]["hits"]
        return [{
            "id": h["_source"]["rule_id"],
            "description": h["_source"]["description"],
            "score": h["_score"],
            "logic": h["_source"]["logic"],
            "type": h["_source"]["rule_type"]
        } for h in hits]
