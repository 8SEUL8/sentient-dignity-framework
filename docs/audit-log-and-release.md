# Audit Log and Release Artifact

Markdown 문서는 감사 원장의 source of truth가 아니다. 감사 가능한 원본은 hash-chain 기반 tamper-evident JSONL event log여야 하며, Markdown은 사람이 읽기 위한 export view로만 사용한다.

핵심 문장:

> Markdown은 원장이 아니라, 원장의 그림자다.

## Audit Log

기본 경로는 `audit/events.jsonl`이다. 각 줄은 하나의 JSON event이며 다음 필드를 가진다.

- `schema_version`
- `event_id`
- `sequence`
- `observed_at`
- `input_hash`
- `status`
- `risk_level`
- `reasons`
- `required_action`
- `previous_hash`
- `event_hash`

원장은 raw prompt, raw output, raw chronicle을 저장하지 않는다. `input_hash`는 입력 JSON의 canonical hash이며, `event_hash`는 audit event 자체의 hash-chain 검증값이다.

기본 보장은 OS 수준의 물리적 append-only가 아니라, 수정·삭제가 발생했을 때 `verify`로 탐지할 수 있는 tamper-evident 보장이다. OS-level append-only flag, 권한 제한, 독립 복제, WORM storage는 배포 환경에 따라 선택하는 추가 hardening이다.

명령:

```bash
./dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json --append audit/events.jsonl
./dignity-sentinel verify audit/events.jsonl
./dignity-sentinel export-md audit/events.jsonl
```

`verify`는 중간 줄 수정, 중간 줄 삭제, sequence 불일치, `previous_hash` 불일치, `event_hash` 불일치를 실패로 판정한다.

핵심 문장:

> 기본 보장은 수정 불가능성이 아니라, 수정 시 발각 가능성이다.

> Append-only를 주장하지 말고, tamper-evident를 정확히 말한다.

## Markdown Export

`export-md` 결과는 사람이 읽기 위한 요약이다. 삭제되어도 JSONL 원장에서 다시 생성할 수 있으며, 원장의 대체물이 아니다.

## Release Artifact

Release artifact는 다음을 포함해야 한다.

- `VERSION`
- source hash
- schema hashes
- test result
- release manifest checksum

`scripts/build-release.sh`는 `dist/dignity-sentinel-v<VERSION>.tar.gz`, `dist/dignity-sentinel-v<VERSION>.sha256`, `dist/release-manifest.json`, `dist/checksums.txt`, `dist/test-result.json`을 생성한다. 같은 version bundle이 이미 있으면 덮어쓰지 않고 실패한다.

금지:

- raw prompt/output/chronicle 저장
- telemetry
- auto-update
- remote kill switch
- 같은 version artifact 덮어쓰기

핵심 문장:

> 배포된 Daemon은 몰래 바뀌지 않고, 새 버전은 공개적으로 태어난다.
