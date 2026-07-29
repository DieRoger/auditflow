"""Import Framework Domain — ImportSession, ImportRecord, MappingProfile

Import Context（不属于 Finance Domain）。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ImportStatus(Enum):
    PENDING = "PENDING"
    MAPPING = "MAPPING"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RecordStatus(Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class SourceType(Enum):
    EXCEL = "EXCEL"
    CSV = "CSV"
    ERP_EXPORT = "ERP_EXPORT"


@dataclass
class ImportSession:
    """一次完整的数据导入操作（聚合根）"""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    filename: str = ""
    uploaded_at: datetime = field(default_factory=datetime.now)
    uploaded_by: str = "system"
    source_type: SourceType = SourceType.EXCEL
    status: ImportStatus = ImportStatus.PENDING
    mapping_profile_id: Optional[str] = None
    row_count: int = 0
    valid_count: int = 0


@dataclass
class ImportRecord:
    """Excel 中的每一行原始数据（raw_data 永不修改）"""
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    session_id: str = ""
    row_number: int = 0
    raw_data: dict = field(default_factory=dict)
    status: RecordStatus = RecordStatus.PENDING
    validation_errors: list[str] = field(default_factory=list)
    canonical_refs: Optional[dict] = None  # {"type": "transaction", "id": "..."}


@dataclass
class MappingProfile:
    """字段映射模板（可保存复用）"""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    mappings: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def revenue_cutoff_default(cls) -> "MappingProfile":
        """Revenue Cutoff Demo 的默认映射"""
        return cls(
            name="Revenue Cutoff Default",
            mappings={
                "transaction_date": {
                    "aliases": ["销售日期", "Date", "Sales Date", "transaction_date"],
                    "required": True, "format": "YYYY-MM-DD",
                },
                "amount": {
                    "aliases": ["金额", "Amount", "Sales Amount", "amount"],
                    "required": True, "format": "Decimal",
                },
                "party_name": {
                    "aliases": ["客户名称", "Customer", "Party", "customer"],
                    "required": True,
                },
                "invoice_no": {
                    "aliases": ["发票号", "Invoice No", "Invoice_No"],
                    "required": False,
                },
                "shipping_date": {
                    "aliases": ["发货日期", "Ship Date", "Shipping_Date"],
                    "required": False, "format": "YYYY-MM-DD",
                },
            },
        )
