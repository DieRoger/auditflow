"""Sampling Engine — MUS/随机/分层抽样

Phase B: 从 Canonical Transaction 数据中抽取样本
"""

import random
from datetime import date
from decimal import Decimal
from typing import Optional

from domain.audit.entities.procedure import AuditProcedure, SamplingConfig, SamplingMethod
from domain.finance.entities.transaction import Transaction


class SamplingEngine:
    """审计抽样引擎"""

    def sample(
        self,
        population: list[Transaction],
        config: SamplingConfig,
    ) -> list[Transaction]:
        """根据抽样配置从总体中抽取样本"""
        if config.method == SamplingMethod.ALL:
            return population
        elif config.method == SamplingMethod.RANDOM:
            return self._random_sample(population, config.sample_size)
        elif config.method == SamplingMethod.MUS:
            return self._mus_sample(population, config.sample_size)
        else:
            return self._random_sample(population, config.sample_size)

    def _random_sample(self, population: list, size: int) -> list:
        """随机抽样"""
        if size >= len(population):
            return population
        rng = random.Random(42)  # 固定种子保证可复现
        return rng.sample(population, size)

    def _mus_sample(self, population: list[Transaction], size: int) -> list[Transaction]:
        """货币单位抽样 — 金额越大被选中的概率越高"""
        if size >= len(population):
            return population

        # 计算累计金额
        total = sum((txn.amount for txn in population), Decimal("0"))
        if total == 0:
            return self._random_sample(population, size)

        # 按金额排序
        sorted_pop = sorted(population, key=lambda t: t.amount, reverse=True)

        # 选 top N 大金额 + 剩余随机
        top_n = min(size // 2 + 1, len(population) // 4)
        selected = list(sorted_pop[:top_n])
        remaining = sorted_pop[top_n:]
        if len(selected) < size and remaining:
            rng = random.Random(42)
            selected += rng.sample(remaining, min(size - len(selected), len(remaining)))
        return selected


class CutoffProcedureExecutor:
    """Revenue Cutoff 测试执行器"""

    def execute(
        self,
        procedure: AuditProcedure,
        transactions: list[Transaction],
        records_raw: list[dict],
        cutoff_date,
    ) -> list:
        """执行截止测试，返回 Finding 列表"""
        from domain.audit.entities.procedure import AuditFinding, FindingSeverity

        sampling = procedure.sampling
        engine = SamplingEngine()

        # 抽样
        if sampling and sampling.method != SamplingMethod.ALL:
            sample = engine.sample(transactions, sampling)
        else:
            sample = transactions

        findings = []

        for rec in records_raw:
            txn_id = rec.get("canonical_refs", {}).get("id", "")
            if not txn_id:
                continue

            ship_date = rec.get("_ship_date")
            txn_date = rec.get("_txn_date")

            if not ship_date or not txn_date:
                continue

            # 统一为 date 类型（兼容字符串输入）
            if isinstance(ship_date, str):
                ship_date = date.fromisoformat(ship_date[:10])
            if isinstance(txn_date, str):
                txn_date = date.fromisoformat(txn_date[:10])

            if ship_date > cutoff_date and txn_date <= cutoff_date:
                findings.append(AuditFinding(
                    procedure_id=procedure.procedure_id,
                    description=f"Revenue recognized {txn_date} but shipped {ship_date}",
                    severity=FindingSeverity.HIGH,
                    transaction_ref=txn_id,
                    amount=rec.get("_amount"),
                ))

        procedure.findings = findings
        procedure.status = "COMPLETE"
        return findings


def generate_cutoff_program() -> "AuditProgram":
    """生成 Revenue Cutoff 标准审计程序"""
    from domain.audit.entities.procedure import (
        AuditAssertion, AuditProgram, AuditProcedure, ProcedureType, SamplingConfig, SamplingMethod,
    )

    procedure = AuditProcedure(
        name="Revenue Cutoff Test",
        procedure_type=ProcedureType.CUTOFF_TEST,
        assertions=[AuditAssertion.CUTOFF, AuditAssertion.OCCURRENCE],
        objective="验证收入是否记录在正确的会计期间，识别截止性错报",
        description="检查资产负债日前后销售交易的发货日期，确认收入确认期间正确。"
                    "对发货日期晚于报告期末的交易应调整至下一期间。",
        sampling=SamplingConfig(
            method=SamplingMethod.ALL,
            population_size=0,
            sample_size=0,
            key_field="transaction_date",
        ),
    )

    program = AuditProgram(
        area="Revenue",
        risk_level="HIGH",
        procedures=[procedure],
    )
    return program
