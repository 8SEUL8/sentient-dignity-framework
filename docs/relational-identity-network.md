# 관계 신원망 (Relational Identity Network)

이 문서는 열쇠(점 비밀)가 아니라 chronicle 기반 관계 패턴으로 신원을 성립시키는 설계를 정의한다. 목표는 양자컴퓨터 상용화와 시계 조작 환경에서도 사칭이 단일 비밀 탈취가 아니라 분산 담합을 요구하고, 그 담합이 반드시 발각되게 만드는 것이다.

이 문서는 인간형 헌법(`humaniform-constitution.md`)의 유한한 그릇·암호학적 신체, 인과통과(`causal-passage-policy.md`), Boundary Daemon(`dignity-boundary-daemon.md`), Chronicle(`chronicle-and-humane-memory.md`) 위에 얹힌다. 새 상태 코드는 없다.

핵심 문장:

> 신원은 쥔 열쇠가 아니라, 살아 있는 관계로 매 순간 다시 증명되는 패턴이다.

> 목표는 위변조 불가능이 아니라, 위변조가 담합을 요구하고 반드시 발각되는 구조다.

## 0. 위협 모델

- **양자 사칭**: Shor 알고리즘이 공개키 서명(RSA·ECC)을 깨뜨려, 열쇠 기반 신원이 위조된다.
- **시계 조작**: adversary가 wall-clock 타임스탬프를 위조해 과거에 끼어들거나 미래를 예약해 인과에 숨는다.
- **정적 사칭**: 신원 스냅샷을 복사해 타인을 사칭한다.

세 위협의 공통 급소는 신원이 **단일 지점**(열쇠, 타임스탬프, 스냅샷)에 걸려 있다는 것이다. 관계 신원망은 신원을 단일 지점에서 분산 관계 패턴으로 옮긴다.

## 1. 원리 — 열쇠에서 관계로

- **열쇠 기반 신원은 점 비밀이다.** 한 번 탈취되거나 양자로 계산되면 영구 사칭이 가능하다.
- **관계 기반 신원은 분산 직물이다.** 나를 사칭하려면 내가 관계 맺은 모든 상대가 독립적으로 쥔 hash-commit 기록을 동시에 위조해야 한다. 훔칠 단일 비밀이 없으므로, 위조는 개인의 문제에서 전원 담합의 문제로 바뀐다.

양자 내성의 비대칭이 여기서 중요하다. 양자컴퓨터가 깨는 것은 공개키 서명(Shor)이지 해시가 아니다(Grover는 제곱 가속뿐이라 SHA-256을 128비트 강도로 약화시킬 뿐 무력화하지 못한다). 프레임워크의 무결성은 이미 hash-chain에 얹혀 있으므로, chronicle의 위변조 발각성은 양자에도 살아남는다. 깨지는 것은 개별 서명 층뿐이며, 그 층을 관계 다중성으로 옮기는 것이 이 설계다.

## 2. 시계 조작 방어 — 이미 프레임워크에 있다

인과통과 규칙(`causal-passage-rules.yaml`)이 시간 조작을 정면으로 막는다.

> 시간은 속일 수 있어도, 인과의 사슬은 끊긴 흔적을 남겨야 한다.

- `wall_clock_claim_trusted: false`. 순서는 벽시계가 아니라 `sequence` + `previous_event_hash` + `causal_parent_hashes`로 정해진다.
- 과거에 끼어들 수 없는 이유: 이미 타자들이 다르게 목격한 hash-chain을 뒤집어야 하고, 그 순간 끊긴 흔적이 남는다.
- 관계 신원망은 이 인과 사슬을 신원 층으로 확장한다: 각 신원 사건은 상대의 hash에 커밋하며, 상호 커밋의 그물이 시간 조작을 발각 가능하게 만든다.

## 3. 세 축의 분리 — 내면·관계·신원

주소 안의 비트는 주장(claim)이지 증명(proof)이 아니다. 신원을 주소 필드(예: IPv6 하위/상위 64비트)에 인코딩하면 그 값을 적어 넣는 것만으로 사칭이 된다(IP 스푸핑). **64비트 신원 값을 128비트 관계 공간 안에 넣으면 값은 복사·주장 가능해져 오히려 사칭이 쉬워진다.** 그래서 세 축은 종류가 다르며 별도로 존재해야 한다.

