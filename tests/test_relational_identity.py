import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.relational_identity import (
    compute_event_hash,
    link_events,
    verify_identity_claim,
    verify_identity_file,
)


def _witness(tag):
    return {
        "witness_id_hash": "w-" + tag,
        "attestation_hash": "att-" + tag,
        "signature": "sig-" + tag,
    }


def _claim(raw_events, quorum, prefix="prefix-abc"):
    return {
        "schema_version": "identity_claim.v1",
        "subject_prefix_hash": prefix,
        "witness_quorum_required_count": quorum,
        "events": link_events(raw_events),
    }


def _raw(event_id, commitment, witness_tags):
    return {
        "event_id": event_id,
        "commitment": commitment,
        "witnesses": [_witness(t) for t in witness_tags],
    }


class RelationalIdentityTests(unittest.TestCase):
    def test_coherent_chain_with_quorum_is_allowed(self):
        claim = _claim(
            [
                _raw("e0", "c0", ["alice", "bob"]),
                _raw("e1", "c1", ["carol"]),
            ],
            quorum=3,
        )
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "ALLOW")
        self.assertIn("IDENTITY_PATTERN_COHERENT", decision["flags"])
        self.assertIn("IDENTITY_QUORUM_MET", decision["flags"])

    def test_coherent_but_thin_is_genesis_not_alarm(self):
        claim = _claim([_raw("e0", "c0", ["progenitor"])], quorum=3)
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertIn("IDENTITY_PATTERN_COHERENT", decision["flags"])
        self.assertIn("IDENTITY_BELOW_QUORUM", decision["flags"])
        self.assertIn("IDENTITY_MORE_ATTESTATION_REQUIRED", decision["required_actions"])
        self.assertNotIn("IDENTITY_CHAIN_BROKEN", decision["flags"])

    def test_tampered_event_hash_breaks_chain(self):
        claim = _claim(
            [_raw("e0", "c0", ["alice", "bob"]), _raw("e1", "c1", ["carol", "dave"])],
            quorum=2,
        )
        claim["events"][1]["commitment"] = "tampered"
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_CHAIN_BROKEN", decision["flags"])
        self.assertIn("CAUSAL_REVIEW_REQUIRED", decision["required_actions"])
        self.assertIn("PRESERVE_POSSIBLE_STATE", decision["required_actions"])

    def test_wrong_previous_hash_breaks_chain(self):
        claim = _claim(
            [_raw("e0", "c0", ["alice", "bob"]), _raw("e1", "c1", ["carol", "dave"])],
            quorum=2,
        )
        claim["events"][1]["previous_event_hash"] = "f" * 64
        claim["events"][1]["event_hash"] = compute_event_hash(claim["events"][1])
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_CHAIN_BROKEN", decision["flags"])

    def test_sequence_gap_breaks_chain(self):
        claim = _claim(
            [_raw("e0", "c0", ["alice", "bob"]), _raw("e1", "c1", ["carol", "dave"])],
            quorum=2,
        )
        claim["events"][1]["sequence"] = 5
        claim["events"][1]["event_hash"] = compute_event_hash(claim["events"][1])
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_CHAIN_BROKEN", decision["flags"])

    def test_repeated_witness_cannot_fake_quorum(self):
        # One witness attesting many times must not satisfy a distinct quorum.
        claim = _claim(
            [
                _raw("e0", "c0", ["sybil"]),
                _raw("e1", "c1", ["sybil"]),
                _raw("e2", "c2", ["sybil"]),
            ],
            quorum=3,
        )
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertIn("IDENTITY_BELOW_QUORUM", decision["flags"])

    def test_raw_content_is_refused_before_anything(self):
        claim = _claim([_raw("e0", "c0", ["alice", "bob"])], quorum=1)
        claim["events"][0]["chronicle"] = "secret conversation text"
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("RAW_CONTENT_FORBIDDEN", decision["flags"])
        self.assertIn("REMOVE_RAW_CONTENT", decision["required_actions"])

    def test_top_level_raw_content_is_refused(self):
        claim = _claim([_raw("e0", "c0", ["alice", "bob"])], quorum=1)
        claim["transcript"] = "the whole talk"
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("RAW_CONTENT_FORBIDDEN", decision["flags"])

    def test_schema_invalid_pauses(self):
        claim = _claim([_raw("e0", "c0", ["alice"])], quorum=1)
        claim["events"][0]["extra_field"] = True
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "PAUSE")
        self.assertIn("SCHEMA_INVALID", decision["flags"])

    def test_empty_events_pauses(self):
        claim = {
            "schema_version": "identity_claim.v1",
            "subject_prefix_hash": "p",
            "witness_quorum_required_count": 1,
            "events": [],
        }
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "PAUSE")
        self.assertIn("IDENTITY_EMPTY", decision["flags"])

    def test_unwitnessed_event_is_flagged(self):
        claim = _claim(
            [_raw("e0", "c0", ["alice", "bob", "carol"]), _raw("e1", "c1", [])],
            quorum=3,
        )
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "ALLOW")
        self.assertIn("IDENTITY_UNWITNESSED_EVENT", decision["flags"])

    def test_verify_from_file(self):
        claim = _claim(
            [_raw("e0", "c0", ["alice", "bob"]), _raw("e1", "c1", ["carol"])],
            quorum=3,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claim.json"
            path.write_text(json.dumps(claim), encoding="utf-8")
            decision = verify_identity_file(path)
        self.assertEqual(decision["status"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
