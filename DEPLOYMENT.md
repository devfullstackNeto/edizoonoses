# Implantação local

`docker compose up --build -d` inicia PostGIS, Redis, MinIO, API, worker e web. O serviço API aplica Alembic e seed. Verifique `docker compose ps` e `/health/ready`. O sistema não representa homologação institucional ou implantação em produção.

Volumes `db_data` e `minio_data` persistem entre reinicializações. Para backup completo, salve ambos, além de dump lógico do PostgreSQL. A restauração exige restaurar os arquivos MinIO e o banco da mesma geração. Não exponha a instalação demo à internet.

As migrações `0002_pilot` e `0003_roles` são aplicadas automaticamente na inicialização da API. `OSRM_BASE_URL` e `AI_*` são opcionais; configure-os em `.env`, jamais no código. O serviço externo OSRM deve ser alcançável pela rede do contêiner. Verifique `docker compose ps`, `http://localhost:8010/health/ready` e a tela de rotas após qualquer atualização. Para um piloto fora do computador local, substitua senhas demo, configure HTTPS, backup de banco e MinIO, observabilidade central e política de acesso institucional antes da exposição.

## Variáveis Sprint 3

`GEOCODER_BASE_URL` vazio mantém busca sintética local; aponte apenas para Nominatim compatível que você opere ou cujo uso esteja autorizado. `GEOCODER_USER_AGENT` identifica o cliente; cache Redis dura 24 h e o adaptador limita requisições a 1/s. `OSRM_BASE_URL` vazio usa distância geodésica; com OSRM, exibe ruas e duração retornadas. `GEOFENCE_RADIUS_M=100` e `LOCATION_RETENTION_DAYS=30` são parâmetros de campo. Depois de `docker compose up --build -d`, verifique `docker compose ps` e `/health/ready`. Migração Alembic chega a 0004; `seed.py` publica quatro fixtures visuais sintéticas no MinIO.
