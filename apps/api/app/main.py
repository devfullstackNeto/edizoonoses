import csv
import html
import hmac
import hashlib
import io
import json
import uuid
import logging
import time
import httpx
from urllib.parse import quote
from typing import Protocol
from collections import Counter
from datetime import datetime, timezone
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import String, func, or_, select, text
from sqlalchemy.orm import Session
from rq import Queue
from redis import Redis
from .core import (
    audit,
    checksum,
    current_user,
    db_session,
    ensure_bucket,
    nearest_neighbor,
    norm,
    passwords,
    require,
    risk,
    s3,
    token_for,
)
from .models import (
    AuditEvent,
    ChatMessage,
    DataQualityIssue,
    DataQualityRule,
    Document,
    FieldVisit,
    KnowledgeItem,
    ModelRegistry,
    OCRJob,
    Occurrence,
    OccurrenceEvent,
    OccurrenceType,
    RoutePlan,
    RolePolicy,
    RouteStop,
    VisitIssue,
    SystemSetting,
    Territory,
    User,
    now,
)
from .schemas import OccurrenceIn, OccurrencePatch
from .settings import settings
from .routing import calculate_route
from .geocoding import search_addresses
from .field_ops import router as field_router, field_event, visit_for

logger = logging.getLogger("edi.requests")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

