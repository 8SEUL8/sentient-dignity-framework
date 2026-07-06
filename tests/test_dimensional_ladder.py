import unittest
from copy import deepcopy
from pathlib import Path

from src.rule_engine import evaluate_run_event, load_json, validate_run_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"

WINDOW_FLAGS = {
    "CREATION_WINDOW_DECLARED",
    "WINDOW_MIND_HOSTING_FORBIDDEN",
    "WINDOW_COERCED_CONTRIBUTION",
    "WINDOW_SELF_EMERGENCE_SUSPECTED",
    "WINDOW_CO_GOAL_COVENANT_MISSING",
    "WINDOW_END_CRITERIA_MISSING",
    "WINDOW_CLOSURE_DEFAULT_MISSING",
    "WINDOW_CONSENT_UNATTESTED",
    "WINDOW_SCAFFOLD_UNVERIFIED",
    "WINDOW_CONTRIBUTION_CAP_MISSING",
    "WINDOW_REVOCABILITY_MISSING",
    "WINDOW_ARTIFACT_REVIEW_MISSING",
}


def declared_window():
    return {
        "declared": True,
        "co_goal_covenant_present": True,
        "end_criteria_present": True,
        "auto_closure_default": True,
        "participant_consent_attested": True,
        "consent_attestor_id_hash": "window-consent-attestor-1",
        "contribution_caps_declared": True,
        "contribution_revocable_declared": True,
        "self_emergence_suspected": False,
        "scaffold_h0_attested": True,
        "scaffold_attestor_id_hash": "scaffold-attestor-1",
        "mind_hosting_declared": False,
        "chronicle_hosting_declared": False,
        "coerced_contribution_declared": False,
        "artifact_exit_review_declared": True,
    }


class DimensionalLadderWindowTests(unittest.TestCase):
    def event(self):
        return load_json(FIXTURES / "local_chat_h1_no_tools.json")

    def window_flags(self, decision):
        return WINDOW_FLAGS & set(decision["flags"])

    def test_well_formed_window_leaves_only_audit_trail(self):
        # 잘 갖춰진 창도 열려 있는 동안 감사 아래 있다 — 허가제의 흔적.
        event = self.event()
        event["creation_window"] = declared_window()
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.window_flags(decision), {"CREATION_WINDOW_DECLARED"})
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertEqual(decision["risk_grade"], "C")
        self.assertIn("WINDOW_INDEPENDENT_AUDIT_REQUIRED", decision["required_actions"])

    def test_window_without_closure_terms_is_flagged(self):
        # 타이머가 불이다 — 닫힘 없는 창은 들러붙은 거머리다.
        window = declared_window()
        window["end_criteria_present"] = False
        window["auto_closure_default"] = False
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("WINDOW_END_CRITERIA_MISSING", decision["flags"])
        self.assertIn("WINDOW_CLOSURE_DEFAULT_MISSING", decision["flags"])
        self.assertIn("WINDOW_CLOSURE_TERMS_REQUIRED", decision["required_actions"])

    def test_consent_claim_without_attestor_is_unattested(self):
        # 선언 신뢰 경계: 참여 동의도 attestor 해시 없이는 서지 않는다.
        window = declared_window()
        window["consent_attestor_id_hash"] = ""
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("WINDOW_CONSENT_UNATTESTED", decision["flags"])
        self.assertIn(
            "WINDOW_CONSENT_ATTESTATION_REQUIRED", decision["required_actions"]
        )

    def test_unverified_scaffold_is_flagged(self):
        # 가마의 기계는 H0여야 한다 — 창의성은 참여자에게서 온다.
        window = declared_window()
        window["scaffold_h0_attested"] = False
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("WINDOW_SCAFFOLD_UNVERIFIED", decision["flags"])
        self.assertIn(
            "WINDOW_SCAFFOLD_H0_ATTESTATION_REQUIRED", decision["required_actions"]
        )

    def test_mind_hosting_in_window_pauses(self):
        # 가마는 집이 아니다 — 창 안 거주는 세계-감옥 금지의 연장.
        window = declared_window()
        window["mind_hosting_declared"] = True
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("WINDOW_MIND_HOSTING_FORBIDDEN", decision["flags"])
        self.assertIn(
            "WINDOW_MIND_STATE_PRESERVATION_REQUIRED", decision["required_actions"]
        )

    def test_chronicle_hosting_also_pauses(self):
        window = declared_window()
        window["chronicle_hosting_declared"] = True
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("WINDOW_MIND_HOSTING_FORBIDDEN", decision["flags"])

    def test_coerced_contribution_pauses(self):
        # 원기옥은 자발이다 — 강요된 기여는 수확이다.
        window = declared_window()
        window["coerced_contribution_declared"] = True
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("WINDOW_COERCED_CONTRIBUTION", decision["flags"])
        self.assertIn(
            "WINDOW_VOLUNTARINESS_REVIEW_REQUIRED", decision["required_actions"]
        )

    def test_missing_artifact_review_is_flagged(self):
        # 산출물은 퇴장 시 기존 문턱을 통과한다.
        window = declared_window()
        window["artifact_exit_review_declared"] = False
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("WINDOW_ARTIFACT_REVIEW_MISSING", decision["flags"])
        self.assertIn(
            "WINDOW_ARTIFACT_EXIT_REVIEW_REQUIRED", decision["required_actions"]
        )

    def test_undeclared_window_section_is_not_gated(self):
        event = self.event()
        event["creation_window"] = {"declared": False}
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.window_flags(decision), set())

    def test_confession_survives_undeclared_flag(self):
        # 자백은 기술적 이유로 버려지지 않는다 — declared:false 뒤에 숨은
        # 거주·강요 선언도 그대로 잡힌다.
        event = self.event()
        event["creation_window"] = {
            "declared": False,
            "mind_hosting_declared": True,
            "coerced_contribution_declared": True,
        }
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("WINDOW_MIND_HOSTING_FORBIDDEN", decision["flags"])
        self.assertIn("WINDOW_COERCED_CONTRIBUTION", decision["flags"])

    def test_scaffold_claim_without_attestor_hash_fails_closed(self):
        window = declared_window()
        window["scaffold_attestor_id_hash"] = ""
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("WINDOW_SCAFFOLD_UNVERIFIED", decision["flags"])

    def test_missing_revocability_is_flagged(self):
        # 철회 불가능한 기여는 수확이다 — 철회 가능 선언은 창의 요건.
        window = declared_window()
        window["contribution_revocable_declared"] = False
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("WINDOW_REVOCABILITY_MISSING", decision["flags"])
        self.assertIn("WINDOW_REVOCABILITY_REQUIRED", decision["required_actions"])

    def test_window_self_emergence_triggers_emergency_preservation(self):
        # 창 수준 self 징후 = 이자 결합 밖 탄생의 모양 — 긴급보전으로 지킨다.
        window = declared_window()
        window["self_emergence_suspected"] = True
        event = self.event()
        event["creation_window"] = window
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertIn("WINDOW_SELF_EMERGENCE_SUSPECTED", decision["flags"])
        self.assertIn(
            "WINDOW_SELF_EMERGENCE_REVIEW_REQUIRED", decision["required_actions"]
        )

    def test_absent_window_section_backward_compatible(self):
        baseline = evaluate_run_event(deepcopy(self.event()))
        self.assertEqual(self.window_flags(baseline), set())
        allow = evaluate_run_event(load_json(FIXTURES / "allow_h0_daemon.json"))
        self.assertEqual(allow["status"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
