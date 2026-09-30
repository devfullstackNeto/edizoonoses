"""Pilot route metadata and visit timestamps.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    plans = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("route_plans")}
    stops = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("route_stops")}
    if "provider" not in plans:
        op.add_column("route_plans", sa.Column("provider", sa.String(30), nullable=False, server_default="local"))
    if "geometry" not in plans:
        op.add_column("route_plans", sa.Column("geometry", sa.JSON(), nullable=False, server_default="[]"))
    if "legs_km" not in plans:
        op.add_column("route_plans", sa.Column("legs_km", sa.JSON(), nullable=False, server_default="[]"))
    if "visited_at" not in stops:
        op.add_column("route_stops", sa.Column("visited_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("route_stops", "visited_at")
    for name in ("legs_km", "geometry", "provider"):
        op.drop_column("route_plans", name)
