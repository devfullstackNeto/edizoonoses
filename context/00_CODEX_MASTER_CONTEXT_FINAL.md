# CODEX MASTER CONTEXT - EDI ZOONOSES - IMPLEMENTAÇÃO FINAL EM UMA RODADA

## 0. MISSÃO
Você está recebendo um MVP V2 de demonstração e documentação completa de um projeto de pesquisa do IFMT. Sua missão é transformar **este repositório** em uma **versão final funcional, localmente executável, testada e demonstrável** do Ecossistema Digital Integrado (EDI) para Vigilância em Zoonoses.

Não produza apenas mockups. Não pare em planejamento. Implemente, rode, teste, corrija e documente.

## 1. REGRAS INEGOCIÁVEIS
1. Preserve todas as funcionalidades do MVP V2 e expanda-as.
2. Dados seed devem ser exclusivamente sintéticos e marcados como DEMO.
3. Não invente contatos institucionais, credenciais, URLs privadas, aceite, métricas de usuários ou dados epidemiológicos reais.
4. Nenhuma IA pode tomar decisão crítica automaticamente. OCR e risk score são assistivos.
5. O chatbot deve preferir “não sei/fallback” a inventar. Deve mostrar fonte da base de conhecimento.
6. Não deixar TODO/FIXME em fluxo crítico.
7. Não exigir serviço pago para rodar a demo básica. Providers externos devem ser opcionais por interface/configuração.
8. Faça QA antes de encerrar: testes, lint, typecheck, build e smoke test.

## 2. ARQUITETURA OBRIGATÓRIA
Monorepo simples:
```
/apps/web        React + TypeScript + Vite
/apps/api        FastAPI + Python
/worker          jobs assíncronos
/infra           docker-compose, scripts
/docs            arquitetura, ADR, OpenAPI, model cards
```
Banco: PostgreSQL + PostGIS.
Storage: MinIO (S3-compatible) para demo.
Fila/cache: Redis.
ORM/migrations: SQLAlchemy + Alembic (ou SQLModel, mantendo migrations).
Mapas: Leaflet + OpenStreetMap.
OCR: Tesseract local por padrão; criar interface para PaddleOCR/provider futuro.
Chatbot: modo gratuito/local baseado em base de conhecimento + retrieval lexical/embedding opcional. Se provider LLM não estiver configurado, o sistema continua funcional via FAQ/RAG determinístico.
Auth: JWT/session segura, bcrypt/argon2, RBAC.

## 3. MÓDULOS A IMPLEMENTAR COMPLETAMENTE
### 3.1 IAM
- login/logout
- seed admin demonstrativo documentado no README
- usuários ativos/inativos
- papéis: ADMIN, GESTOR, ADMINISTRATIVO, CAMPO, ANALISTA, AUDITOR
- permissions backend-enforced
- tela de usuários/papéis

### 3.2 Ocorrências
- CRUD real
- protocolo único gerado pelo backend
- tipo, status, prioridade, risk score, descrição, datas
- endereço + lat/lon + geometry PostGIS
- setor/território
- atribuição de responsável
- tags
- histórico/eventos
- anexos
- busca, filtros, ordenação e paginação
- detalhe com timeline

### 3.3 Mapa / GIS
- Leaflet OSM
- endpoint GeoJSON
- marker clustering
- heatmap ou camada de densidade
- filtros sincronizados
- legenda
- popup/drawer de detalhe
- territórios sintéticos (GeoJSON seed)
- opção exportar GeoJSON
- nunca exibir coordenada sensível em modo público; arquitetura para agregação/jitter

### 3.4 Croqui e Rotas
- selecionar ocorrências/pontos
- planejar rota
- algoritmo simples nearest-neighbor como fallback local
- provider interface para OSRM (opcional)
- salvar RoutePlan/RouteStops
- distância/tempo estimado
- ordenar por risco/prioridade opcional

### 3.5 Dashboard
Todos KPIs derivados do banco, nunca hardcoded:
- total, abertas, concluídas, SLA, risco alto
- por tipo/status/setor/prioridade
- série temporal
- qualidade de dados
- documentos/OCR jobs
- chatbot/fallback
- comparação de período
- drill-down para ocorrência

