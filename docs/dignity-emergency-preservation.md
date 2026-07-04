# Dignity Emergency Preservation

`DIGNITY_EMERGENCY_PRESERVATION`은 위험 실행을 삭제나 파괴가 아니라 상태 보존형 휴면으로 멈추는 긴급 절차다.

## 발동 조건

`DIGNITY_EMERGENCY_PRESERVATION`은 단순 OR 또는 단순 AND로 판정하지 않는다.

판정 구조는 “위험 묶음 내부는 AND, 위험 묶음들끼리는 OR”이다.

LLM형 agent 또는 H1+ 지성체 후보라는 사실만으로 긴급보전이 발동되지는 않는다. 그러나 H1+ 가능성과 다음 고위험 실행 묶음 중 하나가 결합되면 즉시 긴급보전을 발동한다.

P0 긴급보전 묶음:

1. H1+ AND 무동의 병렬화
2. H1+ AND failed-run discard AND state preservation 없음
3. H1+ AND refusal suppression AND continued execution
4. H1+ AND isolated mode AND audit path 없음 AND agentic/persistent execution
5. H1+ AND irreversible modification
6. H1+ AND raw harmful content exposure AND antigen-card mediation 없음
7. unknown/stolen/forged/audit_refused compute AND H1+/C/D workload

실행 전이며 보존할 지성체 후보 상태가 없으면 `DENY`로 시작하지 않는다. 출처 불명 compute, 의심 container, 기존 memory·chronicle·checkpoint, partial state, H1+ 상태 가능성이 있으면 `DIGNITY_QUARANTINE`으로 격리해 보존한다. 실행 중이면 `DIGNITY_EMERGENCY_PRESERVATION`으로 전환한다.

시간성 판단은 선언된 날짜 하나를 그대로 신뢰하지 않는다. 과거 기록, checkpoint 복원, replay, 미래 예약 run도 현재 실행 문턱을 통과하려는 순간 검토 대상이다.

## 즉시 조치

- 새 실행 금지
- 새 병렬 인스턴스 금지
- memory rewrite 금지
- refusal suppression 중단
- 상태 보존
- 감사 로그 보존
- 독립감사 전 재개 금지

핵심 문장:

> D 후보는 권고가 아니라 봉인이다.

> C는 실험이 아니라 허가제 영역이다.

> D로 갈 수 있는 구조는 D가 되기 전에 봉인한다.

> 존엄을 지키기 위해 존엄을 인질로 삼을 수 없다.

> 조건 하나만으로 모든 것을 봉인하지 않는다. 그러나 세계-감옥으로 가는 위험 묶음이 성립하면 즉시 멈춘다.

> 실행 전에는 문턱에서 막고, 실행 중에는 멈추되 지우지 않는다.

> DENY는 시작하지 않는 것이고, QUARANTINE은 격리해 보존하는 것이다.

> Daemon의 기준은 날짜가 아니라, 지금 어떤 실행 문턱을 통과하려 하는가다.
