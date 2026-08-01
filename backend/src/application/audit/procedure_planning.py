"""ProcedurePlanningService — Assessment → AuditProgram

Application Service。消费 Assessment，根据 overall_risk + detected_findings
选择并实例化审计程序，配置抽样策略。

不执行程序（由 CutoffProcedureExecutor 执行）。
"""

from application.assessment.assessment import Assessment
from domain.audit.entities.procedure import (
    AuditAssertion, AuditProgram, AuditProcedure,
    ProcedureType, SamplingConfig, SamplingMethod,
)

# 程序模板索引 — 按 assertion 映射到标准程序
PROCEDURE_TEMPLATES: dict[str, dict] = {
    "CUTOFF": {
        "name": "Revenue Cutoff Test",
        "proc_type": ProcedureType.CUTOFF_TEST,
        "assertions": [AuditAssertion.CUTOFF, AuditAssertion.OCCURRENCE],
        "objective": "验证收入是否记录在正确的会计期间",
        "description": "检查资产负债日前后销售交易的发货日期，确认收入确认期间正确。",
    },
    "OCCURRENCE": {
        "name": "Revenue Occurrence Test",
        "proc_type": ProcedureType.INSPECTION,
        "assertions": [AuditAssertion.OCCURRENCE],
        "objective": "验证记录的收入交易是否真实发生",
        "description": "通过检查销售合同、出库单、发票，确认收入交易真实发生。",
    },
    "COMPLETENESS": {
        "name": "Revenue Completeness Test",
        "proc_type": ProcedureType.INSPECTION,
        "assertions": [AuditAssertion.COMPLETENESS],
        "objective": "验证所有已发生的收入交易是否均已记录",
        "description": "从发货记录追踪至销售明细，验证收入的完整性。",
    },
}


class ProcedurePlanningService:
    """审计程序规划服务 — Assessment 驱动的程序选择"""

    def build_program(self, assessment: Assessment, area: str = "Revenue") -> AuditProgram:
        """根据 Assessment 构建 AuditProgram"""
        assertions_needed = self._collect_assertions(assessment)
        procedures = []

        for assertion in assertions_needed:
            template = PROCEDURE_TEMPLATES.get(assertion)
            if template is None:
                continue
            sampling = self._sampling_for(assessment)
            proc = AuditProcedure(
                name=template["name"],
                procedure_type=template["proc_type"],
                assertions=template["assertions"],
                objective=template["objective"],
                description=template["description"],
                sampling=sampling,
            )
            procedures.append(proc)

        return AuditProgram(
            area=area,
            risk_level=assessment.overall_risk,
            procedures=procedures,
        )

    @staticmethod
    def _collect_assertions(assessment: Assessment) -> list[str]:
        """从 Assessment 的 findings 中收集需要的 assertions，去重"""
        assertions = set()
        for f in assessment.detected_findings:
            for a in f.get("affected_assertions", []):
                assertions.add(a)
        # 至少包含 OCCURRENCE 作为基线
        if not assertions:
            assertions.add("OCCURRENCE")
        return sorted(assertions)

    @staticmethod
    def _sampling_for(assessment: Assessment) -> SamplingConfig:
        """根据风险等级决定抽样策略"""
        finding_count = len(assessment.detected_findings)

        if assessment.overall_risk == "HIGH" or finding_count >= 10:
            return SamplingConfig(
                method=SamplingMethod.ALL,
                population_size=0,  # 外部设定
                sample_size=0,
                key_field="transaction_date",
            )
        elif assessment.overall_risk == "MEDIUM":
            return SamplingConfig(
                method=SamplingMethod.MUS,
                population_size=0,
                sample_size=25,
                key_field="amount",
            )
        else:
            return SamplingConfig(
                method=SamplingMethod.RANDOM,
                population_size=0,
                sample_size=10,
                key_field="transaction_date",
            )
