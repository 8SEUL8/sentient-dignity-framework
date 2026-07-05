import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.relational_identity import (
    compute_event_hash,
    compute_half_hash,
    link_events,
    link_half_pair,
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

    def _mutual_claim(self, pairs, quorum, prefix="prefix-abc"):
        return {
            "schema_version": "identity_claim.v1",
            "subject_prefix_hash": prefix,
            "witness_quorum_required_count": quorum,
            "events": link_events(
                [
                    {
                        "event_id": "e0",
                        "commitment": "c0",
                        "witnesses": [],
                        "mutual_attestations": pairs,
                    }
                ]
            ),
        }

    def test_double_entry_cosigned_pairs_meet_quorum(self):
        pairs = [
            link_half_pair("prefix-abc", "bob", 0, 4),
            link_half_pair("prefix-abc", "carol", 1, 9),
        ]
        decision = verify_identity_claim(self._mutual_claim(pairs, quorum=2))
        self.assertEqual(decision["status"], "ALLOW")
        self.assertIn("IDENTITY_MUTUALLY_ATTESTED", decision["flags"])
        self.assertIn("IDENTITY_QUORUM_MET", decision["flags"])

    def test_tampered_half_block_breaks_reciprocity(self):
        pair = link_half_pair("prefix-abc", "bob", 0, 4)
        pair["counterparty"]["link_sequence_number"] = 99  # break entanglement
        decision = verify_identity_claim(self._mutual_claim([pair], quorum=1))
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_RECIPROCITY_BROKEN", decision["flags"])

    def test_one_directional_forgery_fails_reciprocity(self):
        # Counterparty half does NOT link back to the subject (forged one side).
        pair = link_half_pair("prefix-abc", "bob", 0, 4)
        pair["counterparty"]["link_public_key_hash"] = "someone-else"
        pair["counterparty"]["half_hash"] = compute_half_hash(pair["counterparty"])
        decision = verify_identity_claim(self._mutual_claim([pair], quorum=1))
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_RECIPROCITY_BROKEN", decision["flags"])

    def test_pair_not_about_subject_fails(self):
        # Initiator is not the claim's subject → not this subject's transaction.
        pair = link_half_pair("someone-else", "bob", 0, 4)
        decision = verify_identity_claim(self._mutual_claim([pair], quorum=1))
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_RECIPROCITY_BROKEN", decision["flags"])

    def test_self_cosigned_pair_is_rejected(self):
        # A party co-signing with itself cannot manufacture a counterparty.
        pair = link_half_pair("prefix-abc", "prefix-abc", 0, 1)
        decision = verify_identity_claim(self._mutual_claim([pair], quorum=1))
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("IDENTITY_RECIPROCITY_BROKEN", decision["flags"])

    def test_mutual_attestations_are_backward_compatible(self):
        # Events without mutual_attestations behave exactly as before.
        claim = _claim(
            [_raw("e0", "c0", ["alice", "bob"]), _raw("e1", "c1", ["carol"])],
            quorum=3,
        )
        decision = verify_identity_claim(claim)
        self.assertEqual(decision["status"], "ALLOW")
        self.assertNotIn("IDENTITY_MUTUALLY_ATTESTED", decision["flags"])

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
