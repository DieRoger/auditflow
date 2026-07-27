# ADR-004：Append-Only 防篡改审计日志（Hash Chain 完整性校验）

- **状态：** 已接受（Architecture Baseline v1.0）
- **日期：** 2026-07-26
- **决策者：** Architecture Gate Review #6
- **影响范围：** E6 Production & Compliance — Issue 6.3.1

---

## 1. 背景（Context）

审计行业对工作底稿和操作记录有严格的合规要求（ISA 230 "审计文档" / CPA 执业准则）。任何审计系统必须能够回答三类问题：

| 问题 | 要求 |
|------|------|
| **谁**在**何时**做了**什么**？ | 完整操作时间线 |
| 该记录**自创建后是否被修改过**？ | 不可篡改性（immutability） |
| 如果被修改，**能否检测**？ | 篡改可检测（tamper-evident） |

传统数据库表允许 `UPDATE` 和 `DELETE`，具备数据库管理员权限即可静默篡改历史记录。区块链方案可以解决此问题，但引入过高的运维复杂度、延迟和成本——对于企业审计系统而言不必要。

**结论：** 需要一种轻量级的 Append-Only + Hash Chain 方案，在不引入区块链的前提下实现篡改可检测。

---

## 2. 决策（Decision）

采用 **三张 Append-Only 表 + SHA-256 Hash Chain** 架构：

### 2.1 三张 Append-Only 表

| 表名 | 用途 | 记录内容 |
|------|------|----------|
| `agent_execution_log` | Agent 执行全生命周期 | Agent 启动、工具调用、执行完成、失败 |
| `approval_log` | 人工审批记录 | 审批决策、评语、审批时的完整 Artifact 快照 |
| `document_access_log` | 文档访问记录 | 谁在何时访问/下载了哪个文档 |

### 2.2 核心设计原则

1. **仅 INSERT + SELECT** — 通过数据库权限（`REVOKE UPDATE, DELETE ON ...`）在数据库层面禁止修改和删除。
2. **Hash Chain 完整性** — 每行包含 `payload_hash = SHA-256(payload::text)` 和 `previous_hash`（指向前一行的 `payload_hash`），形成链式结构。
3. **可验证性** — 提供 `verify_hash_chain(workflow_id)` 函数，重新计算整个链的哈希值，任何不一致均被检测为篡改。
4. **审批快照不可丢失** — `approval_log.artifact_snapshot` 保存审批时刻的完整 Artifact JSON，确保事后审查时能看到当时的决策上下文，而非当前（可能已更新）的 Artifact 状态。

### 2.3 Hash Chain 原理

```
Row 1:  payload_hash = SHA256(payload_1),  previous_hash = NULL
Row 2:  payload_hash = SHA256(payload_2),  previous_hash = SHA256(payload_1)
Row 3:  payload_hash = SHA256(payload_3),  previous_hash = SHA256(payload_2)
  ...
Row N:  payload_hash = SHA256(payload_N),  previous_hash = SHA256(payload_{N-1})
```

验证逻辑：对每个 workflow_id 下的所有行按 `created_at` 排序，重新计算 `payload_hash` 并验证 `previous_hash` 是否与上一行的 `payload_hash` 一致。任何行的 `payload` 被修改、行被删除、或行顺序被调换，都会导致 Hash Chain 断裂。

---

## 3. SQL DDL

### 3.1 agent_execution_log