app = FastAPI(
    title="EDI Zoonoses API",
    version="1.0.0",
    description="Dados exclusivamente sintéticos. API demonstrativa; nenhuma decisão epidemiológica automática.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(field_router)


@app.middleware("http")
async def request_headers(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        raise
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    logger.info(
        json.dumps(
            {
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
            }
        )
    )
    return response


@app.get("/health/live")
@app.get("/health")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
@app.get("/ready")
def ready(db: Session = Depends(db_session)):
    db.execute(text("SELECT PostGIS_Version()"))
    Redis.from_url(settings.redis_url).ping()
    ensure_bucket()
    return {"status": "ready", "database": "postgis", "redis": "ok", "storage": "ok"}


@app.post("/api/v1/auth/login")
def login(body: dict, request: Request, db: Session = Depends(db_session)):
    email = str(body.get("email", "")).strip().lower()
    key = "login:" + str(request.client.host if request.client else "unknown")
    redis = Redis.from_url(settings.redis_url)
    attempts = redis.incr(key)
    if attempts == 1:
        redis.expire(key, 60)
    if attempts > 20:
        raise HTTPException(429, "Muitas tentativas; aguarde um minuto")
    user = db.scalar(select(User).where(User.email == email))
    if (
        not user
        or not user.active
        or not passwords.verify(str(body.get("password", "")), user.password_hash)
    ):
        raise HTTPException(401, "Credenciais inválidas")
    audit(db, user, "login", "user", user.id, request_id=request.state.request_id)
    db.commit()
    return {
        "access_token": token_for(user),
        "token_type": "bearer",
        "user": user_data(user),
    }


def user_data(u):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "active": u.active,
    }


@app.get("/api/v1/auth/me")
def me(user: User = Depends(current_user)):
    return user_data(user)


@app.post("/api/v1/auth/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(db_session)):
    audit(db, user, "logout", "user", user.id)
    db.commit()
    return {"ok": True}


def occ_data(o):
    return {
        k: getattr(o, k)
        for k in (
            "id",
            "protocol",
            "type",
            "description",
            "address",
            "geocode_source",
            "latitude",
            "longitude",
            "territory",
            "status",
            "priority",
            "risk_score",
            "occurred_at",
            "created_at",
            "closed_at",
            "assigned_to",
            "source",
            "notes",
            "tags",
        )
    }


def filters(q, status, priority, territory, type, start, end):
    q = q.where(Occurrence.deleted_at.is_(None))
    if status:
        q = q.where(Occurrence.status == status)
    if priority:
        q = q.where(Occurrence.priority == priority)
    if territory:
        q = q.where(Occurrence.territory == territory)
    if type:
        q = q.where(Occurrence.type == type)
    if start:
        q = q.where(Occurrence.occurred_at >= start)
    if end:
        q = q.where(Occurrence.occurred_at <= end)
    return q


@app.get("/api/v1/occurrences")
def list_occurrences(
    search: str = "",
    status: str = "",
    priority: str = "",
    territory: str = "",
    type: str = "",
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    q = filters(select(Occurrence), status, priority, territory, type, start, end)
    if search:
        q = q.where(
            Occurrence.protocol.ilike(f"%{search}%")
            | Occurrence.description.ilike(f"%{search}%")
            | Occurrence.address.ilike(f"%{search}%")
        )
    if user.role == "field_agent":
        q = q.where(Occurrence.assigned_to == user.id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(
        q.order_by(Occurrence.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [occ_data(o) for o in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.post("/api/v1/occurrences", status_code=201)
def create_occurrence(
    body: OccurrenceIn,
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(422, "Latitude e longitude devem ser fornecidas juntas")
    data = body.model_dump(exclude={"occurred_at"})
    if user.role == "field_agent":
        data["assigned_to"] = user.id
    score, _ = risk(body.priority, body.status, body.latitude is not None)
    o = Occurrence(
        **data,
        protocol="DEMO-" + uuid.uuid4().hex[:10].upper(),
        risk_score=score,
        occurred_at=body.occurred_at or now(),
    )
    if body.latitude is not None:
        o.geom = f"SRID=4326;POINT({body.longitude} {body.latitude})"
    db.add(o)
    db.flush()
    db.add(
        OccurrenceEvent(
            occurrence_id=o.id,
            actor_id=user.id,
            action="created",
            payload={"status": o.status},
        )
    )
    audit(db, user, "create", "occurrence", o.id)
    evaluate_quality(db, o)
    db.commit()
    return occ_data(o)


def get_occurrence(db, occ_id, user):
    o = db.get(Occurrence, occ_id)
    if not o or o.deleted_at:
        raise HTTPException(404, "Ocorrência não encontrada")
    if user.role == "field_agent" and o.assigned_to != user.id:
        raise HTTPException(403, "Ocorrência não atribuída")
    return o


@app.get("/api/v1/occurrences/{occ_id}")
def occurrence_detail(
    occ_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)
):
    o = get_occurrence(db, occ_id, user)
    events = db.scalars(
        select(OccurrenceEvent)
        .where(OccurrenceEvent.occurrence_id == occ_id)
        .order_by(OccurrenceEvent.created_at)
    ).all()
    return {
        **occ_data(o),
        "timeline": [
            {"action": e.action, "payload": e.payload, "created_at": e.created_at}
            for e in events
        ],
    }


@app.get("/api/v1/occurrences/{occ_id}/workspace")
def occurrence_workspace(
    occ_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)
):
    occurrence = get_occurrence(db, occ_id, user)
    docs = db.scalars(
        select(Document)
        .where(Document.occurrence_id == occ_id)
        .order_by(Document.created_at.desc())
    ).all()
    if user.role == "viewer":
        docs = [d for d in docs if d.classification == "Público"]
    jobs = (
        db.scalars(
            select(OCRJob).where(OCRJob.document_id.in_([d.id for d in docs]))
        ).all()
        if docs
        else []
    )
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_id == occ_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(30)
    ).all()
    return {
        "occurrence": occ_data(occurrence),
        "documents": [doc_data(d) for d in docs],
        "ocr_jobs": [ocr_data(j) for j in jobs],
        "visits": [
            {
                "id": v.id,
                "status": v.status,
                "outcome": v.outcome,
                "started_at": v.started_at,
                "finished_at": v.finished_at,
                "issues": [
                    {"title": i.title, "severity": i.severity, "status": i.status}
                    for i in db.scalars(
                        select(VisitIssue).where(VisitIssue.visit_id == v.id)
                    ).all()
                ],
            }
            for v in db.scalars(
                select(FieldVisit)
                .where(FieldVisit.occurrence_id == occ_id)
                .order_by(FieldVisit.started_at.desc())
            ).all()
        ],
        "audit": [{"action": e.action, "created_at": e.created_at} for e in events],
    }


@app.get("/api/v1/geocode/search")
def geocode_search(
    q: str = Query(..., min_length=3, max_length=160),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    return search_addresses(
        db, q.strip(), user.id if user.role == "field_agent" else None
    )


@app.patch("/api/v1/occurrences/{occ_id}/location")
def update_occurrence_location(
    occ_id: str,
    body: dict,
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    occurrence = get_occurrence(db, occ_id, user)
    try:
        lat, lon = float(body["latitude"]), float(body["longitude"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(422, "Coordenadas inválidas") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(422, "Coordenadas fora da faixa")
    source = str(body.get("source", "manual-map"))
    if source not in ("manual-map", "manual-coordinates", "database-demo", "nominatim"):
        raise HTTPException(422, "Fonte de geocodificação inválida")
    occurrence.latitude, occurrence.longitude = lat, lon
    occurrence.geom = f"SRID=4326;POINT({lon} {lat})"
    occurrence.geocode_source = source
    if body.get("address"):
        occurrence.address = str(body["address"])[:300]
    field_event(db, occurrence.id, user, "location_updated", {"source": source})
    db.commit()
    return occ_data(occurrence)


@app.patch("/api/v1/occurrences/{occ_id}")
def update_occurrence(
    occ_id: str,
    body: OccurrencePatch,
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    o = get_occurrence(db, occ_id, user)
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in (
        "Pendente",
        "Em análise",
        "Em campo",
        "Concluída",
    ):
        raise HTTPException(422, "Status inválido")
    if "priority" in changes and changes["priority"] not in (
        "Baixa",
        "Média",
        "Alta",
        "Crítica",
    ):
        raise HTTPException(422, "Prioridade inválida")
    for key, value in changes.items():
        setattr(o, key, value)
    if (o.latitude is None) != (o.longitude is None):
        raise HTTPException(422, "Latitude e longitude devem ser fornecidas juntas")
    o.geom = (
        f"SRID=4326;POINT({o.longitude} {o.latitude})"
        if o.latitude is not None
        else None
    )
    o.risk_score, _ = risk(o.priority, o.status, o.latitude is not None)
    if o.status == "Concluída" and not o.closed_at:
        o.closed_at = now()
    if o.status != "Concluída":
        o.closed_at = None
    db.add(
        OccurrenceEvent(
            occurrence_id=o.id, actor_id=user.id, action="updated", payload=changes
        )
    )
    audit(db, user, "update", "occurrence", o.id, {"fields": list(changes)})
    evaluate_quality(db, o)
    db.commit()
    return occ_data(o)


@app.delete("/api/v1/occurrences/{occ_id}")
def delete_occurrence(
    occ_id: str,
    user: User = Depends(require("admin", "manager")),
    db: Session = Depends(db_session),
):
    o = get_occurrence(db, occ_id, user)
    o.deleted_at = now()
    db.add(
        OccurrenceEvent(
            occurrence_id=o.id, actor_id=user.id, action="deleted", payload={}
        )
    )
    audit(db, user, "delete", "occurrence", o.id)
    db.commit()
    return {"ok": True}


@app.get("/api/v1/map/features")
def map_features(
    status: str = "",
    priority: str = "",
    territory: str = "",
    type: str = "",
    start: datetime | None = None,
    end: datetime | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    q = filters(
        select(Occurrence), status, priority, territory, type, start, end
    ).where(Occurrence.geom.is_not(None))
    if user.role == "field_agent":
        q = q.where(Occurrence.assigned_to == user.id)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [o.longitude, o.latitude]},
                "properties": {
                    "id": o.id,
                    "protocol": o.protocol,
                    "type": o.type,
                    "status": o.status,
                    "priority": o.priority,
                    "territory": o.territory,
                    "risk_score": o.risk_score,
                },
            }
            for o in db.scalars(q).all()
        ],
    }


@app.get("/api/v1/territories")
def territories(user: User = Depends(current_user), db: Session = Depends(db_session)):
    return [
        {"id": t.id, "name": t.name}
        for t in db.scalars(select(Territory).order_by(Territory.name)).all()
    ]


@app.get("/api/v1/territories.geojson")
def territory_features(
    user: User = Depends(current_user), db: Session = Depends(db_session)
):
    rows = db.execute(
        select(Territory.id, Territory.name, func.ST_AsGeoJSON(Territory.geom)).where(
            Territory.geom.is_not(None)
        )
    ).all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(geometry),
                "properties": {"id": id, "name": name, "synthetic": True},
            }
            for id, name, geometry in rows
        ],
    }


@app.get("/api/v1/occurrence-types")
def occurrence_types(
    user: User = Depends(current_user), db: Session = Depends(db_session)
):
    return [
        {"id": t.id, "name": t.name, "active": t.active}
        for t in db.scalars(select(OccurrenceType)).all()
    ]


@app.get("/api/v1/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(db_session)):
    q = select(Occurrence).where(Occurrence.deleted_at.is_(None))
    if user.role == "field_agent":
        q = q.where(Occurrence.assigned_to == user.id)
    rows = db.scalars(q).all()

    def by(key):
        return dict(Counter(getattr(o, key) for o in rows))

    monthly = dict(Counter(o.created_at.strftime("%Y-%m") for o in rows))
    closed = [
        (o.closed_at - o.created_at).total_seconds() / 3600 for o in rows if o.closed_at
    ]
    route_q = select(RoutePlan)
    visit_q = select(FieldVisit)
    if user.role == "field_agent":
        route_q = route_q.where(RoutePlan.actor_id == user.id)
        visit_q = visit_q.where(FieldVisit.actor_id == user.id)
    field_routes = db.scalars(route_q).all()
    visits = db.scalars(visit_q).all()
    visible_visit_ids = {v.id for v in visits}
    issue_visit_ids = {
        i.visit_id
        for i in db.scalars(
            select(VisitIssue).where(VisitIssue.status != "resolved")
        ).all()
    }
    durations = [
        (v.finished_at - v.started_at).total_seconds() / 60
        for v in visits
        if v.finished_at and v.started_at
    ]
    today = datetime.now(timezone.utc).date()
    return {
        "total": len(rows),
        "pending": sum(o.status != "Concluída" for o in rows),
        "high_risk": sum(o.risk_score >= 70 for o in rows),
        "by_status": by("status"),
        "by_type": by("type"),
        "by_territory": by("territory"),
        "by_priority": by("priority"),
        "by_period": monthly,
        "average_close_hours": round(sum(closed) / len(closed), 1) if closed else None,
        "documents": db.scalar(select(func.count()).select_from(Document)),
        "ocr_jobs": db.scalar(select(func.count()).select_from(OCRJob)),
        "routes": db.scalar(select(func.count()).select_from(RoutePlan)),
        "quality_issues": db.scalar(
            select(func.count())
            .select_from(DataQualityIssue)
            .where(DataQualityIssue.status == "open")
        ),
        "chat_fallbacks": db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.fallback.is_(True))
        ),
        "ocr_by_status": dict(
            Counter(j.status for j in db.scalars(select(OCRJob)).all())
        ),
        "recent_occurrences": [
            {
                "id": o.id,
                "protocol": o.protocol,
                "type": o.type,
                "status": o.status,
                "priority": o.priority,
                "created_at": o.created_at,
            }
            for o in sorted(rows, key=lambda o: o.created_at, reverse=True)[:6]
        ],
        "recent_activity": [
            {"action": e.action, "entity": e.entity, "created_at": e.created_at}
            for e in db.scalars(
                select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(6)
            ).all()
        ],
        "field": {
            "routes_planned": sum(r.status == "planned" for r in field_routes),
            "routes_active": sum(r.status == "active" for r in field_routes),
            "visits_today": sum(
                v.started_at is not None and v.started_at.date() == today
                for v in visits
            ),
            "visits_completed": sum(v.status == "completed" for v in visits),
            "visits_with_issue": sum(v.id in issue_visit_ids for v in visits),
            "revisits": sum(v.outcome == "requer revisita" for v in visits),
            "issues_open": sum(
                i.status != "resolved" and i.visit_id in visible_visit_ids
                for i in db.scalars(select(VisitIssue)).all()
            ),
            "ocr_pending": sum(
                j.status in ("queued", "processing", "needs_review")
                for j in db.scalars(select(OCRJob)).all()
            ),
            "ocr_reviewed": sum(
                j.status in ("approved", "rejected")
                for j in db.scalars(select(OCRJob)).all()
            ),
            "documents_processed": len(
                {
                    j.document_id
                    for j in db.scalars(
                        select(OCRJob).where(
                            OCRJob.status.in_(("needs_review", "approved", "rejected"))
                        )
                    ).all()
                }
            ),
            "average_visit_minutes": round(sum(durations) / len(durations), 1)
            if durations
            else None,
            "territory_coverage": dict(
                Counter(
                    db.get(Occurrence, v.occurrence_id).territory
                    for v in visits
                    if v.status == "completed"
                )
            ),
        },
    }


ALLOWED_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


def doc_data(d):
    return {
        k: getattr(d, k)
        for k in (
            "id",
            "name",
            "mime",
            "size",
            "sha256",
            "classification",
            "tags",
            "version",
            "parent_id",
            "occurrence_id",
            "visit_id",
            "retention_until",
            "created_at",
        )
    }


@app.post("/api/v1/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    classification: str = Form("Interno"),
    tags: str = Form(""),
    occurrence_id: str | None = Form(None),
    visit_id: str | None = Form(None),
    parent_id: str | None = Form(None),
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, "Formato não permitido")
    data = await file.read(10_000_001)
    if len(data) > 10_000_000:
        raise HTTPException(413, "Arquivo excede 10 MB")
    if not data:
        raise HTTPException(422, "Arquivo vazio")
    if classification not in ("Público", "Interno", "Restrito"):
        raise HTTPException(422, "Classificação inválida")
    if visit_id:
        if user.role not in ("admin", "field_agent", "manager"):
            raise HTTPException(403, "Vínculo de visita não permitido")
        visit, route = visit_for(db, visit_id, user)
        if route.status != "active" or visit.status not in ("arrived", "in_progress"):
            raise HTTPException(409, "Visita não está ativa")
        if occurrence_id and occurrence_id != visit.occurrence_id:
            raise HTTPException(422, "Ocorrência não corresponde à visita")
        occurrence_id = visit.occurrence_id
    if occurrence_id:
        get_occurrence(db, occurrence_id, user)
    parent = db.get(Document, parent_id) if parent_id else None
    if parent_id and not parent:
        raise HTTPException(404, "Versão anterior não encontrada")
    ensure_bucket()
    doc = Document(
        name=(file.filename or "documento")[:255],
        mime=file.content_type,
        size=len(data),
        sha256=checksum(data),
        object_key=f"{uuid.uuid4().hex}{ALLOWED_MIME[file.content_type]}",
        classification=classification,
        tags=[x.strip() for x in tags.split(",") if x.strip()],
        occurrence_id=occurrence_id,
        visit_id=visit_id,
        parent_id=parent_id,
        version=parent.version + 1 if parent else 1,
    )
    s3().put_object(
        Bucket=settings.s3_bucket, Key=doc.object_key, Body=data, ContentType=doc.mime
    )
    db.add(doc)
    db.flush()
    audit(db, user, "upload", "document", doc.id, {"sha256": doc.sha256})
    if occurrence_id:
        field_event(
            db,
            occurrence_id,
            user,
            "document_uploaded",
            {"document_id": doc.id, "visit_id": visit_id},
        )
    db.commit()
    return doc_data(doc)


@app.get("/api/v1/documents")
def list_documents(
    search: str = "",
    occurrence_id: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    q = select(Document)
    if user.role == "viewer":
        q = q.where(Document.classification == "Público")
    if search:
        pattern = f"%{search}%"
        q = q.where(
            or_(
                Document.name.ilike(pattern),
                Document.tags.cast(String).ilike(pattern),
                Document.occurrence_id.in_(
                    select(Occurrence.id).where(Occurrence.protocol.ilike(pattern))
                ),
                Document.id.in_(
                    select(OCRJob.document_id).where(OCRJob.raw_text.ilike(pattern))
                ),
            )
        )
    if occurrence_id:
        q = q.where(Document.occurrence_id == occurrence_id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(
        q.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [doc_data(d) for d in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/v1/documents/{doc_id}/preview")
@app.get("/api/v1/documents/{doc_id}/download")
def download_document(
    doc_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Documento não encontrado")
    if user.role == "viewer" and d.classification != "Público":
        raise HTTPException(403, "Documento restrito")
    body = s3().get_object(Bucket=settings.s3_bucket, Key=d.object_key)["Body"].read()
    inline = request.url.path.endswith("/preview")
    audit(db, user, "preview" if inline else "download", "document", d.id)
    db.commit()
    return Response(
        body,
        media_type=d.mime,
        headers={
            "Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(d.name)}"
        },
    )


@app.post("/api/v1/ocr/jobs", status_code=202)
def create_ocr_job(
    body: dict,
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    d = db.get(Document, body.get("document_id"))
    if not d:
        raise HTTPException(404, "Documento não encontrado")
    if d.mime not in ("image/png", "image/jpeg", "application/pdf"):
        raise HTTPException(415, "OCR aceita imagem ou PDF")
    job = OCRJob(document_id=d.id, visit_id=d.visit_id)
    db.add(job)
    db.commit()
    Queue("ocr", connection=Redis.from_url(settings.redis_url)).enqueue(
        "app.worker.process_ocr", job.id, job_timeout=300
    )
    audit(db, user, "ocr_enqueue", "ocr_job", job.id)
    if d.occurrence_id:
        field_event(
            db,
            d.occurrence_id,
            user,
            "ocr_queued",
            {"job_id": job.id, "visit_id": d.visit_id},
        )
    db.commit()
    return ocr_data(job)


def ocr_data(j):
    return {
        k: getattr(j, k)
        for k in (
            "id",
            "document_id",
            "status",
            "provider",
            "raw_text",
            "fields",
            "reviewed_fields",
            "pages",
            "field_details",
            "visit_id",
            "confidence",
            "reviewed_by",
            "created_at",
            "finished_at",
            "reviewed_at",
        )
    }


@app.get("/api/v1/ocr/jobs")
def list_ocr_jobs(
    user: User = Depends(current_user), db: Session = Depends(db_session)
):
    q = select(OCRJob)
    if user.role == "viewer":
        q = q.where(
            OCRJob.document_id.in_(
                select(Document.id).where(Document.classification == "Público")
            )
        )
    return [
        ocr_data(j)
        for j in db.scalars(q.order_by(OCRJob.created_at.desc()).limit(100)).all()
    ]


@app.get("/api/v1/ocr/jobs/{job_id}")
def get_ocr_job(
    job_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)
):
    j = db.get(OCRJob, job_id)
    if not j:
        raise HTTPException(404, "Job não encontrado")
    if (
        user.role == "viewer"
        and db.get(Document, j.document_id).classification != "Público"
    ):
        raise HTTPException(403, "Documento restrito")
    return ocr_data(j)


@app.post("/api/v1/ocr/jobs/{job_id}/review")
def review_ocr(
    job_id: str,
    body: dict,
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    j = db.get(OCRJob, job_id)
    if not j:
        raise HTTPException(404, "Job não encontrado")
    if j.status != "needs_review":
        raise HTTPException(409, "Job não está pronto para revisão")
    if body.get("decision") not in ("approved", "rejected"):
        raise HTTPException(422, "Decisão inválida")
    reviewed = body.get("fields", {})
    if not isinstance(reviewed, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in reviewed.items()
    ):
        raise HTTPException(422, "Campos revisados inválidos")
    j.reviewed_fields = reviewed
    details = {field["name"]: dict(field) for field in (j.field_details or [])}
    for name, detail in details.items():
        detail["reviewed_value"] = reviewed.get(name)
        detail["status"] = (
            "removed"
            if name not in reviewed
            else "corrected"
            if reviewed[name] != detail["value"]
            else "confirmed"
        )
    for name, value in reviewed.items():
        if name not in details:
            details[name] = {
                "name": name,
                "value": None,
                "confidence": None,
                "page": None,
                "reviewed_value": value,
                "status": "added",
            }
    j.field_details = list(details.values())
    j.reviewed_by = user.id
    j.reviewed_at = now()
    j.status = body["decision"]
    doc = db.get(Document, j.document_id)
    if j.status == "approved" and body.get("occurrence_id"):
        occurrence = get_occurrence(db, body["occurrence_id"], user)
        if (
            doc.visit_id
            and occurrence.id != db.get(FieldVisit, doc.visit_id).occurrence_id
        ):
            raise HTTPException(422, "Ocorrência não corresponde à visita")
        doc.occurrence_id = occurrence.id
        audit(db, user, "ocr_link", "occurrence", occurrence.id, {"job_id": j.id})
    if doc.occurrence_id:
        field_event(
            db,
            doc.occurrence_id,
            user,
            "ocr_reviewed",
            {"job_id": j.id, "decision": j.status, "visit_id": doc.visit_id},
        )
    audit(db, user, "ocr_review", "ocr_job", j.id, {"decision": j.status})
    db.commit()
    return ocr_data(j)


@app.post("/api/v1/ocr/jobs/{job_id}/reprocess", status_code=202)
def reprocess_ocr(
    job_id: str,
    user: User = Depends(require("admin", "field_agent", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    original = db.get(OCRJob, job_id)
    if not original:
        raise HTTPException(404, "Job não encontrado")
    if original.status in ("queued", "processing"):
        raise HTTPException(409, "Processamento ainda em andamento")
    job = OCRJob(document_id=original.document_id, visit_id=original.visit_id)
    db.add(job)
    db.commit()
    Queue("ocr", connection=Redis.from_url(settings.redis_url)).enqueue(
        "app.worker.process_ocr", job.id, job_timeout=300
    )
    audit(
        db, user, "ocr_reprocess", "ocr_job", job.id, {"previous_job_id": original.id}
    )
    doc = db.get(Document, job.document_id)
    if doc.occurrence_id:
        field_event(db, doc.occurrence_id, user, "ocr_reprocessed", {"job_id": job.id})
    db.commit()
    return ocr_data(job)


def chat_answer(question: str, items):
    query = set(norm(question).split()) - {
        "a",
        "as",
        "o",
        "os",
        "e",
        "em",
        "de",
        "da",
        "do",
        "um",
        "uma",
        "uns",
        "umas",
        "como",
        "para",
        "qual",
        "onde",
        "sobre",
        "quero",
        "saber",
        "dos",
        "das",
        "por",
        "que",
        "meu",
        "minha",
    }
    candidates = []
    for item in items:
        title = set(norm(item.title).split())
        tags = set(norm(" ".join(item.tags)).split())
        score = len(query & (title | tags)) * 3
        if score >= 3:
            candidates.append((score, item))
    if not candidates:
        return {
            "text": "Não encontrei orientação validada para essa pergunta. Procure atendimento humano pelos canais oficiais vigentes.",
            "source_refs": [],
            "response_type": "fallback",
            "fallback": True,
            "intent": "fora_do_escopo",
        }
    item = max(candidates, key=lambda x: x[0])[1]
    return {
        "text": item.body,
        "source_refs": [
            {
                "id": item.id,
                "title": item.title,
                "source": item.source,
                "version": item.version,
            }
        ],
        "response_type": "knowledge",
        "fallback": False,
        "intent": norm(item.title).replace(" ", "_"),
    }


class ChatProvider(Protocol):
    def answer(self, question: str, items: list[KnowledgeItem]) -> dict: ...


class MockProvider:
    """Offline provider restricted to the versioned knowledge base."""

    def answer(self, question: str, items: list[KnowledgeItem]) -> dict:
        return chat_answer(question, items)


class OpenAICompatibleProvider:
    """Grounded paraphrase of one retrieved knowledge item, with safe offline fallback."""

    def answer(self, question: str, items: list[KnowledgeItem]) -> dict:
        base = chat_answer(question, items)
        if base["fallback"] or not all(
            (settings.ai_base_url, settings.ai_api_key, settings.ai_model)
        ):
            return base
        try:
            result = httpx.post(
                f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                json={
                    "model": settings.ai_model,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Responda em português somente com o conteúdo da fonte fornecida. Se ela não responder, diga que não há orientação validada. Não invente procedimentos, dados ou fontes.",
                        },
                        {
                            "role": "user",
                            "content": f"Fonte validada:\n{base['text']}\n\nPergunta:\n{question}",
                        },
                    ],
                },
                timeout=8.0,
            )
            result.raise_for_status()
            candidate = result.json()["choices"][0]["message"]["content"].strip()
            if candidate:
                base["text"] = candidate[:4000]
                base["response_type"] = "knowledge_ai"
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            ValueError,
        ):
            pass
        return base


chat_provider: ChatProvider = (
    OpenAICompatibleProvider() if settings.ai_provider == "openai" else MockProvider()
)


@app.post("/api/v1/chat/messages")
def chat(
    body: dict, user: User = Depends(current_user), db: Session = Depends(db_session)
):
    question = str(body.get("text", "")).strip()[:1000]
    if not question:
        raise HTTPException(422, "Pergunta vazia")
    recent = db.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.actor_id == user.id,
            ChatMessage.created_at
            > datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0),
        )
    )
    if recent >= 60:
        raise HTTPException(429, "Limite de perguntas atingido")
    answer = chat_provider.answer(
        question,
        db.scalars(select(KnowledgeItem).where(KnowledgeItem.active.is_(True))).all(),
    )
    session_id = body.get("session_id") or str(uuid.uuid4())
    message = ChatMessage(
        session_id=session_id,
        actor_id=user.id,
        question=question,
        answer=answer["text"],
        intent=answer["intent"],
        source_refs=answer["source_refs"],
        fallback=answer["fallback"],
    )
    db.add(message)
    db.commit()
    return {**answer, "message_id": message.id, "session_id": session_id}


@app.post("/api/v1/chat/messages/{message_id}/feedback")
def chat_feedback(
    message_id: str,
    body: dict,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    message = db.get(ChatMessage, message_id)
    if not message or message.actor_id != user.id:
        raise HTTPException(404, "Mensagem não encontrada")
    if body.get("feedback") not in ("helpful", "unhelpful"):
        raise HTTPException(422, "Feedback inválido")
    message.feedback = body["feedback"]
    db.commit()
    return {"ok": True}


def evaluate_quality(db: Session, o: Occurrence):
    codes = []
    if o.latitude is None:
        codes.append("NO_COORD")
    if len(o.address.strip()) < 5:
        codes.append("SHORT_ADDRESS")
    if not o.territory.strip():
        codes.append("NO_TERRITORY")
    if o.occurred_at and o.occurred_at > now():
        codes.append("FUTURE_DATE")
    if o.risk_score >= 70 and not o.assigned_to:
        codes.append("HIGH_UNASSIGNED")
    rules = {
        r.code: r
        for r in db.scalars(
            select(DataQualityRule).where(DataQualityRule.active.is_(True))
        ).all()
    }
    existing = db.scalars(
        select(DataQualityIssue).where(
            DataQualityIssue.entity == "occurrence", DataQualityIssue.entity_id == o.id
        )
    ).all()
    for issue in existing:
        rule = db.get(DataQualityRule, issue.rule_id)
        if rule and rule.code not in codes and issue.status == "open":
            issue.status, issue.resolved_at = "resolved", now()
    for code in codes:
        rule = rules.get(code)
        if rule and not any(i.rule_id == rule.id for i in existing):
            db.add(
                DataQualityIssue(
                    rule_id=rule.id,
                    entity="occurrence",
                    entity_id=o.id,
                    severity=rule.severity,
                )
            )


@app.get("/api/v1/quality")
def quality(user: User = Depends(current_user), db: Session = Depends(db_session)):
    rules = db.scalars(select(DataQualityRule)).all()
    issues = db.scalars(
        select(DataQualityIssue)
        .order_by(DataQualityIssue.detected_at.desc())
        .limit(200)
    ).all()
    return {
        "rules": [
            {
                "id": r.id,
                "code": r.code,
                "description": r.description,
                "severity": r.severity,
                "active": r.active,
            }
            for r in rules
        ],
        "issues": [
            {
                "id": i.id,
                "rule_id": i.rule_id,
                "entity": i.entity,
                "entity_id": i.entity_id,
                "severity": i.severity,
                "status": i.status,
                "detected_at": i.detected_at,
                "resolved_at": i.resolved_at,
                "note": i.note,
            }
            for i in issues
        ],
    }


@app.post("/api/v1/quality/scan")
def quality_scan(
    user: User = Depends(require("admin", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    for o in db.scalars(
        select(Occurrence).where(Occurrence.deleted_at.is_(None))
    ).all():
        evaluate_quality(db, o)
    db.commit()
    return {
        "open": db.scalar(
            select(func.count())
            .select_from(DataQualityIssue)
            .where(DataQualityIssue.status == "open")
        )
    }


@app.post("/api/v1/quality/issues/{issue_id}/resolve")
def resolve_issue(
    issue_id: str,
    body: dict,
    user: User = Depends(require("admin", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    issue = db.get(DataQualityIssue, issue_id)
    if not issue:
        raise HTTPException(404, "Achado não encontrado")
    if (
        body.get("status") not in ("resolved", "dismissed")
        or not str(body.get("note", "")).strip()
    ):
        raise HTTPException(422, "Informe situação e justificativa")
    issue.status, issue.resolved_at, issue.note = body["status"], now(), body["note"]
    audit(db, user, "quality_review", "quality_issue", issue.id)
    db.commit()
    return {"ok": True}


def route_data(db, route):
    stops = db.scalars(
        select(RouteStop)
        .where(RouteStop.route_id == route.id)
        .order_by(RouteStop.position)
    ).all()
    return {
        "id": route.id,
        "name": route.name,
        "total_km": route.total_km,
        "provider": route.provider,
        "duration_min": route.duration_min,
        "status": route.status,
        "start_latitude": route.start_latitude,
        "start_longitude": route.start_longitude,
        "started_at": route.started_at,
        "finished_at": route.finished_at,
        "geometry": route.geometry,
        "legs_km": route.legs_km,
        "created_at": route.created_at,
        "stops": [
            {
                "id": s.id,
                "occurrence_id": s.occurrence_id,
                "position": s.position,
                "visited": s.visited,
                "visited_at": s.visited_at,
                "segment_km": route.legs_km[
                    s.position - (1 if route.start_latitude is not None else 2)
                ]
                if (route.start_latitude is not None or s.position > 1)
                and len(route.legs_km)
                >= s.position - (0 if route.start_latitude is not None else 1)
                else 0,
            }
            for s in stops
        ],
    }


@app.post("/api/v1/routes")
def create_route(
    body: dict,
    user: User = Depends(require("admin", "field_agent", "manager")),
    db: Session = Depends(db_session),
):
    ids = body.get("occurrence_ids", [])
    if (
        not isinstance(ids, list)
        or not 1 <= len(ids) <= 50
        or len(ids) != len(set(ids))
    ):
        raise HTTPException(422, "Selecione de 1 a 50 pontos únicos")
    points = [get_occurrence(db, oid, user) for oid in ids]
    if any(o.latitude is None for o in points):
        raise HTTPException(422, "Todos os pontos precisam de coordenadas")
    start_lat, start_lon = body.get("start_latitude"), body.get("start_longitude")
    if (start_lat is None) != (start_lon is None):
        raise HTTPException(422, "Informe ambas as coordenadas de partida")
    if start_lat is not None:
        try:
            start_lat, start_lon = float(start_lat), float(start_lon)
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, "Coordenadas inválidas") from exc
        if not (-90 <= start_lat <= 90 and -180 <= start_lon <= 180):
            raise HTTPException(422, "Coordenadas inválidas")
    start = (start_lat, start_lon) if start_lat is not None else None
    ordered, _ = nearest_neighbor(points, start)
    routing = calculate_route(ordered, start)
    route = RoutePlan(
        name=str(body.get("name", "Rota de campo"))[:180],
        actor_id=user.id,
        start_latitude=start_lat,
        start_longitude=start_lon,
        **routing,
    )
    db.add(route)
    db.flush()
    for n, o in enumerate(ordered, 1):
        db.add(RouteStop(route_id=route.id, occurrence_id=o.id, position=n))
        field_event(
            db, o.id, user, "route_planned", {"route_id": route.id, "position": n}
        )
    audit(db, user, "create", "route", route.id)
    db.commit()
    return route_data(db, route)


@app.get("/api/v1/routes")
def list_routes(user: User = Depends(current_user), db: Session = Depends(db_session)):
    q = select(RoutePlan)
    if user.role == "field_agent":
        q = q.where(RoutePlan.actor_id == user.id)
    return [
        route_data(db, r)
        for r in db.scalars(q.order_by(RoutePlan.created_at.desc()).limit(100)).all()
    ]


@app.patch("/api/v1/routes/{route_id}")
def update_route(
    route_id: str,
    body: dict,
    user: User = Depends(require("admin", "field_agent", "manager")),
    db: Session = Depends(db_session),
):
    route = db.get(RoutePlan, route_id)
    if not route or (user.role == "field_agent" and route.actor_id != user.id):
        raise HTTPException(404, "Rota não encontrada")
    if route.status != "planned":
        raise HTTPException(409, "Rota em execução não pode ser reordenada")
    stops = db.scalars(select(RouteStop).where(RouteStop.route_id == route_id)).all()
    if "order" in body:
        if (
            not isinstance(body["order"], list)
            or len(body["order"]) != len(stops)
            or set(body["order"]) != {s.id for s in stops}
        ):
            raise HTTPException(422, "Ordem inválida")
        for n, stop_id in enumerate(body["order"], 1):
            next(s for s in stops if s.id == stop_id).position = n
        points = [
            db.get(Occurrence, next(s for s in stops if s.id == sid).occurrence_id)
            for sid in body["order"]
        ]
        start = (
            (route.start_latitude, route.start_longitude)
            if route.start_latitude is not None
            else None
        )
        routing = calculate_route(points, start)
        for key, value in routing.items():
            setattr(route, key, value)
    if "visited_stop_id" in body:
        stop = next((s for s in stops if s.id == body["visited_stop_id"]), None)
        if not stop:
            raise HTTPException(404, "Parada não encontrada")
        stop.visited = True
        stop.visited_at = now()
        field_event(
            db,
            stop.occurrence_id,
            user,
            "visit_marked",
            {"route_id": route.id, "stop_id": stop.id},
        )
    audit(db, user, "update", "route", route_id)
    db.commit()
    return route_data(db, route)


CSV_COLUMNS = (
    "type",
    "description",
    "address",
    "latitude",
    "longitude",
    "territory",
    "status",
    "priority",
)


def mapping_token(data: bytes, mapping: dict):
    message = (
        checksum(data) + json.dumps(mapping, sort_keys=True, ensure_ascii=False)
    ).encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()


def parse_csv(data: bytes, mapping: dict | None = None):
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "CSV deve estar em UTF-8") from None
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise HTTPException(422, "CSV sem cabeçalho")
    if mapping is not None and (
        not isinstance(mapping, dict)
        or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
        )
    ):
        raise HTTPException(422, "Mapeamento inválido")
    mapping = mapping or {key: key for key in CSV_COLUMNS}
    if (
        set(mapping) != set(CSV_COLUMNS)
        or len(set(mapping.values())) != len(CSV_COLUMNS)
        or not set(mapping.values()).issubset(reader.fieldnames)
    ):
        raise HTTPException(
            422, {"required_columns": CSV_COLUMNS, "headers": reader.fieldnames}
        )
    valid, errors = [], []
    for line, row in enumerate(reader, 2):
        try:
            values = OccurrenceIn(
                **{key: row.get(mapping[key]) or None for key in CSV_COLUMNS}
            )
            valid.append(values)
        except Exception as exc:
            errors.append({"line": line, "error": str(exc)[:300]})
    return valid, errors


@app.post("/api/v1/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    mapping: str = Form(""),
    user: User = Depends(require("admin", "analyst", "manager")),
):
    data = await file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(413, "CSV excede 2 MB")
    try:
        field_mapping = json.loads(mapping) if mapping else None
    except json.JSONDecodeError:
        raise HTTPException(422, "Mapeamento inválido") from None
    valid, errors = parse_csv(data, field_mapping)
    return {
        "valid_count": len(valid),
        "errors": errors,
        "preview": [v.model_dump(mode="json") for v in valid[:10]],
        "sha256": checksum(data),
        "mapping": field_mapping or {key: key for key in CSV_COLUMNS},
        "preview_token": mapping_token(
            data, field_mapping or {key: key for key in CSV_COLUMNS}
        ),
    }


@app.post("/api/v1/import/commit")
async def import_commit(
    file: UploadFile = File(...),
    sha256: str = Form(...),
    mapping: str = Form(""),
    preview_token: str = Form(""),
    user: User = Depends(require("admin", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    data = await file.read(2_000_001)
    if checksum(data) != sha256:
        raise HTTPException(409, "Arquivo mudou após prévia")
    try:
        field_mapping = json.loads(mapping) if mapping else None
    except json.JSONDecodeError:
        raise HTTPException(422, "Mapeamento inválido") from None
    if field_mapping and not hmac.compare_digest(
        preview_token, mapping_token(data, field_mapping)
    ):
        raise HTTPException(409, "Mapeamento mudou após prévia")
    valid, errors = parse_csv(data, field_mapping)
    if errors:
        raise HTTPException(422, {"errors": errors})
    for item in valid:
        values = item.model_dump(exclude={"occurred_at"})
        score, _ = risk(item.priority, item.status, item.latitude is not None)
        o = Occurrence(
            **values, protocol="DEMO-" + uuid.uuid4().hex[:10].upper(), risk_score=score
        )
        if item.latitude is not None:
            o.geom = f"SRID=4326;POINT({item.longitude} {item.latitude})"
        db.add(o)
        db.flush()
        evaluate_quality(db, o)
    audit(db, user, "import", "occurrence", details={"count": len(valid)})
    db.commit()
    return {"imported": len(valid)}


@app.get("/api/v1/export/occurrences.csv")
def export_csv(
    user: User = Depends(require("admin", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("protocol", *CSV_COLUMNS))
    for o in db.scalars(
        select(Occurrence).where(Occurrence.deleted_at.is_(None))
    ).all():
        writer.writerow([o.protocol, *[getattr(o, k) for k in CSV_COLUMNS]])
    audit(db, user, "export", "occurrence", details={"format": "csv"})
    db.commit()
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=ocorrencias-demo.csv"},
    )


@app.get("/api/v1/export/occurrences.geojson")
def export_geojson(
    user: User = Depends(require("admin", "analyst", "manager")),
    db: Session = Depends(db_session),
):
    data = map_features(user=user, db=db)
    audit(db, user, "export", "occurrence", details={"format": "geojson"})
    db.commit()
    return Response(
        json.dumps(data, ensure_ascii=False),
        media_type="application/geo+json",
        headers={
            "Content-Disposition": "attachment; filename=ocorrencias-demo.geojson"
        },
    )


@app.get("/api/v1/reports/{kind}", response_class=HTMLResponse)
def report(
    kind: str, user: User = Depends(current_user), db: Session = Depends(db_session)
):
    if kind not in ("occurrences", "territory", "quality", "ocr", "route"):
        raise HTTPException(404, "Relatório desconhecido")
    stats = dashboard(user=user, db=db)
    values = (
        stats["by_territory"]
        if kind == "territory"
        else stats["by_status"]
        if kind == "occurrences"
        else {"achados": stats["quality_issues"]}
        if kind == "quality"
        else {"jobs": stats["ocr_jobs"]}
        if kind == "ocr"
        else {"rotas": stats["routes"]}
    )
    rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{int(v)}</td></tr>"
        for k, v in values.items()
    )
    extra = ""
    if kind == "route":
        q = select(RoutePlan).order_by(RoutePlan.created_at.desc()).limit(25)
        if user.role == "field_agent":
            q = q.where(RoutePlan.actor_id == user.id)
        routes = db.scalars(q).all()
        entries = "".join(
            f"<tr><td>{html.escape(r.name)}</td><td>{r.total_km:.2f} km</td>"
            f"<td>{len(route_data(db, r)['stops'])}</td><td>{html.escape(r.provider)}</td></tr>"
            for r in routes
        )
        extra = f"<h2>Planos recentes</h2><table><tr><th>Plano</th><th>Distância</th><th>Paradas</th><th>Mecanismo</th></tr>{entries}</table>"
    elif kind == "ocr":
        jobs = db.scalars(
            select(OCRJob).order_by(OCRJob.created_at.desc()).limit(25)
        ).all()
        entries = "".join(
            f"<tr><td>{html.escape(j.status)}</td><td>{html.escape(j.provider)}</td>"
            f"<td>{j.confidence or 0:.1f}%</td></tr>"
            for j in jobs
        )
        extra = f"<h2>Processamentos recentes</h2><table><tr><th>Status</th><th>Provider</th><th>Confiança</th></tr>{entries}</table>"
    titles = {
        "occurrences": "Ocorrências",
        "territory": "Territórios",
        "quality": "Qualidade",
        "ocr": "OCR",
        "route": "Rotas",
    }
    return f"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Relatório EDI</title><style>body{{font:16px Arial;max-width:900px;margin:48px auto;color:#17365d}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:10px;text-align:left}}h2{{margin-top:32px}}</style><h1>EDI Zoonoses — {titles[kind]}</h1><p>DADOS SINTÉTICOS / DEMONSTRAÇÃO</p><table><tr><th>Indicador</th><th>Valor</th></tr>{rows}</table>{extra}<p>Gerado em {now().isoformat()}</p></html>"


@app.get("/api/v1/analytics")
def analytics(user: User = Depends(current_user), db: Session = Depends(db_session)):
    rows = db.scalars(select(Occurrence).where(Occurrence.deleted_at.is_(None))).all()
    samples = [
        {
            "protocol": o.protocol,
            "score": o.risk_score,
            "factors": risk(o.priority, o.status, o.latitude is not None)[1],
        }
        for o in rows[:20]
    ]
    registry = db.scalars(select(ModelRegistry)).all()
    return {
        "label": "Experimental; dados sintéticos; sem validação epidemiológica",
        "samples": samples,
        "models": [
            {"name": m.name, "version": m.version, "metrics": m.metrics, "card": m.card}
            for m in registry
        ],
    }


@app.get("/api/v1/audit")
def list_audit(
    action: str = "",
    page: int = Query(1, ge=1),
    user: User = Depends(require("admin", "manager")),
    db: Session = Depends(db_session),
):
    q = select(AuditEvent)
    if action:
        q = q.where(AuditEvent.action == action)
    rows = db.scalars(
        q.order_by(AuditEvent.created_at.desc()).offset((page - 1) * 100).limit(100)
    ).all()
    return [
        {
            "actor_id": e.actor_id,
            "action": e.action,
            "entity": e.entity,
            "entity_id": e.entity_id,
            "created_at": e.created_at,
            "details": e.details,
            "request_id": e.request_id,
        }
        for e in rows
    ]


@app.get("/api/v1/admin/{kind}")
def admin_list(
    kind: str, user: User = Depends(require("admin")), db: Session = Depends(db_session)
):
    model = {
        "users": User,
        "territories": Territory,
        "types": OccurrenceType,
        "knowledge": KnowledgeItem,
        "rules": DataQualityRule,
        "settings": SystemSetting,
        "roles": RolePolicy,
    }.get(kind)
    if not model:
        raise HTTPException(404, "Catálogo desconhecido")
    rows = db.scalars(select(model)).all()
    if kind == "users":
        return [user_data(x) for x in rows]
    return [
        {
            c.name: getattr(x, c.name)
            for c in model.__table__.columns
            if c.name != "geom"
        }
        for x in rows
    ]


@app.post("/api/v1/admin/{kind}")
def admin_create(
    kind: str,
    body: dict,
    user: User = Depends(require("admin")),
    db: Session = Depends(db_session),
):
    model = {
        "users": User,
        "territories": Territory,
        "types": OccurrenceType,
        "knowledge": KnowledgeItem,
        "rules": DataQualityRule,
        "settings": SystemSetting,
    }.get(kind)
    if not model:
        raise HTTPException(404, "Catálogo desconhecido")
    allowed = {c.name for c in model.__table__.columns} - {
        "id",
        "geom",
        "password_hash",
    }
    values = {k: v for k, v in body.items() if k in allowed}
    if kind == "users":
        if body.get("role") not in (
            "admin",
            "field_agent",
            "analyst",
            "manager",
            "viewer",
        ):
            raise HTTPException(422, "Papel inválido")
        values["password_hash"] = passwords.hash(str(body.get("password", "")))
    row = model(**values)
    db.add(row)
    db.flush()
    audit(db, user, "admin_create", kind, getattr(row, "id", getattr(row, "key", None)))
    db.commit()
    return {"id": getattr(row, "id", getattr(row, "key", None))}


@app.patch("/api/v1/admin/{kind}/{item_id}")
def admin_update(
    kind: str,
    item_id: str,
    body: dict,
    user: User = Depends(require("admin")),
    db: Session = Depends(db_session),
):
    model = {
        "users": User,
        "territories": Territory,
        "types": OccurrenceType,
        "knowledge": KnowledgeItem,
        "rules": DataQualityRule,
        "settings": SystemSetting,
        "roles": RolePolicy,
    }.get(kind)
    if not model:
        raise HTTPException(404, "Catálogo desconhecido")
    row = db.get(model, item_id)
    if not row:
        raise HTTPException(404, "Item não encontrado")
    if kind == "roles":
        from .seed import ROLE_PERMISSIONS

        if item_id == "admin" and (
            body.get("active") is False or body.get("permissions") not in (None, ["*"])
        ):
            raise HTTPException(422, "O papel administrador deve permanecer ativo")
        if "permissions" in body:
            permissions = body["permissions"]
            if (
                not isinstance(permissions, list)
                or not all(isinstance(x, str) for x in permissions)
                or not set(permissions).issubset(ROLE_PERMISSIONS[item_id])
            ):
                raise HTTPException(422, "Permissões fora do perfil permitido")
            row.permissions = permissions
        if "active" in body:
            if not isinstance(body["active"], bool):
                raise HTTPException(422, "Situação inválida")
            row.active = body["active"]
        audit(db, user, "admin_update", "roles", item_id, {"fields": list(body)})
        db.commit()
        return {"ok": True}
    allowed = {c.name for c in model.__table__.columns} - {
        "id",
        "key",
        "geom",
        "password_hash",
    }
    for key, value in body.items():
        if key in allowed:
            setattr(row, key, value)
    if kind == "users" and "password" in body:
        row.password_hash = passwords.hash(str(body["password"]))
    audit(db, user, "admin_update", kind, item_id, {"fields": list(body)})
    db.commit()
    return {"ok": True}


@app.delete("/api/v1/admin/{kind}/{item_id}")
def admin_delete(
    kind: str,
    item_id: str,
    user: User = Depends(require("admin")),
    db: Session = Depends(db_session),
):
    model = {
        "types": OccurrenceType,
        "knowledge": KnowledgeItem,
        "rules": DataQualityRule,
        "settings": SystemSetting,
    }.get(kind)
    if not model:
        raise HTTPException(403, "Exclusão não permitida")
    row = db.get(model, item_id)
    if not row:
        raise HTTPException(404, "Item não encontrado")
    db.delete(row)
    audit(db, user, "admin_delete", kind, item_id)
    db.commit()
    return {"ok": True}
