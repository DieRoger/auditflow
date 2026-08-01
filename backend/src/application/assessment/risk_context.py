"""RiskContext Builder — Transaction → FinancialRiskIndicators → Risk Agent input

Phase 2a: ISA 520 Analytical Procedures pipeline.
Computes ratios, trends, and significant accounts from transaction data,
feeds them into Risk Agent as structured context instead of raw numbers.
"""

from domain.finance.services.analytics import (
    RatioEngine, TrendEngine, AccountAnalyzer, FinancialRiskIndicators,
)


def build_financials_from_transactions(transactions: list) -> dict:
    """从 Transaction 列表提取财务报表科目金额"""
    revenue = sum(float(t.amount) for t in transactions if getattr(t, 'transaction_type', None) is None
                  or str(getattr(t, 'transaction_type', '')).upper() in ('SALES', 'SALES', ''))
    if not revenue:
        revenue = sum(float(t.amount) for t in transactions)

    # Simplified financials from transaction aggregations
    return {
        "revenue": revenue,
        "net_income": revenue * 0.12,       # 假设净利率 12%
        "cogs": revenue * 0.65,             # 假设成本率 65%
        "gross_profit": revenue * 0.35,
        "current_assets": revenue * 0.8,
        "current_liabilities": revenue * 0.5,
        "inventory": revenue * 0.2,
        "receivables": revenue * 0.3,
        "total_assets": revenue * 2.5,
        "total_liabilities": revenue * 1.5,
    }


def build_risk_context(
    current_period: list,
    prior_period: list | None = None,
    account_data: dict | None = None,
) -> FinancialRiskIndicators:
    """构建 Risk Agent 的结构化输入

    Args:
        current_period: 本期 Transaction 列表
        prior_period: 上期 Transaction 列表（用于趋势分析）
        account_data: 科目余额（用于重大账户识别）
    """
    current_fin = build_financials_from_transactions(current_period)

    # Ratio analysis
    ratio_engine = RatioEngine()
    ratios = ratio_engine.analyze(current_fin)

    # Trend analysis (if prior period available)
    trends = []
    anomalies = []
    if prior_period:
        prior_fin = build_financials_from_transactions(prior_period)
        trend_engine = TrendEngine()
        trends = trend_engine.analyze(current_fin, prior_fin)
        anomalies = trend_engine.anomaly_trends(trends)

    # Significant accounts
    if not account_data:
        account_data = {
            "Revenue": current_fin["revenue"],
            "COGS": current_fin["cogs"],
            "Receivables": current_fin["receivables"],
            "Inventory": current_fin["inventory"],
            "Current Assets": current_fin["current_assets"],
            "Current Liabilities": current_fin["current_liabilities"],
        }
    analyzer = AccountAnalyzer()
    sig_accounts = analyzer.identify_significant(account_data)

    return FinancialRiskIndicators(
        ratios=ratios,
        trends=trends,
        anomalies=anomalies,
        significant_accounts=sig_accounts,
    )
