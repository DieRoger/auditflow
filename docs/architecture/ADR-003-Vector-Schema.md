# ADR-003：统一向量存储 Schema 与企业级租户隔离

> **状态：** 已接受（Architecture Baseline v1.0）  
> **日期：** 2026-07-26  
> **冻结里程碑：** E0.5 MileStone 0.5.4  
> **关联文档：** `auditflow/docs/api/embedding-contract.md`

---

## 1. 背景 (Context)

AuditFlow 平台有三个核心模块需要向量存储能力：

| 模块 | 向量检索需求 |
|---|---|
| **Document Intelligence** | 将客户上传的凭证、合同、发票等文档切分后存入向量库，支持语义检索与相似文档匹配。 |
| **Knowledge Layer** | 存储审计准则（ISA、GAAS）、行业法规、历史审计案例的嵌入向量，供 Agent 在规划与风险评估阶段检索。 |
| **Evidence Engine** | 将 Workpaper 段落、风险评估结论、底稿摘要向量化，支持跨证据链的相似性比对与异常检测。 |

在架构基线阶段，我们面临一个关键决策：

> 如果没有统一的向量 Schema，每个模块会各自创建互不兼容的向量表（字段命名、元数据结构、隔离键各不相同），导致"跨源混合检索"在架构层面就不可能实现 —— 你无法在一条 SQL 中同时检索客户文档与审计准则。

更严重的是：**审计行业要求严格的租户间数据隔离**。如果向量存储层没有在 Schema 级别嵌入 `firm_id` / `engagement_id` 并强制注入查询谓词，任何一处疏漏都可能导致跨事务所的数据泄漏 —— 这在 SOC 2 / ISAE 3402 合规审计中是不可接受的设计缺陷。

因此，我们在 E0.5 里程碑冻结了统一的 `EmbeddingItem` Schema 与 `VectorStore` 抽象接口。

---

## 2. 决策 (Decision)

### 2.1 决策 1：统一 EmbeddingItem Schema

**所有**向量数据 —— 无论来源是客户文档、审计准则、Workpaper 还是风险案例 —— 都走同一张 `EmbeddingItem` 表，通过 `source_type` 枚举字段区分来源。

### 2.2 决策 2：强制租户-委托双层隔离

每条向量记录必须携带以下四个隔离字段：

| 字段 | 说明 |
|---|---|
| `firm_id` | 审计事务所 ID（一级租户隔离键） |
| `client_id` | 被审计客户 ID |
| `engagement_id` | 审计委托 ID（二级隔离键 —— 同一事务所的不同项目不可互见） |
| `security_level` | 数据密级（`PUBLIC` / `INTERNAL` / `CONFIDENTIAL` / `RESTRICTED`） |

**所有 `VectorStore` 查询方法必须在内部自动注入 `firm_id` + `engagement_id` 过滤条件**，调用方不应、也不能绕过。

### 2.3 决策 3：PGVector + HNSW 索引

选用 PostgreSQL + `pgvector` 扩展的 HNSW 索引作为首版向量存储引擎。理由：

- 审计数据天然属于关系型模型，PGVector 避免了"关系库 + 向量库"双写一致性问题。
- HNSW 在百万级向量规模下提供 < 10ms 的近似最近邻检索延迟，满足当前需求。
- 与现有 PostgreSQL 运维体系（备份、HA、审计日志）完全兼容。

### 2.4 决策 4：统一 EmbeddingProvider 抽象

提供一个 `EmbeddingProvider` 抽象基类，首批实现：

- **OpenAI `text-embedding-3-large`**（默认，维度 3072）
- **BGE-M3 本地部署**（维度 1024，适用于不允许数据出所的合规场景）

上层模块只依赖 `EmbeddingProvider` 接口，通过 DI 注入具体实现。

---

## 3. 后果 (Consequences)

### 有利后果 ✅