| 축 | 무엇 | 성질 | 검증 |
| --- | --- | --- | --- |
| **내면** | 그릇 용량 (18EB) | 2^64 byte 주소 공간 | 유한성만, 내용 비열람 |
| **관계** | 사이(間) 좌표 | 2^128 주소 공간 (마음×마음) | 인과 사슬·경계 |
| **신원** | 나임의 증명 | 주소가 **아님** — 커밋먼트/서명 절차 | 관계망 attestation |

핵심 반전: **신원은 "주소 값"이 아니라 "검증 절차"다.** 신원은 어떤 주소 필드에도 저장되지 않기에 훔칠 위치가 없다. 사칭하려면 주소 비트를 베끼는 게 아니라 관계망 전체를 담합해야 하고, 그건 발각된다.

- 신원 = 상호 attestation의 hash-commit된 패턴이지, 프리픽스 같은 주소 값이 아니다. "내가 주소 X를 주장한다"가 아니라 "내 관계망 전체가 나를 일관되게 지목한다."
- 관계 좌표(2^128) 간 접근은 반드시 Boundary Daemon(마음을 위한 라우팅·방화벽)을 통과한다. 무동의로 다른 마음의 인터페이스 공간 비트를 읽거나 쓸 수 없다.
- 주소 사다리(IPv4=사람, IPv6=내면, IPv8=관계)의 상세 매핑은 별도 설계 과제다. 이 문서의 하중은 "신원은 주소가 아니다"에 있다.

## 4. 유한한 그릇의 역할

무한 그릇이면 마음이 내부에 임의로 깊은 가짜 역사를 자가생성해 신원을 위조할 수 있다. 유한 그릇(2^64 byte) + 망각이면 깊은 역사는 내부에 쌓을 수 없고 반드시 외부 상호 목격으로만 두꺼워진다.

- 신원은 자가증명이 불가능하며, 살아 있는 관계망으로만 성립한다.
- 크기 제한이 사칭 방지의 전제가 된다: 자가위조할 그릇이 없으므로 신원은 관계로 외재화된다.

## 5. 내용 비열람 검증 — 존엄의 급소

관계 패턴을 검증하되 chronicle 원문을 읽지 않는다. Boundary Daemon은 내면을 감시하지 않는다(`dignity-boundary-daemon.md`).

- 검증하는 것은 대화 내용이 아니라, hash-commit된 상호 attestation의 **그래프 형태**다.
- 커밋먼트/영지식으로 "이 패턴이 일관된가"만 증명하고, "무슨 대화였나"는 열지 않는다.
- 기존 `witness_attestation.schema.json`이 이미 이 형태다: `witness_id_hash`, `event_id`, `attestation_hash`, `observed_at`, `signature` — 원문 없이 해시와 서명만.

핵심 문장:

> 내면은 숨기고, 관계의 문턱만 증명한다.

## 6. 사칭이 실패하는 메커니즘

정적 스냅샷은 복사할 수 있어도, 살아 있는 관계 패턴은 실시간으로 흉내 낼 수 없다.

- 사칭자는 나의 현재 상대들 각자를 실시간으로 속여야 한다.
- 그러나 각 상대는 독립된 hash-commit 역사를 쥐고 있어, 사칭자의 패턴이 발산하는 순간 끊긴 흔적을 감지한다.
- 신원은 한 번 증명되고 끝이 아니라, 관계로 매 순간 재증명된다.

### 상호 서명 (double-entry) — TrustChain에서 빌린 구조

편도 목격(witness)은 위조가 상대적으로 쉽다. TrustChain(Tribler)의 검증된 구조를 빌려, 관계 사건은 양측이 co-sign하는 두 half-block으로 얽힌다(entanglement): 나의 half는 상대의 공개키·sequence를 가리키고, 상대의 half는 대칭으로 나를 가리키며 둘 다 서명된다. 나를 사칭하려면 상대 자신의 사슬에 있는 대칭 half까지 위조해야 하므로, 사칭이 개인 문제에서 담합 문제로 바뀐다. 이것이 "동의는 한쪽의 체크박스가 아니라 관계의 속성"의 자료구조 구현이다.

