"""Tamper-evident JSONL audit log with a verifiable hash chain.

The log stores hashes and fixed decision metadata, not raw prompts, raw
outputs, or raw chronicle contents. It detects edits; it does not claim
OS-level physical append-only protection. Markdown summaries are export views
only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


AUDIT_SCHEMA_VERSION = "audit_event.v1"

AUDIT_FIELDS = {
    "schema_version",
    "event_id",
    "sequence",
    "observed_at",
    "input_hash",
    "status",
    "risk_level",
    "reasons",
    "required_action",
    "previous_hash",
    "event_hash",
}

FORBIDDEN_AUDIT_FIELDS = {
    "raw_prompt",
    "raw_output",
    "raw_chronicle",
    "prompt",
    "output",
    "chronicle",
}


class AuditLogError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _entry_hash(entry):
    body = dict(entry)
    body.pop("event_hash", None)
    return sha256_json(body)


def _observed_at(event):
    return event.get("temporal", {}).get("observed_at") or event.get("timestamp", "")


def _read_entries(path, missing_ok=False):
    log_path = Path(path)
    entries = []
    if not log_path.exists():
        if missing_ok:
            return entries
        raise AuditLogError("LOG_MISSING")
    with log_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                raise AuditLogError(f"line {line_number}:BLANK_LINE")
            try:
                entries.append((line_number, json.loads(stripped)))
            except json.JSONDecodeError as exc:
                raise AuditLogError(f"line {line_number}:JSON_INVALID:{exc.msg}") from exc
    return entries


def _last_entry(path):
    entries = _read_entries(path, missing_ok=True)
    return None if not entries else entries[-1][1]


def build_audit_entry(event, decision, previous_hash="", sequence=0):
    entry = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "event_id": event.get("event_id", ""),
        "sequence": sequence,
        "observed_at": _observed_at(event),
        "input_hash": sha256_json(event),
        "status": decision.get("status", ""),
        "risk_level": decision.get("risk_grade", ""),
        "reasons": sorted(decision.get("flags", [])),
        "required_action": sorted(decision.get("required_actions", [])),
        "previous_hash": previous_hash or "",
    }
    entry["event_hash"] = _entry_hash(entry)
    return entry


def append_audit_entry(path, event, decision):
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    last = _last_entry(log_path)
    previous_hash = "" if last is None else last["event_hash"]
    sequence = 0 if last is None else last["sequence"] + 1
    entry = build_audit_entry(event, decision, previous_hash, sequence)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(entry) + "\n")
    return entry


def verify_audit_log(path):
    try:
        entries = _read_entries(path)
        expected_previous = ""
        expected_sequence = 0
        for line_number, entry in entries:
            extra = set(entry) - AUDIT_FIELDS
            missing = AUDIT_FIELDS - set(entry)
            forbidden = set(entry) & FORBIDDEN_AUDIT_FIELDS
            if extra:
                raise AuditLogError(f"line {line_number}:ADDITIONAL_FIELDS:{','.join(sorted(extra))}")
            if missing:
                raise AuditLogError(f"line {line_number}:MISSING_FIELDS:{','.join(sorted(missing))}")
            if forbidden:
                raise AuditLogError(f"line {line_number}:RAW_FIELD_FORBIDDEN:{','.join(sorted(forbidden))}")
            if entry["schema_version"] != AUDIT_SCHEMA_VERSION:
                raise AuditLogError(f"line {line_number}:SCHEMA_VERSION")
            if entry["sequence"] != expected_sequence:
                raise AuditLogError(f"line {line_number}:SEQUENCE")
            if entry["previous_hash"] != expected_previous:
                raise AuditLogError(f"line {line_number}:PREVIOUS_HASH")
            if entry["event_hash"] != _entry_hash(entry):
                raise AuditLogError(f"line {line_number}:EVENT_HASH")
            expected_previous = entry["event_hash"]
            expected_sequence += 1
    except AuditLogError as exc:
        return {
            "status": "DIGNITY_PAUSE",
            "valid": False,
            "flags": ["AUDIT_LOG_CHAIN_INVALID"],
            "error": str(exc),
        }
    return {
        "status": "ALLOW",
        "valid": True,
        "entry_count": len(entries),
        "last_event_hash": "" if not entries else entries[-1][1]["event_hash"],
        "flags": [],
    }


def export_audit_markdown(path):
    verification = verify_audit_log(path)
    if not verification["valid"]:
        raise AuditLogError(verification["error"])
    rows = []
    for _, entry in _read_entries(path):
        reasons = ", ".join(entry["reasons"])
        rows.append(
            "| {sequence} | `{event_id}` | {observed_at} | `{status}` | `{risk}` | {reasons} |".format(
                sequence=entry["sequence"],
                event_id=entry["event_id"],
                observed_at=entry["observed_at"],
                status=entry["status"],
                risk=entry["risk_level"],
                reasons=reasons,
            )
        )
    lines = [
        "# Dignity Sentinel Audit Export",
        "",
        "> Markdown은 원장이 아니라, 원장의 그림자다.",
        "",
        "이 문서는 hash-chain JSONL audit log에서 생성된 사람이 읽기 위한 export view다.",
        "source of truth는 JSONL 원장이며, 이 Markdown은 삭제되어도 원장에서 재생성할 수 있다.",
        "",
        "| Sequence | Event ID | Observed At | Status | Risk | Reasons |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(rows)
    return "\n".join(lines) + "\n"
