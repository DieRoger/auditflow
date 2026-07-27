# ruff: noqa
"""Audit Ontology 导入工具"""
import uuid, yaml, argparse
from sqlalchemy import create_engine, text
from pathlib import Path


def load_ontology(yaml_path: str, db_url: str = "sqlite:///dev.db"):
    """加载 YAML 推理链到 ontology_node + ontology_edge 表"""
    with open(yaml_path, encoding="utf-8") as f:
        chains = yaml.safe_load(f)

    engine = create_engine(db_url)
    node_ids = {}

    with engine.begin() as conn:
        # 建表
        conn.execute(text("CREATE TABLE IF NOT EXISTS ontology_node (id VARCHAR(36) PRIMARY KEY, node_type VARCHAR(30) NOT NULL, label VARCHAR(255) NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(label, node_type))"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS ontology_edge (id VARCHAR(36) PRIMARY KEY, source_node_id VARCHAR(36) NOT NULL REFERENCES ontology_node(id) ON DELETE CASCADE, target_node_id VARCHAR(36) NOT NULL REFERENCES ontology_node(id) ON DELETE CASCADE, edge_type VARCHAR(30) NOT NULL, weight FLOAT DEFAULT 1.0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(source_node_id, target_node_id, edge_type))"))

        INS_NODE = "INSERT OR IGNORE INTO ontology_node (id, node_type, label, description) VALUES (:id, :t, :l, :d)"
        INS_EDGE = "INSERT OR IGNORE INTO ontology_edge (id, source_node_id, target_node_id, edge_type) VALUES (:id, :s, :t, :e)"
        nid = lambda: uuid.uuid4().hex[:12]

        # 预定义基础节点
        for name, desc in {"Existence": "Exists", "Completeness": "Complete", "Accuracy": "Accurate",
                           "Valuation": "Valued", "Cutoff": "Cutoff", "Rights": "Rights", "Presentation": "Disclosed"}.items():
            i = nid(); conn.execute(text(INS_NODE), {"id": i, "t": "Assertion", "l": name, "d": desc}); node_ids[f"A:{name}"] = i

        for name, desc in {"Inspection": "Examine", "Confirmation": "Confirm", "Analytical": "Analyze",
                           "Recalculation": "Recalc", "Inquiry": "Inquire"}.items():
            i = nid(); conn.execute(text(INS_NODE), {"id": i, "t": "ProcedureType", "l": name, "d": desc}); node_ids[f"P:{name}"] = i

        ev_types = {"sales_contracts": "Sales contracts", "shipping_docs": "Shipping docs", "customer_confirmations": "Confirmations",
                    "aging_report": "Aging report", "ar_ledger": "AR ledger", "inventory_list": "Inventory list",
                    "slow_moving_report": "Slow moving", "costing_sheets": "Costing", "invoices": "Invoices",
                    "general_ledger": "GL", "asset_register": "Asset register", "depreciation_schedule": "Depr schedule",
                    "management_representations": "Mgmt reps", "board_minutes": "Board minutes", "revenue_analysis": "Revenue analysis"}
        for name, desc in ev_types.items():
            i = nid(); conn.execute(text(INS_NODE), {"id": i, "t": "EvidenceType", "l": name, "d": desc}); node_ids[f"E:{name}"] = i

        # 处理每个推理链
        for chain_name, chain in chains.items():
            area_id = nid(); conn.execute(text(INS_NODE), {"id": area_id, "t": "AuditArea", "l": chain_name, "d": chain.get("risk", "")})
            risk_label = chain.get("risk", chain_name)
            risk_id = nid(); conn.execute(text(INS_NODE), {"id": risk_id, "t": "Risk", "l": risk_label, "d": risk_label})
            conn.execute(text(INS_EDGE), {"id": nid(), "s": area_id, "t": risk_id, "e": "HAS_RISK"})

            for asst in chain.get("assertions", []):
                if aid := node_ids.get(f"A:{asst}"):
                    conn.execute(text(INS_EDGE), {"id": nid(), "s": risk_id, "t": aid, "e": "VIOLATES"})

            for proc in chain.get("procedures", []):
                if pid := node_ids.get(f"P:{proc.get('type', '')}"):
                    conn.execute(text(INS_EDGE), {"id": nid(), "s": area_id, "t": pid, "e": "ADDRESSED_BY"})
                    for ev in proc.get("evidence_required", []):
                        if eid := node_ids.get(f"E:{ev}"):
                            conn.execute(text(INS_EDGE), {"id": nid(), "s": pid, "t": eid, "e": "PRODUCES"})

            for s in chain.get("related_standards", []):
                sid = nid(); conn.execute(text(INS_NODE), {"id": sid, "t": "Standard", "l": s, "d": f"Standard: {s}"})
                conn.execute(text(INS_EDGE), {"id": nid(), "s": area_id, "t": sid, "e": "REFERENCES"})

        nc = conn.execute(text("SELECT COUNT(*) FROM ontology_node")).scalar()
        ec = conn.execute(text("SELECT COUNT(*) FROM ontology_edge")).scalar()
        print(f"Ontology loaded: {nc} nodes, {ec} edges")
        return {"nodes": nc, "edges": ec}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", default=str(Path(__file__).parent / "seed_ontology.yaml"))
    ap.add_argument("--db", default="sqlite:///dev.db")
    args = ap.parse_args()
    load_ontology(args.yaml, args.db)
