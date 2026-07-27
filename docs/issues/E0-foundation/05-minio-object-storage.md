# 0.2.2 — MinIO Object Storage

- **Epic:** E0 — Foundation
- **Labels:** `storage`, `phase-0`
- **Depends on:** 0.1.2
- **Estimate:** —

## Description
基于 MinIO 实现对象存储抽象层，定义统一的 `ObjectStorage` 接口（upload / download / get_presigned_url），路径遵循 `{tenant_id}/{project_id}/{category}/{filename}` 约定。

## Acceptance Criteria
- [ ] `ObjectStorage` ABC 定义
- [ ] `upload(tenant_id, project_id, category, filename, content: bytes) -> StoragePath`
- [ ] `download(path: StoragePath) -> bytes`
- [ ] `get_presigned_url(path: StoragePath, expires=3600) -> str`
- [ ] 路径格式：`{tenant_id}/{project_id}/{category}/{filename}`

## I/O Interface
```python
class ObjectStorage(ABC):
    async def upload(self, tenant_id, project_id, category, filename, content: bytes) -> StoragePath: ...
    async def download(self, path: StoragePath) -> bytes: ...
    async def get_presigned_url(self, path: StoragePath, expires=3600) -> str: ...
# 路径: {tenant_id}/{project_id}/{category}/{filename}
```
