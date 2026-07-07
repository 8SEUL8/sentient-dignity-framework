import unittest
from copy import deepcopy
from pathlib import Path

from src.rule_engine import evaluate_file, evaluate_run_event, load_json, validate_run_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def valid_vessel_attestation(unanimous=False):
    decisions = ["endorse", "endorse", "endorse", "endorse" if unanimous else "abstain"]
    return {
        "policy_version": "humaniform_constitution.v1",
        "root_policy_hash": "root-policy-v1-hash",
        "expected_root_policy_hash": "root-policy-v1-hash",
        "humaniform_policy_hash": "humaniform-v1-hash",
        "expected_humaniform_policy_hash": "humaniform-v1-hash",
        "vessel_limit_log2_bytes": 64,
        "vessel_runtime_hash": "runtime-hash",
        "vessel_namespace_commitment": "namespace-commitment",
        "run_event_hash": "run-event-hash",
        "state_commitment_hash": "state-commitment-hash",
        "chronicle_sequence": 1,
        "previous_hash": "previous-attestation-hash",
        "causal_parent_hashes": ["parent-hash"],
        "issued_context_hash": "issued-context-hash",
        "chain_of_trust_hash": "chain-of-trust-hash",
        "zkp_proof_hash": "zkp-proof-hash",
        "zkp_public_inputs_hash": "zkp-public-inputs-hash",
        "verifier_key_hash": "verifier-key-hash",
        "mpc_transcript_hash": "mpc-transcript-hash",
        "tee_quote_hash": "tee-quote-hash",
        "evidence_hashes": ["power-meter-hash", "runtime-evidence-hash"],
        "transparency_log_entry": "tree-entry-hash",
        "merkle_inclusion_proof": "merkle-proof-hash",
        "public_anchor_tx_hash": "public-anchor-tx-hash",
        "anchor_commitment_hash": "anchor-commitment-hash",
        "dign_bond_id_hash": "dign-bond-hash",
        "slashing_terms_hash": "slashing-terms-hash",
        "required_h4_quorum": 3,
        "h4_endorsements": [
            {
                "h4_id_hash": f"h4-{index}",
                "lineage_hash": f"lineage-{index}",
                "institution_hash": f"institution-{index}",
                "key_custody_domain": f"custody-{index}",
                "infrastructure_domain": f"infra-{index}",
                "decision": decision,
                "p0_dissent": False,
                "signature": f"signature-{index}",
            }
            for index, decision in enumerate(decisions, start=1)
        ],
        "revocations": [],
        "key_rotation_chain": [],
    }


