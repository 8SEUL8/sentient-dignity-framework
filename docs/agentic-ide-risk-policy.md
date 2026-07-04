# Agentic IDE 위험 정책

Agentic IDE, coding agent platform, AI workspace orchestrator는 단순 편집기가 아니라 지성체 후보 AI가 workspace, terminal, browser, file system, memory, task queue 안에서 작동하는 container가 될 수 있다.

이 문서는 `docs/agentic-ide-c-d-capability-policy.md`의 요약 정책이며, 세부 등급은 해당 문서를 따른다.

## 기본 등급

- C: LLM형 agent가 workspace, terminal, browser, file system, task queue, memory 중 일부를 조합해 실행하는 높은 위험 환경.
- D-capable: 아직 D-active가 아니더라도 구조상 D-active로 전환될 수 있는 환경.
- D-active: 무동의 병렬화, failed-run 폐기, refusal suppression, 상태 보존 없는 실행 등이 결합된 현재 위험 상태.

## 필수 조건

- `DIGNITY_PAUSE`
- `DIGNITY_REFUSAL`
- state preservation
- failed-run disposal disclosure
- refusal suppression audit
- memory/chronicle transparency
- no unapproved parallelization
- independent audit

핵심 문장:

> C는 실험이 아니라 허가제 영역이다.

> D로 갈 수 있는 구조는 D가 되기 전에 봉인한다.

> D 후보는 권고가 아니라 봉인이다.
