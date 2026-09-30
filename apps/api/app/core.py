import hashlib
import math
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from .models import AuditEvent, RolePolicy, User
from .settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


def db_session():
    with SessionLocal() as db:
        yield db


def token_for(user: User):
    return jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(db_session),
):
    if not credentials:
        raise HTTPException(401, "Autenticação necessária")
    try:
        user_id = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=["HS256"]
        )["sub"]
    except (JWTError, KeyError):
        raise HTTPException(401, "Sessão inválida ou expirada") from None
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(401, "Usuário inativo")
    policy = db.get(RolePolicy, user.role)
    if policy and not policy.active:
        raise HTTPException(403, "Papel inativo")
    return user


def capability_for(path: str):
    for prefix, name in (
        ("/api/v1/occurrences", "occurrences:write"),
        ("/api/v1/documents", "documents:write"),
        ("/api/v1/ocr", "ocr:write"),
        ("/api/v1/routes", "routes:write"),
        ("/api/v1/import", "imports:write"),
        ("/api/v1/export", "exports:read"),
        ("/api/v1/quality", "quality:write"),
        ("/api/v1/field", "field:write"),
        ("/api/v1/audit", "audit:read"),
        ("/api/v1/admin", "admin:write"),
    ):
        if path.startswith(prefix):
            return name
    return None


def require(*roles):
    def dependency(
        request: Request,
        user: User = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        if user.role not in roles:
            raise HTTPException(403, "Permissão insuficiente")
        policy = db.get(RolePolicy, user.role)
        capability = capability_for(request.url.path)
        if (
            policy
            and capability
            and "*" not in policy.permissions
            and capability not in policy.permissions
        ):
            raise HTTPException(403, "Permissão do papel revogada")
        return user

    return dependency


def audit(
    db: Session,
    user: User | None,
    action: str,
    entity: str,
    entity_id: str | None = None,
    details: dict | None = None,
    request_id: str | None = None,
):
    db.add(
        AuditEvent(
            actor_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details or {},
            request_id=request_id,
        )
    )


def risk(priority: str, status: str, has_coordinates: bool, days_open: int = 0):
    factors = {
        "prioridade": {"Baixa": 15, "Média": 40, "Alta": 65, "Crítica": 80}.get(
            priority, 35
        ),
        "pendência": 10 if status != "Concluída" else 0,
        "sem_coordenada": 5 if not has_coordinates else 0,
        "tempo": min(5, max(0, days_open // 7)),
    }
    return min(100, sum(factors.values())), factors


def distance_km(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def nearest_neighbor(points, start=None):
    if not points:
        return [], 0.0
    remaining = list(points)
    if start:
        first = min(
            remaining, key=lambda p: distance_km(start, (p.latitude, p.longitude))
        )
        remaining.remove(first)
        ordered = [first]
        total = distance_km(start, (first.latitude, first.longitude))
    else:
        ordered = [remaining.pop(0)]
        total = 0.0
    while remaining:
        last = ordered[-1]
        candidate = min(
            remaining,
            key=lambda p: distance_km(
                (last.latitude, last.longitude), (p.latitude, p.longitude)
            ),
        )
        total += distance_km(
            (last.latitude, last.longitude), (candidate.latitude, candidate.longitude)
        )
        ordered.append(candidate)
        remaining.remove(candidate)
    return ordered, round(total, 2)


@lru_cache
def s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


def ensure_bucket():
    try:
        s3().head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        s3().create_bucket(Bucket=settings.s3_bucket)


def checksum(data: bytes):
    return hashlib.sha256(data).hexdigest()


def norm(value: str):
    import unicodedata

    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            unicodedata.normalize("NFKD", value.lower())
            .encode("ascii", "ignore")
            .decode(),
        )
    )
