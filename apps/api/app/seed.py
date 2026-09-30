import random
from pathlib import Path
from datetime import timedelta
from sqlalchemy import select
from .core import SessionLocal, passwords, ensure_bucket, s3, checksum
from .models import (
    DataQualityRule,
    Document,
    KnowledgeItem,
    ModelRegistry,
    Occurrence,
    OccurrenceEvent,
    OccurrenceType,
    RoutePlan,
    RolePolicy,
    RouteStop,
    SystemSetting,
    Territory,
    User,
    now,
)
from .settings import settings

USERS = [
    ("Administrador Demo", "admin@demo.local", "admin"),
    ("Agente Demo", "campo@demo.local", "field_agent"),
    ("Analista Demo", "analista@demo.local", "analyst"),
    ("Gestor Demo", "gestor@demo.local", "manager"),
    ("Consulta Demo", "viewer@demo.local", "viewer"),
]
ROLE_PERMISSIONS = {
    "admin": ["*"],
    "field_agent": [
        "occurrences:write",
        "documents:write",
        "ocr:write",
        "routes:write",
        "field:write",
    ],
    "analyst": [
        "occurrences:write",
        "documents:write",
        "ocr:write",
        "imports:write",
        "exports:read",
        "quality:write",
    ],
    "manager": [
        "occurrences:write",
        "documents:write",
        "ocr:write",
        "routes:write",
        "field:write",
        "imports:write",
        "exports:read",
        "quality:write",
        "audit:read",
    ],
    "viewer": [],
}
TYPES = ["Morcego", "Escorpião", "Roedor", "Animal sinantrópico"]
TERRITORIES = ["Centro Demo", "Norte Demo", "Sul Demo", "Leste Demo", "Oeste Demo"]
TOPICS = [
    (
        "Morcegos",
        "Evite contato direto com morcegos. Isole a área e procure orientação pelos canais oficiais vigentes.",
    ),
    (
        "Escorpiões",
        "Evite manipular escorpiões. Em caso de picada, procure atendimento de saúde.",
    ),
    (
        "Roedores",
        "Reduza acesso a alimento, água e abrigo. Registre a ocorrência para avaliação.",
    ),
    (
        "Animais sinantrópicos",
        "O manejo depende da espécie e do contexto. Registre uma ocorrência para avaliação da equipe.",
    ),
    (
        "Registrar ocorrência",
        "Abra Ocorrências, selecione Nova ocorrência e preencha tipo, território e descrição.",
    ),
    (
        "Consultar protocolo",
        "Use a busca em Ocorrências para localizar um protocolo demonstrativo.",
    ),
    (
        "Mapa",
        "O mapa mostra ocorrências com coordenadas, filtros e detalhes autorizados.",
    ),
    (
        "Rota de campo",
        "Selecione ocorrências com coordenadas e gere uma sequência de visitas no módulo Rotas.",
    ),
    (
        "OCR",
        "O OCR extrai texto de um documento; os campos precisam de revisão humana antes de aprovação.",
    ),
    (
        "Revisão documental",
        "Confira o texto original e corrija os campos sugeridos antes de aprovar.",
    ),
    (
        "Repositório",
        "O repositório guarda arquivos e metadados de acordo com a classificação de acesso.",
    ),
    (
        "Classificação",
        "Documentos Públicos podem ser lidos por todos os perfis autenticados; documentos Internos e Restritos exigem perfil operacional.",
    ),
    (
        "Qualidade de dados",
        "O painel de qualidade mostra inconsistências que precisam de correção ou justificativa.",
    ),
    (
        "Dados sintéticos",
        "Todos os registros deste ambiente são sintéticos e destinados somente à demonstração.",
    ),
    (
        "Prioridade",
        "A prioridade operacional é uma classificação assistiva e deve ser revisada por profissional responsável.",
    ),
    (
        "Risk score",
        "O escore demonstrativo soma pesos de prioridade, pendência, coordenada ausente e tempo. Não é modelo epidemiológico validado.",
    ),
    (
        "Dashboard",
        "Os indicadores do dashboard são calculados a partir dos registros armazenados no banco.",
    ),
    (
        "Exportação",
        "Analistas e gestores podem exportar ocorrências sintéticas em CSV ou GeoJSON.",
    ),
    (
        "Importação",
        "A importação CSV mostra prévia e erros por linha antes da confirmação.",
    ),
    ("Auditoria", "A auditoria registra ações críticas com ator, entidade e horário."),
    (
        "Privacidade",
        "Use somente dados sintéticos neste ambiente de demonstração. A operação real depende de governança institucional.",
    ),
    (
        "Atendimento humano",
        "Consulte os canais institucionais oficiais vigentes. Este demonstrador não publica contatos não verificados.",
    ),
]
RULES = [
    ("NO_COORD", "Ocorrência sem coordenadas", "Alta"),
    ("SHORT_ADDRESS", "Endereço incompleto", "Média"),
    ("NO_TERRITORY", "Território ausente", "Alta"),
    ("FUTURE_DATE", "Data futura", "Alta"),
    ("HIGH_UNASSIGNED", "Risco alto sem responsável", "Alta"),
]


