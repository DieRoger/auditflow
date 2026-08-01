"""DetectionFacade — 统一异常检测入口

Application Service。为 AnomalyDetectionAgent 提供单一调用接口，
内部委托给 Domain 层的 RiskScoringEngine。

未来扩展点:
  - Benford's Law
  - Isolation Forest
  - LOF (Local Outlier Factor)
  - Graph-based detection

所有新算法通过 register_detector() 接入，Facade.scan() 自动合并结果。
"""


class DetectionFacade:
    """多引擎检测门面 — 当前只包裹 RiskScoringEngine"""

    def __init__(self):
        self._detectors: list = []
        self._register_defaults()

    def _register_defaults(self):
        """注册默认检测器 — 当前仅 RiskScoringEngine"""
        self._detectors.append(_RiskScoringAdapter())

    def register_detector(self, detector):
        """注册新的检测器（Benford、IsolationForest 等）"""
        self._detectors.append(detector)

    def scan(self, rows: list[dict]) -> list[dict]:
        """对多行数据执行所有已注册检测器，合并 + 去重 + 降噪

        Returns:
            list[dict]: FindingItem-compatible dict 列表
        """
        all_findings: list[dict] = []
        for detector in self._detectors:
            findings = detector.detect(rows)
            all_findings.extend(findings)
        return self._merge(all_findings)

    @staticmethod
    def _merge(findings: list[dict]) -> list[dict]:
        """合并多个检测器的结果，按 risk_type 去重"""
        by_type: dict[str, dict] = {}
        for f in findings:
            key = f.get("risk_type", "unknown")
            if key not in by_type or f.get("score", 0) > by_type[key].get("score", 0):
                by_type[key] = f
        return list(by_type.values())


class _RiskScoringAdapter:
    """Domain RiskScoringEngine 的适配器"""

    def detect(self, rows: list[dict]) -> list[dict]:
        import domain.finance.anomaly  # noqa: F401 — 触发 Signal 注册
        from domain.finance.anomaly.scoring.engine import scan_all
        return scan_all(rows)