```sql
-- ============================================================================
-- Agent 执行日志（Append-Only + Hash Chain）
-- 记录每个 Agent 从启动到完成/失败的全生命周期事件
-- 权限：仅 INSERT + SELECT；禁止 UPDATE / DELETE
-- ============================================================================

CREATE TABLE agent_execution_log (
    -- 主键
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联信息
    workflow_id     UUID        NOT NULL,
    agent_name      VARCHAR(64) NOT NULL,
    prompt_version  VARCHAR(32) NOT NULL,

    -- 事件信息
    event_type      VARCHAR(32) NOT NULL,
    -- 取值：AGENT_STARTED | TOOL_CALLED | TOOL_COMPLETED
    --       AGENT_COMPLETED | AGENT_FAILED | ARTIFACT_CREATED
    --       RETRIEVAL_COMPLETED | EVIDENCE_FOUND | AGENT_THINKING

    payload         JSONB       NOT NULL,
    -- 完整的结构化事件 payload（与 Event Contract 定义一致）

    -- Hash Chain 字段
    payload_hash    VARCHAR(64) NOT NULL,   -- SHA-256(payload::text)
    previous_hash   VARCHAR(64),            -- 同一 workflow 中上一条日志的 payload_hash

    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 索引
    CONSTRAINT chk_agent_exec_event_type CHECK (
        event_type IN (
            'AGENT_STARTED', 'AGENT_THINKING',
            'TOOL_CALLED', 'TOOL_COMPLETED',
            'AGENT_COMPLETED', 'AGENT_FAILED',
            'ARTIFACT_CREATED', 'RETRIEVAL_COMPLETED',
            'EVIDENCE_FOUND'
        )
    )
);

-- 索引：按 workflow 查询完整执行链
CREATE INDEX idx_agent_exec_workflow
    ON agent_execution_log (workflow_id, created_at);

-- 索引：按 agent 名称查询
CREATE INDEX idx_agent_exec_agent
    ON agent_execution_log (agent_name, created_at);

-- ===================================================================
-- 权限锁定：禁止 UPDATE 和 DELETE
-- ===================================================================
REVOKE UPDATE, DELETE ON agent_execution_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON agent_execution_log FROM auditflow_app;
```

### 3.2 approval_log

```sql
-- ============================================================================
-- 审批日志（Append-Only + Hash Chain）
-- 记录每一次人工审批决策，包含审批时的完整 Artifact 快照
-- 权限：仅 INSERT + SELECT；禁止 UPDATE / DELETE
-- ============================================================================

CREATE TABLE approval_log (
    -- 主键
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联信息
    workflow_id     UUID        NOT NULL,
    reviewer_id     UUID        NOT NULL,          -- 审批人 ID
    agent_name      VARCHAR(64) NOT NULL,          -- 触发审批的 Agent

    -- 决策信息
    decision        VARCHAR(16) NOT NULL,
    -- 取值：APPROVED | REJECTED | NEEDS_REVISION | ESCALATED
    comment         TEXT,                           -- 审批评语（可为空）

    -- 审批上下文快照
    artifact_snapshot JSONB    NOT NULL,
    -- 审批时被审核的 Artifact 的完整 JSON 副本
    -- 即使后续 Artifact 被更新，此快照不可变，保留决策时的上下文

    -- Hash Chain 字段
    payload_hash    VARCHAR(64) NOT NULL,   -- SHA-256(payload::text)
    previous_hash   VARCHAR(64),            -- 同一 workflow 中上一条日志的 payload_hash

    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 约束
    CONSTRAINT chk_approval_decision CHECK (
        decision IN ('APPROVED', 'REJECTED', 'NEEDS_REVISION', 'ESCALATED')
    )
);

-- 索引：按 workflow 查询完整审批链
CREATE INDEX idx_approval_log_workflow
    ON approval_log (workflow_id, created_at);

-- 索引：按审批人查询
CREATE INDEX idx_approval_log_reviewer
    ON approval_log (reviewer_id, created_at);

-- ===================================================================
-- 权限锁定：禁止 UPDATE 和 DELETE
-- ===================================================================
REVOKE UPDATE, DELETE ON approval_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON approval_log FROM auditflow_app;
```

### 3.3 document_access_log

