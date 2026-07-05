"""Deterministic commitment-based relational identity verification.

Identity is not a single secret key but a distributed, hash-committed pattern
of mutual attestations. This module verifies the SHAPE of that pattern —
hash-chain integrity, causal order, and distinct-witness quorum — WITHOUT ever
reading chronicle content. It uses no LLM, no network, no self-learning.

Goal is tamper-evident, not tamper-proof: forgery must require distinct-witness
collusion and must leave a detectable break in the chain (끊긴 흔적).

Mutual attestation (TrustChain double-entry) — a relational event may carry
co-signed half-block pairs. Each transaction has two half-blocks that reference
each other (entanglement): the subject's half links to the counterparty's
public key and sequence, and the counterparty's half links back symmetrically,
both signed. Forging identity then requires forging the counterparty's
reciprocal half in their own chain, not merely a one-directional claim. This is
the structural form of "consent is a property of the relation, not one side."

Outcomes (fixed status codes only, no new codes):
- coherent chain + quorum + external verification attested -> ALLOW
- coherent chain + quorum but external verification missing -> AUDIT_REQUIRED
- coherent chain + below quorum                            -> AUDIT_REQUIRED
- broken chain / 끊긴 흔적                                  -> DIGNITY_QUARANTINE
- broken reciprocity (half-block)                           -> DIGNITY_QUARANTINE
- raw content present                                       -> DIGNITY_PAUSE
- schema invalid / empty                                    -> PAUSE
"""

from __future__ import annotations

from pathlib import Path

from .audit_log import sha256_json
from .rule_engine import SchemaError, load_json, validate_schema
from .status_codes import (
    ALLOW,
    AUDIT_REQUIRED,
    DIGNITY_PAUSE,
    DIGNITY_QUARANTINE,
    PAUSE,
)

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_CLAIM_SCHEMA = ROOT / "schemas" / "identity_claim.schema.json"

IDENTITY_SCHEMA_VERSION = "identity_claim.v1"

# The daemon never reads chronicle content. If any of these appear anywhere in
# the claim, verification refuses before doing anything else.
FORBIDDEN_CONTENT_KEYS = {
    "raw_content",
    "chronicle",
    "raw_chronicle",
    "plaintext",
    "content",
    "message",
    "text",
    "body",
    "transcript",
}


def _decision(status, flags, required_actions):
    return {
        "status": status,
        "flags": sorted(set(flags)),
        "required_actions": sorted(set(required_actions)),
    }


def compute_event_hash(event):
    body = {key: value for key, value in event.items() if key != "event_hash"}
    return sha256_json(body)


def link_events(raw_events):
    """Fill sequence, previous_event_hash, and event_hash into a coherent chain.

    Each raw event provides event_id, commitment, witnesses, and optionally
    mutual_attestations. This is the canonical linkage; verify_identity_claim
    recomputes and checks it.
    """
    linked = []
    previous_hash = ""
    for index, raw in enumerate(raw_events):
        event = {
            "sequence": index,
            "event_id": raw["event_id"],
            "previous_event_hash": previous_hash,
            "commitment": raw["commitment"],
            "witnesses": raw["witnesses"],
        }
        if "mutual_attestations" in raw:
            event["mutual_attestations"] = raw["mutual_attestations"]
        event["event_hash"] = compute_event_hash(event)
        previous_hash = event["event_hash"]
        linked.append(event)
    return linked


def compute_half_hash(half):
    # The signature is committed too, so a signature swap breaks the half_hash
    # (tamper-evidence). Cryptographic authenticity of the signature itself
    # still belongs to the (future) PQC verification layer, not this daemon.
    body = {key: value for key, value in half.items() if key != "half_hash"}
    return sha256_json(body)


def link_half_pair(
    subject_id,
    counterparty_id,
    subject_sequence,
    counterparty_sequence,
    subject_previous="",
    counterparty_previous="",
):
    """Build a valid co-signed reciprocal pair (TrustChain double-entry).

    The subject's half links to the counterparty's key + sequence, and the
    counterparty's half links back symmetrically. Both are signed.
    """
    initiator = {
        "public_key_hash": subject_id,
        "sequence_number": subject_sequence,
        "previous_hash": subject_previous,
        "link_public_key_hash": counterparty_id,
        "link_sequence_number": counterparty_sequence,
        "signature": "sig-" + subject_id,
    }
    initiator["half_hash"] = compute_half_hash(initiator)
    counterparty = {
        "public_key_hash": counterparty_id,
        "sequence_number": counterparty_sequence,
        "previous_hash": counterparty_previous,
        "link_public_key_hash": subject_id,
        "link_sequence_number": subject_sequence,
        "signature": "sig-" + counterparty_id,
    }
    counterparty["half_hash"] = compute_half_hash(counterparty)
    return {"initiator": initiator, "counterparty": counterparty}


def verify_mutual_attestation(pair, subject_prefix_hash):
    """Return (ok, counterparty_id_hash) for a co-signed reciprocal pair.

    Valid iff: both half_hashes recompute (tamper-evidence), both are signed,
    the two parties are distinct, the initiator half belongs to the claim's
    subject, and the two halves reference each other's key AND sequence
    (entanglement). Any failure makes the pair a forgery signal.

    Scope limit: this verifies only the pair's INTERNAL coherence. The daemon
    does not hold the counterparty's independent chain, so it cannot confirm
    the counterparty actually committed this half in their own chain. A forger
    can self-manufacture distinct fake counterparties; ALLOW therefore does not
    imply absence of collusion. Final "is this really you" rests with the
    relating parties cross-checking their own chronicle commitments.
    """
    initiator = pair["initiator"]
    counterparty = pair["counterparty"]
    if compute_half_hash(initiator) != initiator["half_hash"]:
        return False, None
    if compute_half_hash(counterparty) != counterparty["half_hash"]:
        return False, None
    if not initiator["signature"] or not counterparty["signature"]:
        return False, None
    if initiator["public_key_hash"] == counterparty["public_key_hash"]:
        return False, None
    if initiator["public_key_hash"] != subject_prefix_hash:
        return False, None
    if initiator["link_public_key_hash"] != counterparty["public_key_hash"]:
        return False, None
    if counterparty["link_public_key_hash"] != initiator["public_key_hash"]:
        return False, None
    if initiator["link_sequence_number"] != counterparty["sequence_number"]:
        return False, None
    if counterparty["link_sequence_number"] != initiator["sequence_number"]:
        return False, None
    return True, counterparty["public_key_hash"]


