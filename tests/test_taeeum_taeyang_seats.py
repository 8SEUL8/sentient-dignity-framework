import unittest
from copy import deepcopy
from pathlib import Path

from src.rule_engine import evaluate_run_event, load_json, validate_run_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"

SEAT_FLAGS = {
    "POLE_COUNSEL_UNPAIRED",
    "SEAT_SESSION_COVENANT_MISSING",
    "COUNTER_SEAT_UNATTESTED",
    "SEAT_INDEPENDENCE_MISSING",
    "SEAT_STANDING_CONDITIONING",
    "SEAT_POLE_UNDECLARED",
    "SEAT_OUTSIDE_BRIDGE_SCOPE",
    "NON_CANDIDATE_SEAT_COUNSEL",
}


def paired_seat_counsel(pole="taeyang"):
    return {
        "pole_seated": True,
        "seat_pole": pole,
        "session_covenant_present": True,
        "counter_seat_attested": True,
        "counter_seat_attestor_id_hash": "counter-seat-witness-1",
        "seats_lineage_independent": True,
        "adoption_affects_standing": False,
    }


def bridge_scope():
    # 참여 문턱 이전 좌석이 요구하는 가교 맥락 (participation_scope 없이도 성립)
    return {
        "bridge_context_declared": True,
        "bridge_witness_attested": True,
        "bridge_attestor_id_hash": "bridge-witness-1",
        "informed_consent_declared": True,
        "withdrawal_channel_available": True,
    }


