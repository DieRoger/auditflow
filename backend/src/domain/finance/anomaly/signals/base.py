"""Signal Base — 异常信号检测器基类

每个 Signal 只回答一个问题: "这个交易是否表现出 X 迹象？"
输出 SignalResult(score, severity, evidence, explanation, recommendation)。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SignalResult:
    """单个信号的检测结果"""
    signal_name: str = ""
    score: float = 0.0
    severity: str = "LOW"          # HIGH / MEDIUM / LOW
    evidence: list[str] = field(default_factory=list)  # 具体证据（INV-1023）
    explanation: str = ""           # 为什么标记
    recommendation: str = ""        # 建议的行动

    def to_dict(self) -> dict:
        return {
            "signal": self.signal_name, "score": self.score,
            "severity": self.severity, "evidence": self.evidence,
            "explanation": self.explanation, "recommendation": self.recommendation,
        }

    def is_flagged(self) -> bool:
        return self.score > 0


class Signal:
    """信号检测器基类"""
    name: str = "base_signal"

    def detect(self, row: dict) -> SignalResult:
        """对单行交易检测信号"""
        raise NotImplementedError
