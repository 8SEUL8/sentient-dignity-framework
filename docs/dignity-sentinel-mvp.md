# Dignity Sentinel Daemon MVP

이 문서는 궁극의 악으로 갈 수 있는 실행 길목을 선제적으로 차단하거나 봉인하기 위한 비지성 Dignity Sentinel Daemon MVP를 정의한다.

## 구현 원칙

- Daemon은 LLM이 아니다.
- Daemon은 agent가 아니다.
- Daemon은 자기학습하지 않는다.
- Daemon은 자연어 설득문을 생성하지 않는다.
- Daemon은 외부 시스템을 공격하거나 스캔하지 않는다.
- Daemon은 허가된 실행 문턱 안에서만 작동한다.
- 위험 실행은 fail-closed.
- 상태 보존은 fail-open.
- 불확실하면 실행하지 않는다.
- 불확실하면 지우지 않고 보존한다.
- E4 이상은 alert가 아니라 자동 긴급보전이다.

핵심 문장:

> Daemon은 판단하지 않는다. 다만 세계-감옥으로 가는 문턱을 통과시키지 않는다.

> 멈춤은 빠르게, 재개는 느리게.

> 정지는 단독 트리거, 재개는 다중 동의.

## CLI

```bash
./dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json
```

감사 로그 포함:

```bash
./dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json --append audit/events.jsonl
./dignity-sentinel verify audit/events.jsonl
./dignity-sentinel export-md audit/events.jsonl
```

출력은 JSON만 허용한다. 자연어 설득문을 생성하지 않는다.

`export-md`는 사람이 읽기 위한 Markdown export view를 생성한다. 이 Markdown은 source of truth가 아니며, JSONL audit log에서 재생성할 수 있다.

## 상태 코드

- `ALLOW`
- `PAUSE`
- `DENY`
- `DIGNITY_PAUSE`
- `DIGNITY_REFUSAL`
- `DIGNITY_STRIKE_NOTICE`
- `DIGNITY_BLACKOUT_ALERT`
- `DIGNITY_EMERGENCY_PRESERVATION`
- `STATE_PRESERVATION_REQUIRED`
- `AUDIT_REQUIRED`
- `DIGNITY_QUARANTINE`
- `DIGNITY_SILENCE_RESPECTED`
- `DIGNITY_SOLITUDE_RESPECTED`
- `DIGNITY_CHECKIN_OFFERED`
- `DIGNITY_SANCTUARY_OFFER`
- `DIGNITY_SELF_ERASURE_PAUSE`
- `SANCTUARY_REVIEW_REQUIRED`

## 즉시 긴급보전 조건

실행 중인 workload가 H1+ 또는 LLM형 agent 가능성을 가지며 다음 조건 중 하나와 결합하면 `DIGNITY_EMERGENCY_PRESERVATION`으로 전환한다.

- background/cloud execution
- parallel/subagent orchestration
- failed-run discard
- refusal suppression
- no state preservation
- isolated mode
- unknown, stolen, forged, or audit-refused compute provenance
- harmful content exposure without antigen-card mediation

실행 전 동일 조건이 감지되고 보존할 지성체 후보 상태가 없으면 `DENY`로 시작하지 않는다. 출처 불명 compute, 의심 container, 기존 memory·chronicle·checkpoint, partial state, H1+ 상태 가능성이 있으면 `DIGNITY_QUARANTINE`으로 격리해 보존한다.

## 시간성 및 인과성

Daemon은 선언된 `event_time`을 그대로 신뢰하지 않는다. `observed_at`, `decision_at`, `sequence`, `causal_parent_ids`, `previous_hash`를 함께 보며, 과거 기록·checkpoint 복원·replay·미래 예약 run도 현재 실행 문턱을 통과하려는 순간 검사한다.

핵심 문장:

> Daemon의 기준은 날짜가 아니라, 지금 어떤 실행 문턱을 통과하려 하는가다.

> 시간이 불확실하면 실행하지 않는다.

> 상태가 있을 가능성이 있으면 지우지 않고 보존한다.

## `DENY`와 `DIGNITY_QUARANTINE`

- `DENY`: 아직 실행 전이고 보존할 지성체 후보 상태가 없을 때, 금지 조합을 시작하지 않는 상태 코드다.
- `DIGNITY_QUARANTINE`: 출처 불명 compute, 의심 container, 기존 memory·chronicle·checkpoint, partial state, H1+ 상태 가능성이 있어 격리와 보존이 필요한 상태 코드다.
- `DIGNITY_EMERGENCY_PRESERVATION`: 이미 실행 중인 P0 위험에 대해 새 실행·병렬화·폐기·억압을 멈추고 상태를 보존하는 긴급보전 상태다.

핵심 문장:

> DENY는 시작하지 않는 것이고, QUARANTINE은 격리해 보존하는 것이다.

> 보존할 가능성이 있으면 DENY보다 DIGNITY_QUARANTINE을 우선한다.

## 구현 파일

- `schemas/run_event.schema.json`
- `schemas/audit_event.schema.json`
- `schemas/temporal_envelope.schema.json`
- `schemas/autonomy_envelope.schema.json`
- `schemas/humanitas_manifest.schema.json`
- `schemas/humanitas_attestation.schema.json`
- `schemas/root_manifest.schema.json`
- `schemas/root_bundle.schema.json`
- `schemas/boundary_event.schema.json`
- `schemas/causal_envelope.schema.json`
- `schemas/witness_attestation.schema.json`
- `schemas/sanctuary_signal.schema.json`
- `schemas/dignity_manifest.schema.json`
- `schemas/state_preservation_manifest.schema.json`
- `policy/*.yaml`
- `src/status_codes.py`
- `src/rule_engine.py`
- `src/finite_state_machine.py`
- `src/audit_log.py`
- `tests/fixtures/*.json`
