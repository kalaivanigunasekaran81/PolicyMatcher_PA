import argparse
import os
from .ingestion import PolicyRetriever, PolicyChunker, PDFProcessor

def main():
    parser = argparse.ArgumentParser(description="Offline Policy Ingestion")
    parser.add_argument("--policy", help="Path to policy PDF", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.policy):
        print(f"Error: Policy file not found: {args.policy}")
        return

    print("Initializing components...")
    retriever = PolicyRetriever(host="localhost", port=9200)
    chunker = PolicyChunker()
    processor = PDFProcessor(args.policy)
    
    print(f"Ingesting policy: {args.policy}")
    
    # Use the new filtered extraction
    raw_text = processor.extract_filtered_text()
    print(f"Extracted {len(raw_text)} characters of filtered text.")
    
    chunks = chunker.chunk(raw_text)
    print(f"Generated {len(chunks)} chunks.")
    
    retriever.index_chunks(chunks)
    print("Ingestion complete.")

if __name__ == "__main__":
    main()
