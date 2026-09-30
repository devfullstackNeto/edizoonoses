# Testes

Execute `docker compose exec -T api pytest -q`, `npm test`, `npm run lint`, `npm run typecheck`, `npm run build` em `apps/web` e `npm run e2e` com navegador Playwright. A suíte API cobre autenticação, RBAC, CRUD, PostGIS/GeoJSON, documento/MinIO, OCR/worker, chatbot, qualidade, importação, exportação e auditoria. O E2E cobre login, navegação e viewport móvel.

Os testes de API usam os serviços e dados sintéticos do Compose e podem deixar registros de teste no banco local. A Sprint 2 inclui testes reais das duas fichas via Redis/worker/Tesseract, prévia autenticada, vínculo OCR, distâncias por trecho, fallback/retorno OSRM, mapeamento CSV, RBAC de papel e provider opcional simulado. O Playwright inclui a jornada completa de criação, OCR, mapa, rota, relatório e auditoria. Veja evidência e limitações em `QA_REPORT.md`.
