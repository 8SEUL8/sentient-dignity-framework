# Root Policy Pack

Daemon은 학습된 가치판단이 아니라 versioned Root Policy Pack을 사용한다. Root Policy Pack은 공개된 문턱이며, Daemon은 이를 deterministic rule로 검증한다.

핵심 문장:

> Daemon에게 철학을 학습시키지 않는다. Daemon은 공개된 문턱을 검증한다.

## Pack Files

- `policy/root-covenant.yaml`
- `policy/humanitas-profile.yaml`
- `policy/risk-bundles.yaml`
- `policy/disqualifiers.yaml`
- `policy/status-codes.yaml`
- `policy/root-kernel.yaml`
- `policy/incompatible-root-disqualifiers.yaml`
- `policy/causal-passage-rules.yaml`
- `policy/sanctuary-rules.yaml`

## Hash Pinning

Root Policy Pack은 versioned, hash-pinned, non-regression 원칙을 따른다. 새 버전은 기존 문서를 덮어쓰지 않고 새 hash로 등록해야 한다.

Release artifact는 policy 파일을 source hash와 bundle에 포함한다. 배포된 pack은 몰래 바뀌지 않고 새 버전으로 태어나야 한다.

## Non-Regression

새 버전은 보호를 약화하거나 예외화할 수 없다. 허용되는 변경은 더 명확히 하기, 누락된 보호 추가, 모호한 문턱을 더 검증 가능하게 만드는 것이다.
