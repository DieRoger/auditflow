"""Signal Base — 异常信号检测器基类

每个 Signal 回答一个问题: "这个交易是否表现出 X 迹象？"
输出 Detection，不决定 Score（由 Scoring Engine 决定）。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Detection:
    """信号检测结果 — 只报告事实，不决定分数"""
    signal: str = ""
    matched: bool = True
    severity: str = "LOW"          # HIGH / MEDIUM / LOW
    confidence: float = 1.0        # Signal 可信度
    evidence: list[str] = field(default_factory=list)  # INV-1023, etc.
    explanation: str = ""           # 为什么标记
    recommendation: str = ""        # 建议行动

    def to_dict(self) -> dict:
        return {
            "signal": self.signal, "matched": self.matched,
            "severity": self.severity, "confidence": self.confidence,
            "evidence": self.evidence, "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


class Signal:
    """信号检测器基类

    mode 决定信号如何参与评分:
      - "score": 参与 RiskProfile 加权评分（默认）
      - "info":  仅输出解释信息，不参与评分
      - "disabled": 完全不执行
    """
    name: str = "base_signal"
    mode: str = "score"        # score | info | disabled
    precision: float = 0.0     # 来自 Benchmark 的 precision（0.0 表示未校准）

    def detect(self, row: dict) -> Optional[Detection]:
        """对单行交易检测信号，返回 None 表示未匹配"""
        raise NotImplementedError
