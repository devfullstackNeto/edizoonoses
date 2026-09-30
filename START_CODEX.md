\# EDI ZOONOSES — EXECUÇÃO FINAL EM UMA ÚNICA RODADA



Você está trabalhando no produto final do projeto:



Ecossistema Digital Integrado com Inteligência Artificial para Modernizar a Vigilância em Zoonoses: Gestão Territorial e Análise de Dados.



Seu objetivo é transformar o baseline demonstrativo existente em um:



MVP FULL STACK FUNCIONAL, INTEGRADO, PERSISTENTE, TESTADO E EXECUTÁVEL LOCALMENTE.



\---



\# ANTES DE ESCREVER CÓDIGO



1\. Leia integralmente:



context/00\_CODEX\_MASTER\_CONTEXT\_FINAL.md

context/01\_ACCEPTANCE\_CHECKLIST.md



2\. Analise todo o conteúdo de:



baseline/



3\. Analise os documentos e referências disponíveis em:



docs/

reference/



4\. Gere:



IMPLEMENTATION\_PLAN.md



NÃO PARE PARA PEDIR APROVAÇÃO.



Após gerar o plano, continue imediatamente para implementação.



\---



\# REGRA PRINCIPAL



Não entregue apenas:



\- planejamento;

\- mockups;

\- documentação;

\- scaffolding;

\- telas estáticas.



IMPLEMENTE O SISTEMA.



Continue até:



\- backend funcionar;

\- frontend funcionar;

\- persistência funcionar;

\- autenticação/RBAC funcionar;

\- banco funcionar;

\- módulos principais estarem integrados;

\- Docker Compose subir;

\- testes P0 passarem;

\- README permitir execução;

\- QA\_REPORT.md não possuir falhas P0 conhecidas.



\---



\# BASELINE



O diretório:



baseline/



é referência visual e funcional.



Preserve:



\- identidade visual;

\- fluxos principais;

\- organização dos módulos;

\- banner de dados sintéticos;

\- clareza de que o ambiente é demonstrativo.



Você pode refatorar completamente o código.



Não precisa manter HTML/JS estático.



\---



\# STACK DESEJADA



Monorepo.



Web:

React

TypeScript

Vite



API:

FastAPI

Python



Worker:

Python



Banco:

PostgreSQL + PostGIS



Cache/jobs:

Redis



Storage:

MinIO / S3-compatible



Infraestrutura:

Docker Compose



Mapas:

Leaflet + OpenStreetMap



IA:

Python

Provider abstraction



OCR:

Tesseract local obrigatório como fallback.



Rotas:

algoritmo local + provider opcional OSRM.



\---



\# PRIORIDADE



Implemente primeiro todos os requisitos P0.



Depois P1.



Não perca tempo com funcionalidades cosméticas enquanto houver P0 incompleto.



\---



\# PERFIS



Implementar:



admin

field\_agent

analyst

manager

viewer



RBAC deve ser aplicado no backend.



\---



\# AUTENTICAÇÃO



Login demo real.



JWT ou sessão segura.



RBAC backend.



Seed com contas demo.



Nunca depender apenas do frontend para autorização.



\---



\# MÓDULO 1 — OCORRÊNCIAS



CRUD completo.



Campos mínimos:



\- protocolo;

\- tipo;

\- descrição;

\- localização;

\- latitude;

\- longitude;

\- território;

\- status;

\- prioridade;

\- data;

\- responsável;

\- origem;

\- observações;

\- anexos/metadados.



Criar timeline de eventos.



Histórico de alteração de status.



Busca, filtros e paginação.



\---



\# MÓDULO 2 — MAPA / GIS



Usar Leaflet.



Mostrar ocorrências georreferenciadas.



Filtros por:



\- tipo;

\- status;

\- território;

\- período;

\- prioridade.



PostGIS obrigatório para armazenamento espacial.



Criar:



\- clustering;

\- heatmap/hotspot simples;

\- camada de ocorrências;

\- popup de detalhe;

\- zoom para ocorrência.



Não inventar dados epidemiológicos reais.



Seed 100% sintética.



\---



\# MÓDULO 3 — CROQUI / ROTAS



Criar planejamento de rota para equipe de campo.



Input:

lista de ocorrências/locais.



Output:

ordem de visita.



Obrigatório:

algoritmo nearest-neighbor local.



Opcional:

OSRM se disponível.



Mostrar rota em mapa.



Permitir:

\- gerar rota;

\- reordenar;

\- salvar plano;

