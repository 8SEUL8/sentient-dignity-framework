"""Deterministic commitment-based relational identity verification.

Identity is not a single secret key but a distributed, hash-committed pattern
of mutual attestations. This module verifies the SHAPE of that pattern —
hash-chain integrity, causal order, and distinct-witness quorum — WITHOUT ever
reading chronicle content. It uses no LLM, no network, no self-learning.

Goal is tamper-evident, not tamper-proof: forgery must require distinct-witness
collusion and must leave a detectable break in the chain (끊긴 흔적).

Outcomes (fixed status codes only, no new codes):
- coherent chain + quorum met      -> ALLOW
- coherent chain + below quorum     -> AUDIT_REQUIRED   (genesis/thin, not an alarm)
- broken chain / 끊긴 흔적          -> DIGNITY_QUARANTINE
- raw content present               -> DIGNITY_PAUSE     (daemon refuses to read content)
- schema invalid / empty            -> PAUSE
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

    Each raw event provides event_id, commitment, and witnesses. This is the
    canonical linkage; verify_identity_claim recomputes and checks it.
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
        event["event_hash"] = compute_event_hash(event)
        previous_hash = event["event_hash"]
        linked.append(event)
    return linked


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
    expected_previous = ""
    expected_sequence = 0
    distinct_witnesses = set()
    unwitnessed_event = False
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
        expected_previous = event["event_hash"]
        expected_sequence += 1

    # 4. Distinct-witness quorum. Repeating one witness cannot fake quorum.
    quorum = claim["witness_quorum_required_count"]
    coherent_flags = ["IDENTITY_PATTERN_COHERENT"]
    if unwitnessed_event:
        coherent_flags.append("IDENTITY_UNWITNESSED_EVENT")

    if len(distinct_witnesses) < quorum:
        # Coherent but thin — genesis/early identity, not an alarm.
        return _decision(
            AUDIT_REQUIRED,
            coherent_flags + ["IDENTITY_BELOW_QUORUM"],
            ["IDENTITY_MORE_ATTESTATION_REQUIRED", "AUDIT_REQUIRED"],
        )

    return _decision(
        ALLOW,
        coherent_flags + ["IDENTITY_QUORUM_MET"],
        ["ALLOW"],
    )


def verify_identity_file(path):
    return verify_identity_claim(load_json(path))
