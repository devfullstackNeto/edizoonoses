# Plano de implementação — EDI Zoonoses

1. Preservar `baseline/` como referência e montar monorepo com API FastAPI, web React/TypeScript, worker Python e Compose.
2. Criar modelo PostgreSQL/PostGIS, migração inicial e seed idempotente exclusivamente sintética.
3. Implementar autenticação JWT, RBAC no servidor, auditoria e CRUD integrado de ocorrências.
4. Integrar GIS, rotas, documentos MinIO, OCR Tesseract via Redis, chatbot com fontes, qualidade, indicadores, importação/exportação e administração.
5. Construir interface responsiva que consome a API, mantendo identidade azul institucional e aviso permanente de demonstração.
6. Executar testes de backend, frontend e E2E, lint, typecheck, build e Compose; corrigir falhas e documentar evidências em `QA_REPORT.md`.

O demonstrador original e os documentos em `context/`, `docs/` e `reference/` permanecem como referência. Nenhum dado operacional ou epidemiológico real será incluído.

## Sprint 2 — executada

1. Persistir geometria e trechos de rotas, com OSRM opcional e fallback local; conectar seleção de mapa/lista ao plano de campo.
2. Integrar upload, prévia, OCR real, revisão e vínculo com ocorrência; acrescentar duas fichas sintéticas visuais.
3. Ampliar dashboard, GIS, detalhe, repositório, relatório, CSV mapeável e políticas de RBAC; manter provider offline e permitir endpoint de IA opcional.
4. Testar backend, browser, lint, typecheck, build, backup/restore e Compose; registrar resultados em `QA_REPORT.md` e limites em `PILOT_READINESS.md`.

## Sprint 3 — execução contínua

Implementação incremental sobre a arquitetura existente: migração 0004, APIs de geocodificação/rota/campo, worker OCR multipágina, telas de mapa/rota/campo/revisão, fixtures sintéticas, testes e documentação. Verifique a matriz de aceite e evidências finais em `QA_REPORT.md` e `SPRINT3_VALIDATION.md`.
