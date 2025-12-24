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

from ..llm_utils import LLMInterface, MockLLM

class RuleMiner:
    """
    Mines candidate rules from text chunks using heuristics/ML.
    """
    def __init__(self, llm: Optional[LLMInterface] = None):
        self.llm = llm or MockLLM()
    
    def mine_rules(self, chunks: List[Dict[str, Any]]) -> List[CandidateRule]:
        candidates = []
        
        for chunk in chunks:
            text = chunk["text"]
            chunk_id = chunk["id"]
            default_rule_type = chunk.get("metadata", {}).get("rule_type", "Eligibility")
            
            # Use LLM (or Mock) to extract rule structure
            extraction = self.llm.extract_rule(text)
            
            # Fallback if extraction is empty or error
            if not extraction:
                extraction = {
                    "rule_type": default_rule_type,
                    "conditions": [{"parameter": "manual_review", "operator": "equals", "value": True}],
                    "description": text[:100] + "..."
                }

            candidate = CandidateRule(
                source_chunk_id=chunk_id,
                source_text=text,
                confidence=0.75, # could come from LLM later
                status="DRAFT",
                rule_data=Rule(
                    id=f"R-{uuid.uuid4().hex[:8]}", 
                    type=extraction.get("rule_type", default_rule_type),
                    conditions=extraction.get("conditions", []),
                    description=extraction.get("description", text[:100] + "..."), 
                    required=True, 
                    parent_policy_id="UNKNOWN" 
                )
            )
            candidates.append(candidate)
            
        return candidates
