"""MinIO 对象存储实现."""

from datetime import timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from .interface import ObjectStorage
from .path import StoragePath


class MinIOStorage(ObjectStorage):
    """基于 MinIO 的 ObjectStorage 实现"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 bucket: str = "auditflow", secure: bool = False):
        self._bucket = bucket
        self._client = Minio(endpoint, access_key=access_key,
                             secret_key=secret_key, secure=secure)

    async def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    async def upload(self, tenant_id: str, project_id: str,
                     category: str, filename: str, content: bytes) -> StoragePath:
        path = StoragePath(tenant_id=tenant_id, project_id=project_id,
                           category=category, filename=filename)
        await self._ensure_bucket()
        self._client.put_object(
            self._bucket, path.path,
            BytesIO(content), length=len(content),
        )
        return path

    async def download(self, path: StoragePath) -> bytes:
        response = self._client.get_object(self._bucket, path.path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def delete(self, path: StoragePath) -> None:
        self._client.remove_object(self._bucket, path.path)

    async def get_presigned_url(self, path: StoragePath, expires: int = 3600) -> str:
        return self._client.presigned_get_object(
            self._bucket, path.path, expires=timedelta(seconds=expires)
        )

    async def exists(self, path: StoragePath) -> bool:
        try:
            self._client.stat_object(self._bucket, path.path)
            return True
        except S3Error:
            return False