\- marcar ponto como visitado.



\---



\# MÓDULO 4 — OCR / DOCUMENT AI



Implementar pipeline assíncrono.



Fluxo:



upload

→ fila

→ OCR

→ extração

→ revisão humana

→ aprovação

→ vínculo com ocorrência/documento



Tesseract local obrigatório.



Criar provider interface para OCR.



Não depender de API paga.



Fornecer fixtures sintéticas.



Registrar:



\- texto bruto;

\- campos extraídos;

\- confiança;

\- revisão;

\- status.



\---



\# MÓDULO 5 — REPOSITÓRIO ELETRÔNICO



Upload/download.



Metadados.



Hash.



Versionamento.



Busca.



Relacionamento com ocorrência.



Controle de acesso.



Armazenamento MinIO/S3.



\---



\# MÓDULO 6 — CHATBOT



Assistente informacional para:



\- dúvidas frequentes;

\- orientação institucional;

\- procedimentos;

\- navegação no sistema;

\- informações da base autorizada.



NÃO inventar informação.



Implementar:



Knowledge Base

RAG simples

sources

fallback

intent

feedback



Provider abstraction:



MockProvider obrigatório offline.



Provider compatível com OpenAI opcional via env.



Resposta deve retornar:



text

source\_refs

response\_type

fallback



Base inicial com pelo menos 20 itens.



\---



\# MÓDULO 7 — DASHBOARD



Dashboard derivado do banco.



Nunca hardcoded.



Indicadores:



\- ocorrências por status;

\- por território;

\- por tipo;

\- por período;

\- tempo médio entre abertura e fechamento;

\- pendências;

\- documentos processados;

\- OCR jobs;

\- rotas;

\- qualidade dos dados.



Todos os números devem vir do banco.



\---



\# MÓDULO 8 — QUALIDADE DE DADOS



Criar engine persistente de regras.



Exemplos:



\- ocorrência sem coordenada;

\- endereço incompleto;

\- duplicidade provável;

\- status inconsistente;

\- data inválida;

\- território ausente;

\- documento sem vínculo.



Cada issue deve ter:



\- rule\_id;

\- entity;

\- severity;

\- status;

\- detected\_at;

\- resolved\_at.



Dashboard de qualidade.



\---



\# MÓDULO 9 — ANALYTICS / IA



Separar claramente:



produção operacional

vs

pesquisa/analytics.



Implementar pelo menos:



1\. score demonstrativo explicável de prioridade operacional

ou

2\. forecast simples de volume de ocorrências.



Obrigatório:



\- baseline;

\- Logistic Regression ou modelo simples quando aplicável;

\- Random Forest ou Gradient Boosting;

\- train/test ou CV;

\- métricas;

\- feature importance;

\- model card.



Usar somente dados sintéticos.



Não apresentar como previsão epidemiológica validada.



\---



\# MÓDULO 10 — IMPORTAÇÃO / EXPORTAÇÃO



Wizard de importação CSV.



Validar colunas.



Preview.



Erros por linha.



Importar apenas após confirmação.



Exportar:



CSV

GeoJSON



\---



\# MÓDULO 11 — RELATÓRIOS



Gerar relatórios:



\- ocorrências;

\- território;

\- período;

\- qualidade;

\- OCR;

\- rota.



HTML obrigatório.



PDF se viável.



\---



\# MÓDULO 12 — ADMINISTRAÇÃO



CRUD de:



\- usuários;

\- papéis;

\- tipos de ocorrência;

\- territórios;

\- regras de qualidade;

\- Knowledge Base;

\- configurações.



\---



\# MÓDULO 13 — AUDITORIA



Registrar ações críticas:



\- login;

\- criação/edição;

\- mudança de status;

\- upload;

\- revisão OCR;

\- mudança em KB;

\- configurações;

\- exclusões.



Campos:



actor

action

entity

entity\_id

timestamp

metadata mínimo.



\---



\# DADOS



Criar seed com:



\- 1 admin;

\- pelo menos 4 usuários;

\- 40 a 60 ocorrências sintéticas;

\- territórios sintéticos;

\- 10 documentos/metadados;

\- pelo menos 2 arquivos fixture para OCR;

\- 20+ itens de Knowledge Base;

\- regras de qualidade;

\- rotas demonstrativas.



Banner permanente:



DADOS SINTÉTICOS / DEMONSTRAÇÃO.



\---



\# API



Usar:



/api/v1



Criar:



/health

/ready



OpenAPI documentado.



Paginação padronizada.



