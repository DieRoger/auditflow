"""Audit Domain — Procedure, Program, Assertion, Finding

Phase B: Audit Procedure Engine 核心领域模型
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class AuditAssertion(Enum):
    """审计认定类型"""
    OCCURRENCE = "OCCURRENCE"           # 发生
    COMPLETENESS = "COMPLETENESS"       # 完整性
    ACCURACY = "ACCURACY"               # 准确性
    CUTOFF = "CUTOFF"                   # 截止
    CLASSIFICATION = "CLASSIFICATION"   # 分类
    EXISTENCE = "EXISTENCE"             # 存在
    RIGHTS = "RIGHTS"                   # 权利义务
    VALUATION = "VALUATION"             # 计价


class ProcedureType(Enum):
    """审计程序类型"""
    INSPECTION = "INSPECTION"           # 检查
    OBSERVATION = "OBSERVATION"         # 观察
    INQUIRY = "INQUIRY"                 # 询问
    CONFIRMATION = "CONFIRMATION"       # 函证
    RECALCULATION = "RECALCULATION"     # 重新计算
    REPERFORMANCE = "REPERFORMANCE"     # 重新执行
    ANALYTICAL = "ANALYTICAL"           # 分析程序
    CUTOFF_TEST = "CUTOFF_TEST"         # 截止测试


class SamplingMethod(Enum):
    """抽样方法"""
    RANDOM = "RANDOM"                   # 随机抽样
    MUS = "MUS"                         # 货币单位抽样
    STRATIFIED = "STRATIFIED"           # 分层抽样
    HAPHAZARD = "HAPHAZARD"             # 随意抽样
    ALL = "ALL"                         # 全部检查


class FindingSeverity(Enum):
    """审计发现严重程度"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class AuditProgram:
    """审计程序集合 — 针对特定审计领域"""
    program_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    area: str = ""                      # Revenue, Inventory, Cash, etc.
    risk_level: str = "MEDIUM"          # 领域风险等级
    procedures: list["AuditProcedure"] = field(default_factory=list)

    def summary(self) -> dict:
        total = len(self.procedures)
        completed = sum(1 for p in self.procedures if p.status == "COMPLETE")
        findings = sum(len(p.findings) for p in self.procedures)
        return {"program_id": self.program_id, "area": self.area,
                "procedures_total": total, "procedures_complete": completed,
                "findings": findings}


@dataclass
class AuditProcedure:
    """单个审计程序 — 一个 Action"""
    procedure_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""                      # "Revenue Cutoff Test"
    procedure_type: ProcedureType = ProcedureType.CUTOFF_TEST
    assertions: list[AuditAssertion] = field(default_factory=list)  # [CUTOFF, OCCURRENCE]
    objective: str = ""                 # "验证收入是否记录在正确的会计期间"
    description: str = ""               # 详细描述
    sampling: Optional["SamplingConfig"] = None
    status: str = "PENDING"             # PENDING → RUNNING → COMPLETE
    findings: list["AuditFinding"] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)  # Document IDs


@dataclass
class SamplingConfig:
    """抽样配置"""
    method: SamplingMethod = SamplingMethod.RANDOM
    population_size: int = 0
    sample_size: int = 0
    key_field: str = ""                 # 抽样依据字段
    confidence: float = 0.95            # 置信水平
    tolerable_error: Decimal = Decimal("0")  # 可容忍误差


@dataclass
class AuditFinding:
    """审计发现"""
    finding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    procedure_id: str = ""
    description: str = ""
    severity: FindingSeverity = FindingSeverity.MEDIUM
    transaction_ref: Optional[str] = None
    amount: Optional[Decimal] = None
    evidence_refs: list[str] = field(default_factory=list)
