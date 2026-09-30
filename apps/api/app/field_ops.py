"""Explicit field activity. Location is recorded only for an active route action."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import audit, db_session, distance_km, require
from .models import (
    Document,
    FieldVisit,
    LocationCheckin,
    OCRJob,
    Occurrence,
    OccurrenceEvent,
    RoutePlan,
    RouteStop,
    User,
    VisitIssue,
    now,
)
from .settings import settings

router = APIRouter(prefix="/api/v1/field", tags=["Operação de campo"])
FIELD_ROLES = ("admin", "field_agent", "manager")
OUTCOMES = (
    "conforme",
    "pendência identificada",
    "endereço divergente",
    "imóvel não encontrado",
    "sem acesso",
    "responsável ausente",
    "requer revisita",
    "encaminhado para análise",
)


@router.get("/assignees")
def list_assignees(
    user: User = Depends(require(*FIELD_ROLES)), db: Session = Depends(db_session)
):
    return [
        {"id": row.id, "name": row.name}
        for row in db.scalars(
            select(User)
            .where(User.role.in_(("field_agent", "manager")), User.active.is_(True))
            .order_by(User.name)
        ).all()
    ]


def route_for(db: Session, route_id: str, user: User) -> RoutePlan:
    route = db.get(RoutePlan, route_id)
    if not route or (user.role == "field_agent" and route.actor_id != user.id):
        raise HTTPException(404, "Rota não encontrada")
    return route


def visit_for(db: Session, visit_id: str, user: User) -> tuple[FieldVisit, RoutePlan]:
    visit = db.get(FieldVisit, visit_id)
    if not visit:
        raise HTTPException(404, "Visita não encontrada")
    return visit, route_for(db, visit.route_id, user)


def field_event(
    db: Session,
    occurrence_id: str,
    user: User,
    action: str,
    payload: dict | None = None,
):
    db.add(
        OccurrenceEvent(
            occurrence_id=occurrence_id,
            actor_id=user.id,
            action=action,
            payload=payload or {},
        )
    )
    audit(db, user, action, "occurrence", occurrence_id, payload or {})


def visit_data(db: Session, visit: FieldVisit):
    occurrence = db.get(Occurrence, visit.occurrence_id)
    issues = db.scalars(
        select(VisitIssue)
        .where(VisitIssue.visit_id == visit.id)
        .order_by(VisitIssue.created_at)
    ).all()
    docs = db.scalars(select(Document).where(Document.visit_id == visit.id)).all()
    jobs = db.scalars(select(OCRJob).where(OCRJob.visit_id == visit.id)).all()
    return {
        "id": visit.id,
        "route_id": visit.route_id,
        "stop_id": visit.stop_id,
        "occurrence_id": visit.occurrence_id,
        "protocol": occurrence.protocol,
        "address": occurrence.address,
        "latitude": occurrence.latitude,
        "longitude": occurrence.longitude,
        "territory": occurrence.territory,
        "status": visit.status,
        "outcome": visit.outcome,
        "observation": visit.observation,
        "actor_id": visit.actor_id,
        "arrived_at": visit.arrived_at,
        "started_at": visit.started_at,
        "finished_at": visit.finished_at,
        "checkin_id": visit.checkin_id,
        "issues": [issue_data(i) for i in issues],
        "documents": [{"id": d.id, "name": d.name, "mime": d.mime} for d in docs],
        "ocr_jobs": [
            {"id": j.id, "status": j.status, "document_id": j.document_id} for j in jobs
        ],
    }


def issue_data(issue: VisitIssue):
    return {
        k: getattr(issue, k)
        for k in (
            "id",
            "visit_id",
            "occurrence_id",
            "title",
            "severity",
            "status",
            "assignee_id",
            "due_at",
            "observation",
            "created_at",
            "resolved_at",
        )
    }


def checkin_data(row: LocationCheckin):
    return {
        k: getattr(row, k)
        for k in (
            "id",
            "route_id",
            "visit_id",
            "actor_id",
            "latitude",
            "longitude",
            "accuracy_m",
            "purpose",
            "distance_m",
            "radius_m",
            "decision",
            "justification",
            "created_at",
        )
    }


def route_field_data(db: Session, route: RoutePlan):
    stops = db.scalars(
        select(RouteStop)
        .where(RouteStop.route_id == route.id)
        .order_by(RouteStop.position)
    ).all()
    visits = {
        v.stop_id: v
        for v in db.scalars(
            select(FieldVisit).where(FieldVisit.route_id == route.id)
        ).all()
    }
    return {
        "id": route.id,
        "name": route.name,
        "status": route.status,
        "provider": route.provider,
        "total_km": route.total_km,
        "duration_min": route.duration_min,
        "started_at": route.started_at,
        "finished_at": route.finished_at,
        "start_latitude": route.start_latitude,
        "start_longitude": route.start_longitude,
        "visits": [visit_data(db, visits[s.id]) for s in stops if s.id in visits],
        "stops": [
            {
                "id": s.id,
                "occurrence_id": s.occurrence_id,
                "position": s.position,
                "visited": s.visited,
            }
            for s in stops
        ],
    }


def coordinates(body: dict, required: bool = True):
    lat, lon = body.get("latitude"), body.get("longitude")
    if lat is None or lon is None:
        if required:
            raise HTTPException(422, "Informe latitude e longitude")
        return None
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        raise HTTPException(422, "Coordenadas inválidas") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(422, "Coordenadas fora da faixa")
    return lat, lon


def add_checkin(
    db: Session,
    route: RoutePlan,
    user: User,
    body: dict,
    purpose: str,
    visit: FieldVisit | None = None,
    distance_m: float | None = None,
    radius_m: float | None = None,
    decision: str = "recorded",
    required: bool = True,
):
    position = coordinates(body, required=required)
    accuracy = body.get("accuracy_m")
    if accuracy is not None:
        try:
            accuracy = float(accuracy)
        except (TypeError, ValueError):
            raise HTTPException(422, "Precisão inválida") from None
        if accuracy < 0 or accuracy > 100000:
            raise HTTPException(422, "Precisão inválida")
    row = LocationCheckin(
        route_id=route.id,
        visit_id=visit.id if visit else None,
        actor_id=user.id,
        latitude=position[0] if position else None,
        longitude=position[1] if position else None,
        accuracy_m=accuracy,
        purpose=purpose,
        distance_m=distance_m,
        radius_m=radius_m,
        decision=decision,
        justification=str(body.get("justification", ""))[:500],
    )
    if position:
        row.geom = f"SRID=4326;POINT({position[1]} {position[0]})"
    db.add(row)
    db.flush()
    audit(
        db,
        user,
        "checkin",
        "route",
        route.id,
        {"checkin_id": row.id, "purpose": purpose, "decision": decision},
    )
    cutoff = now() - timedelta(days=max(1, settings.location_retention_days))
    old = db.scalars(
        select(LocationCheckin).where(LocationCheckin.created_at < cutoff)
    ).all()
    for item in old:
        db.delete(item)
    return row


@router.get("/routes")
def list_field_routes(
    user: User = Depends(require(*FIELD_ROLES)), db: Session = Depends(db_session)
):
    q = select(RoutePlan)
    if user.role == "field_agent":
        q = q.where(RoutePlan.actor_id == user.id)
    routes = db.scalars(q.order_by(RoutePlan.created_at.desc()).limit(100)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "status": r.status,
            "total_km": r.total_km,
            "provider": r.provider,
        }
        for r in routes
    ]


@router.get("/routes/{route_id}")
def get_field_route(
    route_id: str,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    return route_field_data(db, route_for(db, route_id, user))


@router.post("/routes/{route_id}/start")
def start_route(
    route_id: str,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    route = route_for(db, route_id, user)
    if route.status != "planned":
        raise HTTPException(409, "Rota já iniciada ou encerrada")
    route.status, route.started_at = "active", now()
    stops = db.scalars(select(RouteStop).where(RouteStop.route_id == route.id)).all()
    for stop in stops:
        if not db.scalar(select(FieldVisit).where(FieldVisit.stop_id == stop.id)):
            db.add(
                FieldVisit(
                    route_id=route.id,
                    stop_id=stop.id,
                    occurrence_id=stop.occurrence_id,
                    actor_id=route.actor_id,
                )
            )
        field_event(
            db, stop.occurrence_id, user, "route_started", {"route_id": route.id}
        )
    audit(db, user, "route_started", "route", route.id)
    db.commit()
    return route_field_data(db, route)


@router.post("/routes/{route_id}/finish")
def finish_route(
    route_id: str,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    route = route_for(db, route_id, user)
    if route.status != "active":
        raise HTTPException(409, "Rota não está em execução")
    route.status, route.finished_at = "finished", now()
    for visit in db.scalars(
        select(FieldVisit).where(FieldVisit.route_id == route.id)
    ).all():
        field_event(
            db,
            visit.occurrence_id,
            user,
            "route_finished",
            {"route_id": route.id, "visit_status": visit.status},
        )
    audit(db, user, "route_finished", "route", route.id)
    db.commit()
    return route_field_data(db, route)


@router.post("/routes/{route_id}/checkins")
def route_checkin(
    route_id: str,
    body: dict,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    route = route_for(db, route_id, user)
    if route.status != "active":
        raise HTTPException(409, "Check-in exige rota ativa")
    purpose = body.get("purpose", "checkin")
    if purpose not in ("checkin", "periodic"):
        raise HTTPException(422, "Finalidade inválida")
    visit = None
    if body.get("visit_id"):
        visit, parent = visit_for(db, body["visit_id"], user)
        if parent.id != route.id:
            raise HTTPException(422, "Visita fora da rota")
    row = add_checkin(db, route, user, body, purpose, visit)
    db.commit()
    return checkin_data(row)


@router.get("/routes/{route_id}/checkins")
def route_checkins(
    route_id: str,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    route = route_for(db, route_id, user)
    rows = db.scalars(
        select(LocationCheckin)
        .where(LocationCheckin.route_id == route.id)
        .order_by(LocationCheckin.created_at.desc())
        .limit(100)
    ).all()
    audit(db, user, "location_history_read", "route", route.id)
    db.commit()
    return [checkin_data(row) for row in rows]


@router.post("/visits/{visit_id}/arrive")
def arrive(
    visit_id: str,
    body: dict,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    visit, route = visit_for(db, visit_id, user)
    if route.status != "active" or visit.status not in ("pending", "arrived"):
        raise HTTPException(409, "Visita não aceita chegada neste estado")
    target = db.get(Occurrence, visit.occurrence_id)
    try:
        radius = float(body.get("radius_m", settings.geofence_radius_m))
    except (TypeError, ValueError):
        raise HTTPException(422, "Raio inválido") from None
    if not 25 <= radius <= 1000:
        raise HTTPException(422, "Raio deve estar entre 25 e 1000 m")
    position = coordinates(body, required=False)
    distance = (
        round(distance_km(position, (target.latitude, target.longitude)) * 1000, 1)
        if position and target.latitude is not None
        else None
    )
    inside = distance is not None and distance <= radius
    override = body.get("manual_override") is True
    justification = str(body.get("justification", "")).strip()
    if not inside and override and len(justification) < 8:
        raise HTTPException(422, "Justifique a confirmação manual")
    decision = "inside" if inside else "override" if override else "outside"
    row = add_checkin(
        db,
        route,
        user,
        body,
        "arrival",
        visit,
        distance,
        radius,
        decision,
        required=False,
    )
    if inside or override:
        visit.status, visit.arrived_at, visit.checkin_id = "arrived", now(), row.id
        field_event(
            db,
            visit.occurrence_id,
            user,
            "arrival_confirmed" if inside else "arrival_override",
            {
                "visit_id": visit.id,
                "distance_m": distance,
                "radius_m": radius,
                "decision": decision,
            },
        )
    else:
        field_event(
            db,
            visit.occurrence_id,
            user,
            "arrival_outside",
            {"visit_id": visit.id, "distance_m": distance, "radius_m": radius},
        )
    db.commit()
    return {"checkin": checkin_data(row), "visit": visit_data(db, visit)}


@router.post("/visits/{visit_id}/start")
def start_visit(
    visit_id: str,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    visit, route = visit_for(db, visit_id, user)
    if route.status != "active" or visit.status != "arrived":
        raise HTTPException(409, "Confirme a chegada antes de iniciar a visita")
    visit.status, visit.started_at = "in_progress", now()
    field_event(db, visit.occurrence_id, user, "visit_started", {"visit_id": visit.id})
    db.commit()
    return visit_data(db, visit)


@router.post("/visits/{visit_id}/finish")
def finish_visit(
    visit_id: str,
    body: dict,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    visit, route = visit_for(db, visit_id, user)
    if route.status != "active" or visit.status != "in_progress":
        raise HTTPException(409, "Visita não está em andamento")
    if body.get("outcome") not in OUTCOMES:
        raise HTTPException(422, "Resultado inválido")
    visit.status, visit.outcome, visit.finished_at = "completed", body["outcome"], now()
    visit.observation = str(body.get("observation", ""))[:3000]
    stop = db.get(RouteStop, visit.stop_id)
    stop.visited, stop.visited_at = True, visit.finished_at
    field_event(
        db,
        visit.occurrence_id,
        user,
        "visit_completed",
        {"visit_id": visit.id, "outcome": visit.outcome},
    )
    db.commit()
    return visit_data(db, visit)


@router.post("/visits/{visit_id}/issues", status_code=201)
def create_issue(
    visit_id: str,
    body: dict,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    visit, route = visit_for(db, visit_id, user)
    if route.status != "active" or visit.status != "in_progress":
        raise HTTPException(409, "Pendência exige visita em andamento")
    title = str(body.get("title", "")).strip()
    if len(title) < 5:
        raise HTTPException(422, "Descreva a pendência")
    severity = body.get("severity", "Média")
    if severity not in ("Baixa", "Média", "Alta", "Crítica"):
        raise HTTPException(422, "Severidade inválida")
    due = None
    if body.get("due_at"):
        try:
            due = datetime.fromisoformat(body["due_at"].replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise HTTPException(422, "Prazo inválido") from None
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
    assignee = body.get("assignee_id") or None
    if assignee and not db.get(User, assignee):
        raise HTTPException(422, "Responsável inválido")
    issue = VisitIssue(
        visit_id=visit.id,
        occurrence_id=visit.occurrence_id,
        title=title[:180],
        severity=severity,
        due_at=due,
        assignee_id=assignee,
        observation=str(body.get("observation", ""))[:2000],
    )
    db.add(issue)
    db.flush()
    field_event(
        db,
        visit.occurrence_id,
        user,
        "visit_issue_created",
        {"visit_id": visit.id, "issue_id": issue.id, "severity": severity},
    )
    db.commit()
    return issue_data(issue)


@router.patch("/issues/{issue_id}")
def update_issue(
    issue_id: str,
    body: dict,
    user: User = Depends(require(*FIELD_ROLES)),
    db: Session = Depends(db_session),
):
    issue = db.get(VisitIssue, issue_id)
    if not issue:
        raise HTTPException(404, "Pendência não encontrada")
    visit, _ = visit_for(db, issue.visit_id, user)
    if body.get("status") not in ("open", "in_progress", "resolved"):
        raise HTTPException(422, "Status inválido")
    issue.status = body["status"]
    issue.resolved_at = now() if issue.status == "resolved" else None
    field_event(
        db,
        visit.occurrence_id,
        user,
        "visit_issue_updated",
        {"issue_id": issue.id, "status": issue.status},
    )
    db.commit()
    return issue_data(issue)