1. **跨源混合检索成为可能**：一条查询可以同时召回匹配的客户文档段落与审计准则条款，Workflow Engine 在一个查询中构建完整的上下文。
2. **租户-委托隔离在存储层落地**：`VectorStore` 接口在方法签名层面吞噬了隔离逻辑，业务代码几乎不可能写出跨租户查询。
3. **引擎可替换**：未来迁移到 Milvus / Qdrant 等专用向量数据库时，只需实现 `VectorStore` 接口并更换 DI 绑定，上层模块完全无感。
4. **统一的 Embedding 生命周期**：生成、缓存、过期、重新嵌入全走同一套流程，避免了三个模块各自维护 Embedding 管道的重复工作。

### 需关注的风险 ⚠️

1. **单表规模增长**：三个模块的数据汇聚到同一张表，当向量总数达到亿级时，可能需要分区表（按 `firm_id` HASH 分区）或升级引擎。
2. **`metadata` JSONB 的 Schema-Less 风险**：虽然 JSONB 提供了灵活性，但各模块需要遵守一份"元数据键约定"，否则跨源检索的语义一致性无法保证（由 `auditflow/docs/api/embedding-contract.md` 补充约束）。

---

## 4. 核心模型与接口

### 4.1 EmbeddingItem — Pydantic 数据模型

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── 枚举定义 ──────────────────────────────────────────────

class SourceType(str, Enum):
    """向量来源类型 —— 决定了向量在业务语义上的归属。"""
    CLIENT_DOCUMENT = "CLIENT_DOCUMENT"       # 客户上传文档（合同、发票、凭证等）
    AUDIT_STANDARD  = "AUDIT_STANDARD"        # 审计准则 / 法规
    WORKPAPER       = "WORKPAPER"             # 审计底稿段落
    RISK_CASE       = "RISK_CASE"             # 历史风险案例 / 判断摘要


class SecurityLevel(str, Enum):
    """数据密级 —— 遵循企业四级分类标准。"""
    PUBLIC       = "PUBLIC"        # 公开信息（如已发布的审计准则条文）
    INTERNAL     = "INTERNAL"      # 内部使用（如通用底稿模板）
    CONFIDENTIAL = "CONFIDENTIAL"  # 机密（客户财务报表数据）
    RESTRICTED   = "RESTRICTED"    # 受限（如涉及诉讼的风险评估结论）


# ── 核心模型 ──────────────────────────────────────────────

class EmbeddingItem(BaseModel):
    """统一向量条目 —— 所有模块的向量数据共用此 Schema。

    一行对应一条"文本块 + 向量 + 来源元数据"，是语义检索的最小原子单元。
    """

    # ── 主键 ─────────────────────────────────────────────
    id: UUID = Field(
        default_factory=uuid4,
        description="向量条目全局唯一 ID。"
    )

    # ── 多租户隔离键（必填） ─────────────────────────────
    firm_id: str = Field(
        ...,
        description="审计事务所 ID。一级租户隔离键。",
    )
    client_id: str = Field(
        ...,
        description="被审计客户 ID。",
    )
    engagement_id: str = Field(
        ...,
        description="审计委托 ID。同所不同项目之间必须隔离。",
    )

    # ── 来源追踪 ─────────────────────────────────────────
    source_type: SourceType = Field(
        ...,
        description="向量来源类型。用于跨源过滤与混合检索场景区分。",
    )
    source_id: str = Field(
        ...,
        description="来源实体的业务 ID。例如文档 ID、准则条款号、Workpaper ID。",
    )

    # ── 内容 ─────────────────────────────────────────────
    content: str = Field(
        ...,
        description="原始文本块（用于生成 Embedding 的输入）。最大 8192 字符。",
        max_length=8192,
    )
    embedding: list[float] = Field(
        ...,
        description="向量嵌入。维度取决于 EmbeddingProvider 配置。",  
    )

    # ── 可扩展元数据 ─────────────────────────────────────
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "来源特有的扩展字段（JSONB）。各模块需遵守 metadata key 约定，"
            "见 auditflow/docs/api/embedding-contract.md。"
        ),
    )

    # ── 安全分级 ─────────────────────────────────────────
    security_level: SecurityLevel = Field(
        default=SecurityLevel.CONFIDENTIAL,
        description="数据密级。查询时自动过滤：当前用户的安全许可必须 >= 条目的 security_level。",
    )

    # ── 时间戳 ───────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="向量条目创建时间（UTC）。",
    )

    class Config:
        use_enum_values = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
