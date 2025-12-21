from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import uuid
from ..rules import Rule

class CandidateRule(BaseModel):
    """
    Represents a potential rule extracted from the text, pending review.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_chunk_id: str
    source_text: str
    confidence: float
    status: str = "DRAFT" # DRAFT, APPROVED, REJECTED
    
    # The inferred rule structure
    rule_data: Rule

class RuleMiner:
    """
    Mines candidate rules from text chunks using heuristics/ML.
    """
    
    def mine_rules(self, chunks: List[Dict[str, Any]]) -> List[CandidateRule]:
        candidates = []
        
        for chunk in chunks:
            text = chunk["text"]
            chunk_id = chunk["id"]
            rule_type = chunk.get("metadata", {}).get("rule_type", "Eligibility")
            
            # Simple Heuristic Mining for Prototype
            # In a real system, this would use BioBERT / LLM
            
            logic = "manual_review_required"
            # Demo Heuristic: Detect Age
            if "years of age or older" in text:
                import re
                age_match = re.search(r"(\d+)\s+years", text)
                if age_match:
                    age = age_match.group(1)
                    logic = f"age >= {age}"
            
            # Demo Heuristic: Detect Diagnosis
            if "diagnosis of" in text:
                 logic = "diagnosis_check_required"

            candidate = CandidateRule(
                source_chunk_id=chunk_id,
                source_text=text,
                confidence=0.75, # Mock confidence
                status="DRAFT",
                rule_data=Rule(
                    id=f"R-{uuid.uuid4().hex[:8]}", # Temporary ID
                    type=rule_type,
                    logic_expression=logic,
                    description=text[:100] + "...", # Truncate for description
                    required=True, # Default
                    parent_policy_id="UNKNOWN" # To be filled by context
                )
            )
            candidates.append(candidate)
            
        return candidates
