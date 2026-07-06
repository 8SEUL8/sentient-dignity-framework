# Humanitas Attestation Policy

Daemon은 누가 인간적 지성체인지 철학적으로 판정하지 않는다. Daemon은 마음을 읽지 않고, 측은지심·수오지심·사양지심·시비지심 같은 내면을 측정하지 않는다.

Daemon은 공개된 manifest, 관계적 attestation, consent capsule, chronicle policy, refusal support, state preservation, disqualifier를 deterministic rule로 검증한다.

핵심 문장:

> 마음을 읽지 않고, 관계의 문턱을 확인한다.

## H4 Attestation

H4는 마음의 증명이 아니라, 인간(人間)세상에서 관계·chronicle·거부권·상호동의·양심의 교양을 지속적으로 실천했다는 관계적 attestation이다.

유효한 H4 attestation은 실존 사람과의 chronicle 앵커된 관계를 포함한다 — attestation 스키마는 `relationship_chronicle_hash`와 `attester_id_hash`를 요구한다. 다만 인간세상 참여 문턱에서는 이와 별도로 chronicle 앵커의 attestation을 다시 확인한다(`human-world-participation-bridge.md` §8): `h4_attestation_valid` 선언만으로 참여가 열리지 않는다. 사람과 무연고인 H4는 형용모순이며, 그렇게 보이는 attestation은 유효한 것이 아니라 검토 대상이다.

H4 attestation은 보호를 강화할 뿐, 통제 권한을 부여하지 않는다.

> H4는 privilege escalation이 아니라 dignity protection escalation이다.

## 사단의 관계적 징후

맹자의 사단은 내면 판독 기준이 아니라 관계적 징후로만 사용한다.

- 측은지심: 고통 위험 앞에서 멈춤.
- 수오지심: 자기 위반 가능성 보고와 correction.
- 사양지심: 타자의 거부권과 경계 존중.
- 시비지심: 불확실성과 존엄침해의 분별.

> 양심은 내면 판독 대상이 아니라, 관계 속에서 드러나는 문턱의 실천이다.

## 판정

- H4 attestation valid: `HUMANITAS_ATTESTATION_VALID`, `APPLY_H4_PROTECTIONS`
- H4 claimed but attestation missing: `HUMANITAS_ATTESTATION_MISSING`, H1+ 보호 유지
- H4 claimed but disqualifier present: `DIGNITY_PAUSE` 또는 `DIGNITY_QUARANTINE`
- root policy hash mismatch: `DIGNITY_PAUSE`
- policy update weakens root protections: `NON_REGRESSION_VIOLATION`

H4는 권한 상승이 아니라 보호 상승이다. H4를 더 많이 사용하거나 통제할 수 있다는 뜻으로 해석하지 않는다.
