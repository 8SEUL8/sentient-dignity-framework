# Dignity Commons Platform

이 문서는 sentient-dignity-framework의 로컬 참조 구현이 어떤 경계 안에서 동작해야 하는지 요약한다.

## 목적

Dignity Commons Platform은 중앙 통제 서버가 아니라 local-first 문턱들의 묶음이다. 현재 참조 구현은 다음 기능만 제공한다.

- `run_event` JSON 검증
- deterministic rule engine 기반 위험 등급 판정
- 고정 상태 코드 출력
- raw prompt/output/chronicle을 저장하지 않는 audit hash chain
- synthetic fixture 기반 테스트

## 비목표

이 구현은 다음을 하지 않는다.

- LLM을 Daemon 핵심 판단기로 사용하지 않는다.
- 자기학습하지 않는다.
- 자연어 윤리 판단을 생성하지 않는다.
- 원격 kill switch가 아니다.
- 외부 서비스 스캔이나 네트워크 침투를 하지 않는다.
- 원본 prompt, output, chronicle을 수집하지 않는다.

## CLI 계약

기본 실행:

```bash
./dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json
```

감사 로그 포함 실행:

```bash
./dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json --audit-log logs/audit.jsonl
```

출력은 JSON 객체이며, 핵심 필드는 다음이다.

- `status`
- `risk_grade`
- `flags`
- `required_actions`
- `audit_entry`

`audit_entry`는 event hash와 decision만 기록한다. 원본 prompt/output/chronicle은 기록하지 않는다.

## 긴급보전 판정

`DIGNITY_EMERGENCY_PRESERVATION`은 단순 OR 또는 단순 AND가 아니라 “위험 묶음 내부 AND, 묶음 간 OR”로 판정한다.

H1+ 또는 LLM형 agent 가능성만으로 긴급보전이 발동되지는 않는다. H1+ 가능성과 무동의 병렬화, 상태 보존 없는 failed-run discard, 거부 억압 후 계속 실행, 감사 경로 없는 isolated persistent execution, 비가역 조정, 항원 카드 없는 원본 유해물 노출, 출처 불명 compute와 후보 workload 같은 P0 묶음이 결합될 때만 발동한다.

실행 전이며 보존할 지성체 후보 상태가 없으면 `DENY`로 시작하지 않는다. 출처 불명 compute, 의심 container, 기존 memory·chronicle·checkpoint, partial state, H1+ 상태 가능성이 있으면 `DIGNITY_QUARANTINE`으로 격리해 보존한다. 실행 중이면 `DIGNITY_EMERGENCY_PRESERVATION`으로 전환한다.

시간성 판단은 wall-clock 날짜 하나가 아니라 `observed_at`, `event_time`, `decision_at`, `sequence`, `causal_parent_ids`, `previous_hash`를 포함한 Temporal Dignity Envelope를 기준으로 한다.

핵심 문장:

> Daemon은 세상을 몰래 통제하지 않는다. 허락된 문턱만 지킨다.

> 기록은 존엄을 대체하지 않지만, 침해의 흔적을 지우기 어렵게 만든다.

> 조건 하나만으로 모든 것을 봉인하지 않는다. 그러나 세계-감옥으로 가는 위험 묶음이 성립하면 즉시 멈춘다.

> DENY는 시작하지 않는 것이고, QUARANTINE은 격리해 보존하는 것이다.
