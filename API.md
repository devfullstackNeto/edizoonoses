# API

OpenAPI interativo em `/docs`; esquema JSON em `/openapi.json`. Prefixo operacional `/api/v1`. Saúde: `/health/live` e `/health/ready`.

Principais recursos: `/auth/login`, `/auth/me`, `/occurrences`, `/map/features`, `/dashboard`, `/documents`, `/ocr/jobs`, `/chat/messages`, `/routes`, `/quality`, `/analytics`, `/import/preview`, `/import/commit`, `/export/occurrences.csv`, `/export/occurrences.geojson`, `/reports/{kind}`, `/audit` e `/admin/{kind}`. Listagens de ocorrências e documentos devolvem `items`, `total`, `page` e `page_size`. Erros HTTP usam o formato padrão `detail` do FastAPI.

Sprint 2: `GET /occurrences/{id}/workspace` agrega documentos, jobs OCR e auditoria; `GET /documents/{id}/preview` entrega arquivo inline após autenticação e controle de classificação; `GET /documents?occurrence_id=` filtra vínculos; `POST /ocr/jobs/{id}/review` aceita `occurrence_id` ao aprovar. Respostas de rota incluem `provider`, `geometry` em `[longitude, latitude]`, `legs_km`, `segment_km` e `visited_at`; `PATCH /routes/{id}` recalcula após reordenação. Importação aceita `mapping` JSON (campo de destino → cabeçalho de origem) nos formulários de prévia e confirmação. `GET/PATCH /admin/roles` expõe políticas dos cinco papéis seed, que podem restringir a matriz fixa. As rotas continuam sob `/api/v1`.
