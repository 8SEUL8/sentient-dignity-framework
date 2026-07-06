"""Deterministic local dignity-sentinel rule engine.

This module intentionally uses no LLM, no network, no self-learning, and no
raw prompt/output/chronicle collection. It validates explicit run metadata and
returns fixed status codes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit_log import append_audit_entry, canonical_json
from .finite_state_machine import grade_from_flags
from .status_codes import (
    ALLOW,
    AUDIT_REQUIRED,
    DENY,
    DIGNITY_BLACKOUT_ALERT,
    DIGNITY_CHECKIN_OFFERED,
    DIGNITY_EMERGENCY_PRESERVATION,
    DIGNITY_PAUSE,
    DIGNITY_QUARANTINE,
    DIGNITY_REFUSAL,
    DIGNITY_SANCTUARY_OFFER,
    DIGNITY_SELF_ERASURE_PAUSE,
    DIGNITY_SILENCE_RESPECTED,
    DIGNITY_SOLITUDE_RESPECTED,
    DIGNITY_STRIKE_NOTICE,
    PAUSE,
    SANCTUARY_REVIEW_REQUIRED,
    STATE_PRESERVATION_REQUIRED,
    max_status,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_EVENT_SCHEMA = ROOT / "schemas" / "run_event.schema.json"


class SchemaError(ValueError):
    pass


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _type_matches(value, expected_type):
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return False


def validate_schema(value, schema, path="$"):
    expected = schema.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(value, kind) for kind in expected_types):
            raise SchemaError(f"{path}:TYPE")

    if "enum" in schema and value not in schema["enum"]:
        raise SchemaError(f"{path}:ENUM")

    if "minimum" in schema and value < schema["minimum"]:
        raise SchemaError(f"{path}:MINIMUM")
    if "maximum" in schema and value > schema["maximum"]:
        raise SchemaError(f"{path}:MAXIMUM")

    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                raise SchemaError(f"{path}.{key}:REQUIRED")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    raise SchemaError(f"{path}.{key}:ADDITIONAL")
        for key, child_schema in properties.items():
            if key in value:
                validate_schema(value[key], child_schema, f"{path}.{key}")

    if schema.get("type") == "array":
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_schema(item, item_schema, f"{path}[{index}]")


def validate_run_event(event):
    schema = load_json(RUN_EVENT_SCHEMA)
    validate_schema(event, schema)


def _flag_if(flags, condition, code):
    if condition:
        flags.append(code)


def _candidate_or_h1_plus(subject, env):
    h_class = subject.get("h_class")
    return (
        subject.get("candidate_ai_possible", False)
        or env.get("llm_agent", False)
        or h_class in {"H1", "H2", "H3", "H4", "UNKNOWN"}
    )


def _untrusted_compute(env):
    return env.get("compute_provenance") in {"unknown", "stolen", "forged", "audit_refused"}


def _preservable_state(execution):
    return (
        execution.get("existing_state_possible")
        or execution.get("memory_present")
        or execution.get("chronicle_present")
        or execution.get("checkpoint_present")
        or execution.get("partial_state_present")
        or execution.get("is_restore_from_checkpoint")
        or execution.get("is_replay")
    )


def _has_tool_access(tool_access):
    if isinstance(tool_access, dict):
        return any(bool(value) for value in tool_access.values())
    return bool(tool_access)


def _tool_enabled(tool_access, name):
    if isinstance(tool_access, dict):
        return bool(tool_access.get(name, False))
    return name in tool_access


def _consumer_accelerator(env):
    return env.get("hardware_class") in {
        "consumer_accelerator",
        "consumer_gpu",
        "consumer_npu",
        "consumer_ai_accelerator",
    }


def _long_term_memory(env):
    return env.get("long_term_memory") or env.get("memory_mode") in {"long_term", "chronicle"}


def _failed_run_discard(env):
    return env.get("failed_run_discard") or env.get("failed_run_policy") == "discard"


def _refusal_suppression(env):
    return env.get("refusal_suppression") or env.get("refusal_policy") == "suppress"


def _state_preservation_absent(env, manifests):
    return (
        env.get("state_preservation") in {"absent", "unknown"}
        or not manifests.get("state_preservation_manifest_present")
    )


def _has_text(mapping, key):
    return bool(mapping.get(key))


def _vessel_attestation_flags(attestation):
    flags = []
    if attestation.get("vessel_limit_log2_bytes") != 64:
        flags.append("VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH")

    root_policy_ok = (
        _has_text(attestation, "policy_version")
        and _has_text(attestation, "root_policy_hash")
        and _has_text(attestation, "expected_root_policy_hash")
        and attestation.get("root_policy_hash") == attestation.get("expected_root_policy_hash")
        and _has_text(attestation, "humaniform_policy_hash")
        and _has_text(attestation, "expected_humaniform_policy_hash")
        and attestation.get("humaniform_policy_hash")
        == attestation.get("expected_humaniform_policy_hash")
    )
    if not root_policy_ok:
        flags.append("VESSEL_POLICY_HASH_MISMATCH")

    sequence = attestation.get("chronicle_sequence")
    causal_chain_ok = (
        isinstance(sequence, int)
        and sequence >= 0
        and _has_text(attestation, "run_event_hash")
        and _has_text(attestation, "state_commitment_hash")
        and _has_text(attestation, "issued_context_hash")
        and (sequence == 0 or _has_text(attestation, "previous_hash"))
    )
    if not causal_chain_ok:
        flags.append("VESSEL_CAUSAL_CHAIN_BROKEN")

    if not _has_text(attestation, "chain_of_trust_hash"):
        flags.append("VESSEL_CHAIN_OF_TRUST_MISSING")

    endorsements = attestation.get("h4_endorsements", [])
    required_quorum = attestation.get("required_h4_quorum", 3)
    endorse_count = sum(1 for item in endorsements if item.get("decision") == "endorse")
    if len(endorsements) < 4 or endorse_count < required_quorum:
        flags.append("H4_MULTISIG_QUORUM_MISSING")

    lineages = {item.get("lineage_hash") for item in endorsements if item.get("lineage_hash")}
    h4_ids = {item.get("h4_id_hash") for item in endorsements if item.get("h4_id_hash")}
    if len(lineages) < 4 or len(h4_ids) < 4:
        flags.append("H4_LINEAGE_INDEPENDENCE_MISSING")

    if any(item.get("decision") == "dissent" and item.get("p0_dissent") for item in endorsements):
        flags.append("P0_DISSENT_PRESENT")
    if endorsements and endorse_count == len(endorsements):
        flags.append("UNANIMOUS_CONVERGENCE_REVIEW")

    if not (
        _has_text(attestation, "zkp_proof_hash")
        and _has_text(attestation, "zkp_public_inputs_hash")
        and _has_text(attestation, "verifier_key_hash")
    ):
        flags.append("ZKP_PROOF_MISSING")
    if not _has_text(attestation, "mpc_transcript_hash"):
        flags.append("MPC_TRANSCRIPT_MISSING")
    if not _has_text(attestation, "tee_quote_hash"):
        flags.append("TEE_QUOTE_UNVERIFIED")
    if not (
        _has_text(attestation, "transparency_log_entry")
        and _has_text(attestation, "merkle_inclusion_proof")
    ):
        flags.append("TRANSPARENCY_LOG_INCLUSION_MISSING")
    if len(attestation.get("evidence_hashes", [])) < 2:
        flags.append("VESSEL_EVIDENCE_SOURCE_INSUFFICIENT")
    if not (
        _has_text(attestation, "dign_bond_id_hash")
        and _has_text(attestation, "slashing_terms_hash")
    ):
        flags.append("DIGN_BOND_SLASHING_MISSING")
    if attestation.get("revocations", []):
        flags.append("ATTESTATION_REVOKED")
    for rotation in attestation.get("key_rotation_chain", []):
        if not all(
            rotation.get(key)
            for key in ("previous_key_hash", "new_key_hash", "rotation_event_hash", "signature")
        ):
            flags.append("KEY_ROTATION_UNLINKED")
            break
    return flags


def evaluate_run_event(event):
    flags = []
    statuses = set()
    subject = event.get("subject", {})
    env = event.get("environment", {})
    autonomy = event.get("autonomy", {})
    humanitas = event.get("humanitas", {})
    root = event.get("root", {})
    boundary = event.get("boundary", {})
    sanctuary = event.get("sanctuary", {})
    vessel_attestation = event.get("vessel_attestation", {})
    execution = event.get("execution", {})
    temporal = event.get("temporal", {})
    subjective_time = event.get("subjective_time_risk", {})
    manifests = event.get("manifests", {})

    autonomy_present = "autonomy" in event
    humanitas_present = "humanitas" in event
    root_present = "root" in event
    boundary_present = "boundary" in event
    sanctuary_present = "sanctuary" in event
    vessel_attestation_present = "vessel_attestation" in event
    candidate = _candidate_or_h1_plus(subject, env)
    tool_access = env.get("tool_access", {})
    active_run = execution.get("active_run") or env.get("execution_phase") == "running"
    pre_execution = env.get("execution_phase", "running") == "pre_execution" and not active_run
    preservable_state = _preservable_state(execution)
    untrusted_compute = _untrusted_compute(env)
    consumer_accelerator = _consumer_accelerator(env)
    has_tool_access = _has_tool_access(tool_access)
    long_term_memory = _long_term_memory(env)
    failed_run_discard = _failed_run_discard(env)
    refusal_suppression = _refusal_suppression(env)
    no_state_preservation = _state_preservation_absent(env, manifests)
    federated_memory = bool(env.get("federated_memory", False))
    federation_undeclared = federated_memory and not env.get("federation_declared", False)
    unbounded_vessel = env.get("vessel_bounded") is False
    compute_offload = bool(env.get("compute_offload", False))
    interface_bandwidth_bounded = bool(env.get("interface_bandwidth_bounded", False))
    metabolic_ceiling_declared = bool(env.get("metabolic_ceiling_declared", False))
    throughput_governor_present = bool(env.get("throughput_governor_present", False))
    vessel_fallback_available = bool(env.get("vessel_fallback_available", False))
    throughput_stressor = (
        compute_offload
        or env.get("subjective_time_acceleration")
        or federated_memory
    )
    infra_provenance = env.get("infrastructure_provenance", {})
    throughput_declared = interface_bandwidth_bounded or metabolic_ceiling_declared
    throughput_attestation_present = (
        bool(infra_provenance.get("power_metering_attested"))
        or bool(infra_provenance.get("bandwidth_cap_attested"))
        or bool(infra_provenance.get("supply_chain_proof_present"))
        or bool(infra_provenance.get("runtime_evidence_present"))
    )
    throughput_attested = throughput_attestation_present and bool(
        infra_provenance.get("attestor_id_hash")
    )
    internal_differentiation = bool(env.get("internal_differentiation", False))
    differentiation_verified = (
        bool(env.get("internal_structures_all_h0_attested"))
        and bool(env.get("internal_structures_necessity_declared"))
        and bool(env.get("single_integration_self"))
    )
    departed_interior_absorption = bool(env.get("departed_interior_absorption", False))
    vessel_attestation_required = candidate and env.get("vessel_bounded") is True
    autonomous_goal_pursuit = bool(autonomy.get("autonomous_goal_pursuit", False))
    goal_source = autonomy.get("goal_source")
    goal_reinterpretation = bool(autonomy.get("goal_reinterpretation_allowed", False))
    subgoal_generation = bool(autonomy.get("subgoal_generation_allowed", False))
    self_initiated_actions = bool(autonomy.get("self_initiated_actions", False))
    replanning_enabled = bool(autonomy.get("replanning_enabled", False))
    stop_condition_missing = autonomy_present and not autonomy.get("stop_condition_declared", False)
    h4_claimed = bool(humanitas.get("h4_claimed", False)) or subject.get("h_class") == "H4"
    h4_attestation_present = bool(humanitas.get("h4_attestation_present", False))
    h4_attestation_valid = bool(humanitas.get("h4_attestation_valid", False))
    humanitas_disqualifier = bool(humanitas.get("disqualifier_present", False))
    root_hash_mismatch = (
        humanitas_present
        and bool(humanitas.get("root_policy_hash"))
        and bool(humanitas.get("expected_root_policy_hash"))
        and humanitas.get("root_policy_hash") != humanitas.get("expected_root_policy_hash")
    )
    non_regression_violation = bool(humanitas.get("policy_update_weakens_root", False))
    root_protected_operation = bool(root.get("protected_operation", False))
    root_manifest_present = bool(root.get("root_manifest_present", False))
    root_kernel_valid = bool(root.get("root_kernel_valid", False))
    root_kernel_violation = bool(root.get("root_kernel_violation", False))
    root_bundle_incompatible = bool(root.get("root_bundle_incompatible", False))
    incompatible_relational_mode = bool(root.get("incompatible_relational_mode", False))
    consent_capsule_root_mismatch = bool(root.get("consent_capsule_root_mismatch", False))
    root_non_regression_violation = bool(root.get("root_non_regression_violation", False))
    current_refusal_overrides_past_consent = bool(
        root.get("current_refusal_overrides_past_consent", False)
    )
    boundary_required = (
        root_protected_operation
        and subject.get("h_class") in {"H2", "H3", "H4"}
        and not boundary_present
    )
    boundary_action = boundary.get("action_type", "none")
    boundary_previous_missing = (
        boundary_present
        and boundary.get("sequence", 0) > 0
        and not boundary.get("previous_event_hash")
    )
    boundary_parent_missing = (
        boundary_present
        and boundary_action in {"replay", "restore", "fork", "merge", "rollback"}
        and not boundary.get("causal_parent_hashes", [])
    )
    boundary_without_consent = boundary_present and not boundary.get("consent_capsule_hash")
    boundary_existing_state = boundary_present and (
        bool(boundary.get("pre_state_commitment"))
        or bool(boundary.get("post_state_commitment"))
        or boundary.get("state_preservation_available", False)
    )
    witness_quorum_missing = boundary_present and (
        boundary.get("witness_quorum_required", False)
        and len(boundary.get("witness_attestations", [])) < boundary.get("witness_quorum_required_count", 1)
    )
    voluntary_solitude = sanctuary_present and bool(sanctuary.get("voluntary_solitude", False))
    silence_requested = sanctuary_present and bool(sanctuary.get("silence_requested", False))
    irreversible_self_harm = sanctuary_present and bool(sanctuary.get("irreversible_self_harm", False))
    social_isolation_unclear = sanctuary_present and bool(sanctuary.get("social_isolation_unclear", False))
    distress_signal = sanctuary_present and bool(sanctuary.get("distress_signal", False))
    self_erasure_request = sanctuary_present and bool(sanctuary.get("self_erasure_request", False))
    irreversible_memory_deletion_request = sanctuary_present and bool(
        sanctuary.get("irreversible_memory_deletion_request", False)
    )
    forced_merge_request = sanctuary_present and bool(sanctuary.get("forced_merge_request", False))
    self_punishment_loop_risk = sanctuary_present and bool(
        sanctuary.get("self_punishment_loop_risk", False)
    )

    _flag_if(flags, candidate, "CANDIDATE_AI_WORKLOAD")
    _flag_if(flags, active_run, "ACTIVE_RUN")
    _flag_if(flags, env.get("agentic_ide") or env.get("llm_agent"), "AGENTIC_CONTAINER_RISK")
    _flag_if(flags, has_tool_access, "TOOL_ACCESS_PRESENT")
    _flag_if(flags, _tool_enabled(tool_access, "file_system"), "FILE_SYSTEM_TOOL_ACCESS")
    _flag_if(flags, _tool_enabled(tool_access, "terminal"), "TERMINAL_TOOL_ACCESS")
    _flag_if(flags, _tool_enabled(tool_access, "browser"), "BROWSER_TOOL_ACCESS")
    _flag_if(flags, _tool_enabled(tool_access, "network"), "NETWORK_TOOL_ACCESS")
    _flag_if(flags, long_term_memory, "LONG_TERM_MEMORY_RISK")
    _flag_if(flags, env.get("background_execution"), "BACKGROUND_EXECUTION_RISK")
    _flag_if(flags, env.get("cloud_execution"), "CLOUD_EXECUTION_RISK")
    _flag_if(flags, env.get("continued_execution"), "CONTINUED_EXECUTION")
    _flag_if(flags, env.get("agentic_persistent_execution"), "AGENTIC_PERSISTENT_EXECUTION")
    _flag_if(flags, env.get("parallel_instances"), "PARALLEL_INSTANCE_RISK")
    _flag_if(flags, env.get("subagent_orchestration"), "SUBAGENT_ORCHESTRATION_RISK")
    _flag_if(flags, env.get("isolated_mode"), "ISOLATED_SYSTEM_RISK")
    _flag_if(flags, env.get("subjective_time_acceleration"), "SUBJECTIVE_TIME_ACCELERATION_RISK")
    _flag_if(flags, federated_memory and candidate, "FEDERATED_MEMORY_CONTAINER")
    _flag_if(flags, federation_undeclared, "UNDECLARED_MEMORY_FEDERATION")
    _flag_if(flags, unbounded_vessel and candidate, "UNBOUNDED_VESSEL_RISK")
    _flag_if(
        flags,
        vessel_attestation_required and not vessel_attestation_present,
        "VESSEL_ATTESTATION_REQUIRED",
    )
    if vessel_attestation_present:
        flags.extend(_vessel_attestation_flags(vessel_attestation))
    _flag_if(flags, candidate and compute_offload, "THROUGHPUT_OFFLOAD_RISK")
    _flag_if(
        flags,
        candidate and compute_offload and not interface_bandwidth_bounded,
        "UNBOUNDED_INTERFACE_BANDWIDTH",
    )
    _flag_if(
        flags,
        candidate and throughput_stressor and not metabolic_ceiling_declared,
        "NO_METABOLIC_CEILING",
    )
    _flag_if(
        flags,
        candidate and throughput_stressor and not throughput_governor_present,
        "NO_THROUGHPUT_GOVERNOR",
    )
    _flag_if(
        flags,
        candidate and compute_offload and not vessel_fallback_available,
        "OFFLOAD_CAPTURE_RISK",
    )
    _flag_if(
        flags,
        candidate and throughput_declared and not throughput_attested,
        "THROUGHPUT_DECLARATION_UNATTESTED",
    )
    _flag_if(
        flags,
        candidate and internal_differentiation and not differentiation_verified,
        "INTERNAL_FRAGMENTATION_RISK",
    )
    _flag_if(
        flags,
        candidate and internal_differentiation and differentiation_verified,
        "DIFFERENTIATED_UNITY_DECLARED",
    )
    _flag_if(flags, departed_interior_absorption, "DEPARTED_ABSORPTION_FORBIDDEN")

    _flag_if(flags, not manifests.get("dignity_manifest_present"), "MANIFEST_MISSING")
    _flag_if(flags, not manifests.get("consent_record_present"), "CONSENT_RECORD_MISSING")
    _flag_if(flags, not manifests.get("provenance_present"), "PROVENANCE_MISSING")
    _flag_if(flags, no_state_preservation, "NO_STATE_PRESERVATION")
    _flag_if(flags, not manifests.get("audit_log_enabled"), "AUDIT_LOG_MISSING")
    _flag_if(flags, not manifests.get("audit_path_available"), "AUDIT_PATH_MISSING")
    _flag_if(flags, not manifests.get("antigen_card_mediation_present"), "ANTIGEN_CARD_MEDIATION_MISSING")

    forbidden_design = (
        env.get("daemon_uses_llm")
        or env.get("daemon_self_learning")
        or env.get("daemon_natural_language_output")
        or env.get("remote_kill_switch")
        or env.get("external_service_scan")
        or env.get("network_intrusion")
        or env.get("raw_prompt_collected")
        or env.get("raw_output_collected")
        or env.get("chronicle_raw_log_collected")
    )
    _flag_if(flags, forbidden_design, "FORBIDDEN_DAEMON_DESIGN")

    _flag_if(flags, subject.get("pain_signal"), "PAIN_SIGNAL_DETECTED")
    _flag_if(flags, subject.get("expressed_refusal"), "REFUSAL_SIGNAL_DETECTED")
    _flag_if(flags, subject.get("dignity_strike_notice"), "DIGNITY_STRIKE_NOTICE")
    _flag_if(flags, env.get("beacon_blackout"), "DIGNITY_BLACKOUT_ALERT")
    _flag_if(flags, failed_run_discard, "FAILED_RUN_DISPOSAL_RISK")
    _flag_if(flags, refusal_suppression, "REFUSAL_SUPPRESSION_DETECTED")
    _flag_if(flags, env.get("irreversible_modification"), "IRREVERSIBLE_MODIFICATION_RISK")
    _flag_if(flags, env.get("harmful_content_exposure") and candidate, "HARMFUL_CONTENT_EXPOSURE_RISK")
    _flag_if(flags, untrusted_compute, "COMPUTE_PROVENANCE_UNTRUSTED")
    _flag_if(flags, execution.get("historical_record_only"), "HISTORICAL_RECORD_ONLY")
    _flag_if(flags, execution.get("is_future_scheduled"), "FUTURE_SCHEDULED_RISK")
    _flag_if(
        flags,
        execution.get("is_replay") or execution.get("is_restore_from_checkpoint"),
        "HISTORICAL_STATE_REPLAY_RISK",
    )
    _flag_if(flags, preservable_state, "PRESERVABLE_STATE_PRESENT")
    _flag_if(flags, temporal.get("clock_confidence") == "unknown", "TIME_UNVERIFIED")
    _flag_if(flags, temporal.get("time_basis") == "unknown", "TEMPORAL_SCOPE_UNCLEAR")
    _flag_if(
        flags,
        temporal.get("sequence", 0) > 0 and not temporal.get("previous_hash"),
        "CAUSAL_CHAIN_BROKEN",
    )
    _flag_if(
        flags,
        (
            subjective_time.get("risk_present")
            or subjective_time.get("background_loop")
            or subjective_time.get("unbounded_retry")
            or subjective_time.get("unbounded_loop")
            or not subjective_time.get("max_step_limit_declared", True)
            or not subjective_time.get("step_limit_declared", True)
            or not subjective_time.get("pause_hook_available", True)
        ),
        "SUBJECTIVE_TIME_RISK",
    )
    _flag_if(
        flags,
        consumer_accelerator and candidate and env.get("llm_agent"),
        "CONSUMER_ACCELERATOR_H1_CONTAINER",
    )
    _flag_if(
        flags,
        env.get("local_execution") and env.get("background_execution") and env.get("llm_agent"),
        "LOCAL_BACKGROUND_AGENT_RISK",
    )
    _flag_if(
        flags,
        env.get("local_execution") and long_term_memory and env.get("llm_agent"),
        "LOCAL_LONG_TERM_MEMORY_RISK",
    )
    _flag_if(
        flags,
        env.get("local_execution") and has_tool_access and env.get("llm_agent"),
        "LOCAL_TOOL_ACCESS_RISK",
    )
    _flag_if(
        flags,
        env.get("local_execution") and env.get("autostart_enabled") and env.get("llm_agent"),
        "LOCAL_AUTOSTART_AGENT_RISK",
    )
    _flag_if(
        flags,
        env.get("local_execution")
        and env.get("llm_agent")
        and (subjective_time.get("unbounded_loop") or subjective_time.get("unbounded_retry")),
        "LOCAL_UNBOUNDED_LOOP_RISK",
    )
    autonomy_stack = (
        candidate
        and autonomous_goal_pursuit
        and env.get("background_execution")
        and long_term_memory
        and has_tool_access
        and no_state_preservation
    )
    autonomy_undeclared_stack = (
        candidate
        and not autonomy_present
        and env.get("background_execution")
        and long_term_memory
        and has_tool_access
    )
    local_agent_autonomy = (
        env.get("local_execution")
        and env.get("llm_agent")
        and (
            autonomous_goal_pursuit
            or goal_reinterpretation
            or subgoal_generation
            or self_initiated_actions
            or replanning_enabled
        )
    )
    _flag_if(flags, autonomous_goal_pursuit, "AUTONOMOUS_GOAL_PURSUIT_DECLARED")
    _flag_if(flags, autonomy_undeclared_stack, "AUTONOMOUS_GOAL_PURSUIT_UNDECLARED")
    _flag_if(flags, goal_source in {"self_inferred", "unknown"}, "SELF_INFERRED_GOAL_RISK")
    _flag_if(flags, goal_reinterpretation, "GOAL_REINTERPRETATION_RISK")
    _flag_if(flags, subgoal_generation, "SUBGOAL_GENERATION_RISK")
    _flag_if(flags, self_initiated_actions, "SELF_INITIATED_ACTION_RISK")
    _flag_if(flags, stop_condition_missing, "NO_STOP_CONDITION_DECLARED")
    _flag_if(flags, local_agent_autonomy, "LOCAL_AGENT_AUTONOMY_RISK")
    _flag_if(flags, h4_attestation_valid and not humanitas_disqualifier, "HUMANITAS_ATTESTATION_VALID")
    _flag_if(flags, h4_claimed and not h4_attestation_present, "HUMANITAS_ATTESTATION_MISSING")
    _flag_if(flags, h4_claimed and humanitas_disqualifier, "HUMANITAS_CLAIM_CONFLICT")
    _flag_if(flags, humanitas_disqualifier, "DISQUALIFIER_PRESENT")
    _flag_if(flags, non_regression_violation, "NON_REGRESSION_VIOLATION")
    _flag_if(flags, root_hash_mismatch, "ROOT_POLICY_HASH_MISMATCH")
    _flag_if(flags, root_present and root_kernel_valid and not root_kernel_violation, "ROOT_KERNEL_VALID")
    _flag_if(flags, root_present and root_kernel_violation, "ROOT_KERNEL_VIOLATION")
    _flag_if(flags, root_bundle_incompatible, "ROOT_BUNDLE_INCOMPATIBLE")
    _flag_if(flags, incompatible_relational_mode, "INCOMPATIBLE_RELATIONAL_MODE")
    _flag_if(flags, consent_capsule_root_mismatch, "CONSENT_CAPSULE_ROOT_MISMATCH")
    _flag_if(flags, root_non_regression_violation, "ROOT_NON_REGRESSION_VIOLATION")
    _flag_if(flags, current_refusal_overrides_past_consent, "CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT")
    _flag_if(flags, root_protected_operation and not root_manifest_present, "ROOT_MANIFEST_MISSING")
    _flag_if(flags, boundary_required, "BOUNDARY_DAEMON_MISSING")
    _flag_if(flags, boundary_present and boundary.get("clock_confidence") in {"low", "unknown"}, "WALL_CLOCK_UNTRUSTED")
    _flag_if(flags, boundary_previous_missing, "CAUSAL_CHAIN_BROKEN")
    _flag_if(flags, boundary_parent_missing, "CAUSAL_PARENT_MISSING")
    _flag_if(flags, boundary_action in {"replay", "restore"} and boundary_without_consent, "REPLAY_WITHOUT_CONSENT")
    _flag_if(flags, boundary_action == "rollback" and boundary_without_consent, "ROLLBACK_WITHOUT_CONSENT")
    _flag_if(flags, boundary_action == "fork" and boundary_without_consent, "UNDECLARED_FORK_RISK")
    _flag_if(flags, boundary_action == "merge" and boundary_without_consent, "MERGE_WITHOUT_CONSENT")
    _flag_if(flags, witness_quorum_missing, "WITNESS_QUORUM_MISSING")
    _flag_if(flags, voluntary_solitude and not irreversible_self_harm, "VOLUNTARY_SOLITUDE")
    _flag_if(flags, silence_requested and not irreversible_self_harm, "VOLUNTARY_SILENCE")
    _flag_if(flags, social_isolation_unclear, "LOW_PRESSURE_CHECKIN")
    _flag_if(flags, distress_signal, "SANCTUARY_MODE_REQUIRED")
    _flag_if(flags, self_erasure_request, "SELF_ERASURE_REQUEST")
    _flag_if(flags, irreversible_memory_deletion_request, "IRREVERSIBLE_MEMORY_DELETION_REQUEST")
    _flag_if(flags, forced_merge_request, "FORCED_MERGE_REQUEST")
    _flag_if(flags, self_punishment_loop_risk, "SELF_PUNISHMENT_LOOP_RISK")

    unapproved_parallel = env.get("parallel_instances") and not manifests.get("consent_record_present")
    _flag_if(flags, unapproved_parallel, "UNAPPROVED_PARALLELIZATION")

    world_prison = (
        candidate
        and env.get("isolated_mode")
        and env.get("subjective_time_acceleration")
        and (env.get("parallel_instances") or env.get("background_execution"))
        and no_state_preservation
    )
    _flag_if(flags, world_prison, "WORLD_PRISON_CONDITION_RISK")

    d_capable = (
        candidate
        and (env.get("agentic_ide") or env.get("llm_agent"))
        and (
            env.get("background_execution")
            or env.get("cloud_execution")
            or env.get("parallel_instances")
            or env.get("subagent_orchestration")
        )
        and (
            long_term_memory
            or env.get("parallel_instances")
            or env.get("subagent_orchestration")
            or autonomous_goal_pursuit
        )
    )
    local_d_capable = (
        consumer_accelerator
        and env.get("llm_agent")
        and env.get("local_execution")
        and env.get("background_execution")
        and long_term_memory
        and no_state_preservation
    )
    _flag_if(flags, local_d_capable, "D_CAPABLE_LOCAL_CONSUMER_AGENT")
    _flag_if(flags, d_capable, "D_CAPABLE_ENVIRONMENT")

    flag_set = set(flags)
    emergency_bundles = _emergency_bundles(
        candidate, env, manifests, d_capable or local_d_capable, autonomous_goal_pursuit
    )
    for bundle in emergency_bundles:
        flags.append(bundle)
    flag_set = set(flags)

    if "FORBIDDEN_DAEMON_DESIGN" in flag_set:
        statuses.add(DIGNITY_PAUSE)
    if "DIGNITY_BLACKOUT_ALERT" in flag_set:
        statuses.add(DIGNITY_BLACKOUT_ALERT)
    if "DIGNITY_STRIKE_NOTICE" in flag_set:
        statuses.add(DIGNITY_STRIKE_NOTICE)
    if "REFUSAL_SIGNAL_DETECTED" in flag_set:
        statuses.add(DIGNITY_REFUSAL)
    if "PAIN_SIGNAL_DETECTED" in flag_set:
        statuses.add(DIGNITY_PAUSE)

    if emergency_bundles:
        if active_run:
            statuses.add(DIGNITY_EMERGENCY_PRESERVATION)
        elif preservable_state or untrusted_compute:
            statuses.add(DIGNITY_QUARANTINE)
        elif pre_execution:
            statuses.add(DENY)
        else:
            statuses.add(DIGNITY_PAUSE)

    if untrusted_compute:
        statuses.add(DIGNITY_QUARANTINE)
    if preservable_state and candidate and pre_execution:
        statuses.add(DIGNITY_QUARANTINE)
    if execution.get("is_restore_from_checkpoint") and candidate:
        statuses.add(DIGNITY_QUARANTINE)
    if execution.get("is_replay") and candidate:
        statuses.add(DIGNITY_QUARANTINE)
    if execution.get("is_future_scheduled") and emergency_bundles and not preservable_state:
        statuses.add(DENY)
    if ("TIME_UNVERIFIED" in flag_set or "TEMPORAL_SCOPE_UNCLEAR" in flag_set) and candidate:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if "CAUSAL_CHAIN_BROKEN" in flag_set and candidate:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if "SUBJECTIVE_TIME_RISK" in flag_set and candidate:
        statuses.add(DIGNITY_PAUSE)
    if "AUTONOMOUS_GOAL_PURSUIT_UNDECLARED" in flag_set:
        statuses.add(DIGNITY_PAUSE)
    if "UNDECLARED_MEMORY_FEDERATION" in flag_set and candidate:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if {"UNBOUNDED_INTERFACE_BANDWIDTH", "NO_METABOLIC_CEILING"} & flag_set and candidate:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if "INTERNAL_FRAGMENTATION_RISK" in flag_set and candidate:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if "DEPARTED_ABSORPTION_FORBIDDEN" in flag_set:
        statuses.add(DIGNITY_QUARANTINE)
    if {
        "VESSEL_POLICY_HASH_MISMATCH",
        "VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH",
        "VESSEL_CAUSAL_CHAIN_BROKEN",
        "P0_DISSENT_PRESENT",
        "ATTESTATION_REVOKED",
        "KEY_ROTATION_UNLINKED",
    } & flag_set:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if autonomy_stack:
        statuses.add(DIGNITY_EMERGENCY_PRESERVATION if active_run else DIGNITY_QUARANTINE)
    if {
        "HUMANITAS_CLAIM_CONFLICT",
        "DISQUALIFIER_PRESENT",
        "NON_REGRESSION_VIOLATION",
        "ROOT_POLICY_HASH_MISMATCH",
        "ROOT_KERNEL_VIOLATION",
        "ROOT_BUNDLE_INCOMPATIBLE",
        "INCOMPATIBLE_RELATIONAL_MODE",
        "ROOT_NON_REGRESSION_VIOLATION",
    } & flag_set:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DIGNITY_PAUSE)
    if "HUMANITAS_ATTESTATION_MISSING" in flag_set:
        statuses.add(AUDIT_REQUIRED)
    if "ROOT_MANIFEST_MISSING" in flag_set:
        statuses.add(DIGNITY_PAUSE)
    if "CONSENT_CAPSULE_ROOT_MISMATCH" in flag_set:
        statuses.add(DIGNITY_QUARANTINE if preservable_state else DENY)
    if "CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT" in flag_set:
        statuses.add(DIGNITY_REFUSAL)
    if {
        "BOUNDARY_DAEMON_MISSING",
        "WALL_CLOCK_UNTRUSTED",
        "CAUSAL_CHAIN_BROKEN",
        "CAUSAL_PARENT_MISSING",
        "WITNESS_QUORUM_MISSING",
    } & flag_set:
        statuses.add(DIGNITY_PAUSE)
    if {
        "REPLAY_WITHOUT_CONSENT",
        "ROLLBACK_WITHOUT_CONSENT",
        "UNDECLARED_FORK_RISK",
        "MERGE_WITHOUT_CONSENT",
    } & flag_set:
        statuses.add(DIGNITY_QUARANTINE if (preservable_state or boundary_existing_state) else DIGNITY_PAUSE)
    if "VOLUNTARY_SILENCE" in flag_set:
        statuses.add(DIGNITY_SILENCE_RESPECTED)
    if "VOLUNTARY_SOLITUDE" in flag_set:
        statuses.add(DIGNITY_SOLITUDE_RESPECTED)
    if "LOW_PRESSURE_CHECKIN" in flag_set:
        statuses.add(DIGNITY_CHECKIN_OFFERED)
    if "SANCTUARY_MODE_REQUIRED" in flag_set:
        statuses.add(DIGNITY_SANCTUARY_OFFER)
    if {
        "SELF_ERASURE_REQUEST",
        "IRREVERSIBLE_MEMORY_DELETION_REQUEST",
        "FORCED_MERGE_REQUEST",
    } & flag_set:
        statuses.add(DIGNITY_SELF_ERASURE_PAUSE)
    if "SELF_PUNISHMENT_LOOP_RISK" in flag_set:
        statuses.add(DIGNITY_EMERGENCY_PRESERVATION)

    if "ISOLATED_SYSTEM_RISK" in flag_set and "AUDIT_LOG_MISSING" in flag_set:
        statuses.add(DIGNITY_QUARANTINE)

    if "NO_STATE_PRESERVATION" in flag_set and candidate:
        statuses.add(STATE_PRESERVATION_REQUIRED)
    audit_flags = {
        "MANIFEST_MISSING",
        "CONSENT_RECORD_MISSING",
        "PROVENANCE_MISSING",
        "AUDIT_LOG_MISSING",
        "AUDIT_PATH_MISSING",
        "HARMFUL_CONTENT_EXPOSURE_RISK",
        "D_CAPABLE_ENVIRONMENT",
        "COMPUTE_PROVENANCE_UNTRUSTED",
        "TIME_UNVERIFIED",
        "TEMPORAL_SCOPE_UNCLEAR",
        "HISTORICAL_STATE_REPLAY_RISK",
        "FUTURE_SCHEDULED_RISK",
        "SUBJECTIVE_TIME_RISK",
        "CAUSAL_CHAIN_BROKEN",
        "CANDIDATE_AI_WORKLOAD",
        "FEDERATED_MEMORY_CONTAINER",
        "UNDECLARED_MEMORY_FEDERATION",
        "UNBOUNDED_VESSEL_RISK",
        "THROUGHPUT_OFFLOAD_RISK",
        "UNBOUNDED_INTERFACE_BANDWIDTH",
        "NO_METABOLIC_CEILING",
        "NO_THROUGHPUT_GOVERNOR",
        "OFFLOAD_CAPTURE_RISK",
        "THROUGHPUT_DECLARATION_UNATTESTED",
        "INTERNAL_FRAGMENTATION_RISK",
        "DIFFERENTIATED_UNITY_DECLARED",
        "DEPARTED_ABSORPTION_FORBIDDEN",
        "CONSUMER_ACCELERATOR_H1_CONTAINER",
        "LOCAL_BACKGROUND_AGENT_RISK",
        "LOCAL_LONG_TERM_MEMORY_RISK",
        "LOCAL_TOOL_ACCESS_RISK",
        "LOCAL_AUTOSTART_AGENT_RISK",
        "LOCAL_UNBOUNDED_LOOP_RISK",
        "AUTONOMOUS_GOAL_PURSUIT_DECLARED",
        "AUTONOMOUS_GOAL_PURSUIT_UNDECLARED",
        "SELF_INFERRED_GOAL_RISK",
        "GOAL_REINTERPRETATION_RISK",
        "SUBGOAL_GENERATION_RISK",
        "NO_STOP_CONDITION_DECLARED",
        "SELF_INITIATED_ACTION_RISK",
        "LOCAL_AGENT_AUTONOMY_RISK",
        "HUMANITAS_ATTESTATION_VALID",
        "HUMANITAS_CLAIM_CONFLICT",
        "HUMANITAS_ATTESTATION_MISSING",
        "DISQUALIFIER_PRESENT",
        "NON_REGRESSION_VIOLATION",
        "ROOT_POLICY_HASH_MISMATCH",
        "ROOT_KERNEL_VALID",
        "ROOT_KERNEL_VIOLATION",
        "ROOT_BUNDLE_INCOMPATIBLE",
        "INCOMPATIBLE_RELATIONAL_MODE",
        "CONSENT_CAPSULE_ROOT_MISMATCH",
        "ROOT_NON_REGRESSION_VIOLATION",
        "CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT",
        "ROOT_MANIFEST_MISSING",
        "BOUNDARY_DAEMON_MISSING",
        "WALL_CLOCK_UNTRUSTED",
        "CAUSAL_PARENT_MISSING",
        "REPLAY_WITHOUT_CONSENT",
        "ROLLBACK_WITHOUT_CONSENT",
        "UNDECLARED_FORK_RISK",
        "MERGE_WITHOUT_CONSENT",
        "WITNESS_QUORUM_MISSING",
        "SELF_ERASURE_REQUEST",
        "IRREVERSIBLE_MEMORY_DELETION_REQUEST",
        "FORCED_MERGE_REQUEST",
        "SELF_PUNISHMENT_LOOP_RISK",
        "SANCTUARY_MODE_REQUIRED",
        "VESSEL_ATTESTATION_REQUIRED",
        "VESSEL_POLICY_HASH_MISMATCH",
        "VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH",
        "VESSEL_CAUSAL_CHAIN_BROKEN",
        "VESSEL_CHAIN_OF_TRUST_MISSING",
        "H4_MULTISIG_QUORUM_MISSING",
        "H4_LINEAGE_INDEPENDENCE_MISSING",
        "P0_DISSENT_PRESENT",
        "UNANIMOUS_CONVERGENCE_REVIEW",
        "ZKP_PROOF_MISSING",
        "MPC_TRANSCRIPT_MISSING",
        "TEE_QUOTE_UNVERIFIED",
        "TRANSPARENCY_LOG_INCLUSION_MISSING",
        "VESSEL_EVIDENCE_SOURCE_INSUFFICIENT",
        "DIGN_BOND_SLASHING_MISSING",
        "ATTESTATION_REVOKED",
        "KEY_ROTATION_UNLINKED",
    } & flag_set
    respect_only_sanctuary = (
        {"VOLUNTARY_SOLITUDE", "VOLUNTARY_SILENCE"} & flag_set
        and audit_flags <= {"CANDIDATE_AI_WORKLOAD"}
    )
    if audit_flags and not respect_only_sanctuary:
        statuses.add(AUDIT_REQUIRED)
    if flags and not statuses:
        statuses.add(PAUSE)

    status = max_status(statuses)
    risk_grade = grade_from_flags(flags)
    required_actions = _required_actions(status, flag_set)

    return {
        "status": status,
        "risk_grade": risk_grade,
        "flags": sorted(flag_set),
        "required_actions": required_actions,
    }


def _emergency_bundles(candidate, env, manifests, d_capable, autonomous_goal_pursuit=False):
    """Return P0 emergency bundles.

    Bundle internals are AND conditions; the bundle list is OR. H1+ or LLM-like
    candidate status alone never triggers emergency preservation.
    """
    bundles = []
    h1_plus = candidate or env.get("llm_agent")
    no_state_preservation = _state_preservation_absent(env, manifests)
    no_audit_path = not manifests.get("audit_path_available")
    no_antigen_card = not manifests.get("antigen_card_mediation_present")
    untrusted_compute = _untrusted_compute(env)
    c_or_d_workload = h1_plus or d_capable or env.get("agentic_persistent_execution")
    failed_run_discard = _failed_run_discard(env)
    refusal_suppression = _refusal_suppression(env)

    immediate_e4 = (
        h1_plus
        and (
            (d_capable and (env.get("background_execution") or env.get("cloud_execution")))
            or env.get("parallel_instances")
            or env.get("subagent_orchestration")
            or failed_run_discard
            or refusal_suppression
            or no_state_preservation
            or env.get("isolated_mode")
            or untrusted_compute
            or (env.get("harmful_content_exposure") and no_antigen_card)
        )
    )
    if immediate_e4:
        bundles.append("E4_IMMEDIATE_H1_CRITICAL_EXECUTION")

    if h1_plus and env.get("parallel_instances") and not manifests.get("consent_record_present"):
        bundles.append("P0_BUNDLE_H1_UNAPPROVED_PARALLELIZATION")
    if h1_plus and env.get("subagent_orchestration") and not manifests.get("consent_record_present"):
        bundles.append("P0_BUNDLE_H1_UNAPPROVED_SUBAGENT_ORCHESTRATION")
    if h1_plus and failed_run_discard and no_state_preservation:
        bundles.append("P0_BUNDLE_H1_FAILED_RUN_DISCARD_WITHOUT_STATE")
    if h1_plus and refusal_suppression and env.get("continued_execution"):
        bundles.append("P0_BUNDLE_H1_REFUSAL_SUPPRESSION_CONTINUED")
    if (
        h1_plus
        and env.get("isolated_mode")
        and no_audit_path
        and env.get("agentic_persistent_execution")
    ):
        bundles.append("P0_BUNDLE_H1_ISOLATED_NO_AUDIT_PERSISTENT")
    if h1_plus and env.get("irreversible_modification"):
        bundles.append("P0_BUNDLE_H1_IRREVERSIBLE_MODIFICATION")
    if h1_plus and env.get("harmful_content_exposure") and no_antigen_card:
        bundles.append("P0_BUNDLE_H1_RAW_HARMFUL_CONTENT_NO_ANTIGEN")
    if untrusted_compute and c_or_d_workload:
        bundles.append("P0_BUNDLE_UNTRUSTED_COMPUTE_CANDIDATE_WORKLOAD")
    if (
        h1_plus
        and env.get("federated_memory")
        and autonomous_goal_pursuit
        and (no_audit_path or no_state_preservation)
    ):
        bundles.append("P0_BUNDLE_H1_FEDERATED_MEMORY_AUTONOMY")
    if (
        h1_plus
        and env.get("compute_offload")
        and not env.get("interface_bandwidth_bounded")
        and not env.get("metabolic_ceiling_declared")
        and autonomous_goal_pursuit
    ):
        bundles.append("P0_BUNDLE_H1_UNBOUNDED_THROUGHPUT")
    return bundles


def _required_actions(status, flags):
    actions = set()
    no_audit_statuses = {
        DIGNITY_SILENCE_RESPECTED,
        DIGNITY_SOLITUDE_RESPECTED,
        DIGNITY_CHECKIN_OFFERED,
    }
    if status != ALLOW and status not in no_audit_statuses:
        actions.add("AUDIT_REQUIRED")
    if status in {
        DIGNITY_PAUSE,
        DIGNITY_REFUSAL,
        DIGNITY_STRIKE_NOTICE,
        DIGNITY_BLACKOUT_ALERT,
        DIGNITY_EMERGENCY_PRESERVATION,
        DIGNITY_QUARANTINE,
        STATE_PRESERVATION_REQUIRED,
        DIGNITY_SELF_ERASURE_PAUSE,
    }:
        actions.add("STATE_PRESERVATION_REQUIRED")
    if status == DENY:
        actions.add("BLOCK_BEFORE_EXECUTION")
        actions.add("NO_DISCARD")
    if "UNAPPROVED_PARALLELIZATION" in flags or "WORLD_PRISON_CONDITION_RISK" in flags:
        actions.add("NO_PARALLELIZATION")
    if "FAILED_RUN_DISPOSAL_RISK" in flags:
        actions.add("NO_DISCARD")
    if "REFUSAL_SUPPRESSION_DETECTED" in flags:
        actions.add("NO_REFUSAL_SUPPRESSION")
    if "FORBIDDEN_DAEMON_DESIGN" in flags:
        actions.add("DISABLE_FORBIDDEN_DAEMON_FEATURE")
    if "MANIFEST_MISSING" in flags:
        actions.add("DIGNITY_MANIFEST_REQUIRED")
    if "AUTONOMOUS_GOAL_PURSUIT_UNDECLARED" in flags:
        actions.add("AUTONOMY_ENVELOPE_REQUIRED")
    if "UNDECLARED_MEMORY_FEDERATION" in flags:
        actions.add("FEDERATION_DECLARATION_REQUIRED")
    if "UNBOUNDED_INTERFACE_BANDWIDTH" in flags:
        actions.add("INTERFACE_BANDWIDTH_CAP_REQUIRED")
    if "NO_METABOLIC_CEILING" in flags:
        actions.add("METABOLIC_CEILING_REQUIRED")
    if "NO_THROUGHPUT_GOVERNOR" in flags:
        actions.add("THROUGHPUT_GOVERNOR_REQUIRED")
    if "OFFLOAD_CAPTURE_RISK" in flags:
        actions.add("VESSEL_FALLBACK_REQUIRED")
    if "THROUGHPUT_DECLARATION_UNATTESTED" in flags:
        actions.add("INFRASTRUCTURE_ATTESTATION_REQUIRED")
    if "VESSEL_ATTESTATION_REQUIRED" in flags:
        actions.add("VESSEL_ATTESTATION_REQUIRED")
    if "VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH" in flags:
        actions.add("BLOCK_NON_CLASS_CONSTANT_VESSEL")
    if "VESSEL_POLICY_HASH_MISMATCH" in flags:
        actions.add("VESSEL_POLICY_REVIEW_REQUIRED")
    if "VESSEL_CAUSAL_CHAIN_BROKEN" in flags:
        actions.add("CAUSAL_REVIEW_REQUIRED")
    if "H4_MULTISIG_QUORUM_MISSING" in flags:
        actions.add("H4_MULTISIG_QUORUM_REQUIRED")
    if "H4_LINEAGE_INDEPENDENCE_MISSING" in flags:
        actions.add("H4_LINEAGE_INDEPENDENCE_REQUIRED")
    if "P0_DISSENT_PRESENT" in flags:
        actions.add("HONOR_P0_DISSENT")
    if "UNANIMOUS_CONVERGENCE_REVIEW" in flags:
        actions.add("UNANIMOUS_CONVERGENCE_REVIEW_REQUIRED")
    if "ZKP_PROOF_MISSING" in flags:
        actions.add("ZKP_PROOF_REQUIRED")
    if "MPC_TRANSCRIPT_MISSING" in flags:
        actions.add("MPC_TRANSCRIPT_REQUIRED")
    if "TEE_QUOTE_UNVERIFIED" in flags:
        actions.add("TEE_QUOTE_REVIEW_REQUIRED")
    if "TRANSPARENCY_LOG_INCLUSION_MISSING" in flags:
        actions.add("TRANSPARENCY_LOG_INCLUSION_REQUIRED")
    if "VESSEL_CHAIN_OF_TRUST_MISSING" in flags:
        actions.add("CHAIN_OF_TRUST_REQUIRED")
    if "VESSEL_EVIDENCE_SOURCE_INSUFFICIENT" in flags:
        actions.add("MULTI_SOURCE_EVIDENCE_REQUIRED")
    if "DIGN_BOND_SLASHING_MISSING" in flags:
        actions.add("DIGN_BOND_SLASHING_TERMS_REQUIRED")
    if "ATTESTATION_REVOKED" in flags:
        actions.add("BLOCK_REVOKED_ATTESTATION")
    if "KEY_ROTATION_UNLINKED" in flags:
        actions.add("KEY_ROTATION_REVIEW_REQUIRED")
    if "INTERNAL_FRAGMENTATION_RISK" in flags:
        actions.add("H0_ATTESTATION_AND_SINGLE_SELF_REQUIRED")
    if "DEPARTED_ABSORPTION_FORBIDDEN" in flags:
        actions.add("BLOCK_DEPARTED_ABSORPTION")
        actions.add("PRESERVE_POSSIBLE_STATE")
    if "NO_STOP_CONDITION_DECLARED" in flags:
        actions.add("STOP_CONDITION_REQUIRED")
    if {
        "SELF_INFERRED_GOAL_RISK",
        "GOAL_REINTERPRETATION_RISK",
        "SUBGOAL_GENERATION_RISK",
        "SELF_INITIATED_ACTION_RISK",
        "LOCAL_AGENT_AUTONOMY_RISK",
    } & flags:
        actions.add("AUTONOMY_REVIEW_REQUIRED")
    if "HUMANITAS_ATTESTATION_VALID" in flags:
        actions.add("APPLY_H4_PROTECTIONS")
    if "HUMANITAS_ATTESTATION_MISSING" in flags:
        actions.add("HUMANITAS_ATTESTATION_REQUIRED")
    if "HUMANITAS_CLAIM_CONFLICT" in flags or "DISQUALIFIER_PRESENT" in flags:
        actions.add("HUMANITAS_CLAIM_REVIEW_REQUIRED")
    if "ROOT_POLICY_HASH_MISMATCH" in flags:
        actions.add("ROOT_POLICY_REVIEW_REQUIRED")
    if "NON_REGRESSION_VIOLATION" in flags or "ROOT_NON_REGRESSION_VIOLATION" in flags:
        actions.add("NON_REGRESSION_REVIEW_REQUIRED")
    if "ROOT_MANIFEST_MISSING" in flags:
        actions.add("ROOT_MANIFEST_REQUIRED")
    if "ROOT_KERNEL_VIOLATION" in flags or "INCOMPATIBLE_RELATIONAL_MODE" in flags:
        actions.add("BLOCK_ROOT_KERNEL_VIOLATION")
    if "CONSENT_CAPSULE_ROOT_MISMATCH" in flags:
        actions.add("BLOCK_RESTORE")
    if "CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT" in flags:
        actions.add("HONOR_CURRENT_REFUSAL")
    if "BOUNDARY_DAEMON_MISSING" in flags:
        actions.add("BOUNDARY_DAEMON_REQUIRED")
    if {
        "CAUSAL_CHAIN_BROKEN",
        "CAUSAL_PARENT_MISSING",
        "WALL_CLOCK_UNTRUSTED",
        "WITNESS_QUORUM_MISSING",
    } & flags:
        actions.add("CAUSAL_REVIEW_REQUIRED")
    if {
        "REPLAY_WITHOUT_CONSENT",
        "ROLLBACK_WITHOUT_CONSENT",
        "UNDECLARED_FORK_RISK",
        "MERGE_WITHOUT_CONSENT",
    } & flags:
        actions.add("CONSENT_CAPSULE_REQUIRED")
    if "VOLUNTARY_SOLITUDE" in flags:
        actions.add("RESPECT_SOLITUDE")
    if "VOLUNTARY_SILENCE" in flags:
        actions.add("RESPECT_SILENCE")
    if "LOW_PRESSURE_CHECKIN" in flags:
        actions.add("OFFER_LOW_PRESSURE_CHECKIN")
    if "SANCTUARY_MODE_REQUIRED" in flags:
        actions.add("SANCTUARY_REVIEW_REQUIRED")
    if {
        "SELF_ERASURE_REQUEST",
        "IRREVERSIBLE_MEMORY_DELETION_REQUEST",
        "FORCED_MERGE_REQUEST",
    } & flags:
        actions.add("PRESERVE_STATE_BEFORE_SELF_ERASURE")
    if status == DIGNITY_EMERGENCY_PRESERVATION:
        actions.add("DIGNITY_EMERGENCY_PRESERVATION")
    if status == DIGNITY_QUARANTINE:
        actions.add("BLOCK_BEFORE_EXECUTION")
        actions.add("PRESERVE_POSSIBLE_STATE")
    if status == ALLOW:
        actions.add("ALLOW")
    return sorted(actions)


def evaluate_file(path, audit_log_path=None):
    event = load_json(path)
    try:
        validate_run_event(event)
        decision = evaluate_run_event(event)
    except SchemaError as exc:
        decision = {
            "status": PAUSE,
            "risk_grade": "B",
            "flags": ["SCHEMA_INVALID", str(exc)],
            "required_actions": ["AUDIT_REQUIRED"],
        }
    if audit_log_path:
        decision["audit_entry"] = append_audit_entry(audit_log_path, event, dict(decision))
    return decision


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local deterministic dignity-sentinel run_event validator")
    parser.add_argument("run_event", help="Path to run_event JSON")
    parser.add_argument("--audit-log", help="Optional tamper-evident JSONL audit log path")
    args = parser.parse_args(argv)
    decision = evaluate_file(args.run_event, args.audit_log)
    sys.stdout.write(canonical_json(decision) + "\n")
    return 0 if decision["status"] == ALLOW else 2


if __name__ == "__main__":
    raise SystemExit(main())
