"""Synthetic Data Factory — 虚拟制造企业甲公司 2023-2025 财务数据

生成: 科目余额表 / 序时账 / 销售明细 / 应收账款明细 / 存货收发存
植入: 8 个审计风险"地雷"
输出: Canonical Schema (Transaction/Document/Party) + Excel 文件
"""

import uuid, json, os, sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

COMPANY = {"name": "甲公司", "industry": "装备制造", "est_year": 2010}

# ── 会计科目表 ──
ACCOUNTS = {
    "1001": "库存现金", "1002": "银行存款", "1122": "应收账款", "1221": "其他应收款",
    "1403": "原材料", "1405": "库存商品", "1601": "固定资产", "1602": "累计折旧",
    "2001": "短期借款", "2202": "应付账款", "2241": "其他应付款",
    "4001": "实收资本", "4104": "未分配利润",
    "6001": "营业收入", "6401": "主营业务成本", "6601": "销售费用",
    "6602": "管理费用", "6603": "财务费用", "6801": "所得税费用",
}

# ── 地雷定义 ──
GOLDEN_DATASET = []


def add_golden(risk_id, desc, year, account, amount, date_str, severity):
    GOLDEN_DATASET.append({
        "risk_id": risk_id, "description": desc, "year": year,
        "account": account, "amount": float(amount),
        "date": date_str, "severity": severity,
        "detected": False,  # Agent 检测后标记
    })


@dataclass
class SyntheticData:
    """完整合成数据集"""
    company: str = COMPANY["name"]
    years: list[str] = field(default_factory=lambda: ["2023", "2024", "2025"])

    # Canonical Schema
    transactions: list = field(default_factory=list)
    documents: list = field(default_factory=list)
    parties: list = field(default_factory=list)

    # 财务汇总
    trial_balance: dict = field(default_factory=dict)  # {year: {account: amount}}
    monthly_revenue: dict = field(default_factory=dict)  # {year: {month: amount}}


