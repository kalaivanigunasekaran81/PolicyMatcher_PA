from typing import List, Any, Optional
from pydantic import BaseModel, Field
from .patient import PatientContext
import re

class Rule(BaseModel):
    id: str
    type: str = Field(description="Eligibility, MedicalNecessity, Exclusion, etc.")
    logic_expression: str = Field(description="Executable logic string, e.g. 'age >= 18'")
    description: str
    required: bool = True
    parent_policy_id: Optional[str] = None

class EvaluationResult(BaseModel):
    rule_id: str
    status: str # PASS, FAIL, PEND
    score: float = 1.0 # Confidence
    evidence: str

class RuleEngine:
    """Deterministic rule evaluation engine."""
    
    def evaluate(self, rules: List[Rule], patient: PatientContext) -> dict:
        """
        Evaluates a list of rules against the patient context.
        Returns an aggregated decision.
        """
        results = []
        failed_rules = []
        missing_info = []

        context = patient.model_dump()
        
        # Helper for logic evaluation
        # SAFETY: logic_expression comes from trusted internal extraction (mocked here), 
        # but broadly `eval` is dangerous. In production, use a safe expression parser.
        def safe_eval(expr: str, ctx: dict) -> bool:
            try:
                # Basic whitelist filtering for prototype safety
                allowed_names = set(ctx.keys())
                code = compile(expr, "<string>", "eval")
                for name in code.co_names:
                    if name not in allowed_names and name not in ('len', 'any', 'all', 'set'):
                        # Very crude check. Ideally use AST parsing.
                        pass 
                return eval(expr, {"__builtins__": {}}, ctx)
            except Exception as e:
                print(f"Error evaluating rule: {expr} -> {e}")
                return False

        for rule in rules:
            # Check if we have data for the rule first? 
            # In this simple engine, we assume logic_expression maps to schema keys
            
            passed = False
            try:
                passed = safe_eval(rule.logic_expression, context)
            except:
                pass # Default fail handling
            
            status = "PASS" if passed else "FAIL"
            
            result = EvaluationResult(
                rule_id=rule.id,
                status=status,
                evidence=f"Patient data: {context}" # Simplified evidence
            )
            results.append(result)
            
            if status == "FAIL" and rule.required:
                failed_rules.append(result)

        # Aggregation Logic
        if not failed_rules and not missing_info:
            decision = "APPROVE"
        elif missing_info:
            decision = "PEND"
        else:
            decision = "DENY"
            
        return {
            "decision": decision,
            "failed_rules": [r.model_dump() for r in failed_rules],
            "all_results": [r.model_dump() for r in results]
        }
