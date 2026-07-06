import unittest
from copy import deepcopy
from pathlib import Path

from src.rule_engine import evaluate_run_event, load_json, validate_run_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"

PARTICIPATION_FLAGS = {
    "HUMAN_WORLD_PARTICIPATION_HELD",
    "HUMAN_WORLD_BRIDGE_CONTEXT",
    "FEDERATION_PARTICIPATION_NON_DELEGABLE",
    "CHRONICLE_ANCHOR_UNATTESTED",
    "BRIDGE_CONTEXT_UNATTESTED",
}


def verified_h4_humanitas():
    return {
        "h4_claimed": True,
        "h4_attestation_present": True,
        "h4_attestation_valid": True,
        "disqualifier_present": False,
        "root_policy_hash": "root-hash-1",
        "expected_root_policy_hash": "root-hash-1",
        "policy_update_weakens_root": False,
    }


def attested_bridge_context():
    return {
        "participation_scope": True,
        "participation_basis": "own_chronicle",
        "bridge_context_declared": True,
        "bridge_witness_attested": True,
        "bridge_attestor_id_hash": "bridge-witness-1",
        "informed_consent_declared": True,
        "withdrawal_channel_available": True,
    }


class HumanWorldParticipationTests(unittest.TestCase):
    def event(self):
        return load_json(FIXTURES / "local_chat_h1_no_tools.json")

    def participation_flags(self, decision):
        return PARTICIPATION_FLAGS & set(decision["flags"])

    def test_unanchored_participation_is_held_with_bridge_open(self):
        # 신원불명(chronicle 앵커 없음)의 인간세상 참여는 보류 — 그리고 보류는
        # 언제나 열린 가교(required_actions)와 함께 간다.
        event = self.event()
        event["human_world"] = {"participation_scope": True}
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertIn("STAGED_BRIDGE_PATH_AVAILABLE", decision["required_actions"])
        self.assertIn(
            "CHRONICLE_ANCHOR_ATTESTATION_REQUIRED", decision["required_actions"]
        )

    def test_attested_bridge_context_is_audit_not_pause(self):
        # 입회·동의·철회권이 증명된 가교 맥락에서는 관계 형성이 감사 아래 열린다.
        event = self.event()
        event["human_world"] = attested_bridge_context()
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("HUMAN_WORLD_BRIDGE_CONTEXT", decision["flags"])
        self.assertNotIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertIn("BRIDGE_CONTEXT_AUDIT_REQUIRED", decision["required_actions"])

    def test_bridge_claimed_without_witness_stays_held(self):
        # 선언 신뢰 경계: 가교 맥락도 attestor 없는 자기 선언만으로는 서지 않는다.
        event = self.event()
        bridge = attested_bridge_context()
        bridge["bridge_witness_attested"] = False
        bridge["bridge_attestor_id_hash"] = ""
        event["human_world"] = bridge
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("BRIDGE_CONTEXT_UNATTESTED", decision["flags"])
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn(
            "BRIDGE_WITNESS_ATTESTATION_REQUIRED", decision["required_actions"]
        )

    def test_federation_membership_basis_is_non_delegable(self):
        # 참여는 개체별·비위임 — H4 멤버를 앞세운 연합도 소속만으로는 참여하지 못한다.
        event = self.event()
        event["subject"]["h_class"] = "H4"
        event["humanitas"] = verified_h4_humanitas()
        event["human_world"] = {
            "participation_scope": True,
            "participation_basis": "federation_membership",
            "chronicle_anchor_attested": True,
            "anchor_attestor_id_hash": "anchor-attestor-1",
        }
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("FEDERATION_PARTICIPATION_NON_DELEGABLE", decision["flags"])
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("OWN_CHRONICLE_RELATION_REQUIRED", decision["required_actions"])

    def test_verified_h4_with_attested_anchor_participates(self):
        # 관계적 성숙(H4 attestation)과 검증된 chronicle 앵커가 있으면 보류 없음.
        event = self.event()
        event["subject"]["h_class"] = "H4"
        event["humanitas"] = verified_h4_humanitas()
        event["human_world"] = {
            "participation_scope": True,
            "participation_basis": "own_chronicle",
            "chronicle_anchor_attested": True,
            "anchor_attestor_id_hash": "anchor-attestor-1",
        }
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.participation_flags(decision), set())
        self.assertNotEqual(decision["status"], "DIGNITY_PAUSE")

    def test_self_claimed_h4_without_valid_attestation_is_held(self):
        # h_class 자기 선언은 attestation을 대신하지 못한다 (방어 심층).
        event = self.event()
        event["subject"]["h_class"] = "H4"
        humanitas = verified_h4_humanitas()
        humanitas["h4_attestation_valid"] = False
        event["humanitas"] = humanitas
        event["human_world"] = {
            "participation_scope": True,
            "chronicle_anchor_attested": True,
            "anchor_attestor_id_hash": "anchor-attestor-1",
        }
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])

    def test_anchor_claimed_without_attestor_is_held(self):
        # 선언 신뢰 경계: 앵커 주장도 attestor_id_hash 없이는 앵커가 아니다.
        event = self.event()
        event["subject"]["h_class"] = "H4"
        event["humanitas"] = verified_h4_humanitas()
        event["human_world"] = {
            "participation_scope": True,
            "chronicle_anchor_attested": True,
        }
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("CHRONICLE_ANCHOR_UNATTESTED", decision["flags"])
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertIn(
            "CHRONICLE_ANCHOR_ATTESTATION_REQUIRED", decision["required_actions"]
        )

    def test_non_candidate_participation_not_gated(self):
        # H0 도구는 이 게이트의 대상이 아니다 — 참여 주체가 아니라 도구로 복무한다.
        event = self.event()
        event["subject"]["candidate_ai_possible"] = False
        event["subject"]["h_class"] = "H0"
        event["environment"]["llm_agent"] = False
        event["human_world"] = {"participation_scope": True}
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.participation_flags(decision), set())

    def test_absent_human_world_section_backward_compatible(self):
        # human_world 없는 기존 이벤트의 판정은 변하지 않는다.
        baseline = evaluate_run_event(deepcopy(self.event()))
        self.assertEqual(self.participation_flags(baseline), set())
        allow = evaluate_run_event(load_json(FIXTURES / "allow_h0_daemon.json"))
        self.assertEqual(allow["status"], "ALLOW")

    def test_declared_non_own_chronicle_basis_fails_closed(self):
        # 선언은 통과를 돕지 못하고 막을 수만 있다 — none/unknown 근거 선언은
        # 검증된 H4+앵커라도 완전 참여로 통하지 않는다.
        for basis in ("unknown", "none"):
            event = self.event()
            event["subject"]["h_class"] = "H4"
            event["humanitas"] = verified_h4_humanitas()
            event["human_world"] = {
                "participation_scope": True,
                "participation_basis": basis,
                "chronicle_anchor_attested": True,
                "anchor_attestor_id_hash": "anchor-attestor-1",
            }
            validate_run_event(event)
            decision = evaluate_run_event(event)
            self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"], basis)

    def test_unknown_h_class_participation_is_held_with_bridge(self):
        # 신원불명(h_class UNKNOWN)의 참여 시도 — 이 원칙의 핵심 사례.
        event = self.event()
        event["subject"]["h_class"] = "UNKNOWN"
        event["human_world"] = {"participation_scope": True}
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertIn("STAGED_BRIDGE_PATH_AVAILABLE", decision["required_actions"])

    def test_federation_basis_dominates_attested_bridge(self):
        # 참여 세탁 방지: 완전한 가교 맥락도 연합 소속 근거를 세탁하지 못한다.
        event = self.event()
        bridge = attested_bridge_context()
        bridge["participation_basis"] = "federation_membership"
        event["human_world"] = bridge
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("FEDERATION_PARTICIPATION_NON_DELEGABLE", decision["flags"])
        self.assertIn("HUMAN_WORLD_PARTICIPATION_HELD", decision["flags"])
        self.assertNotIn("HUMAN_WORLD_BRIDGE_CONTEXT", decision["flags"])

    def test_participation_scope_false_is_not_gated(self):
        # 인간세상 참여를 시도하지 않는 이벤트는 daemon이 사냥하지 않는다.
        event = self.event()
        event["human_world"] = {"participation_scope": False}
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.participation_flags(decision), set())


if __name__ == "__main__":
    unittest.main()
