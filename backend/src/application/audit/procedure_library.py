"""Procedure Library — 审计程序模板库

Revenue Cycle: Cutoff, Occurrence, Completeness
AR/AP/Inventory: 标准化程序模板
"""

from domain.audit.entities.procedure import (
    AuditAssertion, AuditProcedure, ProcedureType, SamplingConfig, SamplingMethod,
)


def revenue_occurrence_test() -> AuditProcedure:
    """收入发生测试 — 验证收入交易是否真实发生"""
    return AuditProcedure(
        name="Revenue Occurrence Test",
        procedure_type=ProcedureType.INSPECTION,
        assertions=[AuditAssertion.OCCURRENCE],
        objective="验证收入交易具有真实的商业实质，不存在虚构收入",
        description="选取销售收入样本，追踪至销售合同、发货单、客户签收单。"
                    "确认销售金额、日期、客户信息与原始凭证一致。",
        sampling=SamplingConfig(method=SamplingMethod.MUS, key_field="amount", sample_size=15),
    )


def revenue_completeness_test() -> AuditProcedure:
    """收入完整性测试 — 验证收入是否被完整记录"""
    return AuditProcedure(
        name="Revenue Completeness Test",
        procedure_type=ProcedureType.INSPECTION,
        assertions=[AuditAssertion.COMPLETENESS],
        objective="验证所有已发生的收入交易均已记录，不存在遗漏",
        description="从发货单出发，追踪至销售发票和总账记录。"
                    "检查发货单序列号连续性，确认所有已发货的交易均已确认收入。",
        sampling=SamplingConfig(method=SamplingMethod.RANDOM, sample_size=15),
    )


def ar_aging_analysis() -> AuditProcedure:
    """应收账款账龄分析"""
    return AuditProcedure(
        name="AR Aging Analysis",
        procedure_type=ProcedureType.ANALYTICAL,
        assertions=[AuditAssertion.VALUATION, AuditAssertion.EXISTENCE],
        objective="评估应收账款的可回收性，识别重大逾期款项",
        description="按客户和账龄分层分析应收账款。"
                    "对超过90天的应收账款评估信用损失。"
                    "结合客户信用等级和历史回收率评估减值准备的充分性。",
        sampling=SamplingConfig(method=SamplingMethod.ALL),
    )


def ap_existence_test() -> AuditProcedure:
    """应付账款存在性测试"""
    return AuditProcedure(
        name="AP Existence Test",
        procedure_type=ProcedureType.CONFIRMATION,
        assertions=[AuditAssertion.EXISTENCE, AuditAssertion.COMPLETENESS],
        objective="验证应付账款的真实性和完整性",
        description="选取应付账款样本，核对采购订单、入库单、供应商发票。"
                    "对主要供应商执行函证程序。检查期后付款记录以验证完整性。",
        sampling=SamplingConfig(method=SamplingMethod.MUS, key_field="amount", sample_size=10),
    )


def inventory_valuation_test() -> AuditProcedure:
    """存货计价测试"""
    return AuditProcedure(
        name="Inventory Valuation Test",
        procedure_type=ProcedureType.RECALCULATION,
        assertions=[AuditAssertion.VALUATION],
        objective="验证存货按成本与可变现净值孰低计量",
        description="获取期末存货清单，选取样本检查存货单位成本。"
                    "对比最近采购价格和售价，评估是否存在减值迹象。"
                    "对库龄超过12个月的存货单独评估。",
        sampling=SamplingConfig(method=SamplingMethod.STRATIFIED, sample_size=20),
    )


def cash_bank_reconciliation() -> AuditProcedure:
    """银行存款余额调节"""
    return AuditProcedure(
        name="Cash Bank Reconciliation",
        procedure_type=ProcedureType.RECALCULATION,
        assertions=[AuditAssertion.EXISTENCE, AuditAssertion.ACCURACY],
        objective="验证银行存款余额的存在性和准确性",
        description="获取所有银行账户的对账单，编制银行存款余额调节表。"
                    "检查未达账项的性质和期间，确认大额未达账项已在期后结算。",
        sampling=SamplingConfig(method=SamplingMethod.ALL),
    )


PROCEDURE_LIBRARY = {
    "revenue_cutoff": "application.audit.sampling.generate_cutoff_program",
    "revenue_occurrence": revenue_occurrence_test,
    "revenue_completeness": revenue_completeness_test,
    "ar_aging": ar_aging_analysis,
    "ap_existence": ap_existence_test,
    "inventory_valuation": inventory_valuation_test,
    "cash_reconciliation": cash_bank_reconciliation,
}
