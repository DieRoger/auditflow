"""Logging 配置 — structlog JSON 格式 + trace_id 注入."""

import structlog
from structlog.processors import JSONRenderer, TimeStamper


def configure_logging(log_level: str = "INFO") -> None:
    """配置全局日志

    - JSON 格式输出（适合生产日志系统）
    - trace_id 自动注入（通过 contextvars）
    - 过滤 Secrets（避免 API Key 外泄）
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            _drop_secrets,  # 自定义：丢弃包含 Secrets 的字段
            JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # 设置根日志级别
    import logging
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    # 隐藏 httpx/openai 等库的调试日志
    for lib in ("httpx", "openai", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


SENSITIVE_KEYS = {"api_key", "secret", "password", "token", "authorization"}


def _drop_secrets(logger: object, name: str, event_dict: dict) -> dict:
    """过滤敏感字段

    递归检查 event_dict 中的 key，如果匹配 SENSITIVE_KEYS 则替换为 '[REDACTED]'。
    """
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _drop_secrets(logger, name, event_dict[key])
    return event_dict


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取结构化 Logger"""
    return structlog.get_logger(name)