def seed():
    random.seed(2026)
    with SessionLocal() as db:
        for name, permissions in ROLE_PERMISSIONS.items():
            if not db.get(RolePolicy, name):
                db.add(RolePolicy(name=name, permissions=permissions, active=True))
        for name, email, role in USERS:
            if not db.scalar(select(User).where(User.email == email)):
                db.add(
                    User(
                        name=name,
                        email=email,
                        role=role,
                        password_hash=passwords.hash(settings.demo_password),
                    )
                )
        for name in TYPES:
            if not db.scalar(select(OccurrenceType).where(OccurrenceType.name == name)):
                db.add(OccurrenceType(name=name))
        for name in TERRITORIES:
            territory = db.scalar(select(Territory).where(Territory.name == name))
            if not territory:
                territory = Territory(name=name)
                db.add(territory)
            index = TERRITORIES.index(name)
            lon = -56.09 + (index % 3 - 1) * 0.06
            lat = -15.58 + (index // 3 - 0.5) * 0.06
            territory.geom = f"SRID=4326;POLYGON(({lon-0.03} {lat-0.03},{lon+0.03} {lat-0.03},{lon+0.03} {lat+0.03},{lon-0.03} {lat+0.03},{lon-0.03} {lat-0.03}))"
        for code, description, severity in RULES:
            if not db.scalar(
                select(DataQualityRule).where(DataQualityRule.code == code)
            ):
                db.add(
                    DataQualityRule(
                        code=code, description=description, severity=severity
                    )
                )
        for title, body in TOPICS:
            if not db.scalar(select(KnowledgeItem).where(KnowledgeItem.title == title)):
                db.add(
                    KnowledgeItem(
                        title=title,
                        body=body,
                        source="Base demonstrativa EDI, versão 1",
                        tags=[title.lower()],
                        version="1",
                    )
                )
        if not db.scalar(select(SystemSetting).where(SystemSetting.key == "demo_mode")):
            db.add(SystemSetting(key="demo_mode", value={"enabled": True}))
        if not db.scalar(
            select(ModelRegistry).where(ModelRegistry.name == "RiskScoreDemo")
        ):
            db.add(
                ModelRegistry(
                    name="RiskScoreDemo",
                    version="1",
                    metrics={"evaluation": "rule-based; no epidemiological validation"},
                    card="Escala 0-100; soma de pesos explicáveis. Uso exclusivo em dados sintéticos para demonstração. Proibido como decisão clínica ou epidemiológica.",
                )
            )
        db.commit()
        agent = db.scalar(select(User).where(User.role == "field_agent"))
        if not db.scalar(select(Occurrence).limit(1)):
            for n in range(50):
                lat = -15.58 + random.uniform(-0.06, 0.06)
                lon = -56.09 + random.uniform(-0.06, 0.06)
                priority = ["Baixa", "Média", "Alta", "Crítica"][n % 4]
                status = ["Pendente", "Em análise", "Em campo", "Concluída"][n % 4]
                score = {"Baixa": 15, "Média": 40, "Alta": 65, "Crítica": 80}[
                    priority
                ] + (10 if status != "Concluída" else 0)
                opened = now() - timedelta(days=n * 3 + 1)
                o = Occurrence(
                    protocol=f"DEMO-2026-{n+1:04d}",
                    type=TYPES[n % 4],
                    description=f"Registro sintético de {TYPES[n % 4].lower()} para demonstração {n+1}.",
                    address=f"Rua Sintética {n+1}, {100+n}",
                    latitude=lat,
                    longitude=lon,
                    geom=f"SRID=4326;POINT({lon} {lat})",
                    territory=TERRITORIES[n % 5],
                    status=status,
                    priority=priority,
                    risk_score=score,
                    occurred_at=opened,
                    created_at=opened,
                    closed_at=opened + timedelta(days=2)
                    if status == "Concluída"
                    else None,
                    assigned_to=agent.id if n % 2 == 0 else None,
                    source="seed-demo",
                )
                db.add(o)
                db.flush()
                db.add(
                    OccurrenceEvent(
                        occurrence_id=o.id, action="seed", payload={"synthetic": True}
                    )
                )
            db.commit()
        if not db.scalar(select(RoutePlan).limit(1)):
            points = db.scalars(
                select(Occurrence).where(Occurrence.assigned_to == agent.id).limit(3)
            ).all()
            from .routing import calculate_route

            route = RoutePlan(
                name="Rota sintética inicial",
                actor_id=agent.id,
                **calculate_route(points),
            )
            db.add(route)
            db.flush()
            for n, o in enumerate(points, 1):
                db.add(RouteStop(route_id=route.id, occurrence_id=o.id, position=n))
            db.commit()
        ensure_bucket()
        fixture_dir = Path(__file__).resolve().parent.parent / "fixtures"
        for n in range(10):
            name = (
                f"formulario-demo-{n+1:02d}.png"
                if n < 2
                else f"nota-sintetica-{n+1:02d}.txt"
            )
            if db.scalar(select(Document).where(Document.name == name)):
                continue
            data = (
                (fixture_dir / f"formulario_demo_{n+1}.png").read_bytes()
                if n < 2
                else f"Documento sintético de demonstração {n+1}. Nenhum dado real.\n".encode()
            )
            mime = "image/png" if n < 2 else "text/plain"
            key = f"seed/{name}"
            s3().put_object(
                Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=mime
            )
            db.add(
                Document(
                    name=name,
                    mime=mime,
                    size=len(data),
                    sha256=checksum(data),
                    object_key=key,
                    classification="Interno",
                    tags=["demo", "sintetico"],
                )
            )
        for name in (
            "ficha_atendimento_sintetica.png",
            "vistoria_sintetica.png",
            "relatorio_visita_sintetico.png",
            "dossie_visita_sintetico.pdf",
        ):
            if db.scalar(select(Document).where(Document.name == name)):
                continue
            data = (fixture_dir / name).read_bytes()
            key = f"seed/{name}"
            mime = "application/pdf" if name.endswith(".pdf") else "image/png"
            s3().put_object(
                Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=mime
            )
            db.add(
                Document(
                    name=name,
                    mime=mime,
                    size=len(data),
                    sha256=checksum(data),
                    object_key=key,
                    classification="Interno",
                    tags=["demo", "ocr", "sintetico"],
                )
            )
        db.commit()


if __name__ == "__main__":
    seed()
