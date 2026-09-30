# QA Report — EDI Zoonoses, Sprint 3

Data: 29/09/2026. Ambiente: Docker Compose local, exclusivamente dados sintéticos. **Zero P0 FAIL conhecido após a última rodada de validação.**

| ID | Estado | Evidência da execução final |
|---|---|---|
| P0-BASE-01 | PASS | `pytest -q`: 17/17, incluindo testes anteriores de autenticação, RBAC, ocorrências, documentos, OCR, chatbot, qualidade, importação/exportação e rotas. |
| P0-GEO-02 | PASS | Busca local de endereço na API e Playwright; provider Nominatim mockado; correção/associação no mapa e `geocode_source` persistido em PostGIS. |
| P0-ROUTE-03 | PASS | Partida, nearest-neighbor, geometria, trechos, fallback local, OSRM mockado, reordenação, salvamento/recuperação e início/fim. `test_field.py`, `test_sprint3_unit.py`, Playwright. |
| P0-FIELD-04 | PASS | Modo Campo E2E: selecionar rota, check-in, chegada, iniciar visita, evidência, pendência, resultado, conclusão e encerramento. |
| P0-LOC-05 | PASS | Playwright concedeu geolocalização simulada no Chrome e registrou check-in; API rejeitou check-in antes/depois da rota ativa; viewer recebeu 403 no histórico. |
| P0-FENCE-06 | PASS | Distância geográfica, dentro/fora do raio, override manual com justificativa e registro de decisão/distância/raio: `test_field.py`. |
| P0-DOC-07 | PASS | Foto sintética por input com preview/refazer/confirmar no Playwright; upload autenticado ao MinIO, SHA-256 e vínculo visita/ocorrência. |
| P0-OCR-08 | PASS | Worker Redis/RQ executou Tesseract real em PNG e PDF de duas páginas; texto, páginas, confiança, campos, revisão, aprovação, vínculo e reprocessamento disponíveis. Teste PDF em `test_field.py`; Playwright aprovou campos pela UI. |
| P0-SEARCH-09 | PASS | API de documentos pesquisa nome, tags, protocolo de ocorrência e texto OCR, com filtro de classificação para viewer. |
| P0-TIMELINE-10 | PASS | Teste de integração confirma `route_planned`, `route_started`, `arrival_confirmed`, `visit_started`, `document_uploaded`, `ocr_reviewed`, `visit_completed`, `route_finished`; auditoria persiste ações. |
| P0-DASH-11 | PASS | Dashboard calcula rotas, visitas, pendências, revisitas, OCR, documentos processados, tempo médio e cobertura a partir do banco; Playwright abriu a visão. |
| P0-PRIV-12 | PASS | Check-in com finalidade e papel restrito, auditoria de leitura do histórico, sem localização em resposta pública; periódico desligado por padrão e só ativo durante rota. |
| P0-FRONT-13 | PASS | ESLint, TypeScript e Vite build sem erros; Vitest 1/1. |
| P0-E2E-14 | PASS | `npm run e2e`: 4/4 no Chrome, incluindo jornada principal e viewport móvel 390×844. |
| P0-PY-LINT-15 | PASS | `ruff check app tests` sem achados; `ruff format --check app tests`: 18 arquivos formatados. |
| P0-COMPOSE-16 | PASS | `docker compose up --build -d`; api, db, redis, minio, worker e web `healthy`. |
| P0-HEALTH-17 | PASS | `/health/ready`: `database=postgis`, `redis=ok`, `storage=ok`; Alembic `0004 (head)`; PostGIS 3.4; visitas e check-ins persistidos. |
| P0-SEC-18 | PASS | `npm audit --omit=dev --audit-level=high`: 0 vulnerabilidades; varredura `rg` em código próprio sem TODO/FIXME, chaves privadas ou padrões de token. |
| P0-FIX-19 | PASS | Quatro arquivos visuais sintéticos presentes, inclusive três tipos de formulário/imagem e PDF multipágina; seed idempotente. |

## Limites P1/P2 e condições de demonstração

- OSRM e Nominatim externo não foram configurados nesta execução. Fallback geométrico, provider mockado, busca sintética local e coordenadas manuais foram testados. O serviço público do Nominatim não vem configurado; uso externo depende de endpoint autorizado e da [política OSMF](https://operations.osmfoundation.org/policies/nominatim/).
- Geolocalização foi exercitada por permissão simulada no Chrome. Homologação em celulares reais, qualidade de câmera e rede de campo dependem de dispositivos e ambiente de piloto.
- Expurgo de check-ins vencidos ocorre na próxima gravação; uma rotina agendada deve ser implantada antes de dados reais. Credenciais demo, TLS e governança institucional precisam ser substituídos/definidos antes de qualquer uso operacional.
- Métricas e fixtures são sintéticas; não há validação epidemiológica. Os volumes Docker mantêm dados gerados pelos testes até limpeza deliberada.

Acesso local: interface `http://localhost:8090`, API `http://localhost:8010`, console MinIO `http://localhost:9001`. O roteiro recomendado de 8 minutos está em `DEMO_SCRIPT.md`; procedimento e evidências em `FIELD_OPERATIONS.md`, `OCR_PIPELINE.md` e `SPRINT3_VALIDATION.md`.
