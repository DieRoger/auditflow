"""AssessmentPolicy — 8 条显式规则决定 overall_risk

原则: Evidence dominates narrative.
- Rule-based Finding 的权重 > LLM Risk Agent 的叙述性推断
- 所有规则可审计、可解释、无黑盒

规则设计来自 Grill Session Round 4 + Code Review 补充。

⚠️  FROZEN: Maximum 10 rules. If exceeding 10, split into independent Policy classes
    (e.g. RevenueAssessmentPolicy, PurchaseAssessmentPolicy).
"""


class AssessmentPolicy:
    """证据优先的风险融合策略"""

    @staticmethod
    def determine(
        narrative_risk: dict,
        detected_findings: list[dict],
        materiality: float | None = None,
    ) -> str:
        """返回 overall_risk: HIGH / MEDIUM / LOW"""
        narrative_severity = narrative_risk.get("severity", "LOW")
        finding_severities = [f.get("severity", "LOW") for f in detected_findings]
        finding_confidences = [f.get("confidence", 0.0) for f in detected_findings]
        finding_count = len(detected_findings)

        has_high_finding = "HIGH" in finding_severities
        has_medium_finding = "MEDIUM" in finding_severities
        narrative_is_high = narrative_severity in ("HIGH", "CRITICAL")

        # Rule 7: 所有 Finding 的 confidence 都很低 (< 0.3) → 不按证据升级
        if finding_count > 0 and all(c < 0.3 for c in finding_confidences):
            if narrative_is_high:
                return "MEDIUM"
            return "LOW"

        # Rule 8: Materiality Override — Finding 总金额 < 重要性水平 → 降级
        # （在 Rule 1 之前执行，insignificant findings 不升级）
        if materiality is not None and has_high_finding:
            finding_amount = sum(
                f.get("amount", 0.0) for f in detected_findings
                if isinstance(f.get("amount"), (int, float))
            )
            # 只有当所有 HIGH findings 的金额都 < materiality 时才降级
            if finding_amount > 0 and finding_amount < materiality:
                return "LOW"

        # Rule 1: 有 HIGH Finding → overall >= HIGH
        if has_high_finding:
            return "HIGH"

        # Rule 2: Finding 数量 >= 10 → 至少 MEDIUM
        if finding_count >= 10:
            return "MEDIUM"

        # Rule 3: 只有 Narrative HIGH，没有 Finding → MEDIUM
        if narrative_is_high and finding_count == 0:
            return "MEDIUM"

        # Rule 5: 多个 MEDIUM Finding → HIGH
        medium_count = finding_severities.count("MEDIUM")
        if medium_count >= 3:
            return "HIGH"

        # Rule 6: 如果没有任何触发，保持 Narrative severity
        if narrative_is_high:
            return "HIGH"
        if has_medium_finding:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def policy_decisions(
        narrative_risk: dict,
        detected_findings: list[dict],
        materiality: float | None = None,
    ) -> list[str]:
        """返回触发了哪些规则（用于审计追踪）"""
        decisions = []
        finding_severities = [f.get("severity", "LOW") for f in detected_findings]
        finding_confidences = [f.get("confidence", 0.0) for f in detected_findings]
        finding_count = len(detected_findings)
        narrative_severity = narrative_risk.get("severity", "LOW")

        has_high = "HIGH" in finding_severities

        # Rule 7 check
        if finding_count > 0 and all(c < 0.3 for c in finding_confidences):
            decisions.append(
                "Rule 7: All findings low confidence (< 0.3) → capped to MEDIUM/LOW"
            )
        if has_high:
            decisions.append("Rule 1: Any HIGH finding → overall HIGH")

        # Rule 8 check
        if materiality is not None:
            finding_amount = sum(
                f.get("amount", 0.0) for f in detected_findings
                if isinstance(f.get("amount"), (int, float))
            )
            if finding_amount > 0 and finding_amount < materiality:
                decisions.append(
                    f"Rule 8: Finding amount {finding_amount:,.0f} < Materiality "
                    f"{materiality:,.0f} → downgrade to LOW"
                )

        if finding_count >= 10:
            decisions.append(
                f"Rule 2: Finding count {finding_count} >= 10 → at least MEDIUM"
            )
        if narrative_severity in ("HIGH", "CRITICAL") and finding_count == 0:
            decisions.append("Rule 3: Narrative HIGH only → downgrade to MEDIUM")
        if narrative_severity == "LOW" and has_high:
            decisions.append("Rule 4: Finding HIGH overrides Narrative LOW")
        medium_count = finding_severities.count("MEDIUM")
        if medium_count >= 3:
            decisions.append(
                f"Rule 5: {medium_count} MEDIUM findings → escalate to HIGH"
            )
        if finding_count == 0 and narrative_severity == "LOW":
            decisions.append("Rule 6: No triggers → LOW")

        return decisions
