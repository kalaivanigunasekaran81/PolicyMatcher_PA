import argparse
import os
from .pipeline.ingestion import SmartChunker, PDFProcessor
from .pipeline.mining import RuleMiner
from .pipeline.registry import RegistryStore
from .llm_utils import MockLLM, OpenAILLM, HuggingFaceLLM

def main():
    parser = argparse.ArgumentParser(description="Clinical Policy Processing Pipeline")
    parser.add_argument("--policy", help="Path to policy PDF", required=True)
    parser.add_argument("--model", 
                        choices=["mock", "openai", "clinicalbert", "biogpt"], 
                        default="mock",
                        help="LLM to use for extraction (default: mock)")
    args = parser.parse_args()

    if not os.path.exists(args.policy):
        print(f"Error: Policy file not found: {args.policy}")
        return

    # Select LLM
    print(f"Initializing Rule Extraction Model: {args.model.upper()}")
    if args.model == "openai":
        llm = OpenAILLM()
    elif args.model == "clinicalbert":
        # Using a QA-finetuned ClinicalBERT if available, or base
        llm = HuggingFaceLLM(model_name="emilyalsentzer/Bio_ClinicalBERT", mode="qa")
    elif args.model == "biogpt":
        llm = HuggingFaceLLM(model_name="microsoft/biogpt", mode="generation")
    else:
        llm = MockLLM()

    print("--- Step 1: Ingestion ---")
    processor = PDFProcessor(args.policy)
    
    # Metadata
    metadata = processor.extract_metadata()
    print(f"Metadata detected: {metadata}")
    
    # Text
    raw_text = processor.extract_filtered_text()
    print(f"Extracted {len(raw_text)} chars of Policy text.")
    
    print("\n--- Step 2: Smart Chunking ---")
    chunker = SmartChunker()
    chunks = chunker.chunk(raw_text)
    print(f"Generated {len(chunks)} chunks.")
    
    print("\n--- Step 3: Candidate Mining ---")
    miner = RuleMiner(llm=llm)
    candidates = miner.mine_rules(chunks)
    print(f"Mined {len(candidates)} candidate rules.")
    
    print("\n--- Step 4: Structuring & Registry ---")
    registry = RegistryStore()
    # Use policy filename or metadata as ID
    policy_id = metadata.get("policy_number") or os.path.basename(args.policy)
    
    registry.add_candidates(candidates, policy_id)
    print("Pipeline execution complete. Rules are in DRAFT status.")
    print("Run module `policy_matcher.pipeline.review` to approve rules.")

if __name__ == "__main__":
    main()
