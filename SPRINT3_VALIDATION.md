# Validação Sprint 3

Execute no diretório raiz:

```powershell
docker compose up --build -d
docker compose ps
docker compose exec -T api sh -c 'ruff check app tests && ruff format --check app tests && pytest -q'
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
npm run e2e
```

O teste de integração percorre ocorrência, geocodificação local, rota com partida, check-in bloqueado antes/depois da rota ativa, geofence dentro/fora, pendência, PDF de duas páginas, OCR real, revisão e timeline. O Playwright percorre a apresentação pela interface, incluindo viewport móvel em `smoke.spec.ts`. O Compose exige seis serviços saudáveis: db/PostGIS, redis, minio, api, worker e web. Consulte `QA_REPORT.md` para resultados reais da última execução e limites.

Não se deve usar informações pessoais nem interpretar os indicadores como validação epidemiológica. Nominatim externo e OSRM são integrações opcionais; o piloto local permanece funcional sem eles.

## Resultado observado em 29/09/2026

`ruff check`: PASS; `ruff format --check`: PASS (18 arquivos); `pytest`: 17/17; Vitest: 1/1; ESLint: PASS; TypeScript: PASS; Vite build: PASS; Playwright Chrome: 4/4, inclusive Geolocation API simulada e OCR real; Compose: 6/6 serviços saudáveis; Alembic: 0004 (head); `/health/ready`: PostGIS, Redis e storage OK; `npm audit --omit=dev`: 0 vulnerabilidades. A busca por TODO/FIXME, chave privada e padrão de token no código próprio não retornou correspondências. Consulte `QA_REPORT.md` para matriz P0 e limites.
