from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMInterface(ABC):
    @abstractmethod
    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        pass

class MockLLM(LLMInterface):
    """Mock implementation for testing flow without API costs."""
    
    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        return (
            f"Explanation (MOCKED): The request was {decision.get('decision')} because "
            f"{len(decision.get('failed_rules', []))} rules failed. "
            f"Patient Data: {patient_context}"
        )

# TODO: Implement OpenAI/Azure client here
class OpenAILLM(LLMInterface):
    def generate_explanation(self, decision: dict, rules: list, patient_context: dict) -> str:
        # Placeholder for real integration
        return "Real LLM explanation would go here."