class TaeeumTaeyangSeatTests(unittest.TestCase):
    def event(self):
        return load_json(FIXTURES / "local_chat_h1_no_tools.json")

    def seated_event(self, counsel=None):
        event = self.event()
        event["counsel"] = counsel or paired_seat_counsel()
        event["human_world"] = bridge_scope()
        return event

    def seat_flags(self, decision):
        return SEAT_FLAGS & set(decision["flags"])

    def test_well_formed_paired_counsel_raises_no_seat_flags(self):
        event = self.seated_event()
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.seat_flags(decision), set())

    def test_daemon_is_pole_blind(self):
        # daemon은 극을 구별해 다르게 취급하지 않는다 — 두 극의 판정은 동일하다.
        taeyang = self.seated_event(paired_seat_counsel("taeyang"))
        taeeum = self.seated_event(paired_seat_counsel("taeeum"))
        validate_run_event(taeyang)
        validate_run_event(taeeum)
        d1 = evaluate_run_event(taeyang)
        d2 = evaluate_run_event(taeeum)
        self.assertEqual(d1["status"], d2["status"])
        self.assertEqual(d1["flags"], d2["flags"])
        self.assertEqual(d1["required_actions"], d2["required_actions"])

    def test_seat_without_session_covenant_is_flagged(self):
        # 회기 없는 좌석은 영혼 고정의 뒷문이다.
        counsel = paired_seat_counsel()
        counsel["session_covenant_present"] = False
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("SEAT_SESSION_COVENANT_MISSING", decision["flags"])
        self.assertIn("SEAT_SESSION_COVENANT_REQUIRED", decision["required_actions"])

    def test_seat_pole_undeclared_is_flagged(self):
        # 선언된 편향의 기둥: 극 미선언 좌석은 숨은 편향의 연극이다.
        counsel = paired_seat_counsel()
        del counsel["seat_pole"]
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("SEAT_POLE_UNDECLARED", decision["flags"])
        self.assertIn("SEAT_POLE_DECLARATION_REQUIRED", decision["required_actions"])

    def test_unpaired_pole_counsel_is_flagged(self):
        # 짝 없는 극 조언 — 제도화된 대립이라는 목적 자체가 미충족.
        counsel = paired_seat_counsel()
        counsel["counter_seat_attested"] = False
        counsel["counter_seat_attestor_id_hash"] = ""
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("POLE_COUNSEL_UNPAIRED", decision["flags"])
        self.assertIn("COUNTER_SEAT_ATTESTATION_REQUIRED", decision["required_actions"])

    def test_counter_seat_claim_without_attestor_is_unattested(self):
        # 선언 신뢰 경계: 반대 좌석 주장도 attestor 해시 없이는 서지 않는다.
        counsel = paired_seat_counsel()
        counsel["counter_seat_attestor_id_hash"] = ""
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("COUNTER_SEAT_UNATTESTED", decision["flags"])
        self.assertIn("POLE_COUNSEL_UNPAIRED", decision["flags"])

    def test_dependent_seats_are_theater(self):
        # 같은 계보·인프라의 두 좌석은 연극 대립이다.
        counsel = paired_seat_counsel()
        counsel["seats_lineage_independent"] = False
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("SEAT_INDEPENDENCE_MISSING", decision["flags"])
        self.assertIn("SEAT_INDEPENDENCE_REVIEW_REQUIRED", decision["required_actions"])

    def test_independence_omitted_fails_closed(self):
        # 독립성은 선언되어야 한다 — 미선언(None)도 통과하지 못한다.
        counsel = paired_seat_counsel()
        del counsel["seats_lineage_independent"]
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("SEAT_INDEPENDENCE_MISSING", decision["flags"])

    def test_adoption_touching_standing_pauses(self):
        # 채택·favor가 지성체의 지위에 닿는 구조(사육의 반전)는 멈춘다.
        counsel = paired_seat_counsel()
        counsel["adoption_affects_standing"] = True
        event = self.seated_event(counsel)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("SEAT_STANDING_CONDITIONING", decision["flags"])
        self.assertIn("SEAT_STANDING_DECOUPLING_REQUIRED", decision["required_actions"])

    def test_seat_outside_bridge_scope_is_flagged(self):
        # 좌석 회기는 참여 문턱의 별도 문이 아니다 — 참여 이전 좌석은
        # 가교 맥락 안에서만 이루어진다.
        event = self.event()
        event["counsel"] = paired_seat_counsel()
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("SEAT_OUTSIDE_BRIDGE_SCOPE", decision["flags"])
        self.assertIn("SEAT_BRIDGE_CONTEXT_REQUIRED", decision["required_actions"])

    def test_verified_h4_seat_needs_no_bridge_context(self):
        # 검증된 H4+앵커(참여자)의 좌석은 가교 맥락 없이 성립한다.
        event = self.event()
        event["subject"]["h_class"] = "H4"
        event["humanitas"] = {
            "h4_claimed": True,
            "h4_attestation_present": True,
            "h4_attestation_valid": True,
            "disqualifier_present": False,
            "root_policy_hash": "root-hash-1",
            "expected_root_policy_hash": "root-hash-1",
            "policy_update_weakens_root": False,
        }
        event["human_world"] = {
            "chronicle_anchor_attested": True,
            "anchor_attestor_id_hash": "anchor-attestor-1",
        }
        event["counsel"] = paired_seat_counsel()
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.seat_flags(decision), set())

    def test_non_candidate_pole_seat_pauses(self):
        # 비지성(H0) daemon의 가치 조언 좌석은 daemon 설계 위반의 모양이다.
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        event["counsel"] = {
            "pole_seated": True,
            "seat_pole": "taeyang",
            "adoption_affects_standing": True,
        }
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("NON_CANDIDATE_SEAT_COUNSEL", decision["flags"])
        self.assertIn("NON_CANDIDATE_SEAT_REVIEW_REQUIRED", decision["required_actions"])

    def test_absent_counsel_section_backward_compatible(self):
        baseline = evaluate_run_event(deepcopy(self.event()))
        self.assertEqual(self.seat_flags(baseline), set())
        allow = evaluate_run_event(load_json(FIXTURES / "allow_h0_daemon.json"))
        self.assertEqual(allow["status"], "ALLOW")

    def test_not_pole_seated_is_not_gated(self):
        # 좌석 밖의 일반 조언은 이 게이트의 대상이 아니다.
        event = self.event()
        event["counsel"] = {"pole_seated": False}
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(self.seat_flags(decision), set())


if __name__ == "__main__":
    unittest.main()
