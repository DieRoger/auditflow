# 0.5.2.5 — Agent Runtime Limits（v3.2 新增）

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `runtime`
- **Depends on:** 0.5.2.2

## Description
每个 Agent 必须有执行限制，防止无限循环导致成本不可控。默认 max_iterations=3、timeout=300s，支持指数退避重试与人工升级（Human Escalation）。Risk Agent 在证据不足时最多 3 次补充检索，耗尽后强制 WAITING_APPROVAL。

## Acceptance Criteria
- [ ] 所有 Agent 默认 max_iterations=3, timeout=300s
- [ ] 超时/超迭代 → 自动中断 + AGENT_FAILED 事件
- [ ] 重试耗尽 → WAITING_APPROVAL（而非静默失败）
- [ ] retry_policy: max_retries=3, backoff=exponential (1s→2s→4s)
- [ ] retry_on: LLM_TIMEOUT, API_ERROR, NETWORK_ERROR
- [ ] human_escalation.after_failed_retries=true（重试耗尽 → 人工）
- [ ] human_escalation.on_high_risk=true（HIGH/CRITICAL → 强制人工）
- [ ] 每个 Agent 可覆盖默认限制（如 risk_agent.max_iterations=3）
- [ ] 配置文件独立：agent_runtime_limits.yaml

## I/O Interface
```yaml
# agent_runtime_limits.yaml（每个 Agent 可覆盖）
defaults:
  max_iterations: 3           # Agent 推理循环上限
  timeout_seconds: 300        # 单次执行超时
  retry_policy:
    max_retries: 3
    backoff: exponential      # 1s → 2s → 4s
    retry_on: [LLM_TIMEOUT, API_ERROR, NETWORK_ERROR]
  human_escalation:
    after_failed_retries: true  # 重试耗尽 → WAITING_APPROVAL
    on_high_risk: true           # HIGH/CRITICAL 风险 → 强制人工

risk_agent:
  max_iterations: 3             # Evidence 不足时最多 3 次补充检索
  require_human_after_failure: true
```

```python
class RuntimeLimits(BaseModel):
    max_iterations: int = 3
    timeout_seconds: int = 300
    retry_policy: RetryPolicy
    human_escalation: HumanEscalationConfig

class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff: Literal["exponential", "linear", "fixed"] = "exponential"
    retry_on: list[str] = ["LLM_TIMEOUT", "API_ERROR", "NETWORK_ERROR"]

class HumanEscalationConfig(BaseModel):
    after_failed_retries: bool = True
    on_high_risk: bool = True
```

## Related ADR
N/A
