# Segurança

JWT de 8 horas, senhas bcrypt, autorização por papel no backend, checagem de escopo para agente de campo, uploads por tipo e tamanho, nomes de objetos aleatórios, SQL parametrizado pelo ORM e cabeçalhos de proteção básicos. A auditoria registra ações críticas sem senha ou token.

O Compose é uma instalação local de demonstração e inclui credenciais conhecidas. Antes de qualquer ambiente compartilhado, substitua segredos, adote TLS, gestão de credenciais, política de retenção, revisão de permissões, varredura de dependências e proteção de rede. O perfil `viewer` só baixa documentos públicos. Coordenadas não devem ser publicadas anonimamente.

As políticas de papel persistidas só podem revogar capacidades já concedidas pela matriz fixa de RBAC; o papel administrador não pode ser desativado. A prévia de arquivos exige o mesmo JWT e a mesma classificação do download. URLs de objetos MinIO e chaves de AI não são expostas ao navegador. O provider externo, quando habilitado, pode receber a pergunta e um trecho sintético da base; use apenas dados sintéticos e verifique a política de tratamento do serviço contratado. `OSRM_BASE_URL` pode receber coordenadas sintéticas de rota. Logs estruturados incluem método, caminho, status, tempo e request ID, sem token.

## Sprint 3 — localização e evidência

`/api/v1/field/*` exige papel admin, manager ou field_agent, e o agente só acessa rotas atribuídas. Check-in exige rota ativa. O histórico de coordenadas tem endpoint separado, acesso auditado e não é incluído na ocorrência para viewer. Upload de visita exige visita ativa e vínculo consistente. Revisão OCR registra ator/hora; prévia/download passam por autenticação e classificação. A implantação com dados reais exige TLS, segredo JWT próprio, credenciais MinIO próprias e revisão institucional de acesso e retenção.