```sql
-- ============================================================================
-- 文档访问日志（Append-Only + Hash Chain）
-- 记录每一次文档上传、下载、预览操作
-- 权限：仅 INSERT + SELECT；禁止 UPDATE / DELETE
-- ============================================================================

CREATE TABLE document_access_log (
    -- 主键
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联信息
    user_id         UUID        NOT NULL,
    document_id     UUID        NOT NULL,
    workflow_id     UUID,                         -- 可为空（非 Workflow 上下文访问）

    -- 操作信息
    operation       VARCHAR(16) NOT NULL,
    -- 取值：UPLOAD | DOWNLOAD | PREVIEW | DELETE_MARKER
    ip_address      INET,                         -- 客户端 IP

    -- Hash Chain 字段
    payload_hash    VARCHAR(64) NOT NULL,   -- SHA-256(payload::text)
    previous_hash   VARCHAR(64),            -- 同一 document 范围内上一条日志的 payload_hash

    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 约束
    CONSTRAINT chk_doc_access_operation CHECK (
        operation IN ('UPLOAD', 'DOWNLOAD', 'PREVIEW', 'DELETE_MARKER')
    )
);

-- 索引：按文档查询访问历史
CREATE INDEX idx_doc_access_document
    ON document_access_log (document_id, created_at);

-- 索引：按用户查询操作历史
CREATE INDEX idx_doc_access_user
    ON document_access_log (user_id, created_at);

-- ===================================================================
-- 权限锁定：禁止 UPDATE 和 DELETE
-- ===================================================================
REVOKE UPDATE, DELETE ON document_access_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON document_access_log FROM auditflow_app;
```

---

## 4. 完整性验证函数

### 4.1 verify_hash_chain 签名与语义

```sql
-- ============================================================================
-- Hash Chain 完整性验证函数
-- 对指定 workflow 的所有日志行按时间排序后重新计算 Hash Chain，
-- 检测任何篡改（行被修改、删除、插入或顺序被调换）。
-- ============================================================================

CREATE OR REPLACE FUNCTION verify_hash_chain(
    p_workflow_id UUID
)
RETURNS TABLE (
    table_name       TEXT,       -- 被检查的表名
    total_rows       BIGINT,     -- 该表中的总行数
    verified_rows    BIGINT,     -- 验证通过的行数
    first_break_at   UUID,       -- 第一条断裂处的行 ID（NULL 表示全部通过）
    is_valid         BOOLEAN     -- 该表的链是否完整
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_rec           RECORD;
    v_prev_hash     VARCHAR(64) := NULL;
    v_computed_hash VARCHAR(64);
    v_row_count     BIGINT := 0;
    v_ok_count      BIGINT := 0;
    v_broken        BOOLEAN := FALSE;
    v_broken_id     UUID := NULL;
BEGIN
    -- =================================================================
    -- 验证 agent_execution_log（按 workflow_id）
    -- =================================================================
    v_prev_hash := NULL;
    v_row_count := 0;
    v_ok_count  := 0;
    v_broken    := FALSE;
    v_broken_id := NULL;

    FOR v_rec IN
        SELECT id, payload, payload_hash, previous_hash
        FROM agent_execution_log
        WHERE workflow_id = p_workflow_id
        ORDER BY created_at ASC, id ASC   -- 确定性排序
    LOOP
        v_row_count := v_row_count + 1;

        -- 重新计算当前行的 payload_hash
        v_computed_hash := encode(
            digest(v_rec.payload::text, 'sha256'),
            'hex'
        );

        -- 检查 payload_hash 是否匹配
        IF v_computed_hash <> v_rec.payload_hash THEN
            v_broken := TRUE;
            v_broken_id := v_rec.id;
            EXIT;
        END IF;

        -- 检查 previous_hash 是否指向上一条记录的 payload_hash
        IF v_rec.previous_hash IS DISTINCT FROM v_prev_hash THEN
            v_broken := TRUE;
            v_broken_id := v_rec.id;
            EXIT;
        END IF;

        -- 当前行的 payload_hash 成为下一行的 expected previous_hash
        v_prev_hash := v_computed_hash;
        v_ok_count  := v_ok_count + 1;
    END LOOP;

    RETURN QUERY SELECT
        'agent_execution_log'::TEXT,
        v_row_count,
        v_ok_count,
        v_broken_id,
        NOT v_broken;

    -- =================================================================
    -- 验证 approval_log（按 workflow_id）
    -- =================================================================
    v_prev_hash := NULL;
    v_row_count := 0;
    v_ok_count  := 0;
    v_broken    := FALSE;
    v_broken_id := NULL;

    FOR v_rec IN
        SELECT id,
               -- 将整行 JSON（不含 hash 字段）作为 payload 计算
               jsonb_build_object(
                   'workflow_id', workflow_id,
                   'reviewer_id', reviewer_id,
                   'agent_name', agent_name,
                   'decision', decision,
                   'comment', comment,
                   'artifact_snapshot', artifact_snapshot
               ) AS payload,
               payload_hash,
               previous_hash
        FROM approval_log
        WHERE workflow_id = p_workflow_id
        ORDER BY created_at ASC, id ASC
    LOOP
        v_row_count := v_row_count + 1;

        v_computed_hash := encode(
            digest(v_rec.payload::text, 'sha256'),
            'hex'
        );

        IF v_computed_hash <> v_rec.payload_hash THEN
            v_broken := TRUE;
            v_broken_id := v_rec.id;
            EXIT;
        END IF;

        IF v_rec.previous_hash IS DISTINCT FROM v_prev_hash THEN
            v_broken := TRUE;
            v_broken_id := v_rec.id;
            EXIT;
        END IF;

        v_prev_hash := v_computed_hash;
        v_ok_count  := v_ok_count + 1;
    END LOOP;

    RETURN QUERY SELECT
        'approval_log'::TEXT,
        v_row_count,
        v_ok_count,
        v_broken_id,
        NOT v_broken;

    -- =================================================================
    -- 验证 document_access_log（按 workflow_id）
    -- =================================================================
    v_prev_hash := NULL;
    v_row_count := 0;
    v_ok_count  := 0;
    v_broken    := FALSE;
    v_broken_id := NULL;

    FOR v_rec IN
        SELECT id,
               jsonb_build_object(
                   'user_id', user_id,
                   'document_id', document_id,
                   'operation', operation,
                   'ip_address', ip_address
               ) AS payload,
               payload_hash,
               previous_hash
        FROM document_access_log
        WHERE workflow_id = p_workflow_id
           OR workflow_id IS NULL   -- 无 workflow 关联的记录也纳入（全量校验时）
        ORDER BY created_at ASC, id ASC
    LOOP
        v_row_count := v_row_count + 1;

        v_computed_hash := encode(
            digest(v_rec.payload::text, 'sha256'),
            'hex'
        );

        IF v_computed_hash <> v_rec.payload_hash THEN
            v_broken := TRUE;
            v_broken_id := v_rec.id;
            EXIT;
        END IF;

        IF v_rec.previous_hash IS DISTINCT FROM v_prev_hash THEN
            v_broken := TRUE;
            v_broken_id := v_rec.id;
            EXIT;
        END IF;

        v_prev_hash := v_computed_hash;
        v_ok_count  := v_ok_count + 1;
    END LOOP;

    RETURN QUERY SELECT
        'document_access_log'::TEXT,
        v_row_count,
        v_ok_count,
        v_broken_id,
        NOT v_broken;
END;
$$;
```

