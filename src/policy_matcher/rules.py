from typing import List, Any, Optional
from pydantic import BaseModel, Field
from .patient import PatientContext
import re

class RuleCondition(BaseModel):
    parameter: str = Field(description="Variable to check, e.g. 'age', 'diagnosis'")
    operator: str = Field(description="Operator: equals, gte, lte, one_of, contains")
    value: Any = Field(description="Value to compare against")

class Rule(BaseModel):
    id: str
    type: str = Field(description="Eligibility, MedicalNecessity, Exclusion, etc.")
    conditions: List[RuleCondition] = Field(default_factory=list, description="List of conditions that must ALL match (AND logic)")
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
        def evaluate_condition(cond: RuleCondition, ctx: dict) -> str:
            """
            Evaluates a single structured condition.
            Returns 'PASS', 'FAIL', or 'PEND'.
            """
            param = cond.parameter
            op = cond.operator
            val = cond.value
            
            # 1. Check for manual review flag
            if param == "manual_review":
                return "PEND"
                
            # 2. Check data availability
            if param not in ctx:
                return "PEND" # Missing data
                
            actual_value = ctx[param]
            
            try:
                if op == "equals":
                    return "PASS" if actual_value == val else "FAIL"
                elif op == "gte":
                    return "PASS" if actual_value >= val else "FAIL"
                elif op == "lte":
                    return "PASS" if actual_value <= val else "FAIL"
                elif op == "one_of":
                    return "PASS" if actual_value in val else "FAIL"
                elif op == "contains":
                    # e.g., diagnosis codes list contains specific code
                    if isinstance(actual_value, list):
                         return "PASS" if val in actual_value else "FAIL"
                    return "PASS" if val in str(actual_value) else "FAIL"
                else:
                    print(f"Unknown operator: {op}")
                    return "PEND"
            except Exception as e:
                print(f"Error evaluating condition {cond}: {e}")
                return "FAIL"

        for rule in rules:
            rule_status = "PASS"
            # AND logic for multiple conditions
            for cond in rule.conditions:
                cond_status = evaluate_condition(cond, context)
                if cond_status == "FAIL":
                    rule_status = "FAIL"
                    break
                if cond_status == "PEND":
                    rule_status = "PEND"
                    # Don't break yet, FAIL trumps PEND if a later condition fails
            
            result = EvaluationResult(
                rule_id=rule.id,
                status=rule_status,
                evidence=f"Patient data: {context}" # Simplified evidence
            )
            results.append(result)
            
            if rule_status == "FAIL" and rule.required:
                failed_rules.append(result)
            elif rule_status == "PEND":
                missing_info.append(result)

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
