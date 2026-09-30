# Arquitetura

O navegador usa React e envia solicitações REST para `/api/v1`. Nginx encaminha à API FastAPI. SQLAlchemy persiste domínio e auditoria no PostgreSQL; geometrias `POINT` usam PostGIS SRID 4326 com índice GIST. MinIO guarda arquivos e Redis/RQ distribui OCR para worker separado. Tesseract extrai texto e os resultados aguardam revisão humana. Leaflet e OpenStreetMap apresentam GeoJSON da API.

As integrações pagas não são necessárias. O chatbot consulta itens versionados do banco por recuperação lexical determinística e devolve fonte ou fallback. O escore operacional é demonstrativo e explicável, sem intervenção automática.

O planejamento de rota calcula a ordem por nearest-neighbor. Quando `OSRM_BASE_URL` está configurado e responde, persiste geometria GeoJSON e distâncias por ruas; em falha usa coordenadas e distâncias geodésicas locais. O plano registra mecanismo, trechos e visitas. O provider de chat compatível com OpenAI é opcional: só recebe a pergunta e o trecho recuperado da base, mantém referências locais e retorna ao provider mock quando indisponível. Políticas persistidas em `role_policies` podem revogar permissões previstas na matriz fixa de RBAC.

O bootstrap usa Alembic antes da seed idempotente. O Compose fornece healthchecks para os seis serviços. Todos os dados iniciais são sintéticos. Requisições recebem `X-Request-ID` e log estruturado sem credenciais.

## Sprint 3

Novas tabelas `field_visits`, `location_checkins` (Point SRID 4326 e índice GiST) e `visit_issues` na migração 0004. Rotas guardam partida, status, duração e geometria/trechos OSRM ou local. O geocoder possui contrato `GeocoderProvider`, busca local e adaptador Nominatim configurável. Documentos vinculam visita; jobs OCR guardam páginas, detalhes por campo e revisão. O worker lê MinIO, processa páginas com Tesseract e persiste resultados no PostgreSQL. Timeline operacional usa `occurrence_events`; auditoria usa `audit_events`.
