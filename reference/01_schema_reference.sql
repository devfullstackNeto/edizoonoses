-- EDI Zoonoses - schema reference (Codex may implement via Alembic)
CREATE EXTENSION IF NOT EXISTS postgis;
-- Core conceptual entities: users/roles, occurrences/events, territories, documents, OCR, chat, routes, DQ, audit, model registry.
-- Use UUID primary keys, timestamptz, GIST index on geography/geometry and explicit FKs.