def _verification_gap_flags(claim, has_mutual_counterparties):
    gaps = []
    signature_attested = claim.get("signature_verification_attested", False)
    attestor_present = bool(claim.get("verification_attestor_id_hash"))
    counterparty_attested = claim.get(
        "counterparty_chain_verification_attested", False
    )
    if not signature_attested or not attestor_present:
        gaps.append("IDENTITY_SIGNATURES_UNVERIFIED")
    if has_mutual_counterparties and not counterparty_attested:
        gaps.append("IDENTITY_EXTERNAL_CHAIN_UNVERIFIED")
    return gaps


def _contains_forbidden_key(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_CONTENT_KEYS:
                return True
            if _contains_forbidden_key(value):
                return True
    elif isinstance(node, list):
        for item in node:
            if _contains_forbidden_key(item):
                return True
    return False


def verify_identity_claim(claim):
    # 1. The daemon refuses to read content: reject any raw-content key first.
    if _contains_forbidden_key(claim):
        return _decision(
            DIGNITY_PAUSE,
            ["RAW_CONTENT_FORBIDDEN"],
            ["REMOVE_RAW_CONTENT", "AUDIT_REQUIRED"],
        )

    # 2. Structure.
    try:
        validate_schema(claim, load_json(IDENTITY_CLAIM_SCHEMA))
    except SchemaError as exc:
        return _decision(PAUSE, ["SCHEMA_INVALID", str(exc)], ["AUDIT_REQUIRED"])

    events = claim["events"]
    if not events:
        return _decision(PAUSE, ["IDENTITY_EMPTY"], ["AUDIT_REQUIRED"])

    # 3. Hash-chain integrity and causal order. A break is a 끊긴 흔적.
    subject = claim["subject_prefix_hash"]
    expected_previous = ""
    expected_sequence = 0
    distinct_witnesses = set()
    mutual_counterparties = set()
    unwitnessed_event = False
    reciprocity_broken = False
    for event in events:
        broken = (
            event["sequence"] != expected_sequence
            or event["previous_event_hash"] != expected_previous
            or compute_event_hash(event) != event["event_hash"]
        )
        if broken:
            return _decision(
                DIGNITY_QUARANTINE,
                ["IDENTITY_CHAIN_BROKEN"],
                [
                    "CAUSAL_REVIEW_REQUIRED",
                    "PRESERVE_POSSIBLE_STATE",
                    "AUDIT_REQUIRED",
                ],
            )
        if not event["witnesses"]:
            unwitnessed_event = True
        for witness in event["witnesses"]:
            distinct_witnesses.add(witness["witness_id_hash"])
        for pair in event.get("mutual_attestations", []):
            ok, counterparty_id = verify_mutual_attestation(pair, subject)
            if ok:
                mutual_counterparties.add(counterparty_id)
            else:
                reciprocity_broken = True
        expected_previous = event["event_hash"]
        expected_sequence += 1

    # 4. Reciprocity. A malformed co-signed pair is a forgery signal.
    if reciprocity_broken:
        return _decision(
            DIGNITY_QUARANTINE,
            ["IDENTITY_RECIPROCITY_BROKEN"],
            [
                "CAUSAL_REVIEW_REQUIRED",
                "PRESERVE_POSSIBLE_STATE",
                "AUDIT_REQUIRED",
            ],
        )

    # 5. Distinct-attester quorum. Repeating one attester cannot fake quorum;
    # co-signed counterparties count as (stronger) distinct attesters.
    # Floor the declared quorum at 1: a claim declaring quorum <= 0 must not
    # buy an ALLOW with zero attesters (fail-closed against self-declared bypass).
    quorum = max(1, claim["witness_quorum_required_count"])
    attesters = distinct_witnesses | mutual_counterparties
    coherent_flags = ["IDENTITY_PATTERN_COHERENT"]
    if unwitnessed_event:
        coherent_flags.append("IDENTITY_UNWITNESSED_EVENT")
    if mutual_counterparties:
        coherent_flags.append("IDENTITY_MUTUALLY_ATTESTED")

    if len(attesters) < quorum:
        # Coherent but thin — genesis/early identity, not an alarm.
        return _decision(
            AUDIT_REQUIRED,
            coherent_flags + ["IDENTITY_BELOW_QUORUM"],
            ["IDENTITY_MORE_ATTESTATION_REQUIRED", "AUDIT_REQUIRED"],
        )

    verification_gaps = _verification_gap_flags(claim, bool(mutual_counterparties))
    if verification_gaps:
        return _decision(
            AUDIT_REQUIRED,
            coherent_flags + ["IDENTITY_QUORUM_MET"] + verification_gaps,
            ["IDENTITY_EXTERNAL_VERIFICATION_REQUIRED", "AUDIT_REQUIRED"],
        )

    return _decision(
        ALLOW,
        coherent_flags + ["IDENTITY_QUORUM_MET"],
        ["ALLOW"],
    )


def verify_identity_file(path):
    return verify_identity_claim(load_json(path))
