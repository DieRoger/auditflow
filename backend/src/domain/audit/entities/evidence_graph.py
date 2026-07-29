"""Evidence Graph Domain — Assertion → Evidence → 充分性判定

Phase C: 每个审计认定必须有对应的证据链。
LLM 负责找证据，Graph 负责判断充分性。
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class EvidenceStatus(Enum):
    """单项证据状态"""
    PRESENT = "PRESENT"         # ✓ 存在
    MISSING = "MISSING"         # ✗ 缺失
    INSUFFICIENT = "INSUFFICIENT"  # ⚠ 存在但不充分


class AssertionConclusion(Enum):
    """认定结论"""
    SATISFIED = "SATISFIED"                 # 充分
    PARTIALLY_SATISFIED = "PARTIALLY"       # 部分充分
    NOT_SATISFIED = "NOT_SATISFIED"         # 不充分


@dataclass
class EvidenceNode:
    """证据节点 — 一个具体的证据项"""
    evidence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    evidence_type: str = ""          # INVOICE | DELIVERY | CONTRACT | BANK_STATEMENT
    document_no: str = ""            # 文档编号
    description: str = ""            # 简要描述
    status: EvidenceStatus = EvidenceStatus.PRESENT
    source_ref: Optional[str] = None  # 关联的 Document.document_id
    detail: str = ""                  # 补充说明


@dataclass
class AssertionNode:
    """认定节点 — 需要被证明的审计认定"""
    assertion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    assertion_type: str = "OCCURRENCE"  # from AuditAssertion enum
    description: str = ""               # e.g. "收入交易确实发生"
    required_evidence_types: list[str] = field(default_factory=list)  # [INVOICE, DELIVERY]
    evidence_nodes: list[EvidenceNode] = field(default_factory=list)

    def conclusion(self) -> AssertionConclusion:
        """根据证据状态判定结论"""
        if not self.required_evidence_types:
            return AssertionConclusion.SATISFIED

        present = sum(1 for e in self.evidence_nodes
                      if e.status == EvidenceStatus.PRESENT
                      and e.evidence_type in self.required_evidence_types)
        total = len(self.required_evidence_types)

        if present == total:
            return AssertionConclusion.SATISFIED
        elif present > 0:
            return AssertionConclusion.PARTIALLY_SATISFIED
        return AssertionConclusion.NOT_SATISFIED

    def coverage(self) -> float:
        """证据覆盖率 — 按类型计算"""
        if not self.required_evidence_types:
            return 1.0
        present_types = set()
        for e in self.evidence_nodes:
            if e.status == EvidenceStatus.PRESENT and e.evidence_type in self.required_evidence_types:
                present_types.add(e.evidence_type)
        return min(len(present_types) / len(self.required_evidence_types), 1.0)

    def missing_types(self) -> list[str]:
        """缺失的证据类型"""
        present_types = {e.evidence_type for e in self.evidence_nodes
                         if e.status == EvidenceStatus.PRESENT}
        return [t for t in self.required_evidence_types if t not in present_types]


@dataclass
class EvidenceGraph:
    """证据图 — 一次审计程序的完整证据链"""
    graph_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    procedure_id: str = ""
    assertions: list[AssertionNode] = field(default_factory=list)

    def overall_conclusion(self) -> AssertionConclusion:
        """整体充分性结论 — 所有认定中最低的那个"""
        if not self.assertions:
            return AssertionConclusion.NOT_SATISFIED
        conclusions = [a.conclusion() for a in self.assertions]
        if AssertionConclusion.NOT_SATISFIED in conclusions:
            return AssertionConclusion.NOT_SATISFIED
        if AssertionConclusion.PARTIALLY_SATISFIED in conclusions:
            return AssertionConclusion.PARTIALLY_SATISFIED
        return AssertionConclusion.SATISFIED

    def overall_coverage(self) -> float:
        """整体证据覆盖率 — 所有认定的平均覆盖率"""
        if not self.assertions:
            return 0.0
        return sum(a.coverage() for a in self.assertions) / len(self.assertions)

    def total_evidence_nodes(self) -> int:
        """证据节点总数"""
        return sum(len(a.evidence_nodes) for a in self.assertions)

    def missing_evidence_summary(self) -> list[dict]:
        """汇总所有缺失的证据"""
        missing = []
        for a in self.assertions:
            for mt in a.missing_types():
                missing.append({
                    "assertion": a.assertion_type,
                    "missing_type": mt,
                    "required": a.required_evidence_types,
                })
        return missing

    def is_sufficient(self, threshold: float = 0.75) -> bool:
        """证据是否充分（覆盖率 >= 阈值）"""
        return self.overall_coverage() >= threshold

    def summary(self) -> dict:
        """生成摘要"""
        return {
            "graph_id": self.graph_id,
            "procedure_id": self.procedure_id,
            "assertions": [
                {
                    "type": a.assertion_type,
                    "conclusion": a.conclusion().value,
                    "coverage": f"{a.coverage():.0%}",
                    "present": sum(1 for e in a.evidence_nodes if e.status == EvidenceStatus.PRESENT),
                    "missing": a.missing_types(),
                    "required": a.required_evidence_types,
                }
                for a in self.assertions
            ],
            "overall": self.overall_conclusion().value,
            "overall_coverage": f"{self.overall_coverage():.0%}",
            "total_evidence": self.total_evidence_nodes(),
            "sufficient": self.is_sufficient(),
            "missing_evidence": self.missing_evidence_summary(),
        }


class EvidenceMapper:
    """证据映射器 — 从审计程序结果构建 EvidenceGraph"""

    REQUIRED_EVIDENCE = {
        "CUTOFF": ["INVOICE", "DELIVERY"],       # 截止 → 发票 + 发货单
        "OCCURRENCE": ["INVOICE", "CONTRACT", "DELIVERY"],  # 发生 → 发票 + 合同 + 发货单
        "COMPLETENESS": ["INVOICE", "SHIPPING"],   # 完整性 → 发票 + 发货记录
        "ACCURACY": ["INVOICE", "RECALCULATION"],  # 准确性 → 发票 + 重算
        "EXISTENCE": ["CONTRACT", "BANK_STATEMENT"],  # 存在 → 合同 + 银行对账单
        "VALUATION": ["INVOICE", "MARKET_DATA"],    # 计价 → 发票 + 市场数据
    }

    def build_graph(self, procedure, transactions: list, findings: list,
                    documents_by_id: dict) -> EvidenceGraph:
        """从审计程序结果构建证据图"""
        from domain.audit.entities.procedure import FindingSeverity

        graph = EvidenceGraph(procedure_id=procedure.procedure_id)
        assertion_types = [a.value for a in procedure.assertions]

        for assertion_type in assertion_types:
            required = self.REQUIRED_EVIDENCE.get(assertion_type, ["DOCUMENT"])
            assertion = AssertionNode(
                assertion_type=assertion_type,
                required_evidence_types=required,
            )

            # 为每条异常 Finding 创建证据节点
            for finding in findings:
                txn_id = finding.transaction_ref
                evidence_status = EvidenceStatus.PRESENT  # 默认，检查缺失类型

                # 根据 Procedure type 判断证据状态
                for ev_type in required:
                    found = any(
                        d.document_type.value == ev_type and d.party_id == finding.transaction_ref
                        for d in documents_by_id.values()
                    ) if False else None  # 简化：Document 未关联到 Finding

                    # 检查文档是否在 transactions 的 doc_refs 中
                    txn = next((t for t in transactions if t.transaction_id == txn_id), None)
                    has_doc = False
                    if txn and txn.document_refs:
                        has_doc = any(
                            documents_by_id.get(dref) and
                            documents_by_id[dref].document_type.value == ev_type
                            for dref in txn.document_refs
                        )

                    if not has_doc and ev_type in required:
                        # 缺失此类型证据
                        assertion.evidence_nodes.append(EvidenceNode(
                            evidence_type=ev_type,
                            document_no=f"MISSING-{ev_type}",
                            description=f"Missing {ev_type} for transaction {txn_id[:12]}",
                            status=EvidenceStatus.MISSING,
                        ))
                    elif has_doc:
                        assertion.evidence_nodes.append(EvidenceNode(
                            evidence_type=ev_type,
                            document_no=f"DOC-{ev_type}-{txn_id[:8]}",
                            description=f"{ev_type} for transaction {txn_id[:12]}",
                            status=EvidenceStatus.PRESENT,
                        ))

            # 对于没有异常的Finding，添加PRESENT证据
            if not findings:
                for ev_type in required:
                    assertion.evidence_nodes.append(EvidenceNode(
                        evidence_type=ev_type,
                        document_no=f"ALL-{ev_type}",
                        description=f"{ev_type}: no exceptions found",
                        status=EvidenceStatus.PRESENT,
                    ))

            graph.assertions.append(assertion)

        return graph
