"""Planning Engine — 审计计划确定性计算 Service

非 Agent，无自主决策循环。纯确定性公式计算。
"""

import math

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ── 数据模型 ─────────────────────────────────────────────────

class FinancialInput(BaseModel):
    total_assets: float = 0.0
    total_revenue: float = 0.0
    profit_before_tax: float = 0.0

    def is_valid(self) -> bool:
        return self.total_assets > 0 or self.total_revenue > 0 or self.profit_before_tax > 0


class MaterialityResult(BaseModel):
    overall: float = 0.0
    performance: float = 0.0
    clearly_trivial: float = 0.0
    basis: str = ""
    basis_amount: float = 0.0
    percentage: float = 0.0


class SamplingResult(BaseModel):
    population_value: float = 0.0
    sample_size: int = 0
    sampling_interval: float = 0.0
    method: str = "MUS"  # MUS | Stratified | Random


class PlanningOutput(BaseModel):
    materiality: MaterialityResult
    sampling: SamplingResult | None = None
    procedures: list[dict] = Field(default_factory=list)
    timeline: dict = Field(default_factory=dict)


# ── Planning Engine ────────────────────────────────────────────

class PlanningEngine:
    """审计计划引擎 — 确定性计算

    依据 ISA 320（重要性）和 ISA 530（抽样）指南。
    """

    # ISA 320 推荐百分比
    MATERIALITY_PCT = {
        "total_assets": 0.01,    # 1%
        "total_revenue": 0.005,  # 0.5%
        "profit_before_tax": 0.05,  # 5%
    }
    PERFORMANCE_FACTOR = 0.75   # 实际执行 = 整体 × 75%
    TRIVIAL_FACTOR = 0.05       # 明显微小 = 整体 × 5%

    async def calculate_materiality(self, financials: FinancialInput) -> MaterialityResult:
        """计算重要性水平（ISA 320）"""
        if not financials.is_valid():
            raise ValueError("至少需要提供总资产、总收入或税前利润之一")

        # 选择基准（取绝对值最大的）
        candidates = []
        if financials.total_assets > 0:
            candidates.append(("Total Assets", financials.total_assets, self.MATERIALITY_PCT["total_assets"]))
        if financials.total_revenue > 0:
            candidates.append(("Revenue", financials.total_revenue, self.MATERIALITY_PCT["total_revenue"]))
        if financials.profit_before_tax > 0:
            candidates.append(("Profit Before Tax", financials.profit_before_tax, self.MATERIALITY_PCT["profit_before_tax"]))  # noqa: E501

        basis_name, basis_amount, pct = max(candidates, key=lambda c: abs(c[1]))
        overall = round(basis_amount * pct, 2)
        performance = round(overall * self.PERFORMANCE_FACTOR, 2)
        trivial = round(overall * self.TRIVIAL_FACTOR, 2)

        logger.info("materiality_calculated", basis=basis_name, overall=overall, performance=performance)
        return MaterialityResult(
            overall=overall, performance=performance, clearly_trivial=trivial,
            basis=basis_name, basis_amount=basis_amount, percentage=pct,
        )

    async def calculate_sampling(
        self, population_value: float, materiality: float,
        expected_error_rate: float = 0.05, confidence_level: float = 0.95,
    ) -> SamplingResult:
        """计算抽样参数（MUS 方法，ISA 530）"""
        if population_value <= 0 or materiality <= 0:
            raise ValueError("总体金额和重要性水平必须大于0")

        # MUS: 样本量 = (总体金额 × 置信因子) / (可容忍误差 - 预期误差)
        confidence_factor = {0.95: 3.0, 0.90: 2.31, 0.99: 4.61}.get(confidence_level, 3.0)
        tolerable_error = materiality
        expected_error = population_value * expected_error_rate
        denominator = max(tolerable_error - expected_error, materiality * 0.1)  # 至少保留 10% MOE

        sample_size = max(1, math.ceil(
            (population_value * confidence_factor) / denominator
        ))
        sampling_interval = round(population_value / sample_size, 2) if sample_size > 0 else 0

        logger.info("sampling_calculated", population=population_value, sample=sample_size, interval=sampling_interval)
        return SamplingResult(
            population_value=population_value, sample_size=sample_size,
            sampling_interval=sampling_interval, method="MUS",
        )

    async def generate_plan(self, financials: FinancialInput, risks: list[dict] | None = None) -> PlanningOutput:  # noqa: ARG002
        """生成完整审计计划"""
        materiality = await self.calculate_materiality(financials)
        sampling = await self.calculate_sampling(
            population_value=max(financials.total_assets, financials.total_revenue, 1_000_000),
            materiality=materiality.performance,
        )
        return PlanningOutput(materiality=materiality, sampling=sampling)