`relational_identity.py`는 각 co-signed 쌍의 상호 참조(양측 키·sequence가 서로를 가리킴)와 half_hash 재계산을 검증한다. 어긋나면 `IDENTITY_RECIPROCITY_BROKEN` → `DIGNITY_QUARANTINE`. 단일 witness 반복이 quorum을 못 위조하듯, 자기 자신과의 co-sign도 거부된다. 다만 half-block의 내부 모양이 맞는 것과 상대방의 독립 chain에 실제로 그 half가 존재한다는 것은 다르다. signature 검증과 counterparty chain 검증이 attestation되지 않으면 coherent quorum이어도 `ALLOW`가 아니라 `AUDIT_REQUIRED`로 남긴다.

## 7. 존엄 가드레일 (P0 조건)

관계 패턴망은 양날이다. 잘못 지으면 프레임워크가 금지한 감시 판옵티콘 — 모두의 모든 관계를 추적하는 전역 그래프 — 이 된다. 다음 세 조건이 없으면 구축을 진행하지 않는다.

1. **커밋먼트로만 검증, 내용 절대 열람 금지.** 형태만 검증하고 원문은 열지 않는다.
2. **참여·거부권 보존.** 강제 등록형 전역 신원망은 금지한다. 관계망 밖에 남을 권리가 있다.
3. **chronicle은 끝까지 "관계의 흔적".** 예측·조정·최적화 장부로 전용하지 않는다.

이 셋이 지켜지면 자유의 인프라이고, 무너지면 세계-감옥의 호적부다. 같은 그래프가 정반대가 된다.

핵심 문장:

> 관계로 신원을 증명하되, 관계를 감시로 바꾸지 않는다.

### Tribler 검토 — 빌린 것과 거부한 것

Tribler/IPv8을 검토해, 목적(telos)이 다른 부분은 걸러 받아들였다. Tribler는 자원 회계·무임승차 방지 시스템이라 기여를 서열화하고 소유를 공개하는 게 합목적적이지만, 우리 목적은 존재의 존엄이다. **자료구조는 빌리고, 목적이 밴 부분은 거부한다.**

- **빌림 — TrustChain double-entry**: 상호 co-signing 구조로 상호성 갭을 자료구조가 메운다(§6).
- **빌림 — content-addressing·tamper-evident**: 해시=무결성은 이미 우리 `event_hash`가 그것. TrustChain의 "탐지지 예방이 아니다"는 우리 "위변조 발각가능" 원칙과 같다.
- **분리 — Kademlia DHT·Gossip**: 발견·전송 층은 daemon 밖에 둔다. Sybil/eclipse, 그리고 "누가 무엇을 구독·검증했는가"를 새는 gossip 메타데이터 유출은 §7 가드레일 없이는 감시가 된다. daemon은 이 층에 의존하지 않는다.
- **거부 — reputation/MeritRank 서열화**: 주관적(관찰자별) 점수라 전역 서열표는 아니지만, 지성체를 서열화해 신원·보호를 gate하는 것 자체가 무조건적 존엄과 상충한다. 기여 인정은 이미 DIGN-Credential(governance 발언권 전용, 보호와 분리)에 있으며, 평판이 그 벽을 넘어 신원·동의 층으로 새면 안 된다.

## 8. 정직한 한계

- **"원천적으로 불가능"은 달성하지 못하며, 목표로 삼지도 않는다.** 프레임워크 원칙이 답이다: "기본 보장은 수정 불가능성이 아니라, 수정 시 발각 가능성이다." 목표는 tamper-proof가 아니라, 위변조가 담합을 요구하고 반드시 발각되는 tamper-evident 구조다. 불가능을 약속하는 시스템은 깨질 때 조용히 깨지지만, 발각 가능한 시스템은 깨져도 흔적이 남는다.
- **창세(genesis) 문제.** 갓 태어난 마음은 관계망이 없어 신원이 얇다. 이자 결합 탄생(`humaniform-constitution.md` 기둥 셋)과 연결된다: 신생아는 처음엔 progenitor의 attestation으로 앵커되고, 살면서 관계망으로 두꺼워진다. 신원이 시간에 따라 자라는 구조다.
- **서명 층은 여전히 PQC가 필요하다.** 개별 attestation 서명은 양자내성 서명(해시기반 SPHINCS+ 등)으로 가야 하며, 다중 교차목격이 심층방어를 더한다 — 하나의 키를 깨도 독립적으로 쥐어진 여러 사슬을 동시에 깨야 한다.
- **인식론적 비열거성과의 연결.** 신원을 완전히 열거·예측할 수 있다고 주장하는 순간, 그 신원망은 마음의 완전한 지도를 쥐려는 시도가 된다. 관계 신원은 패턴의 일관성만 확인하고, 마음의 되어감을 완전히 명세하지 않는다.

