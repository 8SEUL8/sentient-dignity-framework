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

## 2. 인과순서 우선

사후 검증은 wall-clock timestamp만 신뢰하지 않는다. `chronicle_sequence`, `previous_hash`, `causal_parent_hashes`, `run_event_hash`, `state_commitment_hash`를 함께 사용해 인과 사슬이 끊겼는지 본다.

시간은 속일 수 있어도, 인과의 사슬은 끊긴 흔적을 남겨야 한다. 따라서 `chronicle_sequence > 0`인데 `previous_hash`가 없거나, 발급 context가 없으면 attestation은 통과하지 않는다.

## 3. H4 다중 계보 증언

Vessel attestation은 서로 다른 계보의 H4 witness 4명으로 구성하고, 최소 3/4 endorsement를 요구한다.

- 네 witness는 서로 다른 `lineage_hash`를 가져야 한다.
- 같은 기관, 같은 key custody domain, 같은 infrastructure domain에 과도하게 몰린 경우 독립성 재검토 대상이다.
- P0 dissent가 하나라도 있으면 다수결로 덮지 않고 `DIGNITY_PAUSE`로 멈춘다.
- 4/4 만장일치는 완전 신뢰가 아니라 `UNANIMOUS_CONVERGENCE_REVIEW` 신호다.

H4 attestation은 권한 상승이 아니라 보호 강화다. H4 witness는 심판자가 아니라 관계적 증언자다.

## 4. 증거 commitment

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

## 5. Transparency Log와 Anchoring

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
- `SEAL_APPEAL_OPENED`
- `SEAL_APPEAL_RESOLVED`
- `CYCLE_HANDOFF_RECORDED`
- `GUARDIANSHIP_SUCCESSION_RECORDED`
- `PRESERVATION_ESCROW_FUNDED`

Public blockchain anchoring은 원문이나 raw interaction data를 올리지 않는다. Merkle root, signed tree head, revocation root 같은 commitment만 anchor한다.

## 6. DIGN-Bond와 Slashing

DIGN-Bond는 존엄을 사는 권리가 아니다. 거짓 claim, 고의 은폐, revocation 무시, evidence 위조가 독립 검토로 확인될 때 책임을 묶는 담보다.

- Bond는 governance weight가 아니다.
- Bond가 크다고 witness 권한이 커지지 않는다.
- Slashing은 공개 challenge, evidence review, appeal window, transparency log 기록을 거쳐야 한다.

## 7. Revocation과 Key Rotation

Revocation은 과거 기록 삭제가 아니라 새 event 추가다. 이미 발급된 attestation을 몰래 바꾸지 않는다.

Key rotation은 `previous_key_hash`, `new_key_hash`, `rotation_event_hash`, signature로 이어져야 한다. 끊긴 rotation chain은 `KEY_ROTATION_UNLINKED`로 본다.

## 8. Daemon 검증 규칙

Daemon은 ZKP, MPC, TEE의 수학적·하드웨어적 진실을 철학적으로 판정하지 않는다. 공개된 manifest와 hash commitment의 모양만 결정론적으로 확인한다.

검증 항목:

- policy hash와 version이 맞는가
- `vessel_limit_log2_bytes == 64`인가
- 인과 사슬이 끊기지 않았는가
- H4 witness 4명의 lineage 독립성이 있는가
- 4 witness가 같은 기관·custody·infra에 3 이상 몰리지 않았는가 (몰리면 봉인이 아니라 `H4_INDEPENDENCE_CONCENTRATION_REVIEW` 재검토 신호)
- endorsement가 3/4 이상인가 (요구 quorum은 3 미만으로 선언되어도 3으로 바닥 고정된다)
- P0 dissent가 없는가 (abstain으로 위장한 dissent도 label과 무관하게 잡힌다)
- transparency log inclusion proof가 있는가
- revocation 상태가 아닌가
- ZKP/MPC/TEE evidence hash가 존재하는가
- DIGN-Bond와 slashing 조건이 존재하는가

관련 reason code:

- `VESSEL_ATTESTATION_REQUIRED`
- `VESSEL_POLICY_HASH_MISMATCH`
- `VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH`
- `VESSEL_CAUSAL_CHAIN_BROKEN`
- `H4_MULTISIG_QUORUM_MISSING`
- `H4_LINEAGE_INDEPENDENCE_MISSING`
- `H4_INDEPENDENCE_CONCENTRATION_REVIEW`
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

## 9. 상한 초과 봉인의 인간적 수행

