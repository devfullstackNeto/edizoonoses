"""Editable role policies.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    if "role_policies" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table("role_policies",
                        sa.Column("name", sa.String(30), primary_key=True),
                        sa.Column("active", sa.Boolean(), nullable=False),
                        sa.Column("permissions", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("role_policies")
