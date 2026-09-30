# Prontidão para piloto demonstrativo — EDI Zoonoses

Data: 29/09/2026. Escopo: demonstração local com dados **100% sintéticos**. Esta avaliação não representa autorização institucional nem liberação para dados reais.

## Fluxo demonstrável

1. Entrar com uma das cinco contas demo; criar ocorrência com coordenadas.
2. Consultar mapa PostGIS/Leaflet, filtrar pontos e selecionar visitas.
3. Salvar rota nearest-neighbor, ver geometria, mecanismo e distâncias por trecho; reordenar e marcar visita. OSRM acrescenta ruas quando configurado e acessível; a rota local permanece funcional.
4. Enviar PNG/JPG/PDF; acompanhar Redis/RQ e Tesseract; abrir original, revisar texto/campos/confiança, aprovar e vincular à ocorrência. As duas fichas de demonstração estão em `apps/api/fixtures/` e na seed do repositório.
5. Consultar o documento e o histórico no detalhe da ocorrência, gerar relatório HTML e conferir auditoria.
6. Importar CSV com mapeamento e prévia assinada; exportar CSV ou GeoJSON; consultar chatbot com fonte ou fallback.

O teste `apps/web/e2e/pilot.spec.ts` percorre a jornada pelo navegador. Os testes da API verificam OCR real das duas fichas, MinIO, PostGIS, política de papel, rotas e importação.

## Verificações necessárias antes de apresentar

```sh
docker compose up --build -d
docker compose ps
docker compose exec -T api pytest -q
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
npm run e2e
```

Abra [http://localhost:8090](http://localhost:8090). O Compose deve mostrar `healthy` para web, api, db, redis, minio e worker. A API deve responder em [http://localhost:8010/health/ready](http://localhost:8010/health/ready). Consulte `QA_REPORT.md` para a execução observada nesta rodada.

## Limites de uso

- A configuração padrão usa senhas demo, HTTP local e dados sintéticos. Ela não deve receber dados pessoais ou ser exposta à internet.
- OSRM e endpoint de IA externos não foram fornecidos; os testes automatizados cobrem sucesso/falha simulados, enquanto o ambiente local foi validado com rota geodésica e provider offline. Um teste ao vivo requer as variáveis de `.env` e o smoke descrito no README.
- Rotas locais são estimativas geodésicas, não percursos de ruas. A interface identifica isso explicitamente.
- A política editável restringe os cinco papéis fixos; criação de papéis arbitrários e autorização institucional não fazem parte do piloto.
- Relatórios são HTML para impressão. PDF no servidor, telemetria centralizada, teste de carga, TLS, recuperação de desastres e homologação com operadores reais exigem uma etapa de implantação própria.

Estado: **apto para piloto técnico local e demonstração sintética**, condicionado à manutenção dos resultados de `QA_REPORT.md` após qualquer alteração.

## Sprint 3 — prontidão

Pronto para demonstração técnica local com dados sintéticos: endereço, rota, visita, geofence, evidência, OCR real em imagem/PDF, revisão e indicadores. Serviços externos OSRM/Nominatim não são pré-requisitos. Para uso institucional com pessoas ou ocorrências reais ainda são necessários governança de dados, credenciais e TLS, política automatizada de retenção, homologação em dispositivo de campo e revisão epidemiológica. Resultados verificados em `QA_REPORT.md`.