Erros padronizados.



\---



\# TESTES



Executar:



pytest

Vitest

Playwright

lint

typecheck

build



Testar obrigatoriamente:



\- login;

\- RBAC;

\- CRUD ocorrência;

\- mapa;

\- PostGIS;

\- OCR fixture;

\- revisão OCR;

\- chatbot fonte/fallback;

\- documento storage;

\- dashboard não hardcoded;

\- import CSV;

\- export GeoJSON;

\- qualidade de dados;

\- auditoria;

\- backup/smoke;

\- mobile/responsividade;

\- segurança.



\---



\# DOCKER



Criar:



docker-compose.yml



Subir:



web

api

db

redis

minio

worker



Com healthchecks.



Com seed.



Com .env.example.



\---



\# DOCUMENTAÇÃO FINAL



Gerar:



README.md

ARCHITECTURE.md

SECURITY.md

PRIVACY.md

DATA\_MODEL.md

API.md

TESTING.md

DEPLOYMENT.md

MODEL\_CARDS.md

CHANGELOG.md

QA\_REPORT.md

SCREENSHOT\_GUIDE.md

DEMO\_SCRIPT.md



\---



\# QA REPORT



QA\_REPORT.md deve listar:



Test ID

Status

Evidence

Notes



Nenhum P0 pode ficar FAIL.



Se houver FAIL:



CORRIJA.



Rode novamente.



Continue até não haver falha P0 conhecida.



\---



\# VERIFICAÇÃO FINAL



Antes de encerrar:



1\. docker compose up --build

2\. verificar healthchecks

3\. backend tests

4\. frontend tests

5\. E2E

6\. OCR fixture

7\. chatbot source/fallback

8\. PostGIS/map

9\. storage MinIO

10\. CSV import

11\. GeoJSON export

12\. lint

13\. typecheck

14\. build

15\. TODO/FIXME scan

16\. secret scan

17\. smoke test

18\. QA\_REPORT

19\. screenshot guide

20\. demo script



\---



\# CRITÉRIOS ADICIONAIS DE COMPLETUDE



\## NÃO SIMULAR INTEGRAÇÃO QUANDO ELA PODE SER IMPLEMENTADA



Sempre que o serviço estiver disponível localmente, use a integração real:



\- PostgreSQL/PostGIS para dados e geometrias;

\- Redis para fila/cache quando previsto;

\- MinIO para documentos;

\- Tesseract para OCR;

\- banco de dados para dashboard e indicadores.



Não substituir esses componentes por arrays hardcoded, JSON estático ou mocks na versão final.



Mocks são permitidos somente para integrações externas opcionais.



\---



\## EVIDÊNCIA EXECUTÁVEL



Para cada módulo principal, deve existir pelo menos uma evidência executável:



\- teste automatizado;

\- fixture;

\- seed;

\- endpoint funcional;

\- fluxo E2E;

\- ou smoke test documentado.



Não considerar um módulo concluído apenas porque sua interface foi criada.



\---



\## INTEGRIDADE DO FRONTEND



Todas as páginas da interface devem consumir API real quando houver domínio persistente.



Não deixar páginas principais usando números, listas ou indicadores hardcoded.



O banner de dados sintéticos pode ser estático, mas os dados exibidos devem vir do banco/seed.



\---



\## POLIMENTO FINAL



Após todos os P0 passarem:



\- revisar português da interface;

\- remover textos técnicos desnecessários expostos ao usuário;

\- eliminar placeholders visuais;

\- conferir estados vazios;

\- conferir loading/error states;

\- conferir responsividade;

\- preparar dados de demonstração visualmente convincentes.



Não sacrificar requisitos P0 para realizar este polimento.



\# NÃO FAÇA



Não pare no planejamento.



Não peça confirmação intermediária.



Não invente:



\- dados reais da UVZ;

\- agentes reais;

\- métricas reais de campo;

\- aprovação institucional;

\- resultados epidemiológicos;

\- usuários reais.



Use sempre dados sintéticos.



\---



\# RESULTADO ESPERADO



Ao final deve existir um MVP FULL STACK funcional do EDI Zoonoses, apto para:



\- rodar localmente;

\- demonstrar;

\- tirar screenshots;

\- gravar vídeo;

\- servir como evidência do projeto;

\- realizar validação técnica;

\- ser posteriormente publicado.



O sistema final deve ser suficientemente completo para que uma demonstração possa ser realizada sem editar banco, código ou arquivos manualmente durante a apresentação.

