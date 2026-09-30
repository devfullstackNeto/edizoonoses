# Model cards

## RiskScoreDemo v1

Finalidade: ordenação demonstrativa de ocorrências sintéticas. Entrada: prioridade, situação, presença de coordenadas e tempo de abertura. Saída: soma de pesos limitada a 100. O endpoint `/analytics` mostra cada contribuição. Não há treinamento epidemiológico ou validação de campo. O escore não executa decisões automáticas e não pode fundamentar intervenção real.

## OCR Tesseract

Reconhecimento de caracteres local em imagem/PDF. Texto, campos e confiança média são sugestões; aprovação exige revisão humana. A confiança é a média dos blocos válidos reportados pelo Tesseract, não probabilidade calibrada por campo.

## SyntheticPriorityComparison v1

Comparação reprodutível em 50 registros **sintéticos**: classe majoritária, regressão logística e Random Forest; divisão estratificada treino/teste 70/30, acurácia, F1 e importância das variáveis. O rótulo foi derivado do próprio escore por regras, portanto essas métricas demonstram apenas o pipeline técnico. Elas não estimam validade epidemiológica nem desempenho em campo. Resultados são gravados em `model_registry` e exibidos em Analytics.
