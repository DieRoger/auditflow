"""Ontology Query — 审计本体推理链查询

供 Planner / Risk Agent 获取审计领域专业知识。
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class OntologyQuerier:
    """本体查询器 — 基于 ontology_node + ontology_edge 的推理链查询"""

    def __init__(self, connection: Any):
        self._conn = connection

    async def get_reasoning_chain(self, audit_area: str) -> dict:
        """给定审计领域 → 返回完整推理链"""
        from sqlalchemy import text
        sql = text("""
            WITH RECURSIVE chain AS (
                -- 起点：AuditArea
                SELECT n.id, n.label, n.node_type, 0 AS depth, ARRAY[n.label::text] AS path
                FROM ontology_node n
                WHERE n.label = :area AND n.node_type = 'AuditArea'
                UNION ALL
                -- 递归遍历出边
                SELECT tgt.id, tgt.label, tgt.node_type, c.depth + 1,
                       c.path || tgt.label::text
                FROM chain c
                JOIN ontology_edge e ON e.source_node_id = c.id
                JOIN ontology_node tgt ON tgt.id = e.target_node_id
                WHERE c.depth < 10
            )
            SELECT DISTINCT label, node_type FROM chain
            ORDER BY node_type, label
        """)
        result = await self._conn.execute(sql, {"area": audit_area})
        rows = result.fetchall()

        if not rows:
            return {"area": audit_area, "found": False, "message": f"未找到审计领域 '{audit_area}'"}

        chain = {"area": audit_area, "found": True, "nodes": {}}
        for label, node_type in rows:
            chain["nodes"].setdefault(node_type, []).append(label)

        logger.info("ontology_query", area=audit_area, node_types=list(chain["nodes"].keys()))
        return chain

    async def get_standards_for_area(self, audit_area: str) -> list[str]:
        """获取给定审计领域的相关准则"""
        from sqlalchemy import text
        sql = text("""
            SELECT DISTINCT tgt.label
            FROM ontology_node n
            JOIN ontology_edge e ON e.source_node_id = n.id AND e.edge_type = 'REFERENCES'
            JOIN ontology_node tgt ON tgt.id = e.target_node_id
            WHERE n.label = :area AND n.node_type = 'AuditArea'
            ORDER BY tgt.label
        """)
        result = await self._conn.execute(sql, {"area": audit_area})
        return [row[0] for row in result.fetchall()]

    async def get_procedures_for_area(self, audit_area: str) -> list[dict]:
        """获取给定审计领域的推荐审计程序"""
        from sqlalchemy import text
        sql = text("""
            SELECT DISTINCT tgt.label AS procedure_type
            FROM ontology_node n
            JOIN ontology_edge e ON e.source_node_id = n.id AND e.edge_type = 'ADDRESSED_BY'
            JOIN ontology_node tgt ON tgt.id = e.target_node_id
            WHERE n.label = :area AND n.node_type = 'AuditArea'
            ORDER BY tgt.label
        """)
        result = await self._conn.execute(sql, {"area": audit_area})
        return [{"procedure_type": row[0]} for row in result.fetchall()]
