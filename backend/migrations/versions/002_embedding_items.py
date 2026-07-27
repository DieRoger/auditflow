"""Add embedding_items table with PGVector HNSW index

Revision ID: 002
Revises: 001
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "embedding_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=False),
        sa.Column("engagement_id", sa.String(36), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float), nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("security_level", sa.String(20), server_default="INTERNAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # HNSW 索引 — 加速向量检索
    op.execute(
        "CREATE INDEX idx_embedding_hnsw ON embedding_items "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)"
    )

    # 业务索引 — 支持多维过滤
    op.create_index("idx_embedding_firm", "embedding_items", ["firm_id"])
    op.create_index("idx_embedding_engagement", "embedding_items", ["engagement_id"])
    op.create_index("idx_embedding_source_type", "embedding_items", ["source_type"])


def downgrade() -> None:
    op.drop_index("idx_embedding_hnsw", if_exists=True)
    op.drop_index("idx_embedding_firm", if_exists=True)
    op.drop_index("idx_embedding_engagement", if_exists=True)
    op.drop_index("idx_embedding_source_type", if_exists=True)
    op.drop_table("embedding_items")
