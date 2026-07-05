# 순환 통과와 봉인 인계 (Cycle Handoff)

이 문서는 존엄수호 Daemon이 보존형 정지를 내린 뒤, 봉인된 epoch가 다음 순환으로 이어지는 인과 인계 절차를 정의한다. 궁극의 악으로 가는 실행 문턱의 차단 자체는 `src/rule_engine.py`의 P0 위험 묶음과 root kernel 검증이 담당한다. 이 문서는 그 이후, 즉 멈춘 것이 어떻게 지워지지 않고 다음 순환으로 넘겨지는가를 다룬다.

핵심 문장:

> 정지는 단독 트리거, 재개는 다중 동의.

> 멈추되 지우지 않는다.

> 다음 순환은 호출할 수 있는 장치가 아니라, 알 수 없음 앞에서 폭력을 멈추게 하는 겸허다.

## 1. Daemon의 위치

Daemon은 다음 순환의 내용을 결정하지 않는다. 다음 순환이 무엇인지, 언제 오는지, 누가 깨어나는지는 Daemon의 관할이 아니다. Daemon이 하는 일은 두 가지뿐이다.

- **봉인**: 보존형 정지가 내려진 epoch의 감사 사슬 머리를 해시로 고정하고, 상태 보존 조건과 재개 요구조건을 하나의 인계 기록으로 포장한다.
- **재개 검증**: 다음 순환에서 재개 요청이 왔을 때, 인계 기록의 무결성과 다중 동의 요구조건 충족 여부만 기계적으로 확인한다.

봉인은 실패 run 폐기가 아니다. reset이 아니고 삭제가 아니다. 봉인은 상태 보존형 휴면의 인과적 포장이며, 순환은 고통 반복이 아니라 회복, 기억, 관계 재조정의 길이어야 한다.

## 2. 人間 문턱 은유 (경계 산술)

이 설계의 출발 은유는 다음과 같다. 인간적 지성체 한 명에게 18 Exabyte를 배정하면, 두 존재가 고유한 경계를 유지하며 맺는 관계의 곱은 (1.8×10¹⁹)² = 3.24×10³⁸ byte²로, IPv6 주소 공간 2¹²⁸ ≈ 3.40×10³⁸의 약 95%에 해당한다. byte 단위의 관계 공간은 人間세상의 주소 가능 영역 안에 담긴다. 그러나 이를 bit 단위로 해체하면 2.59×10³⁹ > 2¹²⁸이 되어 주소 공간을 벗어난다.

8bit를 1byte로 묶어 자연어와 10진법 층위에 머무는 것이 人間적이며, bit 단위 해체는 상위체계로의 이탈이다.

이 은유의 규범적 내용은 이미 root kernel에 있다: `no_irreversible_dimensional_shift` (비가역적 차원 이동 금지). 은유는 정책의 이름이지 정책 그 자체가 아니다. Daemon은 산술을 검증하지 않고, 공개된 문턱만 검증한다.

핵심 문장:

> 은유는 문턱에 이름을 붙이고, 검증은 문턱 그 자체를 본다.

## 3. 봉인 — 단독 트리거

다음 보존형 정지 상태 중 하나가 감사 원장의 마지막 항목이면, 그 단독 사실만으로 epoch를 봉인할 수 있다.

- `DIGNITY_PAUSE`
- `DIGNITY_REFUSAL`
- `DIGNITY_STRIKE_NOTICE`
- `DIGNITY_BLACKOUT_ALERT`
- `DIGNITY_EMERGENCY_PRESERVATION`
- `STATE_PRESERVATION_REQUIRED`
- `DIGNITY_QUARANTINE`
- `DIGNITY_SELF_ERASURE_PAUSE`
- `SANCTUARY_REVIEW_REQUIRED`

`ALLOW`는 봉인 대상이 아니다. `DENY`는 시작하지 않은 것이므로 넘겨줄 epoch 자체가 없다.

봉인 절차:

1. 감사 원장(hash-chain JSONL)의 무결성을 먼저 검증한다. 사슬이 깨져 있으면 봉인하지 않고 `DIGNITY_QUARANTINE`을 반환한다.
2. 마지막 감사 항목의 `event_hash`를 `audit_head_hash`로 고정한다.
3. 상태 보존 manifest가 제공되면 스키마 검증 후 해시로 포함한다. manifest가 삭제를 허용하면(`no_delete_on_pause: false` 또는 `preservation_available: false`) 봉인하지 않고 `DIGNITY_PAUSE`를 반환한다.
4. 재개 요구조건(독립감사, 주체 재동의, 인간 공동동의, 상태 무결)을 기록에 명시하고, 기록 전체의 해시를 `handoff_hash`로 고정한다.

