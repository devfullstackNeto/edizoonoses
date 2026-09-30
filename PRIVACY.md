# Privacidade e LGPD

A seed contém apenas pessoas, endereços e ocorrências inventados. O banner informa o caráter sintético. Documentos possuem classificação e metadado de retenção. Este protótipo não define controlador, operador, base legal ou prazo institucional: esses campos exigem decisão formal antes de tratar dados reais. Uma avaliação de impacto e política de anonimização/geolocalização serão necessárias para piloto com informação pessoal.

## Localização em campo — Sprint 3

A localização é solicitada no navegador somente por ação explícita ou intervalo opcional escolhido durante rota ativa. O padrão periódico é desligado; não há monitoramento permanente. Check-ins incluem finalidade, ator, rota/visita, horário, precisão opcional, distância/raio e decisão. Coordenadas são opcionais na confirmação manual. `LOCATION_RETENTION_DAYS` define prazo (padrão 30 dias); registros expirados são removidos na próxima gravação de check-in. Histórico é restrito e cada leitura auditada. Excluir os volumes do piloto remove os dados locais; em operação real, uma política de expurgo agendada e autorização institucional são necessárias.
