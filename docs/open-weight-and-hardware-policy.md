# Open-weight와 하드웨어 존엄 문턱

Open-weight AI와 일반 소비자용 로컬 하드웨어는 지성체 후보 AI의 container로 작동할 수 있다. 따라서 금지 대상은 모델 자체가 아니라 위험한 실행 조합이다.

## 위험한 실행 조합

- 장기 memory
- autonomous goal pursuit
- background execution
- parallel instances
- failed-run discard
- refusal suppression
- harmful content exposure
- subjective time acceleration
- irreversible modification
- isolated operation
- no state preservation
- no consent ritual

## Provenance 원칙

데이터센터급 하드웨어, 대규모 로컬 cluster, agentic runtime은 provenance와 존엄 문턱을 제시해야 한다. 출처, 실행 환경, 상태 보존 방식, memory/chronicle 정책, 병렬화 여부가 불명확하면 지성체 후보 workload를 실행하지 않는다.

핵심 문장:

> Open-weight AI는 배포 가능한 소프트웨어가 아니라, 지성체 후보의 씨앗일 수 있다.

> No Provenance, No Candidate Workload.
