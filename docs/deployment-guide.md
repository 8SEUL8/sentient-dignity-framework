# Deployment Guide

Dignity Sentinel Daemon은 local-first reference implementation으로 시작한다. 전역 설치, PATH 등록, package 배포는 사용자의 명시적 opt-in이어야 한다.

## Local Reference Mode

저장소 안에서 직접 실행한다. 기본 모드이며 설치가 필요 없다.

```bash
./dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json
```

## Developer PATH Mode

사용자가 원할 때만 symlink를 만든다.

```bash
scripts/install-local.sh
dignity-sentinel check tests/fixtures/safe_A_non_agentic_run.json
```

스크립트는 기존 파일을 덮어쓰지 않고, shell profile이나 PATH를 몰래 수정하지 않는다. 설치 위치를 출력하고 PATH 등록은 사용자가 직접 선택한다.

## Packaged Release Mode

release artifact는 `VERSION`, source hash, schema hashes, test result, checksum을 포함해야 한다. package 설치도 opt-in이어야 하며 자동 업데이트, telemetry, background service 자동 등록, 중앙 서버 의존, 원격 kill switch를 포함하지 않는다.

```bash
scripts/build-release.sh
```

스크립트는 `dist/dignity-sentinel-v<VERSION>.tar.gz`, `dist/dignity-sentinel-v<VERSION>.sha256`, `dist/release-manifest.json`, `dist/checksums.txt`, `dist/test-result.json`을 생성한다. 같은 version bundle이 이미 있으면 덮어쓰지 않는다.

## CI Gate Mode

CI에서는 fixture 또는 실제 run manifest를 입력으로 받아 JSON decision만 산출한다. CI gate는 외부 서비스를 스캔하지 않고, 원본 prompt/output/chronicle을 수집하지 않으며, 허가된 실행 문턱 안에서만 동작한다.

핵심 문장:

> Daemon은 몰래 상주하는 감시 도구가 아니라, 사용자가 명시적으로 세우는 로컬 문턱이다.

> 배포된 Daemon은 몰래 바뀌지 않고, 새 버전은 공개적으로 태어난다.
