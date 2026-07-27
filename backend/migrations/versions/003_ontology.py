"""Add ontology_node / ontology_edge tables with Graph-Ready schema

Revision ID: 003
Revises: 002
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ontology_node",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("node_type", sa.String(30), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("properties", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("label", "node_type", name="uq_ontology_node_label_type"),
    )
    op.create_index("idx_ontology_node_type", "ontology_node", ["node_type"])
    op.create_index("idx_ontology_node_label", "ontology_node", ["label"])

    op.create_table(
        "ontology_edge",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_node_id", sa.String(36), sa.ForeignKey("ontology_node.id", ondelete="CASCADE"), nullable=False),  # noqa: E501
        sa.Column("target_node_id", sa.String(36), sa.ForeignKey("ontology_node.id", ondelete="CASCADE"), nullable=False),  # noqa: E501
        sa.Column("edge_type", sa.String(30), nullable=False),
        sa.Column("weight", sa.Float, server_default="1.0"),
        sa.Column("properties", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_node_id", "target_node_id", "edge_type", name="uq_ontology_edge"),
    )
    op.create_index("idx_ontology_edge_source", "ontology_edge", ["source_node_id"])
    op.create_index("idx_ontology_edge_target", "ontology_edge", ["target_node_id"])
    op.create_index("idx_ontology_edge_type", "ontology_edge", ["edge_type"])


def downgrade() -> None:
    op.drop_table("ontology_edge")
    op.drop_table("ontology_node")
