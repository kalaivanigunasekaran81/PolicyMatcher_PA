from .pipeline.registry import RegistryStore
from .pipeline.indexing import RuleIndexer

def main():
    print("=== Rule Indexing Service ===")
    
    # 1. Load Approved Rules
    registry = RegistryStore()
    rules = registry.get_approved_rules()
    
    if not rules:
        print("No APPROVED rules found in registry. Please run review first.")
        return
        
    print(f"Loaded {len(rules)} approved rules.")
    
    # 2. Index
    indexer = RuleIndexer(index_name="clinical_rules")
    indexer.index_rules(rules)
    
    print("Indexing complete.")

if __name__ == "__main__":
    main()