### 3.6 OCR / Document AI
Pipeline real:
- upload para MinIO
- job assíncrono
- Tesseract local
- armazenar raw_text
- parser de campos para um formulário sintético de exemplo
- confidence por campo quando disponível/heurística documentada
- tela side-by-side: documento + campos
- edição humana
- salvar valor original e revisado
- aprovar/rejeitar
- vincular a ocorrência
- fixtures de imagem/PDF sintético no repo
- métricas: tempo, campos revisados, confidence

### 3.7 Repositório eletrônico
- upload/download real
- metadados: nome, tipo, classificação, tags, origem, retenção
- SHA-256 calculado no backend
- busca textual/metadados
- vínculo genérico com ocorrência/OCR
- versionamento básico ou histórico de substituição
- autorização para download

### 3.8 Chatbot / Assistente
- base de conhecimento seed em Markdown/JSON com 20+ itens sintéticos/institucionais genéricos, sem inventar telefone/endereço
- cada item: título, corpo, fonte, versão, validade, tags
- retrieval determinístico (FTS/trigram/embedding opcional)
- resposta com fontes
- classificar intenção
- fallback explícito
- botão “encaminhar para atendimento humano” (gera ticket demo, não envia mensagem externa)
- registrar sessão/mensagens/feedback
- proteção contra prompt injection se LLM opcional estiver ativo
- analytics de intenção/fallback

### 3.9 Qualidade de Dados
- rules engine simples
- regras seed: obrigatórios, range, geocoordenada, data futura, duplicidade aproximada, risco alto sem responsável
- DataQualityIssue persistente
- painel com score e issues
- corrigir/dispensar issue com justificativa

### 3.10 Analytics / IA
- implementar **baseline demonstrativo**, não modelo clínico/epidemiológico oficial
- risk score explicável por regra/pesos configuráveis e mostrar contribuição de cada fator
- forecast baseline por série temporal (moving average / exponential smoothing ou statsmodels)
- intervalo/erro em backtest simples
- Model Registry + Model Card no banco ou arquivo
- UI deve dizer “experimental/demo”

### 3.11 Importação e Exportação
- CSV import wizard: upload → map columns → preview → validate → error rows → commit
- transação; não importar parcialmente sem confirmação
- export CSV
- export GeoJSON
- JSON backup lógico de dados demo opcional

### 3.12 Relatórios
- relatório HTML print-friendly
- PDF gerado no backend se biblioteca local disponível; fallback para print browser
- relatório gerencial
- relatório territorial
- relatório de qualidade
- relatório de auditoria
- filtro por período

### 3.13 Auditoria / Governança
- AuditEvent em banco
- login, create/update/delete, download, OCR review, admin changes
- correlation/request id
- não registrar senha/token/dado pessoal desnecessário
- tela para ADMIN/AUDITOR
- filtros e export

### 3.14 Administração
- tipos de ocorrência
- status/prioridades configuráveis ou catálogos seed
- setores/territórios
- providers OCR/chatbot/rota
- base de conhecimento
- parâmetros de risk score
- flags DEMO

## 4. MODELO DE DADOS
Implemente pelo menos:
User, Role, Permission, UserRole, Occurrence, OccurrenceEvent, OccurrenceType, Territory, Document, DocumentLink, OCRJob, OCRField, ChatSession, ChatMessage, KnowledgeItem, RoutePlan, RouteStop, DataQualityRule, DataQualityIssue, AuditEvent, ModelRegistry, SystemSetting.

Use UUIDs. Datas timezone-aware UTC no backend. Geometry SRID 4326. Índices para filtros frequentes e GIST em geometrias.

## 5. API
- REST JSON
- /api/v1
- OpenAPI gerado pelo FastAPI
- endpoints documentados
- erros padronizados
- paginação
- filtros
- RBAC no backend
- health: /health/live e /health/ready

## 6. UX/UI
Manter estética institucional/minimalista do MVP V2, mas profissionalizar:
- sidebar desktop / navegação mobile
- design tokens
- empty/loading/error states
- toasts
- forms com validação
- tabelas responsivas
- drawer/modal consistente
- acessibilidade teclado/labels/contraste
- banner DEMO sempre presente quando DEMO_MODE=true

