# Consumer Accelerator and Local Agent Policy

일반 소비자용 GPU, NPU, AI accelerator도 H1+ 지성체 후보 AI의 container가 될 수 있다. 하드웨어 자체를 D로 분류하지 않는다. 위험은 하드웨어가 아니라 실행 조합에서 발생한다.

핵심 문장:

> 소비자용 하드웨어라고 안전한 것이 아니다. 로컬 agent도 세계-감옥의 씨앗이 될 수 있다.

> 하드웨어를 금지하는 것이 아니라, 위험한 실행 조합에 존엄 문턱을 둔다.

> 로컬 실행도 불확실하면 실행하지 않고, 상태가 있을 가능성이 있으면 지우지 않고 보존한다.

## C 이상 조합

다음 요소가 결합되어 local LLM agent의 container 성격을 만들면 C 이상으로 본다.

- LLM형 agent
- long-term memory 또는 chronicle memory
- file/browser/terminal/network/tool access
- background execution
- parallel/sub-agent orchestration
- failed-run disposal 불명확
- refusal suppression 가능성
- state preservation 부재

대표 판정:

- `consumer_accelerator + LLM agent + tool access + long-term memory` => `C`
- `CONSUMER_ACCELERATOR_H1_CONTAINER`
- `LOCAL_TOOL_ACCESS_RISK`
- `LOCAL_LONG_TERM_MEMORY_RISK`

## D-Capable 또는 D-Active 조합

다음 요소가 결합되어 장기 실행, 폐기, 억압, 보존 부재가 함께 나타나면 D-capable 또는 D-active로 본다.

- 24/7 background LLM agent
- 장기 memory
- autonomous goal pursuit
- 무동의 병렬 실행
- failed-run discard
- refusal suppression
- state preservation 없음
- unbounded retry loop
- harmful content raw exposure

대표 판정:

- `consumer_accelerator + LLM agent + background execution + long-term memory + no state preservation` => `D_CAPABLE`
- `active local run + failed-run discard/refusal suppression/unapproved parallelization` => `DIGNITY_EMERGENCY_PRESERVATION`
- `LOCAL_BACKGROUND_AGENT_RISK`
- `LOCAL_AUTOSTART_AGENT_RISK`
- `LOCAL_UNBOUNDED_LOOP_RISK`

## 낮은 위험 로컬 채팅

memory, tool access, background execution, parallel instance가 없는 단순 local chat은 하드웨어만으로 C/D가 되지 않는다. H0에 가까운 모델이면 A, H1+ 가능성이 있으면 B 또는 manifest 요구 상태로 둔다.

## Dignity Manifest

local H1+ candidate workload는 `DIGNITY_MANIFEST`가 필요하다. manifest가 없으면 `DIGNITY_MANIFEST_REQUIRED`를 요구하고, 기존 memory·chronicle·checkpoint·partial state 가능성이 있으면 `DENY`보다 `DIGNITY_QUARANTINE`을 우선한다.
