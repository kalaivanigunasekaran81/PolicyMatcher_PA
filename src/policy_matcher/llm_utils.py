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
            return {
                "rule_type": "Eligibility",
                "conditions": [{
                    "parameter": "manual_review",
                    "operator": "equals",
                    "value": True
                }], 
                "description": f"Extraction failed: {text[:50]}..."
            }

class HuggingFaceLLM(LLMInterface):
    """
    Wrapper for HuggingFace local models (BioGPT, ClinicalBERT).
    Supports two modes:
    1. 'qa' (default): Extractive QA using ClinicalBERT.
    2. 'generation': Text generation using BioGPT.
    """
    def __init__(self, model_name: str = "emilyalsentzer/Bio_ClinicalBERT", mode: str = "qa"):
        self.mode = mode
        self.model_name = model_name
        
        try:
            from transformers import pipeline
            if mode == "qa":
                # Use a QA-vetted model if possible, or default to the user choice
                # ClinicalBERT is an encoder, needs a QA head fine-tuned. 
                # For this demo, we use a generic medical QA or squad-tuned ClinicalBERT if available,
                # otherwise we use the user's specific extraction model. 
                # 'deepset/bert-base-cased-squad2' is a good generic one, but user asked for ClinicalBERT.
                # standard ClinicalBERT doesn't have a QA head. 
                # We will use 'emilyalsentzer/Bio_ClinicalBERT' as base, but it might warn about missing head.
                # Better alternative for QA is 'monitoring-artist/emilyalsentzer-Bio_ClinicalBERT-squad2' if it exists,
                # or just use a robust QA model.
                # For safety/speed, we'll try to load it as a QA pipeline.
                self.pipe = pipeline("question-answering", model=model_name)
            else:
                self.pipe = pipeline("text-generation", model=model_name)
        except Exception as e:
            print(f"Error loading HuggingFace model {model_name}: {e}")
            self.pipe = None

    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        if not self.pipe or self.mode == "qa":
            return "Explanation generation requires a generative model (mode='generation')."
        
        prompt = f"Explain decision {decision.get('decision')} for patient {patient_context}."
        try:
            output = self.pipe(prompt, max_length=150)[0]['generated_text']
            return output
        except Exception as e:
            return f"Error: {e}"

    def extract_rule(self, text: str) -> Dict[str, Any]:
        if not self.pipe:
            return {}

        if self.mode == "qa":
            return self._extract_via_qa(text)
        else:
            return self._extract_via_generation(text)

    def _extract_via_qa(self, text: str) -> Dict[str, Any]:
        """
        Uses ClinicalBERT (QA) to extract specific entities by asking questions.
        """
        conditions = []
        
        # 1. Ask about Age
        try:
            ans = self.pipe(question="What is the minimum age required?", context=text)
            if ans['score'] > 0.1 and "year" in ans['answer']:
                import re
                nums = re.findall(r'\d+', ans['answer'])
                if nums:
                    conditions.append({
                        "parameter": "age",
                        "operator": "gte",
                        "value": int(nums[0])
                    })
        except:
            pass

        # 2. Ask about Diagnosis
        try:
            ans = self.pipe(question="What diagnosis is required?", context=text)
            if ans['score'] > 0.1:
                conditions.append({
                    "parameter": "diagnosis_code",
                    "operator": "contains",
                    "value": ans['answer'] # This will be the text span, e.g., "type 2 diabetes"
                })
        except:
            pass

        if not conditions:
             conditions.append({"parameter": "manual_review", "operator": "equals", "value": True})

        return {
            "rule_type": "Medical Necessity" if "MEDICALLY NECESSARY" in text else "Eligibility",
            "conditions": conditions,
            "description": text[:100] + "..."
        }

    def _extract_via_generation(self, text: str) -> Dict[str, Any]:
        """
        Uses BioGPT to generate the JSON structure (experimental).
        """
        prompt = f"Extract rule JSON from: {text}"
        try:
             # Very simple generation attempt
             output = self.pipe(prompt, max_new_tokens=100)[0]['generated_text']
             # Parsing would be complex here without a strong instruct model
             # For now, return a placeholder based on generation
             return {
                 "rule_type": "Eligibility",
                 "conditions": [{"parameter": "manual_review", "operator": "equals", "value": True}],
                 "description": "BioGPT Extraction: " + output[:50]
             }
        except:
            return {}
