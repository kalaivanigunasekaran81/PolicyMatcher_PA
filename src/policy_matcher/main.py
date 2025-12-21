import argparse
import json
import os
from .pipeline.indexing import RuleIndexer
from .patient import normalize_features
from .rules import RuleEngine, Rule
from .llm_utils import MockLLM

def main():
    parser = argparse.ArgumentParser(description="PA Decision Support System")
    parser.add_argument("--policy", help="Path to policy PDF", default="data/sample_policy.pdf")
    parser.add_argument("--patient", help="Path to patient JSON", default="data/sample_patient.json")
    parser.add_argument("--demo", action="store_true", help="Run with demo data")
    args = parser.parse_args()

    # 1. Setup
    print("Initializing components...")
    # Using the new RuleIndexer
    indexer = RuleIndexer(index_name="clinical_rules")

    # 2. Patient Data
    if args.demo and not os.path.exists(args.patient):
        raw_patient = {
            "age": 17, # Matches rule failure case
            "gender": "M",
            "diagnosis_codes": ["M17.11"],
            "procedure_codes": ["27447"],
            "prior_treatments": []
        }
    else:
        with open(args.patient, 'r') as f:
            raw_patient = json.load(f)
            
    patient = normalize_features(raw_patient)
    print(f"Patient normalized: {patient}")

    # 3. Retrieve Rules (Dynamic)
    print("Retrieving relevant rules...")
    
    # In a real scenario, we'd search for rules specific to the procedure
    # For this demo, we want to run ALL rules we just ingested, or a broad search
    # query = f"Rules for {patient.procedure_codes[0]}"  # Too specific if rules don't mention procedure code explicitly
    query = "diabetes eligibility medical necessity" # Broad search to pull back our test rules
    
    rules_data = indexer.search(query, k=50)
    print(f"Retrieved {len(rules_data)} potentially relevant rules.")
    
    rules = []
    for r_data in rules_data:
        # Convert dict back to Rule object
        # Note: RuleIndexer.search returns dicts with 'id', 'logic', 'description', 'type'
        # We need to reconstruct the Rule object. 
        # CAUTION: The Rule model expects 'logic_expression', search result has 'logic'
        rules.append(Rule(
            id=r_data["id"],
            type=r_data["type"],
            logic_expression=r_data["logic"],
            description=r_data["description"],
            required=True, # Defaulting to True for now as metadata might not be full
            parent_policy_id="unknown"
        ))
    
    # 4. Evaluation
    print("Evaluating rules...")
    engine = RuleEngine()
    result = engine.evaluate(rules, patient)
    
    # 5. LLM Explanation
    llm = MockLLM()
    explanation = llm.generate_explanation(result, rules, patient.model_dump())
    
    # 6. Final Output
    final_output = {
        "decision": result["decision"],
        "reason": explanation,
        "details": result
    }
    
    print(json.dumps(final_output, indent=2))

if __name__ == "__main__":
    main()
