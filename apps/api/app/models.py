import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from geoalchemy2 import Geometry


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RolePolicy(Base):
    __tablename__ = "role_policies"
    name: Mapped[str] = mapped_column(String(30), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class Territory(Base):
    __tablename__ = "territories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    geom = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)


class OccurrenceType(Base):
    __tablename__ = "occurrence_types"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Occurrence(Base):
    __tablename__ = "occurrences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    protocol: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(300), default="")
    geocode_source: Mapped[str] = mapped_column(String(40), default="manual")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    territory: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="Pendente")
    priority: Mapped[str] = mapped_column(String(40), index=True, default="Média")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(100), default="manual")
    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


Index("ix_occurrences_geom", Occurrence.geom, postgresql_using="gist")


class OccurrenceEvent(Base):
    __tablename__ = "occurrence_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    occurrence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("occurrences.id"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    object_key: Mapped[str] = mapped_column(String(300), unique=True)
    classification: Mapped[str] = mapped_column(String(30), default="Interno")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True
    )
    occurrence_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("occurrences.id"), nullable=True
    )
    visit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("field_visits.id"), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OCRJob(Base):
    __tablename__ = "ocr_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    provider: Mapped[str] = mapped_column(String(40), default="tesseract")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewed_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    pages: Mapped[list] = mapped_column(JSON, default=list)
    field_details: Mapped[list] = mapped_column(JSON, default=list)
    visit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("field_visits.id"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=0)
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(30), default="1")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(100))
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    fallback: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RoutePlan(Base):
    __tablename__ = "route_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(180))
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    total_km: Mapped[float] = mapped_column(Float, default=0)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(30), default="local")
    geometry: Mapped[list] = mapped_column(JSON, default=list)
    legs_km: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RouteStop(Base):
    __tablename__ = "route_stops"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    route_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("route_plans.id"), index=True
    )
    occurrence_id: Mapped[str] = mapped_column(String(36), ForeignKey("occurrences.id"))
    position: Mapped[int] = mapped_column(Integer)
    visited: Mapped[bool] = mapped_column(Boolean, default=False)
    visited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FieldVisit(Base):
    __tablename__ = "field_visits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    route_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("route_plans.id"), index=True
    )
    stop_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("route_stops.id"), unique=True
    )
    occurrence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("occurrences.id"), index=True
    )
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    outcome: Mapped[str | None] = mapped_column(String(60), nullable=True)
    observation: Mapped[str] = mapped_column(Text, default="")
    arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class LocationCheckin(Base):
    __tablename__ = "location_checkins"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    route_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("route_plans.id"), index=True
    )
    visit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("field_visits.id"), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    purpose: Mapped[str] = mapped_column(String(40))
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str] = mapped_column(String(40), default="recorded")
    justification: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VisitIssue(Base):
    __tablename__ = "visit_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    visit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("field_visits.id"), index=True
    )
    occurrence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("occurrences.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    severity: Mapped[str] = mapped_column(String(30), default="Média")
    status: Mapped[str] = mapped_column(String(30), default="open")
    assignee_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


Index("ix_location_checkins_geom", LocationCheckin.geom, postgresql_using="gist")


class DataQualityRule(Base):
    __tablename__ = "quality_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DataQualityIssue(Base):
    __tablename__ = "quality_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("quality_rules.id"))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36))
    severity: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("rule_id", "entity_id"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(30))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    card: Mapped[str] = mapped_column(Text)
