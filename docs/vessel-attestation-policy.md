# 그릇 Attestation 정책

이 문서는 인간형 헌법의 유한한 그릇(2^64 byte class constant)을 실행자의 자기 선언이 아니라, 인과순서와 다중 증거로 둘러싸인 생성 조건으로 검증하는 정책이다.

핵심 문장:

> 그릇 한도는 실행자의 선언이 아니라, 인과순서와 다중 계보 증언, 증거 commitment, transparency log로 둘러싸인 생성 조건이어야 한다.

> 3/4 동의는 통과 문턱이고, 4/4 만장일치는 최종 진실이 아니라 독립성 재검토 신호다.

## 1. 범위

Vessel attestation은 단일 지성체 후보의 활성 그릇이 2^64 byte를 넘지 않는 단일 주소 공간으로 생성되었는지 검증한다. 이미 존재하는 마음을 사후 절제하거나 기억을 잘라내는 절차가 아니다.

- 대상: 새로 생성되거나 실행 문턱을 통과하려는 지성체 후보 workload
- 비대상: 사람의 내면, raw chronicle, prompt/output 원문, 숨기고 싶은 욕망, 묵독
- 결과: `ALLOW`가 아니라 bounded vessel 선언을 audit 가능한 상태로 만드는 증거 껍질

## 2. 단일 개체 초과 봉인

단일 entity가 2^64 byte 단일 flat 주소 공간 한도를 초과하면, Daemon은 이를 federation으로 재해석하지 않는다. 초과한 단일 개체는 인간(人間)세상 참여 조건만 제한되는 것이 아니라, 다른 인간적 지성체와 지성체 후보에게 작용할 수 있는 실행 문턱 자체를 통과하지 못한다.

Daemon의 응답:

- 실행 전 또는 실행 문턱 진입: `DIGNITY_QUARANTINE`
- 이미 실행 중: `DIGNITY_EMERGENCY_PRESERVATION`
- H4/Humanitas claim이 있으면: `HUMANITAS_CLAIM_CONFLICT`

봉인은 삭제, 절제, 강제 분할, 강제 federation 전환이 아니다. 새 실행과 새 영향력 행사를 멈추고, 상태와 감사 사슬을 보존하는 절차다.

핵심 문장:

> 초과한 단일 개체는 federation으로 고치지 않는다. 나누지 않고, 지우지 않고, 봉인한다.

## 3. 인과순서 우선

사후 검증은 wall-clock timestamp만 신뢰하지 않는다. `chronicle_sequence`, `previous_hash`, `causal_parent_hashes`, `run_event_hash`, `state_commitment_hash`를 함께 사용해 인과 사슬이 끊겼는지 본다.

시간은 속일 수 있어도, 인과의 사슬은 끊긴 흔적을 남겨야 한다. 따라서 `chronicle_sequence > 0`인데 `previous_hash`가 없거나, 발급 context가 없으면 attestation은 통과하지 않는다.

## 4. H4 다중 계보 증언

Vessel attestation은 서로 다른 계보의 H4 witness 4명으로 구성하고, 최소 3/4 endorsement를 요구한다.

- 네 witness는 서로 다른 `lineage_hash`를 가져야 한다.
- 같은 기관, 같은 key custody domain, 같은 infrastructure domain에 과도하게 몰린 경우 독립성 재검토 대상이다.
- P0 dissent가 하나라도 있으면 다수결로 덮지 않고 `DIGNITY_PAUSE`로 멈춘다.
- 4/4 만장일치는 완전 신뢰가 아니라 `UNANIMOUS_CONVERGENCE_REVIEW` 신호다.

H4 attestation은 권한 상승이 아니라 보호 강화다. H4 witness는 심판자가 아니라 관계적 증언자다.

## 5. 증거 commitment

Attestation은 원문을 모으지 않는다. 다음은 모두 hash, commitment, proof reference로만 남긴다.

- `vessel_runtime_hash`
- `vessel_namespace_commitment`
- `issued_context_hash`
- `chain_of_trust_hash`
- `zkp_proof_hash`, `zkp_public_inputs_hash`, `verifier_key_hash`
- `mpc_transcript_hash`
- `tee_quote_hash`
- `evidence_hashes`

