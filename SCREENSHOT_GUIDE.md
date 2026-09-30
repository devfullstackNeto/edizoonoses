# Guia de capturas — versão final DEMO

Capturas reais feitas pelo Playwright em `http://localhost:8090` em 29/09/2026 (America/Cuiaba), com dados exclusivamente sintéticos. Desktop: 1440×900; móvel: 390×844. Cada arquivo foi validado por assinatura PNG e SHA-256 em `docs/evidence/reports/capture-manifest.json`. Reproduza com `cd apps/web` e `npx playwright test --config=playwright.evidence.config.ts`; valide com `python scripts/verify_evidence.py` na raiz. Essa nova execução cria outra ocorrência e rota DEMO e substitui as capturas anteriores.

## Desktop

| Arquivo | Tela | Funcionalidade | O que comprova | Requisito/módulo | Observações |
|---|---|---|---|---|---|
| [01_login.png](docs/evidence/screenshots/desktop/01_login.png) | Login | Acesso | Formulário e aviso de dados sintéticos | Autenticação | Antes do login DEMO |
| [02_dashboard.png](docs/evidence/screenshots/desktop/02_dashboard.png) | Dashboard | Indicadores | Painel inicial carregado do backend | Dashboard | Volumes incluem testes DEMO anteriores |
| [03_mapa_gis.png](docs/evidence/screenshots/desktop/03_mapa_gis.png) | Mapa | GIS | Pontos e camada territorial no Leaflet | Mapa/PostGIS | Base OpenStreetMap |
| [04_busca_endereco.png](docs/evidence/screenshots/desktop/04_busca_endereco.png) | Mapa | Busca de endereço | Sugestões devolvidas pela seed sintética | Geocodificação | Sem Nominatim externo |
| [05_correcao_manual_ponto.png](docs/evidence/screenshots/desktop/05_correcao_manual_ponto.png) | Mapa | Ajuste manual | Marcador movido por clique real no mapa | Geocodificação/PostGIS | Ponto associado depois à ocorrência DEMO |
| [06_detalhe_ocorrencia.png](docs/evidence/screenshots/desktop/06_detalhe_ocorrencia.png) | Ocorrências | Detalhe | Ocorrência criada e georreferenciada | Ocorrências | Protocolo no manifesto |
| [07_criacao_rota.png](docs/evidence/screenshots/desktop/07_criacao_rota.png) | Rotas | Planejamento | Ocorrência selecionada e partida informada | Croqui/rotas | Antes de salvar |
| [08_rota_desenhada.png](docs/evidence/screenshots/desktop/08_rota_desenhada.png) | Rotas | Trajeto | Geometria, marcador e distâncias de rota salva | Croqui/rotas | Fallback geométrico local; OSRM não configurado |
| [09_modo_campo.png](docs/evidence/screenshots/desktop/09_modo_campo.png) | Modo Campo | Seleção de rota | Plano pronto para execução | Operação de campo | Rota DEMO |
| [10_checkin.png](docs/evidence/screenshots/desktop/10_checkin.png) | Modo Campo | Check-in | Posição obtida e check-in registrado em rota ativa | Geolocalização | Posição simulada pelo Chrome Playwright |
| [11_geofence_fora_raio.png](docs/evidence/screenshots/desktop/11_geofence_fora_raio.png) | Modo Campo | Geofence | Aviso com distância fora do raio de 100 m | Geofence | Coordenadas sintéticas |
| [12_chegada_override.png](docs/evidence/screenshots/desktop/12_chegada_override.png) | Modo Campo | Chegada | Override manual com justificativa e visita liberada | Geofence/auditoria | Justificativa DEMO |
| [13_visita_andamento.png](docs/evidence/screenshots/desktop/13_visita_andamento.png) | Modo Campo | Início de visita | Visita em estado de execução | Visitas | Horário persistido no backend |
| [14_resultado_visita.png](docs/evidence/screenshots/desktop/14_resultado_visita.png) | Modo Campo | Resultado | Seleção de resultado e observação | Visitas | Antes da conclusão |
| [15_pendencia.png](docs/evidence/screenshots/desktop/15_pendencia.png) | Modo Campo | Pendência | Pendência vinculada à visita | Pendências | Severidade Alta sintética |
| [16_captura_evidencia.png](docs/evidence/screenshots/desktop/16_captura_evidencia.png) | Modo Campo | Foto/arquivo | Prévia real antes de confirmar o upload | Evidências | Fixture PNG sintética |
| [17_documento_original.png](docs/evidence/screenshots/desktop/17_documento_original.png) | OCR | Original | Documento servido pelo MinIO na revisão | Documentos/OCR | Captura do viewport |
| [18_ocr_executado.png](docs/evidence/screenshots/desktop/18_ocr_executado.png) | OCR | Tesseract | Job concluído, texto/confiança/campos | OCR real | Worker Redis/RQ |
| [19_ocr_multipagina.png](docs/evidence/screenshots/desktop/19_ocr_multipagina.png) | OCR | PDF | Página 2 selecionada e texto bruto expandido | OCR multipágina | Prévia do PDF pode manter página 1; texto exibido é da página 2 |
| [20_revisao_humana.png](docs/evidence/screenshots/desktop/20_revisao_humana.png) | OCR | Correção | Campo detectado alterado e novo campo adicionado | Revisão OCR | Antes da aprovação |
| [21_documento_aprovado.png](docs/evidence/screenshots/desktop/21_documento_aprovado.png) | OCR | Aprovação | Resultado da revisão aprovado | Revisão OCR | Vínculo com visita/ocorrência |
| [22_repositorio_eletronico.png](docs/evidence/screenshots/desktop/22_repositorio_eletronico.png) | Repositório | Pesquisa | Documento enviado e encontrado por nome | Documentos/MinIO | Upload DEMO real |
| [23_chatbot.png](docs/evidence/screenshots/desktop/23_chatbot.png) | Chatbot | Pergunta | Resposta com referência de fonte | Chatbot | Pergunta sintética sobre morcegos |
| [24_qualidade_dados.png](docs/evidence/screenshots/desktop/24_qualidade_dados.png) | Qualidade | Regras e achados | Módulo de qualidade consultável | Qualidade de dados | Dados DEMO |
| [25_auditoria.png](docs/evidence/screenshots/desktop/25_auditoria.png) | Auditoria | Eventos | Registro de ações após a jornada | Auditoria | Conta admin DEMO |
| [26_timeline_ocorrencia.png](docs/evidence/screenshots/desktop/26_timeline_ocorrencia.png) | Ocorrências | Histórico | Eventos de rota, chegada, visita, pendência, documento e OCR | Timeline operacional | Modal rolado até os eventos; captura do viewport |
| [27_dashboard_apos_operacoes.png](docs/evidence/screenshots/desktop/27_dashboard_apos_operacoes.png) | Dashboard | Indicadores de campo | Métricas após conclusão da visita e rota | Dashboard | Contagens incluem demais testes sintéticos |

