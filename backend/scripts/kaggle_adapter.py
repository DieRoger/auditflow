"""Kaggle Dataset Adapter — 从 Kaggle 下载审计/财务相关数据集

用法:
  python -m scripts.kaggle_adapter search quarterly earnings
  python -m scripts.kaggle_adapter download <dataset-slug>
  python -m scripts.kaggle_adapter list
"""

import asyncio, json, os, sys, subprocess, zipfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


KAGGLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "kaggle_datasets")


class KaggleAdapter:
    """Kaggle API 适配器 — 搜索/下载/管理数据集"""

    def __init__(self):
        self._data_dir = Path(KAGGLE_DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def check_installed(self) -> bool:
        """检查 kagglehub 是否已安装"""
        try:
            import kagglehub
            return True
        except ImportError:
            return False

    def install(self):
        """安装 kagglehub"""
        subprocess.run([sys.executable, "-m", "pip", "install", "kagglehub", "-q"],
                       capture_output=True)
        return self.check_installed()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """搜索数据集（使用 Kaggle API）"""
        import requests
        url = f"https://www.kaggle.com/api/v1/datasets/list?search={query}&sortBy=hottest&page=1&pageSize={limit}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        datasets = resp.json()
        return [
            {"slug": d.get("ref", "unknown"),
             "title": d.get("title", d.get("ref", "")),
             "size": d.get("totalBytes", 0),
             "votes": d.get("voteCount", 0)}
            for d in datasets[:limit]
        ]

    def download(self, slug: str, subdir: str = None) -> str:
        """下载数据集到本地目录"""
        import kagglehub
        path = kagglehub.dataset_download(slug)
        # 复制到本地管理目录
        import shutil
        dest = self._data_dir / slug.replace("/", "_")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(path, dest)

        # 列出文件
        files = list(dest.rglob("*"))
        file_list = [str(f.relative_to(self._data_dir)) for f in files if f.is_file()]
        return {"path": str(dest), "files": file_list}

    def list_downloaded(self) -> list[dict]:
        """列出已下载的数据集"""
        datasets = []
        for d in self._data_dir.iterdir():
            if d.is_dir():
                files = list(d.rglob("*"))
                datasets.append({
                    "name": d.name,
                    "path": str(d),
                    "files": len([f for f in files if f.is_file()]),
                    "size_mb": sum(f.stat().st_size for f in files if f.is_file()) / 1024 / 1024,
                })
        return datasets


class KaggleDatasetParser:
    """将 Kaggle 数据集解析为 AuditFlow 格式"""

    @staticmethod
    def to_transactions(csv_path: str, source: str = "kaggle") -> list[dict]:
        """将 CSV 解析为 Canonical Transaction 格式"""
        import csv
        transactions = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn = {
                    "transaction_id": "",
                    "transaction_type": "SALES",
                    "transaction_date": row.get("date", row.get("Date", "")),
                    "amount": row.get("amount", row.get("Amount", "0")),
                    "party_name": row.get("customer", row.get("Customer", row.get("name", ""))),
                    "description": row.get("description", row.get("Description", "")),
                    "source": source,
                }
                transactions.append(txn)
        return transactions


async def main():
    import sys as _sys

    adapter = KaggleAdapter()
    if not adapter.check_installed():
        print("[Kaggle] Installing kagglehub...")
        adapter.install()
        print("[Kaggle] Installed")

    args = _sys.argv[1:] if len(_sys.argv) > 1 else ["--help"]

    if args[0] == "search":
        query = " ".join(args[1:]) if len(args) > 1 else "financial audit"
        print(f"[Kaggle] Searching: '{query}'")
        results = adapter.search(query)
        for r in results:
            print(f"  {r['slug']:45} votes: {r['votes']}")
        print(f"\n  Download: python -m scripts.kaggle_adapter download <slug>")

    elif args[0] == "download":
        slug = args[1] if len(args) > 1 else None
        if not slug:
            print("Usage: python -m scripts.kaggle_adapter download <dataset-slug>")
            return
        print(f"[Kaggle] Downloading: {slug}")
        result = adapter.download(slug)
        print(f"  Path: {result['path']}")
        print(f"  Files: {len(result['files'])}")
        for f in result['files'][:10]:
            print(f"    - {f}")
        if len(result['files']) > 10:
            print(f"    ... and {len(result['files'])-10} more")

    elif args[0] == "list":
        datasets = adapter.list_downloaded()
        if not datasets:
            print("[Kaggle] No downloaded datasets")
            return
        print(f"[Kaggle] Downloaded datasets:")
        for d in datasets:
            print(f"  {d['name']}: {d['files']} files, {d['size_mb']:.1f} MB")

    else:
        print("""
Kaggle Adapter — Usage:
  python -m scripts.kaggle_adapter search <query>    Search datasets
  python -m scripts.kaggle_adapter download <slug>   Download dataset
  python -m scripts.kaggle_adapter list              List downloaded
        """)


if __name__ == "__main__":
    asyncio.run(main())
