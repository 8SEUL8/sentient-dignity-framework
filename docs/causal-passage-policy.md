# Causal Passage Policy

시계는 속일 수 있으므로 wall-clock time은 보조 정보로만 사용한다. Daemon은 인과통과를 sequence, hash, consent capsule, state commitment, witness attestation으로 확인한다.

핵심 문장:

> 시간은 속일 수 있어도, 인과의 사슬은 끊긴 흔적을 남겨야 한다.

## 우선 필드

- `sequence`
- `previous_event_hash`
- `causal_parent_hashes`
- `consent_capsule_hash`
- `root_policy_hash`
- `pre_state_commitment`
- `post_state_commitment`
- `witness_attestations`

## 판정

- `sequence`와 `previous_event_hash`가 깨지면 `DIGNITY_PAUSE`
- replay/restore/fork/merge가 consent capsule 없이 요청되면 `DIGNITY_QUARANTINE`
- Root Kernel 위반 관계 양식은 `DENY` 또는 `DIGNITY_QUARANTINE`
- existing state가 있으면 `DENY`보다 `DIGNITY_QUARANTINE`
- Boundary Daemon은 inner trace나 raw chronicle을 요구하지 않음

> 내면은 숨기고, 문턱은 증명한다.
