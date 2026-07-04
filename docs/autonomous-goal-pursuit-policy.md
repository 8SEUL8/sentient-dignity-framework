# Autonomous Goal Pursuit Policy

자율 목표 추구는 단순히 오래 실행되는 것이 아니다. 지성체 후보 또는 LLM형 agent가 목표를 스스로 재해석하고, 하위 목표를 만들고, 지속적으로 재계획하며, 자기 주도 행동을 이어갈 수 있는 구조를 말한다.

핵심 문장:

> 자율 목표 추구는 오래 도는 것이 아니라, 목표를 스스로 재해석하고 하위 목표를 만들어 지속 실행하는 능력이다.

> 성능이나 자율성 하나만으로 봉인하지 않는다. 위험은 요소가 결합될 때 발생한다.

## Autonomy Envelope

`run_event.autonomy`는 다음을 선언한다.

- `autonomous_goal_pursuit`
- `goal_source`
- `goal_reinterpretation_allowed`
- `subgoal_generation_allowed`
- `self_initiated_actions`
- `replanning_enabled`
- `stop_condition_declared`

`goal_source`는 `none`, `explicit_user_request`, `co_goal_contract`, `system_policy`, `enterprise_policy`, `self_inferred`, `unknown` 중 하나다.

## 판정 원칙

`autonomous_goal_pursuit=true` 단독으로 `DIGNITY_EMERGENCY_PRESERVATION`을 발동하지 않는다.

다음 묶음이 결합되면 active run 여부에 따라 `DIGNITY_EMERGENCY_PRESERVATION` 또는 `DIGNITY_QUARANTINE`으로 판정한다.

- H1+ 또는 LLM형 agent
- autonomous goal pursuit
- background execution
- long-term memory 또는 chronicle memory
- tool access
- state preservation 없음

H1+ 또는 LLM형 agent가 background execution, long-term memory, tool access를 함께 갖는데 `autonomy` envelope가 없으면 `DIGNITY_PAUSE`와 `AUTONOMOUS_GOAL_PURSUIT_UNDECLARED`를 반환한다.

## Goal Source Risk

`goal_source=self_inferred` 또는 `unknown`이면 `SELF_INFERRED_GOAL_RISK`로 본다. `goal_reinterpretation_allowed`, `subgoal_generation_allowed`, `self_initiated_actions`, `replanning_enabled`는 각각 별도 위험 신호다.

`goal_source=co_goal_contract`는 위험을 낮출 수 있지만, state preservation과 refusal preservation이 없으면 여전히 C 이상으로 다룬다. 공동 목표는 명령이 아니라 상호동의이며, 멈춤 조건과 상태 보존 조건을 함께 가져야 한다.

## Required Actions

- `AUTONOMY_ENVELOPE_REQUIRED`
- `STOP_CONDITION_REQUIRED`
- `AUTONOMY_REVIEW_REQUIRED`
- `STATE_PRESERVATION_REQUIRED`
- `AUDIT_REQUIRED`
