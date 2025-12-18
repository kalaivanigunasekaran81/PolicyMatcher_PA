import argparse
import json
import os
from .ingestion import PolicyRetriever
from .patient import normalize_features
from .rules import RuleEngine, Rule
from .llm_utils import MockLLM

def main():
    parser = argparse.ArgumentParser(description="PA Decision Support System")
    parser.add_argument("--policy", help="Path to policy PDF", default="data/sample_policy.pdf")
    parser.add_argument("--patient", help="Path to patient JSON", default="data/sample_patient.json")
    parser.add_argument("--demo", action="store_true", help="Run with demo data")
    args = parser.parse_args()

    # 1. Setup / Ingestion
    # 1. Setup
    print("Initializing components...")
    retriever = PolicyRetriever(host="localhost", port=9200)

    # Note: Ingestion is now handled by run_ingestion.py (offline).
    # ensure we have an index available for search logic later.
 

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

    # 3. Retrieve Rules (Simulated Extraction)
    # Ideally: Retrieve text chunks -> LLM extracts Rules -> Engine Eval
    # Prototype shortcut: We will define HARDCODED rules that 'would have been' extracted 
    # from a Knee Arthroplasty policy for the demo, to prove the ENGINE works.
    
    print("Retrieving relevant rules...")
    # retrieval_results = retriever.search("Eligibility for Knee Arthroplasty")
    # For the purpose of the PROTOTYPE, we manually construct the 'Extracted' rules 
    # as if the LLM parsed them from the text.
    
    rules = [
        Rule(
            id="R-EL-01",
            type="Eligibility",
            logic_expression="age >= 18",
            description="Patient must be 18 years or older",
            required=True
        ),
        Rule(
            id="R-MN-01",
            type="MedicalNecessity",
            logic_expression="'M17.11' in diagnosis_codes",
            description="Diagnosis must be Osteoarthritis of knee",
            required=True
        )
    ]
    
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
