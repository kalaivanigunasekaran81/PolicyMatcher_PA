import sys
import json
from .registry import RegistryStore

import sys
import argparse
import json
from .registry import RegistryStore

def main():
    parser = argparse.ArgumentParser(description="Rule Review CLI")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve all DRAFT rules (Demo mode)")
    args = parser.parse_args()

    print("=== Rule Review CLI ===")
    registry = RegistryStore()
    draft_rules = registry.get_rules_by_status("DRAFT")
    
    if not draft_rules:
        print("No DRAFT rules found.")
        return

    print(f"Found {len(draft_rules)} rules to review.")
    
    if args.auto_approve:
        print("Auto-approving all rules...")
        for rule in draft_rules:
            registry.update_rule_status(rule['id'], "APPROVED")
        print("Done.")
        return
    
    for i, rule in enumerate(draft_rules):
        rule_data = rule["rule_data"]
        print(f"\n[{i+1}/{len(draft_rules)}] Reviewing Candidate {rule['id']}")
        print(f"Type: {rule_data['type']}")
        print(f"Source: \"{rule['source_text'][:200]}...\"")
        print(f"derived Logic: {rule_data['logic_expression']}")
        
        while True:
            choice = input("Action [A]pprove, [R]eject, [E]dit Logic, [S]kip: ").lower().strip()
            
            if choice == 'a':
                registry.update_rule_status(rule['id'], "APPROVED")
                break
            elif choice == 'r':
                registry.update_rule_status(rule['id'], "REJECTED")
                break
            elif choice == 'e':
                new_logic = input("Enter new logic expression: ")
                registry.update_rule_status(rule['id'], "APPROVED", new_logic=new_logic)
                break
            elif choice == 's':
                print("Skipped.")
                break
            else:
                print("Invalid choice.")

if __name__ == "__main__":
    main()