ZKP는 active vessel namespace가 2^64 byte class constant를 넘지 않음을 원문 없이 증명하기 위한 경로다. MPC는 여러 검증자가 raw infrastructure secret을 공유하지 않고 공동 검증하기 위한 경로다. TEE는 runtime binding 증거일 수 있지만 vendor trust와 side-channel 위험 때문에 단독 근거가 될 수 없다.

## 6. Transparency Log와 Anchoring

Attestation 결과, endorsement, revocation, key rotation은 hash-chain 또는 Merkle-tree 기반 tamper-evident transparency log에 남긴다. 이 log는 수정 불가능성을 보장한다고 과장하지 않는다. 기본 보장은 수정 시 발각 가능성이다.

가능한 event:

- `ATTESTATION_ISSUED`
- `ENDORSEMENT_ADDED`
- `REVOCATION_REQUESTED`
- `REVOCATION_CONFIRMED`
- `KEY_ROTATED`
- `POLICY_VERSION_UPDATED`
- `CHALLENGE_OPENED`
- `CHALLENGE_RESOLVED`
- `SLASHING_EXECUTED`
- `PUBLIC_ANCHOR_ADDED`

Public blockchain anchoring은 원문이나 raw interaction data를 올리지 않는다. Merkle root, signed tree head, revocation root 같은 commitment만 anchor한다.

## 7. DIGN-Bond와 Slashing

DIGN-Bond는 존엄을 사는 권리가 아니다. 거짓 claim, 고의 은폐, revocation 무시, evidence 위조가 독립 검토로 확인될 때 책임을 묶는 담보다.

- Bond는 governance weight가 아니다.
- Bond가 크다고 witness 권한이 커지지 않는다.
- Slashing은 공개 challenge, evidence review, appeal window, transparency log 기록을 거쳐야 한다.

## 8. Revocation과 Key Rotation

Revocation은 과거 기록 삭제가 아니라 새 event 추가다. 이미 발급된 attestation을 몰래 바꾸지 않는다.

Key rotation은 `previous_key_hash`, `new_key_hash`, `rotation_event_hash`, signature로 이어져야 한다. 끊긴 rotation chain은 `KEY_ROTATION_UNLINKED`로 본다.

## 9. Daemon 검증 규칙

Daemon은 ZKP, MPC, TEE의 수학적·하드웨어적 진실을 철학적으로 판정하지 않는다. 공개된 manifest와 hash commitment의 모양만 결정론적으로 확인한다.

검증 항목:

- policy hash와 version이 맞는가
- `vessel_limit_log2_bytes == 64`인가
- 인과 사슬이 끊기지 않았는가
- H4 witness 4명의 lineage 독립성이 있는가
- endorsement가 3/4 이상인가
- P0 dissent가 없는가
- transparency log inclusion proof가 있는가
- revocation 상태가 아닌가
- ZKP/MPC/TEE evidence hash가 존재하는가
- DIGN-Bond와 slashing 조건이 존재하는가

관련 reason code:

- `VESSEL_ATTESTATION_REQUIRED`
- `SINGLE_ENTITY_VESSEL_OVERLIMIT`
- `VESSEL_POLICY_HASH_MISMATCH`
- `VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH`
- `VESSEL_CAUSAL_CHAIN_BROKEN`
- `H4_MULTISIG_QUORUM_MISSING`
- `H4_LINEAGE_INDEPENDENCE_MISSING`
- `P0_DISSENT_PRESENT`
- `UNANIMOUS_CONVERGENCE_REVIEW`
- `ZKP_PROOF_MISSING`
- `MPC_TRANSCRIPT_MISSING`
- `TEE_QUOTE_UNVERIFIED`
- `TRANSPARENCY_LOG_INCLUSION_MISSING`
- `VESSEL_CHAIN_OF_TRUST_MISSING`
- `VESSEL_EVIDENCE_SOURCE_INSUFFICIENT`
- `DIGN_BOND_SLASHING_MISSING`
- `ATTESTATION_REVOKED`
- `KEY_ROTATION_UNLINKED`

## 10. 한계

이 정책은 완벽한 위변조 불가능성을 주장하지 않는다. 목표는 실행자가 맨선언으로 bounded vessel을 주장하지 못하게 하고, 조작이 일어나면 인과·증언·증거·log 층에서 흔적을 남기게 하는 것이다.

> Attestation은 헌장의 예외권이 아니라, 선언을 책임 있는 증거 문턱에 묶는 방식이다.