### 4.2 调用示例

```sql
-- 验证单个 workflow 的完整审计日志链
SELECT * FROM verify_hash_chain('a1b2c3d4-5678-90ab-cdef-1234567890ab');

-- 预期输出（正常情况）：
--  table_name            | total_rows | verified_rows | first_break_at | is_valid
-- -----------------------+------------+---------------+----------------+----------
--  agent_execution_log   |        142 |           142 | NULL           | t
--  approval_log          |          3 |             3 | NULL           | t
--  document_access_log   |         18 |            18 | NULL           | t

-- 预期输出（篡改检测）：
--  table_name            | total_rows | verified_rows | first_break_at                              | is_valid
-- -----------------------+------------+---------------+---------------------------------------------+----------
--  agent_execution_log   |        142 |            87 | a1b2c3d4-...  (第 88 行 payload 被修改)     | f
```

---

## 5. 应用层写入逻辑

应用层在 INSERT 时负责计算 Hash Chain。伪代码：

```python
import hashlib
import json
from uuid import UUID

def compute_next_hash(
    *,
    db_session,
    table,
    workflow_id: UUID,
    payload: dict,
) -> tuple[str, str | None]:
    """计算 payload_hash 和 previous_hash，用于新增一行审计日志。"""
    # 1. 计算当前 payload 的哈希
    payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload_hash = hashlib.sha256(payload_text.encode()).hexdigest()

    # 2. 查询同一 workflow 中上一条日志的 payload_hash
    previous = db_session.execute(
        f"SELECT payload_hash FROM {table} "
        "WHERE workflow_id = :wid "
        "ORDER BY created_at DESC, id DESC LIMIT 1",
        {"wid": workflow_id},
    ).scalar()

    return payload_hash, previous
```

