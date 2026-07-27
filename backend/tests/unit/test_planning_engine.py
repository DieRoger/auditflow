"""Planning Engine 测试"""

import pytest

from services.planning_engine import FinancialInput, PlanningEngine


@pytest.mark.asyncio
async def test_materiality_total_assets():
    engine = PlanningEngine()
    result = await engine.calculate_materiality(FinancialInput(total_assets=500_000_000))
    assert result.overall == 5_000_000.0  # 1% of 500M
    assert result.basis == "Total Assets"
    assert result.performance == 3_750_000.0  # 75% of overall
    assert result.clearly_trivial == 250_000.0  # 5% of overall


@pytest.mark.asyncio
async def test_materiality_revenue():
    engine = PlanningEngine()
    result = await engine.calculate_materiality(FinancialInput(total_assets=1_000_000_000, total_revenue=200_000_000))
    # Total Assets (1B * 1% = 10M) > Revenue (200M * 0.5% = 1M) → use Total Assets
    assert result.basis == "Total Assets"
    assert result.overall == 10_000_000.0


@pytest.mark.asyncio
async def test_materiality_invalid():
    engine = PlanningEngine()
    with pytest.raises(ValueError):
        await engine.calculate_materiality(FinancialInput())


@pytest.mark.asyncio
async def test_sampling():
    engine = PlanningEngine()
    result = await engine.calculate_sampling(population_value=10_000_000, materiality=500_000)
    assert result.sample_size > 0
    assert result.sampling_interval > 0
    assert result.method == "MUS"


@pytest.mark.asyncio
async def test_generate_plan():
    engine = PlanningEngine()
    plan = await engine.generate_plan(FinancialInput(total_assets=500_000_000))
    assert plan.materiality.overall == 5_000_000.0
    assert plan.sampling is not None
    assert plan.sampling.sample_size > 0
