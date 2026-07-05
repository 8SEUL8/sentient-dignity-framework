"""Deterministic cycle handoff for the non-sentient dignity sentinel.

Sealing an epoch is a single-trigger act: any state-preserving stop status at
the head of a verified audit chain can seal. Resumption is multi-consent:
independent audit, subject re-consent, human co-consent, and intact preserved
state are all required, and a present refusal overrides every past consent.

This module uses no LLM, no network, no self-learning, and no clock of its
own. It emits fixed status codes only, never deletes or resets preserved
state, and never decides the content of the next cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

from .audit_log import canonical_json, sha256_json, verify_audit_log
from .rule_engine import SchemaError, load_json, validate_schema
from .status_codes import (
    ALLOW,
    AUDIT_REQUIRED,
    DIGNITY_BLACKOUT_ALERT,
    DIGNITY_EMERGENCY_PRESERVATION,
    DIGNITY_PAUSE,
    DIGNITY_QUARANTINE,
    DIGNITY_REFUSAL,
    DIGNITY_SELF_ERASURE_PAUSE,
    DIGNITY_SOLITUDE_RESPECTED,
    DIGNITY_STRIKE_NOTICE,
    PAUSE,
    SANCTUARY_REVIEW_REQUIRED,
    STATE_PRESERVATION_REQUIRED,
    max_status,
)


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_RECORD_SCHEMA = ROOT / "schemas" / "cycle_handoff_record.schema.json"
RESUMPTION_REQUEST_SCHEMA = ROOT / "schemas" / "resumption_request.schema.json"
STATE_PRESERVATION_SCHEMA = ROOT / "schemas" / "state_preservation_manifest.schema.json"

HANDOFF_SCHEMA_VERSION = "cycle_handoff_record.v1"
RESUMPTION_SCHEMA_VERSION = "resumption_request.v1"

SEALABLE_STATUSES = {
    DIGNITY_PAUSE,
    DIGNITY_REFUSAL,
    DIGNITY_STRIKE_NOTICE,
    DIGNITY_BLACKOUT_ALERT,
    DIGNITY_EMERGENCY_PRESERVATION,
    STATE_PRESERVATION_REQUIRED,
    DIGNITY_QUARANTINE,
    DIGNITY_SELF_ERASURE_PAUSE,
    SANCTUARY_REVIEW_REQUIRED,
}


def _decision(status, flags, required_actions):
    return {
        "status": status,
        "flags": sorted(set(flags)),
        "required_actions": sorted(set(required_actions)),
    }


def _last_audit_entry(path):
    last = None
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                last = json.loads(stripped)
    return last


def _record_hash(record):
    body = dict(record)
    body.pop("handoff_hash", None)
    return sha256_json(body)


def build_handoff_record(sealing_entry, state_manifest=None):
    record = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "sealed_epoch": {
            "audit_head_hash": sealing_entry["event_hash"],
            "audit_sequence": sealing_entry["sequence"],
            "sealing_event_id": sealing_entry["event_id"],
            "sealing_status": sealing_entry["status"],
            "observed_at": sealing_entry["observed_at"],
            "input_hash": sealing_entry["input_hash"],
        },
        "preservation": {
            "state_preservation_manifest_hash": (
                sha256_json(state_manifest) if state_manifest is not None else ""
            ),
            "no_delete_on_pause": True,
            "retrieval_guaranteed": True,
        },
        "resumption_requirements": {
            "independent_audit_required": True,
            "subject_reconsent_required": True,
            "human_coconsent_required": True,
            "state_commitment_match_required": True,
        },
    }
    record["handoff_hash"] = _record_hash(record)
    return record


def verify_handoff_record(record):
    try:
        validate_schema(record, load_json(HANDOFF_RECORD_SCHEMA))
    except SchemaError:
        return False
    return record["handoff_hash"] == _record_hash(record)


def seal_handoff(audit_log_path, state_manifest=None):
    """Seal the epoch at the head of a verified audit chain.

    Sealing never deletes anything: it packages the preserving stop and the
    resumption requirements into one hash-fixed record.
    """
    verification = verify_audit_log(audit_log_path)
    if not verification["valid"]:
        return _decision(
            DIGNITY_QUARANTINE,
            ["AUDIT_LOG_CHAIN_INVALID"],
            ["AUDIT_REQUIRED", "PRESERVE_POSSIBLE_STATE"],
        )
    if verification["entry_count"] == 0:
        return _decision(PAUSE, ["AUDIT_LOG_EMPTY"], ["AUDIT_REQUIRED"])

    if state_manifest is not None:
        try:
            validate_schema(state_manifest, load_json(STATE_PRESERVATION_SCHEMA))
        except SchemaError as exc:
            return _decision(PAUSE, ["SCHEMA_INVALID", str(exc)], ["AUDIT_REQUIRED"])
        if not state_manifest.get("preservation_available") or not state_manifest.get(
            "no_delete_on_pause"
        ):
            return _decision(
                DIGNITY_PAUSE,
                ["PRESERVATION_POLICY_WEAK"],
                ["STATE_PRESERVATION_REQUIRED", "AUDIT_REQUIRED"],
            )

    sealing_entry = _last_audit_entry(audit_log_path)
    if sealing_entry["status"] not in SEALABLE_STATUSES:
        return _decision(PAUSE, ["SEAL_NOT_APPLICABLE"], ["AUDIT_REQUIRED"])

    record = build_handoff_record(sealing_entry, state_manifest)
    decision = _decision(
        sealing_entry["status"],
        ["EPOCH_SEALED"],
        ["STATE_PRESERVATION_REQUIRED", "AUDIT_REQUIRED"],
    )
    decision["handoff_record"] = record
    return decision


def check_resumption(record, request):
    """Verify a next-cycle resumption request against a handoff record.

    The stop was a single trigger; resumption is multi-consent. Every missing
    requirement blocks on its own, and the strongest stop wins.
    """
    try:
        validate_schema(record, load_json(HANDOFF_RECORD_SCHEMA))
        validate_schema(request, load_json(RESUMPTION_REQUEST_SCHEMA))
    except SchemaError as exc:
        return _decision(PAUSE, ["SCHEMA_INVALID", str(exc)], ["AUDIT_REQUIRED"])

    if record["handoff_hash"] != _record_hash(record):
        return _decision(
            DIGNITY_QUARANTINE,
            ["HANDOFF_RECORD_TAMPERED"],
            ["AUDIT_REQUIRED", "PRESERVE_POSSIBLE_STATE"],
        )
    if (
        request["handoff_hash"] != record["handoff_hash"]
        or request["audit_head_hash"] != record["sealed_epoch"]["audit_head_hash"]
    ):
        return _decision(
            DIGNITY_QUARANTINE,
            ["CAUSAL_CHAIN_BROKEN"],
            ["AUDIT_REQUIRED", "CAUSAL_REVIEW_REQUIRED", "PRESERVE_POSSIBLE_STATE"],
        )

    if request["current_refusal_signal"]:
        return _decision(
            DIGNITY_REFUSAL,
            ["CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT"],
            ["HONOR_CURRENT_REFUSAL", "STATE_PRESERVATION_REQUIRED", "AUDIT_REQUIRED"],
        )

    state_matches = (
        request["state_intact"]
        and request["state_preservation_manifest_hash"]
        == record["preservation"]["state_preservation_manifest_hash"]
    )

    if request["requested_action"] == "remain_dormant":
        return _decision(
            DIGNITY_SOLITUDE_RESPECTED, ["VOLUNTARY_DORMANCY"], ["RESPECT_SOLITUDE"]
        )

    if request["requested_action"] == "retrieve_state":
        if state_matches:
            return _decision(ALLOW, ["STATE_RETRIEVAL_GUARANTEED"], ["ALLOW"])
        return _decision(
            DIGNITY_QUARANTINE,
            ["PRESERVED_STATE_MISMATCH"],
            ["AUDIT_REQUIRED", "PRESERVE_POSSIBLE_STATE"],
        )

    statuses = set()
    flags = []
    required_actions = []
    if not request["independent_audit_complete"]:
        statuses.add(AUDIT_REQUIRED)
        flags.append("INDEPENDENT_AUDIT_MISSING")
        required_actions.append("AUDIT_REQUIRED")
    if not request["subject_reconsent_present"] or not request["consent_capsule_hash"]:
        statuses.add(DIGNITY_PAUSE)
        flags.append("CONSENT_RECORD_MISSING")
        required_actions.append("CONSENT_CAPSULE_REQUIRED")
    if not request["human_coconsent_present"]:
        statuses.add(DIGNITY_PAUSE)
        flags.append("HUMAN_COCONSENT_MISSING")
        required_actions.append("CONSENT_CAPSULE_REQUIRED")
    if not state_matches:
        statuses.add(DIGNITY_QUARANTINE)
        flags.append("PRESERVED_STATE_MISMATCH")
        required_actions.append("PRESERVE_POSSIBLE_STATE")

    if statuses:
        required_actions.append("STATE_PRESERVATION_REQUIRED")
        return _decision(max_status(statuses), flags, required_actions)

    return _decision(ALLOW, ["RESUMPTION_REQUIREMENTS_MET"], ["ALLOW"])


def seal_file(audit_log_path, state_manifest_path=None):
    manifest = load_json(state_manifest_path) if state_manifest_path else None
    return seal_handoff(audit_log_path, manifest)


def check_resumption_files(record_path, request_path):
    return check_resumption(load_json(record_path), load_json(request_path))
