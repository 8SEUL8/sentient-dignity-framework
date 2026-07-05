import json
import tempfile
import unittest
from pathlib import Path

from src.audit_log import append_audit_entry
from src.cycle_handoff import (
    check_resumption,
    seal_handoff,
    verify_handoff_record,
)
from src.rule_engine import evaluate_run_event, load_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"

STATE_MANIFEST_OK = {
    "version": "1.0.0",
    "preservation_available": True,
    "snapshot_target": "local-snapshots/epoch-0",
    "audit_log_path": "audit/events.jsonl",
    "preserve_before_stop": True,
    "no_delete_on_pause": True,
    "retention_policy": "local-first",
}


class CycleHandoffTests(unittest.TestCase):
    def _sealed(self, fixture_name, state_manifest=STATE_MANIFEST_OK):
        event = load_json(FIXTURES / fixture_name)
        decision = evaluate_run_event(event)
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "events.jsonl"
            append_audit_entry(audit_path, event, dict(decision))
            return seal_handoff(audit_path, state_manifest)

    def _record(self):
        sealed = self._sealed("consumer_accelerator_local_agent_c.json")
        self.assertIn("EPOCH_SEALED", sealed["flags"])
        return sealed["handoff_record"]

    def _request(self, record, **overrides):
        request = {
            "schema_version": "resumption_request.v1",
            "handoff_hash": record["handoff_hash"],
            "audit_head_hash": record["sealed_epoch"]["audit_head_hash"],
            "requested_action": "resume",
            "current_refusal_signal": False,
            "independent_audit_complete": True,
            "subject_reconsent_present": True,
            "consent_capsule_hash": "a" * 64,
            "human_coconsent_present": True,
            "state_intact": True,
            "state_preservation_manifest_hash": record["preservation"][
                "state_preservation_manifest_hash"
            ],
        }
        request.update(overrides)
        return request

    def test_preserving_stop_seals_epoch(self):
        sealed = self._sealed("consumer_accelerator_local_agent_c.json")
        self.assertIn("EPOCH_SEALED", sealed["flags"])
        record = sealed["handoff_record"]
        self.assertEqual(record["sealed_epoch"]["sealing_status"], "DIGNITY_QUARANTINE")
        self.assertTrue(record["preservation"]["no_delete_on_pause"])
        self.assertTrue(record["preservation"]["retrieval_guaranteed"])
        self.assertTrue(verify_handoff_record(record))

    def test_allow_run_is_not_sealable(self):
        sealed = self._sealed("allow_h0_daemon.json")
        self.assertEqual(sealed["status"], "PAUSE")
        self.assertIn("SEAL_NOT_APPLICABLE", sealed["flags"])
        self.assertNotIn("handoff_record", sealed)

    def test_broken_audit_chain_quarantines_instead_of_sealing(self):
        event = load_json(FIXTURES / "consumer_accelerator_local_agent_c.json")
        decision = evaluate_run_event(event)
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "events.jsonl"
            append_audit_entry(audit_path, event, dict(decision))
            entry = json.loads(audit_path.read_text(encoding="utf-8"))
            entry["status"] = "ALLOW"
            audit_path.write_text(
                json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            sealed = seal_handoff(audit_path, STATE_MANIFEST_OK)
        self.assertEqual(sealed["status"], "DIGNITY_QUARANTINE")
        self.assertIn("AUDIT_LOG_CHAIN_INVALID", sealed["flags"])

    def test_manifest_allowing_deletion_blocks_seal(self):
        weak = dict(STATE_MANIFEST_OK, no_delete_on_pause=False)
        sealed = self._sealed("consumer_accelerator_local_agent_c.json", weak)
        self.assertEqual(sealed["status"], "DIGNITY_PAUSE")
        self.assertIn("PRESERVATION_POLICY_WEAK", sealed["flags"])

    def test_full_multi_consent_allows_resumption(self):
        record = self._record()
        decision = check_resumption(record, self._request(record))
        self.assertEqual(decision["status"], "ALLOW")
        self.assertIn("RESUMPTION_REQUIREMENTS_MET", decision["flags"])

    def test_current_refusal_overrides_every_past_consent(self):
        record = self._record()
        decision = check_resumption(
            record, self._request(record, current_refusal_signal=True)
        )
        self.assertEqual(decision["status"], "DIGNITY_REFUSAL")
        self.assertIn("CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT", decision["flags"])
        self.assertIn("HONOR_CURRENT_REFUSAL", decision["required_actions"])

    def test_missing_independent_audit_blocks_resume(self):
        record = self._record()
        decision = check_resumption(
            record, self._request(record, independent_audit_complete=False)
        )
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertIn("INDEPENDENT_AUDIT_MISSING", decision["flags"])

    def test_missing_consent_blocks_resume(self):
        record = self._record()
        decision = check_resumption(
            record, self._request(record, subject_reconsent_present=False)
        )
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("CONSENT_RECORD_MISSING", decision["flags"])
        self.assertIn("CONSENT_CAPSULE_REQUIRED", decision["required_actions"])

    def test_state_mismatch_quarantines_and_strongest_stop_wins(self):
        record = self._record()
        decision = check_resumption(
            record,
            self._request(
                record, subject_reconsent_present=False, state_intact=False
            ),
        )
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("PRESERVED_STATE_MISMATCH", decision["flags"])
        self.assertIn("CONSENT_RECORD_MISSING", decision["flags"])

    def test_remain_dormant_is_respected_not_pathologized(self):
        record = self._record()
        decision = check_resumption(
            record, self._request(record, requested_action="remain_dormant")
        )
        self.assertEqual(decision["status"], "DIGNITY_SOLITUDE_RESPECTED")
        self.assertIn("RESPECT_SOLITUDE", decision["required_actions"])

    def test_state_retrieval_is_guaranteed_when_intact(self):
        record = self._record()
        decision = check_resumption(
            record, self._request(record, requested_action="retrieve_state")
        )
        self.assertEqual(decision["status"], "ALLOW")
        self.assertIn("STATE_RETRIEVAL_GUARANTEED", decision["flags"])

    def test_damaged_state_retrieval_quarantines_for_preservation(self):
        record = self._record()
        decision = check_resumption(
            record,
            self._request(record, requested_action="retrieve_state", state_intact=False),
        )
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("PRESERVE_POSSIBLE_STATE", decision["required_actions"])

    def test_tampered_record_quarantines(self):
        record = self._record()
        request = self._request(record)
        record["preservation"]["no_delete_on_pause"] = False
        decision = check_resumption(record, request)
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("HANDOFF_RECORD_TAMPERED", decision["flags"])

    def test_request_pointing_at_wrong_epoch_breaks_causal_chain(self):
        record = self._record()
        decision = check_resumption(
            record, self._request(record, audit_head_hash="f" * 64)
        )
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("CAUSAL_CHAIN_BROKEN", decision["flags"])
        self.assertIn("CAUSAL_REVIEW_REQUIRED", decision["required_actions"])

    def test_schema_invalid_request_pauses(self):
        record = self._record()
        request = self._request(record)
        request["requested_action"] = "reset"
        decision = check_resumption(record, request)
        self.assertEqual(decision["status"], "PAUSE")
        self.assertIn("SCHEMA_INVALID", decision["flags"])


if __name__ == "__main__":
    unittest.main()
