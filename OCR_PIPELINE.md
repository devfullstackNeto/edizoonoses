# Pipeline OCR — Sprint 3

O upload autenticado preserva o original no MinIO com hash SHA-256 e referência no PostgreSQL. Um job Redis/RQ chama Tesseract local (`por+eng`) no worker. PNG/JPG/JPEG entram como imagem única; PDF passa por `pdfinfo` e `pdftoppm` a 180 dpi, até dez páginas, com OCR em cada página. Falha de leitura produz status `failed` e pode ser reprocessada.

Cada imagem recebe correção EXIF, tentativa de orientação pelo Tesseract OSD, grayscale, autocontraste, filtro mediano e resize quando estreita. Threshold é aplicado apenas em baixo contraste para reduzir perda de caracteres. As etapas efetivas são salvas por página. O texto bruto, confiança média do Tesseract, campos reconhecidos, página e confiança por campo são persistidos; campos extraídos por rótulo são sugestões, nunca dados automaticamente aprovados.

A tela **OCR / Document AI** apresenta original, página, texto bruto e campos com confiança. Operador autorizado pode corrigir, remover, adicionar, aprovar, rejeitar ou reprocessar. A revisão salva valor detectado, valor revisado, status de cada campo, usuário e horário. O documento pode ser associado à ocorrência; evidência criada no Modo Campo já mantém o vínculo da visita. O conteúdo OCR alimenta a busca do repositório junto com nome, tags e protocolo.

Fixtures sintéticas: `ficha_atendimento_sintetica.png`, `vistoria_sintetica.png`, `relatorio_visita_sintetico.png` e `dossie_visita_sintetico.pdf` (duas páginas). Regere com `scripts/generate_ocr_fixtures.py`. O teste `test_field_journey_geofence_evidence_ocr_and_privacy` processa o PDF real e verifica páginas, campos, revisão e vínculo. A qualidade do reconhecimento depende da foto; confirmação humana é obrigatória.
