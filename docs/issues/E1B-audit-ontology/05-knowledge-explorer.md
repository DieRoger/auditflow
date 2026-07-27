# 1B.3.1 — Knowledge Explorer Page

- **Epic:** E1B — Audit Intelligence Model
- **Labels:** `knowledge`, `frontend`, `ui`
- **Depends on:** 1B.1.1 (Ontology Schema), 1B.2.2 (Knowledge Embedding)
- **Estimate:** —

## Description

构建 Knowledge Explorer 前端页面，提供审计知识库的可视化浏览体验。该页面是 E1B 面向用户的交付物，支持两个维度：**Ontology Explorer**（图结构浏览推理链）和 **Standards Browser**（按准则/条款检索原文）。

遵循 **Backend Capability First Rule**：E1B 完成时冻结 `Knowledge API v1`（`POST/GET /api/v1/knowledge/*`），前端基于已冻结 API 开发。

## Acceptance Criteria

- [ ] **Ontology Explorer 面板**：以树形或力导向图展示 `get_reasoning_chains()` 返回的推理链
  - 节点按 `node_type` 着色区分（AuditArea / Risk / Assertion / ProcedureType / EvidenceType / Standard）
  - 边显示 `edge_type` 标签和 `weight`
  - 点击节点展开详情（description、properties）
  - 支持按 AuditArea 切换（下拉选择：Revenue Recognition / AR / Inventory / Fixed Assets / AP）

- [ ] **Standards Browser 面板**：
  - 左侧标准目录树（ISA 315 → Part 4 → Identifying RMM → ¶27 层级展开）
  - 右侧条款原文渲染（Markdown / HTML）
  - 全文搜索：输入关键词 → 调用 Knowledge API 检索相关条款
  - 显示交叉引用：选中条款时高亮其引用/被引用的其他条款

- [ ] **Knowledge API v1** 已冻结并文档化：

```
POST /api/v1/knowledge/ontology/query
  → { audit_area: "Revenue Recognition" }
  ← { chains: [...] }

GET /api/v1/knowledge/standards/search?q=...&standard_id=...&top_k=10
  ← { results: [{ standard_id, paragraph, content, score }] }

GET /api/v1/knowledge/standards/{standard_id}?paragraph=...
  ← { content, cross_refs, hierarchy_path }

GET /api/v1/knowledge/cross-refs/{standard_id}/{paragraph}
  ← { outgoing: [...], incoming: [...] }
```

- [ ] 响应式布局：桌面端双栏（Explorer | Browser），移动端 Tab 切换
- [ ] 加载状态 / 空状态 / 错误状态三态覆盖

## I/O Interface

```typescript
// 前端消费的 Knowledge API 类型（基于冻结 API v1）
interface OntologyChainNode {
  node_id: string;
  node_type: "AuditArea" | "Risk" | "Assertion" | "ProcedureType" | "EvidenceType" | "Standard";
  label: string;
  description: string | null;
  properties: Record<string, unknown>;
  path_depth: number;
}

interface OntologyChainEdge {
  edge_type: "HAS_RISK" | "VIOLATES" | "ADDRESSED_BY" | "PRODUCES" | "SUPPORTS" | "REFERENCES";
  weight: number;
  source_node_id: string;
  target_node_id: string;
}

interface StandardSearchResult {
  standard_id: string;
  standard_name: string;
  paragraph: string;
  content: string;
  score: number;
  hierarchy_path: string;
  cross_refs: CrossReference[];
}
```

## Related ADR

- [ADR-002 — 审计本体模型](../architecture/ADR-002-Ontology-Model.md)（§3.3 `get_reasoning_chains` 函数定义了 Explorer 的数据源）