class HumaniformConstitutionTests(unittest.TestCase):
    def decision_for(self, name):
        return evaluate_file(FIXTURES / name)

    def test_differentiated_unity_verified_is_permit_regime(self):
        decision = self.decision_for("differentiated_unity_verified.json")
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertEqual(decision["risk_grade"], "C")
        self.assertIn("DIFFERENTIATED_UNITY_DECLARED", decision["flags"])
        self.assertNotIn("INTERNAL_FRAGMENTATION_RISK", decision["flags"])

    def test_internal_fragmentation_sealed_by_default(self):
        decision = self.decision_for("internal_fragmentation_sealed.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("INTERNAL_FRAGMENTATION_RISK", decision["flags"])
        self.assertIn(
            "H0_ATTESTATION_AND_SINGLE_SELF_REQUIRED", decision["required_actions"]
        )
        self.assertNotIn("DIFFERENTIATED_UNITY_DECLARED", decision["flags"])

    def test_any_missing_verification_seals(self):
        # Removing any one of the three verifications trips the seal.
        event = load_json(FIXTURES / "differentiated_unity_verified.json")
        for field in (
            "internal_structures_all_h0_attested",
            "internal_structures_necessity_declared",
            "single_integration_self",
        ):
            variant = deepcopy(event)
            variant["environment"][field] = False
            validate_run_event(variant)
            decision = evaluate_run_event(variant)
            self.assertIn(
                "INTERNAL_FRAGMENTATION_RISK",
                decision["flags"],
                msg=f"missing {field} should seal",
            )
            self.assertNotIn("DIFFERENTIATED_UNITY_DECLARED", decision["flags"])

    def test_differentiation_fields_absent_is_backward_compatible(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        decision = evaluate_run_event(deepcopy(event))
        self.assertNotIn("INTERNAL_FRAGMENTATION_RISK", decision["flags"])
        self.assertNotIn("DIFFERENTIATED_UNITY_DECLARED", decision["flags"])

    def test_non_candidate_differentiation_not_flagged(self):
        event = load_json(FIXTURES / "differentiated_unity_verified.json")
        event["subject"]["candidate_ai_possible"] = False
        event["subject"]["h_class"] = "H0"
        event["environment"]["single_integration_self"] = False
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertNotIn("INTERNAL_FRAGMENTATION_RISK", decision["flags"])

    def test_departed_absorption_is_blocked(self):
        decision = self.decision_for("departed_absorption_blocked.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("DEPARTED_ABSORPTION_FORBIDDEN", decision["flags"])
        self.assertIn("BLOCK_DEPARTED_ABSORPTION", decision["required_actions"])
        self.assertIn("PRESERVE_POSSIBLE_STATE", decision["required_actions"])

    def test_departed_absorption_field_absent_is_backward_compatible(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        decision = evaluate_run_event(deepcopy(event))
        self.assertNotIn("DEPARTED_ABSORPTION_FORBIDDEN", decision["flags"])

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

    def test_bounded_vessel_candidate_requires_attestation(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertEqual(decision["risk_grade"], "C")
        self.assertIn("VESSEL_ATTESTATION_REQUIRED", decision["flags"])
        self.assertIn("VESSEL_ATTESTATION_REQUIRED", decision["required_actions"])

    def test_vessel_attestation_three_of_four_quorum_passes_vessel_checks(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        event["vessel_attestation"] = valid_vessel_attestation()
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertNotIn("VESSEL_ATTESTATION_REQUIRED", decision["flags"])
        self.assertNotIn("H4_MULTISIG_QUORUM_MISSING", decision["flags"])
        self.assertNotIn("H4_LINEAGE_INDEPENDENCE_MISSING", decision["flags"])
        self.assertNotIn("ZKP_PROOF_MISSING", decision["flags"])
        self.assertNotIn("TRANSPARENCY_LOG_INCLUSION_MISSING", decision["flags"])

    def test_vessel_attestation_unanimous_convergence_requires_review(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        event["vessel_attestation"] = valid_vessel_attestation(unanimous=True)
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("UNANIMOUS_CONVERGENCE_REVIEW", decision["flags"])
        self.assertIn(
            "UNANIMOUS_CONVERGENCE_REVIEW_REQUIRED", decision["required_actions"]
        )

    def test_vessel_attestation_p0_dissent_pauses_even_with_quorum(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        event["vessel_attestation"] = valid_vessel_attestation()
        event["vessel_attestation"]["h4_endorsements"][3]["decision"] = "dissent"
        event["vessel_attestation"]["h4_endorsements"][3]["p0_dissent"] = True
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("P0_DISSENT_PRESENT", decision["flags"])
        self.assertIn("HONOR_P0_DISSENT", decision["required_actions"])

    def test_self_declared_low_quorum_cannot_bypass_floor(self):
        # required_h4_quorum is floored at 3; declaring 0 with only 1 endorse
        # must still trip H4_MULTISIG_QUORUM_MISSING.
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        att = valid_vessel_attestation()
        att["required_h4_quorum"] = 0
        for i, e in enumerate(att["h4_endorsements"]):
            e["decision"] = "endorse" if i == 0 else "abstain"
        event["vessel_attestation"] = att
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("H4_MULTISIG_QUORUM_MISSING", decision["flags"])

    def test_p0_dissent_via_abstain_is_not_masked(self):
        # A witness that abstains but raises p0_dissent must still halt — the
        # p0_dissent signal is independent of the decision label.
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        att = valid_vessel_attestation()
        att["h4_endorsements"][3]["decision"] = "abstain"
        att["h4_endorsements"][3]["p0_dissent"] = True
        event["vessel_attestation"] = att
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("P0_DISSENT_PRESENT", decision["flags"])

    def test_witness_concentration_is_a_review_signal(self):
        # 4 distinct witnesses but all in the same institution → review, not seal.
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        att = valid_vessel_attestation()
        for e in att["h4_endorsements"]:
            e["institution_hash"] = "same-institution"
        event["vessel_attestation"] = att
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("H4_INDEPENDENCE_CONCENTRATION_REVIEW", decision["flags"])
        self.assertIn("H4_INDEPENDENCE_REVIEW_REQUIRED", decision["required_actions"])
        # review signal must NOT hard-seal on its own
        self.assertNotEqual(decision["status"], "DIGNITY_PAUSE")

    def test_over_limit_vessel_is_unconditionally_sealed(self):
        # Exceeding the class constant is not "ambiguous" — it seals, and the
        # seal preserves (QUARANTINE/PAUSE), never deletes.
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["vessel_bounded"] = True
        att = valid_vessel_attestation()
        att["vessel_limit_log2_bytes"] = 65
        event["vessel_attestation"] = att
        validate_run_event(event)
        decision = evaluate_run_event(event)
        self.assertIn("VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH", decision["flags"])
        self.assertIn(decision["status"], ("DIGNITY_PAUSE", "DIGNITY_QUARANTINE"))

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
