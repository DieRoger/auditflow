"""Storage 层 — 统一对象存储"""

from .interface import ObjectStorage
from .minio_storage import MinIOStorage
from .path import StoragePath

__all__ = ["StoragePath", "ObjectStorage", "MinIOStorage"]
