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
    """对一行数据运行所有已注册的 Signal"""
    results = []
    for sig in _registry.values():
        detection = sig.detect(row)
        if detection and detection.matched:
            results.append(detection)
    return results