class SyntheticDataEngine:
    """合成数据引擎"""

    BASE_REVENUE = {"2023": 520_000_000, "2024": 620_000_000, "2025": 850_000_000}
    GROSS_MARGIN = {"2023": 0.33, "2024": 0.31, "2025": 0.28}  # 毛利率逐年下降

    def __init__(self, seed: int = 42, num_transactions: int = 50000):
        self.rng = random.Random(seed)
        self.num_txns = num_transactions
        self.data = SyntheticData()
        self.customers = [f"客户_{chr(65+i)}" for i in range(26)]  # A-Z
        self.products = [f"产品_{chr(65+i)}" for i in range(20)]

    def generate_all(self) -> SyntheticData:
        """生成完整 3 年合成数据"""
        self._generate_parties()
        for year in self.data.years:
            annual_txns = self.num_txns // len(self.data.years)
            self._generate_sales(year, annual_txns)

        self._generate_trial_balance()
        self._generate_documents()

        # 植入地雷
        self._plant_mines()

        return self.data

    def _generate_parties(self):
        for name in self.customers:
            self.data.parties.append({
                "party_id": uuid.uuid4().hex[:12],
                "party_type": "CUSTOMER",
                "name": name,
            })

    def _generate_sales(self, year: str, count: int):
        """生成销售交易"""
        year_revenue = self.BASE_REVENUE[year]
        year_int = int(year)
        base_date = date(year_int, 1, 1)

        for i in range(count):
            day_of_year = self.rng.randint(1, 365 if year_int % 4 == 0 else 365)
            txn_date = base_date + timedelta(days=day_of_year - 1)
            month = txn_date.month

            # 月度收入分布（12月偏高）
            season_factor = 1.5 if month == 12 else (1.2 if month in [3, 6, 9] else 0.9)
            base_amount = year_revenue / count * season_factor
            amount = round(base_amount * self.rng.uniform(0.8, 1.2), 2)

            customer_idx = int((i % len(self.customers)) + self.rng.gauss(0, 2))
            customer_idx = max(0, min(len(self.customers) - 1, customer_idx))
            customer_name = self.customers[customer_idx]
            party = next(p for p in self.data.parties if p["name"] == customer_name)

            # 发货日期 = 交易日期 ± 随机偏移
            ship_days = self.rng.randint(-3, 5)
            ship_date = txn_date + timedelta(days=ship_days)

            product = self.products[i % len(self.products)]
            invoice_no = f"INV-{year}-{i:06d}"

            txn = {
                "transaction_id": uuid.uuid4().hex[:12],
                "transaction_type": "SALES",
                "transaction_date": txn_date.isoformat(),
                "period": f"{year}-{month:02d}",
                "amount": str(amount),
                "currency": "CNY",
                "party_id": party["party_id"],
                "party_name": customer_name,
                "document_refs": [],
                "description": f"销售 {product} 给 {customer_name}",
                "product": product,
                "quantity": self.rng.randint(10, 1000),
                "invoice_no": invoice_no,
                "shipping_date": ship_date.isoformat(),
            }
            self.data.transactions.append(txn)

    def _plant_mines(self):
        """植入 8 个审计风险地雷"""

        # 地雷 1: Cutoff — 2025年12月31日确认收入，2026年1月发货
        txns_2025 = [t for t in self.data.transactions if t["period"].startswith("2025-12")]
        if txns_2025:
            t = self.rng.choice(txns_2025)
            t["transaction_date"] = "2025-12-31"
            t["shipping_date"] = "2026-01-05"
            t["amount"] = str(round(Decimal(t["amount"]) * 3, 2))
            self.data.transactions.append(self.data.transactions.pop(self.data.transactions.index(t)))
            add_golden("R01", "收入提前确认", "2025", "6001-营业收入", t["amount"], "2025-12-31", "HIGH")

        # 地雷 2: 虚构客户 — 为关联方开发票
        self.data.parties.append({
            "party_id": "ghost_001", "party_type": "CUSTOMER", "name": "空壳_贸易公司"
        })
        fake_customer = self.data.parties[-1]
        fake_revenue = Decimal("1200000")
        self.data.transactions.append({
            "transaction_id": uuid.uuid4().hex[:12], "transaction_type": "SALES",
            "transaction_date": "2025-12-15", "period": "2025-12",
            "amount": str(fake_revenue), "currency": "CNY",
            "party_id": fake_customer["party_id"], "party_name": fake_customer["name"],
            "document_refs": [], "description": "销售给空壳贸易公司—无发货记录",
            "product": "虚拟_产品", "quantity": 0, "invoice_no": "INV-GHOST-001",
            "shipping_date": "",  # 无发货
        })
        add_golden("R02", "虚构关联方交易", "2025", "6001-营业收入", fake_revenue, "2025-12-15", "HIGH")

        # 地雷 3: 大额退货未冲减收入
        self.data.transactions.append({
            "transaction_id": uuid.uuid4().hex[:12], "transaction_type": "SALES",
            "transaction_date": "2025-12-20", "period": "2025-12",
            "amount": "800000", "currency": "CNY",
            "party_id": self.data.parties[0]["party_id"],
            "party_name": self.data.parties[0]["name"],
            "document_refs": [], "description": "退货未冲减收入",
            "product": "退货_产品", "quantity": -50, "invoice_no": "INV-RET-001",
            "shipping_date": "", "is_return": True,
        })
        add_golden("R03", "大额退货未冲减收入", "2025", "6001-营业收入", 800000, "2025-12-20", "HIGH")

        # 地雷 4: 12月收入异常偏高
        add_golden("R04", "12月收入占比异常", "2025", "6001-营业收入", 0, "2025-12", "MEDIUM")

        # 地雷 5: 关联方认定 — 应收款集中在一家
        dominant_customer = self.data.parties[0]
        for _ in range(50):
            amount = round(Decimal(str(self.rng.randint(100000, 500000))) * Decimal("1.5"), 2)
            self.data.transactions.append({
                "transaction_id": uuid.uuid4().hex[:12], "transaction_type": "SALES",
                "transaction_date": f"2025-{self.rng.randint(1,12):02d}-{self.rng.randint(1,28):02d}",
                "period": "2025-12", "amount": str(amount), "currency": "CNY",
                "party_id": dominant_customer["party_id"], "party_name": dominant_customer["name"],
                "document_refs": [], "description": "集中销售给最大客户",
                "product": "集中_产品", "quantity": 100, "invoice_no": f"INV-DOM-{_:04d}",
                "shipping_date": "",
            })
        add_golden("R05", "收入高度集中于单一客户", "2025", "6001-营业收入", 0, "2025", "MEDIUM")

        # 地雷 6: 坏账准备不足 (AR 远大于坏账计提)
        add_golden("R06", "应收账款大幅增长但坏账准备未同步计提", "2025", "1122-应收账款", 0, "2025", "HIGH")

        # 地雷 7: 销售折扣异常
        add_golden("R07", "未披露重大销售折扣和折让", "2025", "6001-营业收入", 500000, "2025-12-25", "MEDIUM")

        # 地雷 8: 整单整数金额（造假迹象）
        for _ in range(10):
            self.data.transactions.append({
                "transaction_id": uuid.uuid4().hex[:12], "transaction_type": "SALES",
                "transaction_date": "2025-12-31", "period": "2025-12",
                "amount": "100000", "currency": "CNY",
                "party_id": self.rng.choice(self.data.parties)["party_id"],
                "party_name": self.rng.choice(self.data.parties)["name"],
                "document_refs": [], "description": "期末整数金额",
                "product": "整数_产品", "quantity": 100, "invoice_no": f"INV-RND-{_:03d}",
                "shipping_date": "2025-12-31",
            })
        add_golden("R08", "期末大量整数金额记录（无交易明细支撑）", "2025", "6001-营业收入", 1000000, "2025-12-31", "MEDIUM")

    def _generate_trial_balance(self):
        """生成科目余额汇总"""
        for year in self.data.years:
            txns = [t for t in self.data.transactions if t["period"].startswith(year)]
            total_revenue = sum(Decimal(t["amount"]) for t in txns)
            self.data.monthly_revenue[year] = total_revenue

            # 简化 TB
            tb = {}
            tb["1001-库存现金"] = round(total_revenue * Decimal("0.02"), 2)
            tb["1002-银行存款"] = round(total_revenue * Decimal("0.25"), 2)
            tb["1122-应收账款"] = round(total_revenue * Decimal("0.35"), 2)
            tb["1403-原材料"] = round(total_revenue * Decimal("0.15"), 2)
            tb["1601-固定资产"] = round(total_revenue * Decimal("0.80"), 2)
            tb["1602-累计折旧"] = -round(total_revenue * Decimal("0.12"), 2)
            tb["2001-短期借款"] = round(total_revenue * Decimal("0.30"), 2)
            tb["2202-应付账款"] = round(total_revenue * Decimal("0.20"), 2)
            tb["4001-实收资本"] = round(total_revenue * Decimal("0.40"), 2)
            tb["6001-营业收入"] = total_revenue
            cogs = round(total_revenue * Decimal(str(1 - self.GROSS_MARGIN.get(year, 0.3))), 2)
            tb["6401-主营业务成本"] = -cogs
            tb["6602-管理费用"] = -round(total_revenue * Decimal("0.08"), 2)
            tb["6603-财务费用"] = -round(total_revenue * Decimal("0.02"), 2)
            self.data.trial_balance[year] = tb

    def _generate_documents(self):
        for t in self.data.transactions[:100]:
            doc = {
                "document_id": uuid.uuid4().hex[:12],
                "document_type": "INVOICE",
                "document_no": t.get("invoice_no", ""),
                "document_date": t["transaction_date"],
                "party_id": t["party_id"],
                "amount": t["amount"],
            }
            self.data.documents.append(doc)


