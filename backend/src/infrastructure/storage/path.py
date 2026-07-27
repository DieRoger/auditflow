"""StoragePath — 对象存储路径值对象."""

from pydantic import BaseModel


class StoragePath(BaseModel):
    """统一对象存储路径

    格式：{tenant_id}/{project_id}/{category}/{filename}
    示例：company_a/audit_2026/original/annual_report.pdf
    """
    tenant_id: str
    project_id: str
    category: str  # "original" | "processed"
    filename: str

    @property
    def path(self) -> str:
        return f"{self.tenant_id}/{self.project_id}/{self.category}/{self.filename}"
