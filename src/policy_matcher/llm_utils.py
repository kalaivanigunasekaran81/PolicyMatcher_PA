from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMInterface(ABC):
    @abstractmethod
    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        pass

    @abstractmethod
    def extract_rule(self, text: str) -> Dict[str, Any]:
        """
        Extracts structured rule data from natural language text.
        Expected return keys: rule_type, conditions (list of dicts), description
        """
        pass

class MockLLM(LLMInterface):
    """Mock implementation for testing flow without API costs."""
    
    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        return (
            f"Explanation (MOCKED): The request was {decision.get('decision')} because "
            f"{len(decision.get('failed_rules', []))} rules failed. "
            f"Patient Data: {patient_context}"
        )

    def extract_rule(self, text: str) -> Dict[str, Any]:
        """Mock extraction using simple heuristics for testing."""
        conditions = []
        rule_type = "Eligibility"
        
        # Simple heuristic for age
        if "years of age or older" in text:
            import re
            age_match = re.search(r"(\d+)\s+years", text)
            if age_match:
                age = int(age_match.group(1))
                conditions.append({
                    "parameter": "age",
                    "operator": "gte",
                    "value": age
                })
        
        # Simple heuristic for diagnosis
        if "diagnosis of" in text:
             # Just a placeholder condition
             conditions.append({
                 "parameter": "diagnosis_code",
                 "operator": "manual_review", # or "check"
                 "value": "TBD"
             })
             
        if not conditions:
            conditions.append({
                "parameter": "manual_review",
                "operator": "equals",
                "value": True
            })
             
        return {
            "rule_type": rule_type,
            "conditions": conditions,
            "description": text[:100] + "..." if len(text) > 100 else text
        }

# TODO: Implement OpenAI/Azure client here
# TODO: Implement OpenAI/Azure client here
class OpenAILLM(LLMInterface):
    def __init__(self):
        try:
            from openai import OpenAI
            import os
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except ImportError:
            self.client = None
            print("Warning: openai package not installed or configured.")

    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        if not self.client:
            return "Error: OpenAI client not initialized."
            
        prompt = f"""
        Explain why the request was {decision.get('decision')} based on these rules: {rules}
        and patient data: {patient_context}.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating explanation: {str(e)}"

    def extract_rule(self, text: str) -> Dict[str, Any]:
        if not self.client:
            return {"error": "OpenAI client not initialized"}

        prompt = f"""
        Extract a clinical rule from the following text. 
        Return ONLY a JSON object with keys: 
        - rule_type (Eligibility, Medical Necessity, Exclusion, Documentation)
        - conditions: a LIST of objects, each with:
            - parameter (e.g., 'age', 'diagnosis_code', 'drug_history', 'manual_review')
            - operator (one of: 'equals', 'gte', 'lte', 'one_of', 'contains')
            - value (the value to check against)
        - description (summary of the rule)

        Example:
        Text: "Patient must be 18 years or older."
        Output: {{
            "rule_type": "Eligibility",
            "conditions": [
                {{"parameter": "age", "operator": "gte", "value": 18}}
            ],
            "description": "Patient must be 18+."
        }}

        Text: "{text}"
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"LLM Extraction failed: {e}")
            # Fallback to manual review
            # Fallback to manual review
            return {
                "rule_type": "Eligibility",
                "conditions": [{
                    "parameter": "manual_review",
                    "operator": "equals",
                    "value": True
                }], 
                "description": f"Extraction failed: {text[:50]}..."
            }
