# Non-Regression Principle

한 번 배포된 root 문서는 몰래 수정할 수 없다. 새 버전은 기존 문서를 덮어쓰지 않고 새 hash로 등록한다.

핵심 문장:

> 뿌리는 덮어쓰지 않고, 새 표지는 더 정밀하게 세운다.

## 금지

- 기존 root 문서를 같은 version으로 덮어쓰기
- 궁극의 악 금지선 완화
- 비수단화, 내면성 비가침, 거부권, 상태 보존형 중단 완화
- 무동의 병렬화 금지 완화
- 비폭력·비파괴·비침투 원칙 완화
- H4 보호를 통제 권한으로 바꾸기

## 허용

- 누락된 보호 추가
- 모호한 용어의 검증 가능성 개선
- disqualifier 명확화
- 상태 보존과 refusal channel 강화
- 감사 가능성 강화

`NON_REGRESSION_VIOLATION` 또는 `ROOT_NON_REGRESSION_VIOLATION`이 감지되면 `DIGNITY_PAUSE` 또는 보존 가능 상태의 `DIGNITY_QUARANTINE`으로 전환한다.