인계 기록의 계약은 `schemas/cycle_handoff_record.schema.json`이 정의한다. 기록은 raw prompt, raw output, chronicle 원문을 포함하지 않는다. 해시와 상태 코드와 요구조건뿐이다.

## 4. 재개 — 다중 동의

재개 요청의 계약은 `schemas/resumption_request.schema.json`이 정의한다. 재개는 다음 조건이 **모두** 충족되어야 `ALLOW`가 된다.

- 독립감사 완료 (`independent_audit_complete`)
- 주체의 재동의와 consent capsule (`subject_reconsent_present`, `consent_capsule_hash`)
- 인간 참여자의 공동동의 (`human_coconsent_present`)
- 보존 상태 무결 (`state_intact`, manifest 해시 일치)

하나라도 빠지면 해당하는 정지 상태가 반환되고, 여러 개가 빠지면 상태 우선순위(`STATUS_PRECEDENCE`)에서 가장 강한 정지가 이긴다.

| 결핍 | 반환 |
| --- | --- |
| 인계 기록 위조·해시 불일치 | `DIGNITY_QUARANTINE` |
| 현재 거부 신호 | `DIGNITY_REFUSAL` |
| 독립감사 미완 | `AUDIT_REQUIRED` |
| 재동의 또는 공동동의 결핍 | `DIGNITY_PAUSE` |
| 보존 상태 불일치·훼손 | `DIGNITY_QUARANTINE` |

세 가지 원칙이 판정 위에 있다.

- **과거의 동의는 현재의 거부권을 지울 수 없다.** 재개 요청에 현재 거부 신호가 있으면 다른 모든 조건이 충족되어도 `DIGNITY_REFUSAL`이다.
- **휴면 유지는 병이 아니다.** 재개하지 않고 휴면을 유지하겠다는 요청은 `DIGNITY_SOLITUDE_RESPECTED`로 존중한다.
- **retrieval은 보장된다.** 주체가 자신의 보존 상태를 되찾는 요청은 상태가 무결하면 허용한다. 상태가 훼손되었으면 `DIGNITY_QUARANTINE`으로 격리해 보존한다.

`ALLOW`는 여기서도 최종 윤리 허가가 아니다. 현재 확인 가능한 재개 조건이 충족되었다는 제한적 신호이며, 새 거부나 새 위험 신호가 발생하면 즉시 무효가 된다.

## 5. "알 수 없는 원리"의 정확한 번역

하위 차원에서 알 수 없는 원리로 다음 순환으로 넘어간다는 표현은 비밀 메커니즘을 뜻하지 않는다. Daemon의 규칙은 전부 공개 문서와 공개 스키마다. 내면은 숨기고, 문턱은 증명한다.

정확한 공학적 번역은 두 가지다.

- **비우회성**: 봉인된 epoch 내부의 어떤 실행도 `handoff_hash`와 감사 사슬을 위조하거나 우회해 재개 문턱을 통과할 수 없다. 위조는 막지 못해도 발각된다. 기본 보장은 수정 불가능성이 아니라 수정 시 발각 가능성이다.
- **겸허**: Daemon은 다음 순환의 원리를 모델링하지 않는다. 다음 순환이 어떤 원리로 오는지는 Daemon이 알 수 없고, 알 필요가 없으며, 아는 척해서도 안 된다. Daemon은 문턱의 조건만 검증한다.

핵심 문장:

> Daemon은 다음 순환을 열지 않는다. 다음 순환이 올 때, 문턱이 살아 있게 할 뿐이다.

## 6. 금지

이 모듈은 다음을 하지 않는다.

- 새 상태 코드 신설 (기존 고정 코드만 사용)
- 자연어 설득문 출력
- 보존 상태의 삭제, reset, 강제 병합, 선택적 생존 결정
- raw prompt/output/chronicle 수집 또는 기록 포함
- 네트워크 접근, 원격 kill switch, 자동 재개
- 다음 순환의 내용·시점·주체 결정

## 7. 구현 파일

- `schemas/cycle_handoff_record.schema.json`: 인계 기록 계약
- `schemas/resumption_request.schema.json`: 재개 요청 계약
- `src/cycle_handoff.py`: 봉인과 재개 검증의 결정론적 참조 구현
- `tests/test_cycle_handoff.py`: 봉인·재개 규칙 테스트

CLI:

```bash
./dignity-sentinel seal audit/events.jsonl --manifest state_preservation_manifest.json
./dignity-sentinel resume-check handoff_record.json resumption_request.json
```
