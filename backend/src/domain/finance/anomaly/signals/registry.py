"""Signal Registry — 统一管理所有信号检测器"""

from .base import Signal


_registry: dict[str, Signal] = {}


def register(signal: Signal) -> None:
    """注册一个信号检测器"""
    _registry[signal.name] = signal


def register_many(*signals: Signal) -> None:
    for s in signals:
        register(s)


def get(name: str) -> Signal:
    return _registry.get(name)


def all_signals() -> list[Signal]:
    return list(_registry.values())


def detect_all(row: dict) -> list:
    """对一行数据运行所有已注册的 Signal

    返回所有检测结果（包括 info 模式的信号）。
    调用方（Scoring Engine）通过 signal.mode 决定是否参与评分。
    """
    results = []
    for sig in _registry.values():
        if sig.mode == "disabled":
            continue
        detection = sig.detect(row)
        if detection and detection.matched:
            results.append(detection)
    return results


def score_signals(row: dict) -> list:
    """仅返回 mode='score' 的信号检测结果（用于评分）"""
    return [d for d in detect_all(row)
            if _registry.get(d.signal) and _registry[d.signal].mode == "score"]


def info_signals(row: dict) -> list:
    """仅返回 mode='info' 的信号检测结果（用于解释说明）"""
    return [d for d in detect_all(row)
            if _registry.get(d.signal) and _registry[d.signal].mode == "info"]


def signal_modes() -> dict[str, str]:
    """返回 {signal_name: mode} 映射"""
    return {name: sig.mode for name, sig in _registry.items()}
