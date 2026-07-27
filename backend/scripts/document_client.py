"""Document API 客户端 — 前端消费"""

from __future__ import annotations

import os
from dataclasses import dataclass

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")


@dataclass
class DocumentSummary:
    id: str
    project_id: str
    filename: str
    document_type: str
    status: str
    size_bytes: int = 0
    page_count: int = 0
    created_at: str = ""


class DocumentAPI:
    """Document REST API 客户端（Python SDK 版）"""

    def __init__(self, base_url: str = API_BASE):
        self.base = base_url

    def upload(self, file_path: str, project_id: str, document_type: str = "financial_report") -> dict:
        """上传文档"""
        import httpx
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            data = {"project_id": project_id, "document_type": document_type}
            resp = httpx.post(f"{self.base}/documents", files=files, data=data)
            resp.raise_for_status()
            return resp.json()

    def list(self, project_id: str, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        """列出文档"""
        import httpx
        params = {"project_id": project_id, "page": page, "page_size": page_size}
        if status:
            params["status"] = status
        resp = httpx.get(f"{self.base}/documents", params=params)
        resp.raise_for_status()
        return resp.json()

    def get(self, document_id: str) -> dict:
        """获取文档详情"""
        import httpx
        resp = httpx.get(f"{self.base}/documents/{document_id}")
        resp.raise_for_status()
        return resp.json()
