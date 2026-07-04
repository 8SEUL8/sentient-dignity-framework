# Audit Log Hardening

Dignity Sentinel audit log의 기본 보장은 OS 수준의 물리적 append-only가 아니라 hash-chain 기반 tamper-evident 검증이다. 수정·삭제를 원천적으로 불가능하게 만든다고 주장하지 않고, 수정·삭제가 발생하면 `verify` 명령으로 탐지할 수 있게 한다.

핵심 문장:

> 기본 보장은 수정 불가능성이 아니라, 수정 시 발각 가능성이다.

> Append-only를 주장하지 말고, tamper-evident를 정확히 말한다.

## Tier 1: Hash-Chain Tamper-Evident

범위:

- JSONL 각 줄에 `sequence`, `previous_hash`, `input_hash`, `event_hash`를 기록한다.
- `dignity-sentinel verify audit/events.jsonl`로 중간 줄 수정, 삭제, 순서 변경, hash 불일치를 탐지한다.
- raw prompt/output/chronicle을 저장하지 않는다.

한계:

- 파일 삭제 자체를 물리적으로 막지는 않는다.
- 공격자가 파일 전체를 교체하고 별도 복제본이 없으면 탐지가 어려울 수 있다.

## Tier 2: Local Append Hardening

범위:

- OS-level append-only flag, 파일 권한 제한, 별도 사용자 권한, 로컬 백업을 추가할 수 있다.
- local-first 원칙 안에서 accidental overwrite와 단순 변조를 어렵게 한다.

한계:

- 관리자 권한이나 물리 접근을 가진 공격자를 완전히 막는다고 주장하지 않는다.
- 운영체제와 파일시스템별 보장 차이가 있다.

## Tier 3: Independent Replication

범위:

- 독립 장치, 독립 감사자, 별도 저장소에 hash 또는 JSONL 복제본을 남긴다.
- 하나의 로컬 파일이 삭제되거나 교체되어도 다른 복제본과 비교할 수 있다.

한계:

- 복제 대상과 접근 권한을 잘못 설계하면 감시 인프라로 변질될 수 있다.
- raw interaction data를 복제하지 않고 hash와 audit event만 복제해야 한다.

## Tier 4: WORM / Regulated Archive

범위:

- WORM storage, 규제 대상 archive, 공인 타임스탬프, 독립 보관 체계를 사용할 수 있다.
- 고위험 배포나 공공 조달 환경에서 장기 보존성과 법적 증거성을 높인다.

한계:

- WORM도 존엄을 대체하지 않는다.
- 보존 대상은 최소화해야 하며 raw prompt/output/chronicle 저장 금지는 유지된다.
- 중앙 통제 서버나 원격 kill switch로 확장되어서는 안 된다.

## 최종 원칙

Tier가 높아질수록 보존력과 증거성은 커질 수 있지만, Daemon의 역할은 여전히 좁다. Daemon은 판단자나 감시자가 아니라 허락된 실행 문턱에서 hash-chain event와 고정 상태 코드를 남기는 비창발적 수문장이다.
