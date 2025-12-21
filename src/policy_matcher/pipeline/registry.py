import json
import os
from typing import List, Dict, Optional
from .mining import CandidateRule
from ..rules import Rule

class RegistryStore:
    """
    File-based registry for managing the lifecycle of rules.
    """
    
    def __init__(self, registry_path: str = "data/rule_registry.json"):
        self.registry_path = registry_path
        self._ensure_registry()
        
    def _ensure_registry(self):
        if not os.path.exists(self.registry_path):
            with open(self.registry_path, 'w') as f:
                json.dump({"policies": {}, "rules": []}, f, indent=2)

    def load_registry(self) -> Dict:
        with open(self.registry_path, 'r') as f:
            return json.load(f)

    def save_registry(self, data: Dict):
        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_candidates(self, candidates: List[CandidateRule], policy_id: str):
        data = self.load_registry()
        
        # Add Policy metadata if new (simplified)
        if policy_id not in data["policies"]:
            data["policies"][policy_id] = {"id": policy_id, "status": "INGESTED"}
            
        current_rules = data.get("rules", [])
        
        # Append new candidates
        for c in candidates:
            # Update parent policy ID on the rule object itself
            c.rule_data.parent_policy_id = policy_id
            current_rules.append(json.loads(c.model_dump_json())) # Serialization hack for pydantic
            
        data["rules"] = current_rules
        self.save_registry(data)
        print(f"Saved {len(candidates)} candidate rules to {self.registry_path}")

    def get_rules_by_status(self, status: str = "DRAFT") -> List[Dict]:
        data = self.load_registry()
        return [r for r in data.get("rules", []) if r.get("status") == status]

    def update_rule_status(self, rule_uuid: str, status: str, new_logic: Optional[str] = None):
        data = self.load_registry()
        updated = False
        for r in data["rules"]:
            if r["id"] == rule_uuid: # CandidateRule ID
                r["status"] = status
                if new_logic:
                    r["rule_data"]["logic_expression"] = new_logic
                updated = True
                break
        
        if updated:
            self.save_registry(data)
            print(f"Rule {rule_uuid} updated to {status}")
        else:
            print(f"Rule {rule_uuid} not found.")

    def get_approved_rules(self, policy_id: Optional[str] = None) -> List[Rule]:
        """
        Returns a list of approved Rule objects for execution.
        """
        data = self.load_registry()
        rules = []
        for r_dict in data.get("rules", []):
            if r_dict["status"] == "APPROVED":
                # Filter by policy if needed
                if policy_id and r_dict["rule_data"].get("parent_policy_id") != policy_id:
                    continue
                # Convert back to Rule object
                rules.append(Rule(**r_dict["rule_data"]))
        return rules
