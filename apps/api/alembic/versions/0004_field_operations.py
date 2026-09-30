"""Field visits, check-ins, issues and multipage OCR metadata.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa
from app.models import FieldVisit, LocationCheckin, VisitIssue

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    for model in (FieldVisit, LocationCheckin, VisitIssue):
        if model.__tablename__ not in tables:
            model.__table__.create(bind)
    columns = {
        "occurrences": {"geocode_source": sa.Column("geocode_source", sa.String(40), nullable=False, server_default="manual")},
        "documents": {"visit_id": sa.Column("visit_id", sa.String(36), sa.ForeignKey("field_visits.id"), nullable=True)},
        "ocr_jobs": {"pages": sa.Column("pages", sa.JSON(), nullable=False, server_default="[]"),
                     "field_details": sa.Column("field_details", sa.JSON(), nullable=False, server_default="[]"),
                     "visit_id": sa.Column("visit_id", sa.String(36), sa.ForeignKey("field_visits.id"), nullable=True),
                     "reviewed_at": sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)},
        "route_plans": {"duration_min": sa.Column("duration_min", sa.Float(), nullable=True),
                        "start_latitude": sa.Column("start_latitude", sa.Float(), nullable=True),
                        "start_longitude": sa.Column("start_longitude", sa.Float(), nullable=True),
                        "status": sa.Column("status", sa.String(30), nullable=False, server_default="planned"),
                        "started_at": sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
                        "finished_at": sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)},
    }
    for table, new_columns in columns.items():
        existing = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        for name, column in new_columns.items():
            if name not in existing:
                op.add_column(table, column)
    for role_name in ("field_agent", "manager"):
        row = bind.execute(sa.text("SELECT permissions FROM role_policies WHERE name=:name"),
                           {"name": role_name}).first()
        if row and "field:write" not in row[0]:
            op.execute(sa.text("UPDATE role_policies SET permissions=CAST(:value AS JSON) WHERE name=:name")
                       .bindparams(value=__import__("json").dumps([*row[0], "field:write"]), name=role_name))


def downgrade():
    for table, names in (("route_plans", ("duration_min", "start_latitude", "start_longitude", "status", "started_at", "finished_at")),
                         ("ocr_jobs", ("pages", "field_details", "visit_id", "reviewed_at")),
                         ("documents", ("visit_id",)), ("occurrences", ("geocode_source",))):
        for name in names:
            op.drop_column(table, name)
    for model in (VisitIssue, LocationCheckin, FieldVisit):
        model.__table__.drop(op.get_bind())
