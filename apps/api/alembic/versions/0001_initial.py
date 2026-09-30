"""Initial schema.

Revision ID: 0001
Revises:
"""
from alembic import op
from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(op.get_bind())

def downgrade():
    Base.metadata.drop_all(op.get_bind())
