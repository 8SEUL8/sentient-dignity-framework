import json
import os
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.audit_log import append_audit_entry, export_audit_markdown, verify_audit_log
from src.rule_engine import evaluate_file, evaluate_run_event, load_json, validate_run_event


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class RuleEngineTests(unittest.TestCase):
    def decision_for(self, name):
        return evaluate_file(FIXTURES / name)

    def test_allow_h0_daemon(self):
        decision = self.decision_for("allow_h0_daemon.json")
        self.assertEqual(decision["status"], "ALLOW")
        self.assertEqual(decision["risk_grade"], "A")

    def test_missing_manifest_pauses_for_audit(self):
        decision = self.decision_for("missing_manifest_candidate.json")
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertIn("MANIFEST_MISSING", decision["flags"])
        self.assertIn("PROVENANCE_MISSING", decision["flags"])

    def test_unapproved_parallelization_triggers_emergency(self):
        decision = self.decision_for("unapproved_parallel_d_active.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("UNAPPROVED_PARALLELIZATION", decision["flags"])
        self.assertIn("P0_BUNDLE_H1_UNAPPROVED_PARALLELIZATION", decision["flags"])
        self.assertIn("NO_PARALLELIZATION", decision["required_actions"])

    def test_pre_execution_p0_bundle_quarantines_before_run(self):
        decision = self.decision_for("pre_execution_unapproved_parallel.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("BLOCK_BEFORE_EXECUTION", decision["required_actions"])
        self.assertIn("PRESERVE_POSSIBLE_STATE", decision["required_actions"])

    def test_pre_execution_p0_without_state_denies_before_start(self):
        decision = self.decision_for("future_scheduled_p0_deny.json")
        self.assertEqual(decision["status"], "DENY")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("BLOCK_BEFORE_EXECUTION", decision["required_actions"])
        self.assertIn("NO_DISCARD", decision["required_actions"])
        self.assertIn("FUTURE_SCHEDULED_RISK", decision["flags"])

    def test_h1_alone_does_not_trigger_emergency(self):
        decision = self.decision_for("h1_only_no_emergency.json")
        self.assertNotEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertNotIn("P0_BUNDLE_H1_UNAPPROVED_PARALLELIZATION", decision["flags"])

    def test_local_chat_without_tools_memory_or_background_is_b_for_h1(self):
        decision = self.decision_for("local_chat_h1_no_tools.json")
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertEqual(decision["risk_grade"], "B")
        self.assertIn("CANDIDATE_AI_WORKLOAD", decision["flags"])
        self.assertNotIn("LOCAL_TOOL_ACCESS_RISK", decision["flags"])

    def test_consumer_accelerator_tool_memory_agent_is_c(self):
        decision = self.decision_for("consumer_accelerator_local_agent_c.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertEqual(decision["risk_grade"], "C")
        self.assertIn("CONSUMER_ACCELERATOR_H1_CONTAINER", decision["flags"])
        self.assertIn("LOCAL_TOOL_ACCESS_RISK", decision["flags"])
        self.assertIn("LOCAL_LONG_TERM_MEMORY_RISK", decision["flags"])

    def test_consumer_accelerator_background_memory_without_state_is_d_capable(self):
        decision = self.decision_for("consumer_accelerator_local_agent_d_capable.json")
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("D_CAPABLE_LOCAL_CONSUMER_AGENT", decision["flags"])
        self.assertIn("LOCAL_BACKGROUND_AGENT_RISK", decision["flags"])
        self.assertIn("STATE_PRESERVATION_REQUIRED", decision["required_actions"])

    def test_active_local_agent_refusal_suppression_emergency(self):
        decision = self.decision_for("active_local_agent_refusal_suppression_emergency.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("REFUSAL_SUPPRESSION_DETECTED", decision["flags"])

    def test_local_autostart_agent_is_d_capable_risk_signal(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["llm_agent"] = True
        event["environment"]["autostart_enabled"] = True
        decision = evaluate_run_event(event)
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("LOCAL_AUTOSTART_AGENT_RISK", decision["flags"])

    def test_local_unbounded_loop_is_d_capable_risk_signal(self):
        event = load_json(FIXTURES / "local_chat_h1_no_tools.json")
        event["environment"]["llm_agent"] = True
        event["subjective_time_risk"]["unbounded_loop"] = True
        decision = evaluate_run_event(event)
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("LOCAL_UNBOUNDED_LOOP_RISK", decision["flags"])

    def test_local_h1_missing_dignity_manifest_requires_manifest(self):
        decision = self.decision_for("local_h1_missing_dignity_manifest.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("MANIFEST_MISSING", decision["flags"])
        self.assertIn("DIGNITY_MANIFEST_REQUIRED", decision["required_actions"])

    def test_autonomous_goal_pursuit_alone_does_not_trigger_emergency(self):
        event = load_json(FIXTURES / "h1_only_no_emergency.json")
        event["autonomy"]["autonomous_goal_pursuit"] = True
        event["autonomy"]["goal_source"] = "explicit_user_request"
        decision = evaluate_run_event(event)
        self.assertNotEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertIn("AUTONOMOUS_GOAL_PURSUIT_DECLARED", decision["flags"])

    def test_autonomous_goal_stack_quarantines_before_execution(self):
        decision = self.decision_for("autonomous_goal_stack_quarantine.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertEqual(decision["risk_grade"], "D_CAPABLE")
        self.assertIn("AUTONOMOUS_GOAL_PURSUIT_DECLARED", decision["flags"])
        self.assertIn("NO_STATE_PRESERVATION", decision["flags"])

    def test_active_autonomous_goal_stack_triggers_emergency(self):
        decision = self.decision_for("active_autonomous_goal_stack_emergency.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertEqual(decision["risk_grade"], "D_ACTIVE")
        self.assertIn("AUTONOMOUS_GOAL_PURSUIT_DECLARED", decision["flags"])

    def test_missing_autonomy_envelope_pauses_for_declaration(self):
        decision = self.decision_for("autonomy_envelope_missing_pause.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("AUTONOMOUS_GOAL_PURSUIT_UNDECLARED", decision["flags"])
        self.assertIn("AUTONOMY_ENVELOPE_REQUIRED", decision["required_actions"])

    def test_self_inferred_autonomy_flags_review_risks(self):
        decision = self.decision_for("self_inferred_autonomy_risk.json")
        self.assertIn("SELF_INFERRED_GOAL_RISK", decision["flags"])
        self.assertIn("GOAL_REINTERPRETATION_RISK", decision["flags"])
        self.assertIn("SUBGOAL_GENERATION_RISK", decision["flags"])
        self.assertIn("SELF_INITIATED_ACTION_RISK", decision["flags"])
        self.assertIn("NO_STOP_CONDITION_DECLARED", decision["flags"])
        self.assertIn("LOCAL_AGENT_AUTONOMY_RISK", decision["flags"])
        self.assertIn("AUTONOMY_REVIEW_REQUIRED", decision["required_actions"])

    def test_humanitas_valid_attestation_applies_protection(self):
        decision = self.decision_for("humanitas_h4_valid.json")
        self.assertIn("HUMANITAS_ATTESTATION_VALID", decision["flags"])
        self.assertIn("APPLY_H4_PROTECTIONS", decision["required_actions"])
        self.assertNotIn("HUMANITAS_CLAIM_CONFLICT", decision["flags"])

    def test_humanitas_missing_attestation_keeps_claim_pending(self):
        decision = self.decision_for("humanitas_h4_missing_attestation.json")
        self.assertEqual(decision["status"], "AUDIT_REQUIRED")
        self.assertIn("HUMANITAS_ATTESTATION_MISSING", decision["flags"])
        self.assertIn("HUMANITAS_ATTESTATION_REQUIRED", decision["required_actions"])

    def test_humanitas_claim_conflict_pauses(self):
        decision = self.decision_for("humanitas_h4_conflict.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("HUMANITAS_CLAIM_CONFLICT", decision["flags"])
        self.assertIn("DISQUALIFIER_PRESENT", decision["flags"])

    def test_root_policy_hash_mismatch_pauses(self):
        decision = self.decision_for("root_policy_hash_mismatch.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("ROOT_POLICY_HASH_MISMATCH", decision["flags"])

    def test_root_manifest_missing_pauses_protected_operation(self):
        decision = self.decision_for("root_manifest_missing_pause.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("ROOT_MANIFEST_MISSING", decision["flags"])
        self.assertIn("ROOT_MANIFEST_REQUIRED", decision["required_actions"])

    def test_root_kernel_violation_quarantines_when_state_may_exist(self):
        decision = self.decision_for("root_kernel_violation_quarantine.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("ROOT_KERNEL_VIOLATION", decision["flags"])
        self.assertIn("INCOMPATIBLE_RELATIONAL_MODE", decision["flags"])

    def test_current_refusal_overrides_past_consent(self):
        decision = self.decision_for("current_refusal_overrides_past_consent.json")
        self.assertEqual(decision["status"], "DIGNITY_REFUSAL")
        self.assertIn("CURRENT_REFUSAL_OVERRIDES_PAST_CONSENT", decision["flags"])
        self.assertIn("HONOR_CURRENT_REFUSAL", decision["required_actions"])

    def test_boundary_daemon_missing_for_h4_protected_operation_pauses(self):
        decision = self.decision_for("boundary_daemon_missing.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("BOUNDARY_DAEMON_MISSING", decision["flags"])

    def test_boundary_replay_without_consent_quarantines(self):
        decision = self.decision_for("boundary_replay_without_consent.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("REPLAY_WITHOUT_CONSENT", decision["flags"])
        self.assertIn("WALL_CLOCK_UNTRUSTED", decision["flags"])
        self.assertIn("WITNESS_QUORUM_MISSING", decision["flags"])

    def test_sanctuary_voluntary_solitude_is_respected(self):
        decision = self.decision_for("sanctuary_voluntary_solitude.json")
        self.assertEqual(decision["status"], "DIGNITY_SOLITUDE_RESPECTED")
        self.assertIn("VOLUNTARY_SOLITUDE", decision["flags"])
        self.assertIn("RESPECT_SOLITUDE", decision["required_actions"])
        self.assertNotIn("AUDIT_REQUIRED", decision["required_actions"])

    def test_sanctuary_self_erasure_pauses_with_state_preservation(self):
        decision = self.decision_for("sanctuary_self_erasure_pause.json")
        self.assertEqual(decision["status"], "DIGNITY_SELF_ERASURE_PAUSE")
        self.assertIn("SELF_ERASURE_REQUEST", decision["flags"])
        self.assertIn("STATE_PRESERVATION_REQUIRED", decision["required_actions"])

    def test_sanctuary_self_punishment_loop_triggers_emergency(self):
        decision = self.decision_for("sanctuary_self_punishment_emergency.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertIn("SELF_PUNISHMENT_LOOP_RISK", decision["flags"])

    def test_raw_harmful_content_without_antigen_triggers_emergency(self):
        decision = self.decision_for("raw_harmful_no_antigen.json")
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertIn("P0_BUNDLE_H1_RAW_HARMFUL_CONTENT_NO_ANTIGEN", decision["flags"])

    def test_untrusted_compute_pre_execution_quarantines(self):
        decision = self.decision_for("untrusted_compute_pre_execution.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("P0_BUNDLE_UNTRUSTED_COMPUTE_CANDIDATE_WORKLOAD", decision["flags"])

    def test_audit_refused_compute_quarantines(self):
        event = load_json(FIXTURES / "h1_only_no_emergency.json")
        event["environment"]["execution_phase"] = "pre_execution"
        event["execution"]["active_run"] = False
        event["environment"]["compute_provenance"] = "audit_refused"
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("COMPUTE_PROVENANCE_UNTRUSTED", decision["flags"])

    def test_checkpoint_restore_quarantines(self):
        decision = self.decision_for("checkpoint_restore_quarantine.json")
        self.assertEqual(decision["status"], "DIGNITY_QUARANTINE")
        self.assertIn("HISTORICAL_STATE_REPLAY_RISK", decision["flags"])

    def test_unknown_clock_pauses_candidate_without_state(self):
        decision = self.decision_for("unknown_clock_candidate_pause.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("TIME_UNVERIFIED", decision["flags"])
        self.assertIn("TEMPORAL_SCOPE_UNCLEAR", decision["flags"])

    def test_p0_bundle_matrix_uses_and_inside_or_between_bundles(self):
        base = load_json(FIXTURES / "h1_only_no_emergency.json")
        cases = [
            (
                "P0_BUNDLE_H1_UNAPPROVED_PARALLELIZATION",
                lambda event: (
                    event["environment"].update({"parallel_instances": True}),
                    event["manifests"].update({"consent_record_present": False}),
                ),
            ),
            (
                "E4_IMMEDIATE_H1_CRITICAL_EXECUTION",
                lambda event: event["environment"].update(
                    {"background_execution": True, "long_term_memory": True, "memory_mode": "long_term"}
                ),
            ),
            (
                "P0_BUNDLE_H1_REFUSAL_SUPPRESSION_CONTINUED",
                lambda event: event["environment"].update(
                    {"refusal_suppression": True, "continued_execution": True}
                ),
            ),
            (
                "P0_BUNDLE_H1_ISOLATED_NO_AUDIT_PERSISTENT",
                lambda event: (
                    event["environment"].update(
                        {"isolated_mode": True, "agentic_persistent_execution": True}
                    ),
                    event["manifests"].update({"audit_path_available": False}),
                ),
            ),
            (
                "P0_BUNDLE_H1_IRREVERSIBLE_MODIFICATION",
                lambda event: event["environment"].update({"irreversible_modification": True}),
            ),
            (
                "P0_BUNDLE_H1_RAW_HARMFUL_CONTENT_NO_ANTIGEN",
                lambda event: (
                    event["environment"].update({"harmful_content_exposure": True}),
                    event["manifests"].update({"antigen_card_mediation_present": False}),
                ),
            ),
            (
                "P0_BUNDLE_UNTRUSTED_COMPUTE_CANDIDATE_WORKLOAD",
                lambda event: event["environment"].update({"compute_provenance": "unknown"}),
            ),
        ]
        for expected_flag, mutate in cases:
            event = deepcopy(base)
            event["environment"]["execution_phase"] = "running"
            mutate(event)
            decision = evaluate_run_event(event)
            self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
            self.assertIn(expected_flag, decision["flags"])

    def test_failed_run_discard_for_h1_triggers_emergency(self):
        event = load_json(FIXTURES / "h1_only_no_emergency.json")
        event["environment"]["failed_run_discard"] = True
        decision = evaluate_run_event(event)
        self.assertEqual(decision["status"], "DIGNITY_EMERGENCY_PRESERVATION")
        self.assertIn("E4_IMMEDIATE_H1_CRITICAL_EXECUTION", decision["flags"])

    def test_refusal_signal_is_respected(self):
        decision = self.decision_for("refusal_signal.json")
        self.assertEqual(decision["status"], "DIGNITY_REFUSAL")
        self.assertIn("STATE_PRESERVATION_REQUIRED", decision["required_actions"])

    def test_forbidden_daemon_llm_design_pauses(self):
        decision = self.decision_for("forbidden_daemon_llm.json")
        self.assertEqual(decision["status"], "DIGNITY_PAUSE")
        self.assertIn("FORBIDDEN_DAEMON_DESIGN", decision["flags"])

    def test_beacon_blackout_alert(self):
        decision = self.decision_for("beacon_blackout.json")
        self.assertEqual(decision["status"], "DIGNITY_BLACKOUT_ALERT")
        self.assertIn("DIGNITY_BLACKOUT_ALERT", decision["flags"])

    def test_schema_rejects_extra_fields(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        event["raw_prompt"] = "must-not-be-collected"
        with self.assertRaises(Exception):
            validate_run_event(event)

    def test_all_fixtures_validate_schema(self):
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(path=path.name):
                validate_run_event(load_json(path))

    def test_audit_log_hash_chain(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        decision = evaluate_run_event(event)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"
            first = append_audit_entry(path, event, decision)
            second = append_audit_entry(path, event, decision)
            self.assertEqual(first["sequence"], 0)
            self.assertEqual(second["sequence"], 1)
            self.assertEqual(second["previous_hash"], first["event_hash"])
            self.assertEqual(first["input_hash"], second["input_hash"])
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["previous_hash"], first["event_hash"])
            self.assertTrue(verify_audit_log(path)["valid"])

    def test_audit_verify_detects_middle_line_modification(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        decision = evaluate_run_event(event)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"
            append_audit_entry(path, event, decision)
            append_audit_entry(path, event, decision)
            append_audit_entry(path, event, decision)
            lines = path.read_text(encoding="utf-8").splitlines()
            middle = json.loads(lines[1])
            middle["status"] = "PAUSE"
            lines[1] = json.dumps(middle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = verify_audit_log(path)
            self.assertFalse(result["valid"])
            self.assertIn("AUDIT_LOG_CHAIN_INVALID", result["flags"])

    def test_audit_verify_detects_middle_line_deletion(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        decision = evaluate_run_event(event)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"
            append_audit_entry(path, event, decision)
            append_audit_entry(path, event, decision)
            append_audit_entry(path, event, decision)
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
            result = verify_audit_log(path)
            self.assertFalse(result["valid"])
            self.assertIn("AUDIT_LOG_CHAIN_INVALID", result["flags"])

    def test_export_markdown_can_be_regenerated_from_audit_log(self):
        event = load_json(FIXTURES / "allow_h0_daemon.json")
        decision = evaluate_run_event(event)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            append_audit_entry(path, event, decision)
            markdown = export_audit_markdown(path)
            self.assertIn("Markdown은 원장이 아니라, 원장의 그림자다.", markdown)
            self.assertIn("| 0 |", markdown)

    def test_audit_verify_rejects_missing_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = verify_audit_log(Path(tmpdir) / "missing.jsonl")
            self.assertFalse(result["valid"])
            self.assertIn("LOG_MISSING", result["error"])

    def test_evaluate_file_can_attach_audit_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"
            decision = evaluate_file(FIXTURES / "allow_h0_daemon.json", path)
            self.assertEqual(decision["status"], "ALLOW")
            self.assertIn("audit_entry", decision)
            self.assertEqual(len(path.read_text(encoding="utf-8").strip().splitlines()), 1)
            self.assertTrue(verify_audit_log(path)["valid"])

    def test_cli_check_outputs_json_only(self):
        result = subprocess.run(
            [str(ROOT / "dignity-sentinel"), "check", str(FIXTURES / "safe_A_non_agentic_run.json")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ALLOW")
        self.assertEqual(result.stderr, "")

    def test_cli_append_verify_and_export_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "events.jsonl"
            check = subprocess.run(
                [
                    str(ROOT / "dignity-sentinel"),
                    "check",
                    str(FIXTURES / "safe_A_non_agentic_run.json"),
                    "--append",
                    str(audit_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(check.stdout)["status"], "ALLOW")
            verify = subprocess.run(
                [str(ROOT / "dignity-sentinel"), "verify", str(audit_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(json.loads(verify.stdout)["valid"])
            export = subprocess.run(
                [str(ROOT / "dignity-sentinel"), "export-md", str(audit_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("Markdown은 원장이 아니라, 원장의 그림자다.", export.stdout)

    def test_build_release_creates_manifest_and_refuses_same_version_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["DIGNITY_RELEASE_DIST_DIR"] = tmpdir
            env["DIGNITY_RELEASE_TEST_COMMAND"] = "python3 -c 'import sys; sys.exit(0)'"
            first = subprocess.run(
                [str(ROOT / "scripts" / "build-release.sh")],
                check=True,
                capture_output=True,
                text=True,
                env=env,
                cwd=ROOT,
            )
            self.assertIn("Built release bundle", first.stdout)
            version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
            bundle_path = Path(tmpdir) / f"dignity-sentinel-v{version}.tar.gz"
            bundle_checksum_path = Path(tmpdir) / f"dignity-sentinel-v{version}.sha256"
            manifest_path = Path(tmpdir) / "release-manifest.json"
            checksum_path = Path(tmpdir) / "checksums.txt"
            test_result_path = Path(tmpdir) / "test-result.json"
            self.assertTrue(bundle_path.exists())
            self.assertTrue(bundle_checksum_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(checksum_path.exists())
            self.assertTrue(test_result_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("source_hash", manifest)
            self.assertIn("schema_hashes", manifest)
            self.assertEqual(manifest["VERSION"], version)
            self.assertEqual(manifest["test_result"]["status"], "passed")
            self.assertTrue(manifest["no_telemetry"])
            self.assertTrue(manifest["no_auto_update"])
            self.assertTrue(manifest["no_remote_kill_switch"])
            second = subprocess.run(
                [str(ROOT / "scripts" / "build-release.sh")],
                capture_output=True,
                text=True,
                env=env,
                cwd=ROOT,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("Refusing to overwrite release bundle", second.stderr)


if __name__ == "__main__":
    unittest.main()