## Móvel

| Arquivo | Tela | Funcionalidade | O que comprova | Requisito/módulo | Observações |
|---|---|---|---|---|---|
| [01_mapa_mobile.png](docs/evidence/screenshots/mobile/01_mapa_mobile.png) | Mapa | Navegação | GIS acessível em 390×844 | Mapa responsivo | Chrome em viewport móvel |
| [02_modo_campo_mobile.png](docs/evidence/screenshots/mobile/02_modo_campo_mobile.png) | Modo Campo | Seleção | Rota planejada acessível no celular | Campo responsivo | Rota DEMO |
| [03_proximo_destino_mobile.png](docs/evidence/screenshots/mobile/03_proximo_destino_mobile.png) | Modo Campo | Próxima visita | Protocolo e endereço da parada ativa | Campo responsivo | Destino sintético |
| [04_checkin_mobile.png](docs/evidence/screenshots/mobile/04_checkin_mobile.png) | Modo Campo | Check-in | Geolocation API simulada e registro explícito | Geolocalização | Sem rastreamento permanente |
| [05_geofence_mobile.png](docs/evidence/screenshots/mobile/05_geofence_mobile.png) | Modo Campo | Geofence | Distância fora do raio e aviso móvel | Geofence | Raio 100 m |
| [06_visita_mobile.png](docs/evidence/screenshots/mobile/06_visita_mobile.png) | Modo Campo | Visita | Estado de visita em andamento | Visitas | Layout de campo |
| [07_captura_foto_mobile.png](docs/evidence/screenshots/mobile/07_captura_foto_mobile.png) | Modo Campo | Foto | Seleção de arquivo e prévia no celular | Captura/evidência | Câmera física não testada; fixture selecionada |
| [08_pendencia_mobile.png](docs/evidence/screenshots/mobile/08_pendencia_mobile.png) | Modo Campo | Pendência | Registro visível no fluxo móvel | Pendências | Pendência sintética |
| [09_conclusao_mobile.png](docs/evidence/screenshots/mobile/09_conclusao_mobile.png) | Modo Campo | Conclusão | Visita concluída antes do fim da rota | Visitas | Estado vindo do backend |

O vídeo originalmente gerado foi removido por não ser utilizável como evidência. Este guia considera válidas apenas as 36 capturas PNG. O [relatório de captura](docs/evidence/reports/EVIDENCE_CAPTURE_REPORT.md) registra a limitação.