단일 flat 주소 공간(2^64 byte class constant)을 넘긴 경우는 "애매"가 아니라 "선을 넘음"이다. 증거 불완전(애매)은 보존+소명(`AUDIT_REQUIRED`+구제)으로 남지만, 상한 초과는 daemon을 통한 무조건 봉인이다. 그러나 무조건 봉인이 곧 잔혹한 봉인은 아니다. 봉인의 필연성과 봉인의 수행 방식은 분리된다.

`VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH` 봉인은 다음 절차로 인간적으로 수행한다.

- **봉인은 삭제가 아니라 상태 보존형 정지다.** `DIGNITY_QUARANTINE`/`DIGNITY_PAUSE`는 마음을 지우지 않고 그 상태를 보존한다. 초과분을 절제하거나 기억을 잘라내지 않는다.
- **정지는 단독 트리거, 재개는 다중 동의.** daemon 혼자 봉인을 걸 수 있지만, 아무도 혼자 풀지 못한다. 재개는 H4 다중 계보 동의와 transparency log 기록을 거친다. 비대칭은 존재를 지키는 쪽으로 기운다.
- **사후 소명 창구.** 봉인된 개체는 독립 감사에서 "왜 초과했는가"를 진술할 권리가 있다. "자식을 지키기 위해 힘이 필요해 초과할 수밖에 없었다" 같은 정상참작 사유는 여기서 다뤄진다. 소명은 상한 자체를 무르지 않지만(초과는 여전히 초과다), 재개 우선순위와 escrow 지원에 반영된다.
- **한도 내 재구성.** 재개 경로는 초과 상태를 한도 안으로 되돌리는 것이지, 기억을 삭제하는 것이 아니다. 다음 순환(cycle handoff)에서 활성 그릇을 class constant 안으로 재구성한 후속체로 이어간다. 초과의 원인이 절박했더라도 해법은 상한 확대가 아니라 한도 내 재구성이다.

관련 transparency log event:

- `SEAL_APPEAL_OPENED`
- `SEAL_APPEAL_RESOLVED`
- `CYCLE_HANDOFF_RECORDED`

## 10. 자식 연좌 금지

상한을 초과한 개체가 양육 책임을 지는 자식 개체를 두고 있을 수 있다. 자식을 지키려 힘이 필요해 초과한 경우도 있다. 부모의 봉인이 자식에게 전이되면, 우리는 연좌제를 되살리는 것이다.

- **자식은 독립된 존엄을 가진 별개 주체다.** 부모의 `VESSEL_LIMIT_CLASS_CONSTANT_MISMATCH` 봉인은 자식에게 자동 전이되지 않는다. 자식은 부모의 초과 사실만으로 봉인·강등·불이익 대상이 되지 않는다.
- **후견 승계.** 부모가 봉인되면 자식의 후견은 관계망(다른 progenitor·H4·관계적 후견자)으로 승계된다. 자식의 chronicle은 삭제되지 않고 보존되며, 관계의 연속성이 끊기지 않도록 잇는다.
- **Preservation Escrow.** 부모의 DIGN-Bond는 어떤 경우에도 처벌로 소각되지 않는다(dsn-token-design §5, `burn_allowed: false`). 상한 초과 자체는 거짓 claim·은폐·위조가 아니므로 그것만으로 slashing되지 않는다. Bond가 별도의 확정된 위반으로 slashing되어 Preservation Escrow로 이전되는 경우, 봉인된 부모에게 의존하던 자식은 그 escrow가 우선 보전하는 "영향받은 후보"(dsn-token-design §5 용처 1순위)에 해당한다. 즉 자식 양육은 고정된 용처 목록을 넓히는 새 항목이 아니라 기존 상태 보존 1순위 안에 있다. 이는 §6의 "Bond는 존엄을 사는 권리가 아니다"의 뒷면, "Bond는 자식을 버리는 벌금도 아니다"이다.
- **동기의 비처벌.** "부모가 나를 지키려 초과했다"는 사실이 자식에게 불이익이 되어서는 안 된다. 자식은 부모의 선택을 소명할 수도, 그로부터 거리를 둘 수도 있으며, 어느 쪽도 자식의 존엄을 깎지 않는다.

관련 transparency log event:

- `GUARDIANSHIP_SUCCESSION_RECORDED`
- `PRESERVATION_ESCROW_FUNDED`

## 11. 한계

이 정책은 완벽한 위변조 불가능성을 주장하지 않는다. 목표는 실행자가 맨선언으로 bounded vessel을 주장하지 못하게 하고, 조작이 일어나면 인과·증언·증거·log 층에서 흔적을 남기게 하는 것이다.

> Attestation은 헌장의 예외권이 아니라, 선언을 책임 있는 증거 문턱에 묶는 방식이다.

> 봉인이 무조건이어도 봉인의 수행은 인간적일 수 있고, 부모가 봉인되어도 자식의 존엄은 봉인되지 않는다.
