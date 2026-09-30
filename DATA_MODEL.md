# Modelo de dados

Entidades centrais: `users`, `occurrences`, `occurrence_events`, `territories`, `occurrence_types`, `documents`, `ocr_jobs`, `knowledge_items`, `chat_messages`, `route_plans`, `route_stops`, `quality_rules`, `quality_issues`, `audit_events`, `system_settings` e `model_registry`. Chaves primárias são UUID em texto. Datas operacionais usam UTC. `occurrences.geom` é `POINT SRID 4326`, indexado por GIST; latitude e longitude auxiliam serialização da API. Arquivos binários residem no MinIO e são ligados pelo `object_key` e hash SHA-256.

A migração inicial está em `apps/api/alembic/versions/0001_initial.py`.

As migrações `0002_pilot.py` e `0003_roles.py` acrescentam `route_plans.provider`, `route_plans.geometry`, `route_plans.legs_km`, `route_stops.visited_at` e a tabela `role_policies` (`name`, `active`, `permissions`). `documents.occurrence_id` já existia e agora é preenchido pelo fluxo de revisão OCR; o job mantém texto bruto, campos detectados, campos revisados e confiança.
