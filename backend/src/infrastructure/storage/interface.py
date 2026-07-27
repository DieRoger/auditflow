"""ObjectStorage — 统一对象存储抽象接口."""

from abc import ABC, abstractmethod

from .path import StoragePath


class ObjectStorage(ABC):
    """对象存储抽象层

    所有文件存储（文档、图片、报告）必须通过此接口。
    禁止直接操作 MinIO/S3 API。
    """

    @abstractmethod
    async def upload(self, tenant_id: str, project_id: str,
                     category: str, filename: str, content: bytes) -> StoragePath:
        """上传文件，返回 StoragePath"""
        ...

    @abstractmethod
    async def download(self, path: StoragePath) -> bytes:
        """下载文件"""
        ...

    @abstractmethod
    async def delete(self, path: StoragePath) -> None:
        """删除文件"""
        ...

    @abstractmethod
    async def get_presigned_url(self, path: StoragePath, expires: int = 3600) -> str:
        """获取预签名 URL（用于前端直连下载/预览）"""
        ...

    @abstractmethod
    async def exists(self, path: StoragePath) -> bool:
        """检查文件是否存在"""
        ...