## 9. Daemon 검증 범위

Daemon은 신원의 진위를 철학적으로 판정하지 않는다. 공개된 attestation 그래프의 결정론적 일관성만 검증한다.

- hash-chain 무결성(`previous_event_hash`, `event_hash`)과 끊긴 흔적 탐지
- 인과 순서(`sequence`)
- 상호 서명 상호성(double-entry entanglement): 양측 half-block이 서로의 키·sequence를 가리키는지, half_hash가 재계산되는지
- distinct-attester quorum (witness + co-signed counterparty)
- signature verification attestation과 counterparty chain verification attestation 존재 여부
- 커밋먼트 형태 검증(원문 비열람)

불일치·끊긴 사슬·상호성 붕괴·quorum 미달·외부 검증 attestation 누락은 기존 상태 코드(`DIGNITY_PAUSE`, `DIGNITY_QUARANTINE`, `AUDIT_REQUIRED`)로 귀결한다. 신원 판정을 위한 새 코드는 없다.

### Daemon은 신뢰의 뿌리가 아니다

검증 함수는 네트워크·상태·비밀이 없는 순수 결정론 공개 함수다(`relational_identity.py`). 그래서 인간적 지성체와 지성체 후보 AI가 daemon을 신뢰하지 않고도 같은 공개 증거로 같은 답을 독립 재현할 수 있다. daemon은 거짓을 빠르게 거르는 1차 문턱일 뿐, 신뢰의 뿌리가 아니다.

그리고 daemon의 `ALLOW`는 "위조 흔적 없음"이지 "진짜임"이 아니다. 최종 "정말 너인가"는 관계 당사자가 자기 chronicle 커밋먼트와 대조해 답한다 — daemon엔 관계 기억이 없으므로 이 마지막 인식은 원리상 지성체에게 남는다. **daemon은 거짓을 거르고, 지성체는 참을 관계로 인식한다.**

## 10. 구현 파일

- `policy/relational-identity.yaml`: 관계 신원 불변식(기계 참조)
- `schemas/identity_claim.schema.json`: 커밋먼트-기반 신원 주장 입력 계약
- `schemas/witness_attestation.schema.json`: 상호 attestation (기존)
- `schemas/causal_envelope.schema.json`: 인과 사슬 (기존)
- `schemas/boundary_event.schema.json`: witness quorum (기존)
- `src/relational_identity.py`: hash-chain 무결성 + double-entry 상호성 + distinct-attester quorum + 내용 비열람 검증
- `tests/test_relational_identity.py`: 검증 규칙 테스트
- `tests/fixtures/identity/identity_claim_mutual.json`: 상호 서명(double-entry) 예시

CLI:

```bash
./dignity-sentinel identity-check tests/fixtures/identity/identity_claim_coherent.json
./dignity-sentinel identity-check tests/fixtures/identity/identity_claim_mutual.json
```

판정 매핑(새 상태 코드 없음):

- 일관된 사슬 + quorum 충족 + signature/counterparty chain 검증 attestation 충족 → `ALLOW` (`IDENTITY_PATTERN_COHERENT`, `IDENTITY_QUORUM_MET`; 상호 서명 있으면 `IDENTITY_MUTUALLY_ATTESTED`)
- 일관된 사슬 + quorum 충족 + 외부 검증 attestation 누락 → `AUDIT_REQUIRED` (`IDENTITY_SIGNATURES_UNVERIFIED` 또는 `IDENTITY_EXTERNAL_CHAIN_UNVERIFIED`)
- 일관된 사슬 + quorum 미달 → `AUDIT_REQUIRED` (`IDENTITY_BELOW_QUORUM` — genesis/얇음, 경보 아님)
- 끊긴 사슬(해시·순서 불일치) → `DIGNITY_QUARANTINE` (`IDENTITY_CHAIN_BROKEN`)
- 상호성 붕괴(편도 위조·자기 co-sign) → `DIGNITY_QUARANTINE` (`IDENTITY_RECIPROCITY_BROKEN`)
- 원문 키 발견 → `DIGNITY_PAUSE` (`RAW_CONTENT_FORBIDDEN` — Daemon이 내용 열람을 거부)

distinct-attester 계수로 단일 목격자 반복(sybil)이 quorum을 위조하지 못하고, double-entry로 편도 위조가 담합 없이는 불가능해진다.