```

### 4.2 EmbeddingProvider — 抽象基类

```python
from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    """向量嵌入服务抽象。

    上层模块通过此接口获取文本嵌入，不感知底层模型是 OpenAI 还是本地 BGE-M3。
    每个实现负责自己的维度声明、批处理策略与重试逻辑。
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回该 Provider 生成的嵌入向量维度。"""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> np.ndarray:
        """将一批文本编码为嵌入向量。

        Args:
            texts: 待编码的文本列表。每条长度不应超过模型上下文窗口。

        Returns:
            shape=(len(texts), self.dimension) 的 float32 数组。
        """
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> np.ndarray:
        """单条文本嵌入的便捷方法。默认实现可复用 embed()。"""
        ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding-3-large 实现。"""

    @property
    def dimension(self) -> int:
        return 3072

    async def embed(self, texts: list[str]) -> np.ndarray:
        # 实际实现调用 openai.AsyncOpenAI
        ...

    async def embed_single(self, text: str) -> np.ndarray:
        ...


class BGEM3EmbeddingProvider(EmbeddingProvider):
    """BGE-M3 本地部署实现（维度 1024，适用于合规要求数据不出所的场景）。"""

    @property
    def dimension(self) -> int:
        return 1024

    async def embed(self, texts: list[str]) -> np.ndarray:
        # 实际实现调用本地 BGE-M3 推理服务
        ...

    async def embed_single(self, text: str) -> np.ndarray:
        ...
```

### 4.3 VectorStore — 抽象基类

```python
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

import numpy as np


class VectorStore(ABC):
    """向量存储抽象。

    所有实现必须强制注入 firm_id + engagement_id 过滤，
    调用方不应在 search 参数中手动传入这两个隔离键。
    """

    @abstractmethod
    async def insert(self, item: EmbeddingItem) -> UUID:
        """插入一条向量条目。返回其 id。"""
        ...

    @abstractmethod
    async def insert_batch(self, items: list[EmbeddingItem]) -> list[UUID]:
        """批量插入。默认实现可复用 insert()。"""
        ...

    @abstractmethod
    async def search(
        self,
        *,
        query_embedding: np.ndarray,
        firm_id: str,
        engagement_id: str,
        top_k: int = 10,
        source_types: Optional[list[SourceType]] = None,
        security_levels: Optional[list[SecurityLevel]] = None,
    ) -> list[EmbeddingItem]:
        """基于余弦相似度的近似最近邻搜索。

        Args:
            query_embedding: 查询向量 (dimension,)。
            firm_id: 强制租户过滤 —— 由 Workflow Engine 注入。
            engagement_id: 强制委托过滤 —— 由 Workflow Engine 注入。
            top_k: 返回最相似的 K 条记录。
            source_types: 可选来源类型过滤（跨源混合检索时不传或传多种类型）。
            security_levels: 可选密级过滤（默认仅返回当前用户可见的密级）。

        Returns:
            按相似度降序排列的 EmbeddingItem 列表。
        """
        ...

    @abstractmethod
    async def delete_by_source(self, *, source_type: SourceType, source_id: str) -> int:
        """按来源删除向量（例如文档被删除时级联清理）。返回删除行数。"""
        ...

    @abstractmethod
    async def delete_by_engagement(self, *, firm_id: str, engagement_id: str) -> int:
        """删除指定委托下的全部向量（项目归档或销毁）。返回删除行数。"""
        ...
```

### 4.4 PGVector DDL

```sql
-- ============================================================================
-- ADR-003 统一向量存储 Schema — PostgreSQL + pgvector DDL
-- 要求: PostgreSQL 15+、pgvector 0.5.0+
-- ============================================================================

-- 1. 启用扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. 枚举类型（与应用层 Pydantic Enum 保持同步）
CREATE TYPE source_type_enum AS ENUM (
    'CLIENT_DOCUMENT',
    'AUDIT_STANDARD',
    'WORKPAPER',
    'RISK_CASE'
);

CREATE TYPE security_level_enum AS ENUM (
    'PUBLIC',
    'INTERNAL',
    'CONFIDENTIAL',
    'RESTRICTED'
);

-- 3. 核心向量表
CREATE TABLE embedding_item (
    -- ── 主键 ──────────────────────────────────────────
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- ── 多租户隔离键 ──────────────────────────────────
    firm_id         VARCHAR(64)  NOT NULL,
    client_id       VARCHAR(64)  NOT NULL,
    engagement_id   VARCHAR(64)  NOT NULL,

    -- ── 来源追踪 ─────────────────────────────────────
    source_type     source_type_enum  NOT NULL,
    source_id       VARCHAR(256) NOT NULL,

    -- ── 内容（最大 8192 字符） ───────────────────────
    content         TEXT NOT NULL CHECK (char_length(content) <= 8192),

    -- ── 向量（维度由 EmbeddingProvider 配置决定；DDL 阶段不约束维度） ─
    embedding       vector NOT NULL,

    -- ── 扩展元数据 ───────────────────────────────────
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- ── 安全分级 ─────────────────────────────────────
    security_level  security_level_enum NOT NULL DEFAULT 'CONFIDENTIAL',

    -- ── 时间戳 ───────────────────────────────────────
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. HNSW 索引（pgvector 0.5.0+ 原生支持）
--    索引建立在 cosin similarity 的 vector_l2_ops 或 vector_cosine_ops 上。
--    m=16, ef_construction=200 是 pgvector 推荐的均衡参数。
CREATE INDEX idx_embedding_item_hnsw
    ON embedding_item
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- 5. 隔离键复合索引 —— 保证所有查询都走 firm_id + engagement_id 前缀
CREATE INDEX idx_embedding_item_isolation
    ON embedding_item (firm_id, engagement_id, source_type);

-- 6. 来源追踪索引 —— 支持按 source_type + source_id 快速定位与级联删除
CREATE INDEX idx_embedding_item_source
    ON embedding_item (source_type, source_id);

-- 7. 安全分级索引 —— 查询时快速过滤用户不可见的密级
CREATE INDEX idx_embedding_item_security
    ON embedding_item (security_level);

-- 8. 时间范围索引 —— 支持归档策略（例如仅保留最近 3 年的向量）
CREATE INDEX idx_embedding_item_created
    ON embedding_item (created_at DESC);

-- 9. 示例查询模板（供 VectorStore 实现参考）
--    必须形状：firm_id + engagement_id + cosine 相似度 + 可选 source_type 过滤
--
-- SELECT id, content, metadata, source_type, security_level,
--        1.0 - (embedding <=> $query_vector) AS similarity
-- FROM embedding_item
-- WHERE firm_id = $firm_id
--   AND engagement_id = $engagement_id
--   AND ($source_type_filter IS NULL OR source_type = ANY($source_type_filter))
--   AND security_level = ANY($allowed_levels)
-- ORDER BY embedding <=> $query_vector
-- LIMIT $top_k;
```

---

## 5. 迁移与演进路线

| 阶段 | 存储引擎 | 触发条件 |
|---|---|---|
| **当前 (v1.0)** | PostgreSQL + pgvector (HNSW) | 向量总量 < 500 万，延迟 < 10ms |
| **未来 (v1.5)** | PGVector 分区表（按 `firm_id` HASH 16 分区） | 向量总量 > 500 万，单表写入压力明显 |
| **未来 (v2.0)** | Milvus / Qdrant（实现 VectorStore 接口替代 PGVector） | 向量总量 > 5000 万，或需要多模态向量（图片、表格嵌入） |

从 PGVector 迁移到 Milvus 的路径已通过 `VectorStore` 抽象接口保障：上层模块不需要任何修改，仅需在 DI 容器中替换绑定即可，并在迁移期间维护一个双写适配器以确保零停机。

---

> **冻结声明：** 本文档所列 `EmbeddingItem` Schema、`VectorStore` 接口方法签名及 PGVector DDL 为 Architecture Baseline v1.0 的组成部分。任何修改必须通过 ADR 修订流程（提交新的 ADR 并标注 `supersedes: ADR-003`），并同步更新 `auditflow/docs/api/embedding-contract.md`。
