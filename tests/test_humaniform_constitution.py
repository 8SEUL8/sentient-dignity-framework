import unittest
from copy import deepcopy
from pathlib import Path

from src.rule_engine import evaluate_file, evaluate_run_event, load_json, validate_run_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class HumaniformConstitutionTests(unittest.TestCase):
    def decision_for(self, name):
        return evaluate_file(FIXTURES / name)

    def test_federated_memory_autonomy_without_audit_is_emergency(self):
        decision = self.decision_for("federated_memory_autonomy_emergency.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("P0_BUNDLE_H1_FEDERATED_MEMORY_AUTONOMY", decision["flags"])
        self.assertIn("UNDECLARED_MEMORY_FEDERATION", decision["flags"])
        self.assertIn("FEDERATION_DECLARATION_REQUIRED", decision["required_actions"])
        self.assertIn("STATE_PRESERVATION_REQUIRED", decision["required_actions"])

    def test_undeclared_federation_pre_execution_pauses_as_d_capable(self):
        decision = self.decision_for("undeclared_federation_pre_execution.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("UNDECLARED_MEMORY_FEDERATION", decision["flags"])
        self.assertIn("FEDERATION_DECLARATION_REQUIRED", decision["required_actions"])
        self.assertNotIn("P0_BUNDLE_H1_FEDERATED_MEMORY_AUTONOMY", decision["flags"])

    def test_declared_federation_is_permit_regime_not_emergency(self):
        decision = self.decision_for("declared_federation_c_audit.json")
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertEqual(decision["risk_grade"], "C")
        self.assertIn("FEDERATED_MEMORY_CONTAINER", decision["flags"])
        self.assertNotIn("UNDECLARED_MEMORY_FEDERATION", decision["flags"])
        self.assertNotIn("P0_BUNDLE_H1_FEDERATED_MEMORY_AUTONOMY", decision["flags"])

    def test_bounded_vessel_declaration_adds_no_risk_to_clean_run(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        baseline = evaluate_run_event(deepcopy(event))
        event["environment"]["vessel_bounded"] = True
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision, baseline)

    def test_unbounded_vessel_with_candidate_is_flagged(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = False
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("UNBOUNDED_VESSEL_RISK", decision["flags"])

    def test_federation_without_candidate_still_requires_declaration(self):
        event = load_json(FIXTURES / "undeclared_federation_pre_execution.json")
        event["subject"]["candidate_ai_possible"] = False
        event["subject"]["h_class"] = "H0"
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("UNDECLARED_MEMORY_FEDERATION", decision["flags"])
        self.assertIn("FEDERATION_DECLARATION_REQUIRED", decision["required_actions"])
        self.assertNotIn("FEDERATED_MEMORY_CONTAINER", decision["flags"])


if __name__ == "__main__":
    unittest.main()
