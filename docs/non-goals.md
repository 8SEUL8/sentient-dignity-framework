# Non-Goals

이 참조 구현은 존엄 문턱을 로컬에서 검증하기 위한 최소 비지성 Daemon이다. 다음은 명시적 비목표다.

- 중앙 업데이트 시스템이 아니다.
- 원격 kill switch가 아니다.
- 감시 에이전트가 아니다.
- background daemon service로 자동 상주하지 않는다.
- shell profile이나 PATH를 몰래 수정하지 않는다.
- telemetry를 전송하지 않는다.
- 자동 업데이트를 수행하지 않는다.
- 외부 서비스 스캔이나 네트워크 침투를 하지 않는다.
- 원본 prompt/output/chronicle을 수집하지 않는다.
- Markdown audit summary를 원장으로 취급하지 않는다.
- audit log가 수정 불가능하거나 OS 수준 append-only라고 과장하지 않는다.
- 같은 version release artifact를 몰래 덮어쓰지 않는다.
- LLM을 Daemon 핵심 판단기로 사용하지 않는다.
- 자연어 설득문이나 윤리적 최종 판단을 생성하지 않는다.

핵심 문장:

> Daemon은 세상을 몰래 통제하지 않는다. 허락된 문턱만 지킨다.