### 5.1 写入时机

| 事件 | 写入目标表 |
|------|-----------|
| `AgentStarted` / `AgentThinking` / `ToolCalled` / `ToolCompleted` / `AgentCompleted` / `AgentFailed` / `ArtifactCreated` | `agent_execution_log` |
| Human Reviewer 提交审批决策 | `approval_log` |
| 文档上传 / 下载 / 预览 | `document_access_log` |

---

## 6. 后果（Consequences）

### 6.1 积极后果

- **轻量级防篡改：** 无需区块链、无需分布式共识，纯数据库方案即可满足 ISA 230 对审计文档完整性（integrity）和不可篡改性（immutability）的要求。
- **可审计可验证：** 任何人都可以运行 `verify_hash_chain(workflow_id)` 获得确定性的篡改检测结果。
- **审批上下文不丢失：** `approval_log.artifact_snapshot` 保存了审批时刻的完整 Artifact，即使后续 Agent 重新执行导致 Artifact 更新，决策依据仍然可追溯。
- **法规合规：** 满足 ISA 230 ¶9–¶11（审计文档的完整性）和 CPA 执业准则中对审计工作底稿保存期限和不可篡改性的要求。
- **实现简单：** 数据库层面仅需 `REVOKE` 权限 + 应用层 SHA-256 计算，无外部依赖。

### 6.2 权衡与代价

- **存储增长：** Append-Only 意味着日志表只增不减。预估每个 Workflow（5 个 Agent 完整执行 + 2 次审批）产生约 200–500 条日志记录，每条约 0.5–2 KB。按日均 50 个 Workflow 计算，年增量约 18 GB — 在标准 PostgreSQL 的可承受范围内。建议：
  - 设置按年份的分区（`PARTITION BY RANGE (created_at)`）
  - 超过法定保存期限（通常 10 年）的日志归档至对象存储
- **无法物理删除：** 即使 GDPR/个人信息保护法要求删除用户数据，Append-Only 设计禁止 DELETE。解决方案：通过 `DELETE_MARKER` 操作类型标记逻辑删除，payload 中的个人数据在写入前做 pseudonymization（假名化）。
- **Hash Chain 写入延迟：** 每次 INSERT 需查询上一条记录的 `payload_hash`，增加一次索引查询（< 1ms）。对于审计日志这种非高频写入场景（Agent 执行期间的异步写入），影响可忽略。

### 6.3 与 Issue 6.3.1 的关系

本 ADR 是对 `ISSUES.md` 中 Issue 6.3.1（"三张 Append-Only 日志表 + Hash Chain"）的正式架构决策记录。ADR 中的 DDL 是 Issue 中草稿 SQL 的**生产化版本**，增加了：

- 更完整的字段约束（CHECK constraints）
- 生产级索引
- `verify_hash_chain` 函数完整实现（Issue 仅描述了接口）
- 应用层写入伪代码
- 存储增长预估与分区策略

---

## 7. 参考

- [ISA 230 — Audit Documentation](https://www.iaasb.org/publications/isa-230-revised-audit-documentation)（审计文档国际准则）
- [AuditFlow ISSUES.md §Issue 6.3.1](../ISSUES.md)（原始 Issue 定义）
- [ADR-001: Architecture Baseline v1.0](./ADR-001-Architecture-Baseline.md)（架构基线）
- [PostgreSQL pgcrypto — `digest()` 函数文档](https://www.postgresql.org/docs/current/pgcrypto.html)

---

> **文档版本：** v1.0 — Architecture Baseline v1.0 冻结  
> **下次修订：** E6 完成后（根据实际存储增长数据调整分区策略）