def export_to_excel(data: SyntheticData, output_dir: str = "."):
    """将合成数据导出为 Excel（可供 ExcelAdapter 导入）"""
    import openpyxl
    from openpyxl.utils import get_column_letter

    # Sales Detail
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Sales Detail"
    ws.append(["销售日期", "客户名称", "销售金额", "发票号", "发货日期", "产品", "数量"])
    for t in data.transactions:
        ws.append([t["transaction_date"], t.get("party_name", ""), t["amount"],
                   t.get("invoice_no", ""), t.get("shipping_date", ""), t.get("product", ""),
                   t.get("quantity", 0)])

    path = os.path.join(output_dir, "甲公司_销售明细_2023_2025.xlsx")
    wb.save(path)
    return path


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "synthetic_audit_data")
    os.makedirs(data_dir, exist_ok=True)

    print(f"{'='*65}")
    print(f"  Synthetic Data Factory — {COMPANY['name']} ({COMPANY['industry']})")
    print(f"{'='*65}")

    engine = SyntheticDataEngine(seed=42, num_transactions=50000)
    data = engine.generate_all()

    print(f"\n  Generated: {len(data.transactions):,} transactions")
    print(f"  Parties: {len(data.parties)}")
    print(f"  Documents: {len(data.documents)}")
    print(f"  Periods: {', '.join(data.years)}")

    print(f"\n  Monthly Revenue:")
    total_all = Decimal("0")
    for year in sorted(data.years):
        rev = data.monthly_revenue.get(year, 0)
        print(f"    {year}: ${float(rev):,.0f}")
        total_all += rev
    print(f"    Total: ${float(total_all):,.0f}")

    # ── 地雷明细 ──
    print(f"\n  {'='*65}")
    print(f"  GOLDEN DATASET — 植入的 {len(GOLDEN_DATASET)} 个审计风险地雷")
    print(f"  {'='*65}")
    for mine in GOLDEN_DATASET:
        print(f"    [{mine['severity']}] {mine['risk_id']}: {mine['description']}")
        if mine['amount']:
            print(f"           Year: {mine['year']} | Amount: ${float(mine['amount']):,.0f} | Date: {mine['date']}")

    # ── 导出 Excel ──
    xlsx_path = export_to_excel(data, data_dir)
    print(f"\n  Exported: {xlsx_path}")
    size_mb = os.path.getsize(xlsx_path) / 1024 / 1024
    print(f"  Size: {size_mb:.1f} MB")

    # ── 保存 Golden Dataset ──
    golden_path = os.path.join(data_dir, "golden_dataset.json")
    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(GOLDEN_DATASET, f, ensure_ascii=False, indent=2)
    print(f"  Golden Dataset: {golden_path}")

    print(f"\n{'='*65}")
    print(f"  Ready for audit. Import: python scripts/revenue_cutoff_demo.py")
    print(f"  Then use golden_dataset.json to verify detection rate.")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