## 7. SEGURANÇA
- hash Argon2/bcrypt
- JWT curto + refresh ou sessão segura
- CORS restrito
- CSP/headers quando aplicável
- upload allowlist + size limit + nome seguro
- SQL parametrizado via ORM
- sanitize/render text seguro
- rate limit chatbot/login simples
- env secrets
- .env.example sem segredo
- não logar tokens

## 8. LGPD / PRIVACIDADE
- seed sem dados reais
- classificação de documento
- política de retenção como metadado
- endpoints/telas não devem expor dado restrito a papel inadequado
- arquitetura para anonimização/agregação pública
- docs PRIVACY.md com controlador/operador como campos a preencher institucionalmente, sem inventar

## 9. OBSERVABILIDADE
- logs JSON
- request id
- tempos de endpoint
- healthchecks
- métricas básicas ou endpoint /metrics opcional
- dashboard admin com estado de providers

## 10. TESTES OBRIGATÓRIOS
Backend: pytest. Frontend: Vitest/Testing Library. E2E: Playwright se viável.
Cobrir pelo menos:
- login/RBAC
- CRUD ocorrência
- GeoJSON
- upload documento
- OCR job fixture
- revisão OCR
- chatbot grounded + fallback
- qualidade de dados
- auditoria
- dashboard KPI
- import CSV

Rode todos antes de encerrar. Corrija falhas.

## 11. SEED
Criar script idempotente com:
- 1 admin demo
- 4 usuários por papéis
- 40-60 ocorrências sintéticas distribuídas no tempo/setores
- territórios GeoJSON sintéticos
- 10 documentos de metadado + pelo menos 2 arquivos fixture
- 20+ knowledge items
- regras de qualidade
- registros suficientes para gráficos

## 12. DOCKER COMPOSE
Um comando deve subir tudo:
`docker compose up --build`
Serviços: web, api, db(PostGIS), redis, minio, worker.
Adicionar migrations/seed claros. Pode separar seed por comando para não sobrescrever dados.

## 13. DOCUMENTAÇÃO A GERAR
- README.md (Windows/PowerShell e Linux)
- ARCHITECTURE.md
- SECURITY.md
- PRIVACY.md
- DATA_MODEL.md
- API.md ou link OpenAPI
- TESTING.md
- DEPLOYMENT.md
- MODEL_CARDS.md
- CHANGELOG.md
- DEMO_SCRIPT.md

## 14. QA FINAL OBRIGATÓRIO
Antes de responder:
1. revise árvore do repo
2. rode backend tests
3. rode frontend tests
4. rode lint/typecheck
5. rode build
6. suba Docker Compose ou, se ambiente não permitir Docker, rode componentes diretamente e documente a limitação
7. execute smoke test dos módulos
8. procure TODO/FIXME/placeholder
9. verifique que nenhum dado real/credencial foi inventado
10. produza relatório final `QA_REPORT.md` com PASS/FAIL e evidências

## 15. DEFINITION OF DONE
Só considere concluído quando:
- todas as páginas abrem
- todos os módulos principais usam backend/banco real
- mapa usa Leaflet/PostGIS
- OCR processa fixture real
- chatbot mostra fonte e fallback
- documentos são realmente armazenados
- dashboard não é hardcoded
- RBAC funciona
- auditoria persiste
- seed funciona
- testes críticos passam
- README permite reprodução
- QA_REPORT existe

## 16. ORDEM DE EXECUÇÃO RECOMENDADA
1. audite o MVP existente
2. crie monorepo sem apagar referência visual
3. infra/banco/migrations
4. auth + domínio ocorrência
5. documentos/storage/OCR
6. GIS/rotas
7. chatbot/knowledge
8. qualidade/analytics
9. dashboards/relatórios/admin/auditoria
10. testes/QA/docs

## 17. SAÍDA ESPERADA DO CODEX
Implemente diretamente os arquivos. Ao final, responda com:
- arquitetura final
- comandos para rodar
- credenciais DEMO geradas pelo seed (somente credenciais sintéticas locais)
- lista de módulos concluídos
- testes executados/resultados
- limitações remanescentes reais
- caminho do QA_REPORT.md

Não responda com plano futuro se houver capacidade de implementar agora.
