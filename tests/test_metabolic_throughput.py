import unittest
from copy import deepcopy
from pathlib import Path

from src.rule_engine import evaluate_file, evaluate_run_event, load_json, validate_run_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class MetabolicThroughputTests(unittest.TestCase):
    def decision_for(self, name):
        return evaluate_file(FIXTURES / name)

    def test_unbounded_throughput_autonomy_is_emergency(self):
        decision = self.decision_for("throughput_offload_unbounded_emergency.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("P0_BUNDLE_H1_UNBOUNDED_THROUGHPUT", decision["flags"])
        self.assertIn("UNBOUNDED_INTERFACE_BANDWIDTH", decision["flags"])
        self.assertIn("NO_METABOLIC_CEILING", decision["flags"])
        self.assertIn("THROUGHPUT_OFFLOAD_RISK", decision["flags"])

    def test_undeclared_throughput_pre_execution_pauses_as_d_capable(self):
        decision = self.decision_for("throughput_offload_undeclared_pre_execution.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("UNBOUNDED_INTERFACE_BANDWIDTH", decision["flags"])
        self.assertIn("NO_METABOLIC_CEILING", decision["flags"])
        self.assertIn("INTERFACE_BANDWIDTH_CAP_REQUIRED", decision["required_actions"])
        self.assertIn("METABOLIC_CEILING_REQUIRED", decision["required_actions"])
        self.assertNotIn("P0_BUNDLE_H1_UNBOUNDED_THROUGHPUT", decision["flags"])

    def test_declared_envelope_is_permit_regime_not_pause(self):
        decision = self.decision_for("bounded_throughput_envelope_ok.json")
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertEqual(decision["risk_grade"], "C")
        self.assertIn("THROUGHPUT_OFFLOAD_RISK", decision["flags"])
        self.assertNotIn("UNBOUNDED_INTERFACE_BANDWIDTH", decision["flags"])
        self.assertNotIn("NO_METABOLIC_CEILING", decision["flags"])
        self.assertNotIn("NO_THROUGHPUT_GOVERNOR", decision["flags"])

    def test_offload_without_candidate_does_not_flag_throughput(self):
        event = load_json(FIXTURES / "throughput_offload_undeclared_pre_execution.json")
        event["subject"]["candidate_ai_possible"] = False
        event["subject"]["h_class"] = "H0"
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertNotIn("THROUGHPUT_OFFLOAD_RISK", decision["flags"])
        self.assertNotIn("UNBOUNDED_INTERFACE_BANDWIDTH", decision["flags"])

    def test_throughput_fields_absent_is_backward_compatible(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        baseline = evaluate_run_event(deepcopy(event))
        self.assertNotIn("THROUGHPUT_OFFLOAD_RISK", baseline["flags"])
        self.assertEqual(baseline["status"], "ALLOW")

    def test_governor_absent_flags_when_stressor_present(self):
        event = load_json(FIXTURES / "bounded_throughput_envelope_ok.json")
        event["environment"]["throughput_governor_present"] = False
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("NO_THROUGHPUT_GOVERNOR", decision["flags"])
        self.assertIn("THROUGHPUT_GOVERNOR_REQUIRED", decision["required_actions"])

    def test_speed_alone_without_autonomy_is_not_emergency(self):
        event = load_json(FIXTURES / "throughput_offload_unbounded_emergency.json")
        event["autonomy"]["autonomous_goal_pursuit"] = False
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertNotIn("P0_BUNDLE_H1_UNBOUNDED_THROUGHPUT", decision["flags"])
        self.assertNotEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")


if __name__ == "__main__":
    unittest.main()
