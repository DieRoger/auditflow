"""Excel Adapter — Phase A MVP

读取 Excel/CSV 文件，生成 ImportSession + ImportRecord 列表。
"""

import json
import structlog
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from domain.finance.entities.import_framework import (
    ImportRecord, ImportSession, ImportStatus, MappingProfile, SourceType,
)

logger = structlog.get_logger(__name__)


class ExcelAdapter:
    """Excel/CSV 文件解析器"""

    def __init__(self, mapping: Optional[MappingProfile] = None):
        self._mapping = mapping or MappingProfile.revenue_cutoff_default()

    def parse(self, file_path: str, uploaded_by: str = "system") -> tuple[ImportSession, list[ImportRecord]]:
        """解析 Excel 文件，返回 ImportSession + 行列表"""
        import openpyxl

        path = Path(file_path)
        session = ImportSession(
            filename=path.name,
            uploaded_by=uploaded_by,
            source_type=SourceType.CSV if path.suffix == ".csv" else SourceType.EXCEL,
            status=ImportStatus.PENDING,
        )

        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        if not rows:
            return session, []

        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]

        records = []
        for row_idx, row in enumerate(rows[1:], start=1):
            raw = {}
            for col_idx, value in enumerate(row):
                col_name = headers[col_idx] if col_idx < len(headers) else f"col_{col_idx}"
                raw[col_name] = str(value).strip() if value is not None else ""

            records.append(ImportRecord(
                session_id=session.session_id,
                row_number=row_idx + 1,  # +1 for header row
                raw_data=raw,
            ))

        session.row_count = len(records)
        logger.info("excel_parsed", file=path.name, rows=len(records))
        return session, records

    def validate(self, records: list[ImportRecord]) -> tuple[list[ImportRecord], int]:
        """逐行验证，标记 VALID/FAILED"""
        valid_count = 0
        for rec in records:
            errors = []
            raw = rec.raw_data

            # 检查 required 字段
            for field, config in self._mapping.mappings.items():
                if not config.get("required", False):
                    continue
                matched = self._find_value(raw, config.get("aliases", []))
                if matched is None or str(matched).strip() == "":
                    errors.append(f"Required field '{field}' not found or empty")

            # 检查日期格式
            aliases = self._mapping.mappings.get("transaction_date", {}).get("aliases", [])
            date_val = self._find_value(raw, aliases)
            if date_val:
                try:
                    self._parse_date(str(date_val))
                except ValueError:
                    errors.append(f"Invalid date format: {date_val}")

            # 检查金额
            aliases = self._mapping.mappings.get("amount", {}).get("aliases", [])
            amt_val = self._find_value(raw, aliases)
            if amt_val:
                try:
                    self._parse_amount(str(amt_val))
                except ValueError:
                    errors.append(f"Invalid amount: {amt_val}")

            if errors:
                rec.status = ImportRecord.status.__class__.FAILED
                rec.validation_errors = errors
            else:
                rec.status = ImportRecord.status.__class__.VALID
                valid_count += 1

        return records, valid_count

    def generate_transactions(self, records: list[ImportRecord]) -> tuple[list, list]:
        """从 VALID ImportRecord 生成 Canonical Transaction + Document + Party"""
        from domain.finance.entities.transaction import (
            Document, DocumentType, Party, PartyType, Transaction, TransactionType,
        )

        transactions = []
        documents = []
        parties_seen = {}

        for rec in records:
            if rec.status != rec.status.__class__.VALID:
                continue

            raw = rec.raw_data
            party_name = self._find_value(raw, self._mapping.mappings.get("party_name", {}).get("aliases", [])) or "Unknown"

            # Party (dedup by name)
            if party_name not in parties_seen:
                parties_seen[party_name] = Party(party_type=PartyType.CUSTOMER, name=str(party_name))
            party = parties_seen[party_name]

            # Document (Invoice)
            invoice_no = self._find_value(raw, self._mapping.mappings.get("invoice_no", {}).get("aliases", []))
            inv_doc = None
            if invoice_no and str(invoice_no).strip():
                inv_doc = Document(
                    document_type=DocumentType.INVOICE,
                    document_no=str(invoice_no),
                    party_id=party.party_id,
                )
                documents.append(inv_doc)

            # Document (Delivery) — if shipping_date present
            shipping_val = self._find_value(raw, self._mapping.mappings.get("shipping_date", {}).get("aliases", []))
            del_doc = None
            if shipping_val:
                del_doc = Document(
                    document_type=DocumentType.DELIVERY,
                    document_no=f"DEL-{rec.row_number}",
                    party_id=party.party_id,
                )
                documents.append(del_doc)

            # Transaction
            date_val = self._parse_date(str(self._find_value(raw, self._mapping.mappings.get("transaction_date", {}).get("aliases", [])) or ""))
            amount_val = self._parse_amount(str(self._find_value(raw, self._mapping.mappings.get("amount", {}).get("aliases", [])) or "0"))

            doc_refs = [d.document_id for d in [inv_doc, del_doc] if d]
            txn = Transaction(
                transaction_type=TransactionType.SALES,
                transaction_date=date_val,
                amount=amount_val,
                party_id=party.party_id,
                document_refs=doc_refs,
                source=rec.session_id,
            )
            transactions.append(txn)

            # 关联 ImportRecord → Transaction
            rec.canonical_refs = {"type": "transaction", "id": txn.transaction_id}

        return transactions, list(parties_seen.values())

    # ── helpers ──

    def _find_value(self, raw: dict, aliases: list[str]) -> Optional[str]:
        """在 raw_data 中按别名列表查找值（先精确匹配，再模糊匹配）"""
        for alias in aliases:
            # 精确匹配
            if alias in raw:
                return raw[alias]
        for alias in aliases:
            # 模糊匹配（别名是 key 的子串）
            for key in raw:
                if alias.lower() in key.lower():
                    return raw[key]
        return None

    @staticmethod
    def _parse_date(val: str) -> datetime:
        """尝试多种日期格式"""
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {val}")

    @staticmethod
    def _parse_amount(val: str) -> Decimal:
        """解析金额，去除逗号/空格"""
        cleaned = val.replace(",", "").replace(" ", "").replace("¥", "").replace("$", "")
        return Decimal(cleaned)
