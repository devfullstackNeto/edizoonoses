# Relatório final de captura de evidências — EDI Zoonoses

## Identificação e ambiente

- **Captura:** 29/09/2026, fuso America/Cuiaba; manifesto gravado em 30/09/2026 às 01:18:39 UTC.
- **Versão:** versão final DEMO após Sprint 3; frontend `edi-zoonoses-web` 1.0.0 e migração Alembic `0004 (head)`.
- **Jornada:** protocolo sintético `DEMO-FD3CE1E508`, ocorrência `656d8794-2e5a-4067-b3a1-012616ffe753` e rota `Rota Evidência DEMO 1790731094634`.
- **Ambiente:** Docker Compose local no Windows; Chrome controlado por Playwright. Interface `http://localhost:8090`; API `http://localhost:8010`. Desktop 1440×900; viewport móvel 390×844.
- **Dados:** exclusivamente DEMO/sintéticos. A seed PostGIS continha 50 ocorrências `seed-demo` na verificação. Volumes locais também contêm registros DEMO de testes anteriores.

## Disponibilidade dos serviços

Os seis serviços estavam `healthy` na verificação: `web`, `api`, `db` (PostGIS 3.4), `redis`, `minio` e `worker`. A API respondeu `/health/ready` com `database=postgis`, `redis=ok` e `storage=ok`. Registros brutos: [Compose](compose-status.txt), [API e migração](api-readiness.txt), [seed e PostGIS](seed-postgis.txt).

## Jornada realmente executada

O [teste de captura Playwright](../../../apps/web/evidence/capture.spec.ts) abriu o login DEMO e o dashboard; criou uma ocorrência sintética; pesquisou endereço na seed, corrigiu e salvou o ponto no mapa; criou e iniciou uma rota; registrou check-ins com localização simulada pelo Chrome; verificou rejeição pela geofence e confirmou a chegada mediante override justificado; iniciou a visita, definiu resultado e pendência; selecionou uma imagem sintética com prévia, enviou ao MinIO e executou OCR no worker; abriu o documento original, processou um PDF sintético de duas páginas, revisou campos e aprovou o resultado; pesquisou no repositório, consultou chatbot, qualidade e auditoria; concluiu a visita e a rota; abriu a timeline da ocorrência e retornou ao dashboard. Uma segunda página Chrome em 390×844 percorreu os estados móveis da mesma rota, incluindo check-in próprio e geofence. A visita foi concluída pela página desktop e a conclusão foi observada na página móvel.

## Evidências válidas

| Tipo | Quantidade | Local |
|---|---:|---|
| Capturas desktop | 27 | [screenshots/desktop](../screenshots/desktop/) |
| Capturas móveis | 9 | [screenshots/mobile](../screenshots/mobile/) |

O [índice](../EVIDENCE_INDEX.md) enumera individualmente as **36 evidências válidas**. O [guia](../../../SCREENSHOT_GUIDE.md) explica tela, função, comprovação, módulo e observações de cada PNG. O [manifesto](capture-manifest.json) registra protocolo, nomes e SHA-256.

**Vídeo: 0 evidências válidas.** O WebM originalmente gerado apresentou apenas quadros esparsos e foi considerado não utilizável para comprovar a jornada. O arquivo e seus metadados foram removidos do pacote; o diretório `videos/` permanece vazio. Nenhum novo vídeo foi gerado.

## Testes e integridade

- Captura Playwright desta rodada: **1/1 PASS**, em 25,8 s, com ações e respostas de interface/API verificadas por assertions.
- `python scripts/verify_evidence.py`: **PASS**, 27 PNG desktop e 9 PNG móveis; assinatura, dimensões, contagem e hashes SHA-256 conferidos. Vídeos não integram a validação.
- A [validação anterior da Sprint 3](../../../QA_REPORT.md) documenta 17/17 testes API, 4/4 E2E padrão, build/lint e zero P0 FAIL conhecido. Esses conjuntos não foram reexecutados para esta captura; a execução nova é o teste de evidências acima.

Para reproduzir a captura: `cd apps/web` e `npx playwright test --config=playwright.evidence.config.ts`. A execução cria outra ocorrência/rota DEMO e substitui as evidências e o manifesto. Depois, execute `python scripts/build_evidence_index.py` e `python scripts/verify_evidence.py` na raiz do projeto. Use o ambiente Compose local e a seed sintética.

## Limitações observadas

- O executável FFmpeg opcional do Playwright falhou neste host (`spawn EFTYPE`). A tentativa alternativa por screencast CDP gerou 19 quadros esparsos e foi descartada como evidência não utilizável. Não há vídeo válido neste pacote.
- O PDF multipágina exibiu o texto OCR da página 2 selecionada; a prévia embutida do PDF pode continuar exibindo a página 1. A [captura D19](../screenshots/desktop/19_ocr_multipagina.png) comprova a seleção e o texto, não sincronização visual da prévia.
- Geolocalização e viewport móvel foram simulados no Chrome. Não houve câmera física, celular real, usuários externos, dados de pacientes ou homologação institucional.
- Nominatim e OSRM externos não foram configurados. Busca local sintética, correção manual e fallback geométrico da rota foram os caminhos executados.
- Todas as telas pedidas foram capturadas; não há tela omitida nesta rodada. O fluxo de foto móvel comprova seleção e prévia de arquivo, não uma captura por câmera física. A jornada é comprovada pelo teste Playwright e pelos 36 screenshots, sem evidência em vídeo.
