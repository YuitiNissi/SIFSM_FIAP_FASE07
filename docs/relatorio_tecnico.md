# Relatório Técnico — Sistema Integrado de Futuro Sustentável em Marte (SIFSM)

## 1. Introdução

O Sistema Integrado de Futuro Sustentável em Marte (SIFSM) é um protótipo acadêmico concebido para apoiar a organização e a análise da operação da colônia Aurora Siger. A proposta integra gestão de módulos, dados operacionais, lógica de decisão, simulação energética, modelagem linear e reflexões sobre inteligência artificial, arquitetura computacional e sustentabilidade.

O foco técnico da versão analisada é o balanço energético da colônia: consumo dos módulos, geração por painéis solares e reator, armazenamento em bateria e identificação de períodos em que a energia disponível não atende à demanda.

## 2. Objetivos

- Organizar informações dos módulos da colônia.
- Simular a evolução do consumo, da geração e da bateria.
- Identificar condições críticas por meio de uma regra booleana.
- Utilizar integração numérica para estimar energia a partir da potência.
- Aplicar regressão linear para estimar o consumo diário.
- Documentar uma arquitetura conceitual de IA e os impactos computacionais e socioambientais.

## 3. Organização dos dados e sistema de módulos

O repositório contém um script SQL para criação da tabela `MODULOS`, com identificador, nome, tipo, consumo, temperatura e status. Também contém `data/dados_teste.json`, com três módulos de exemplo: habitacional, agrícola e laboratório. O código de simulação lê os dados do JSON no formato correspondente aos campos esperados.

O arquivo `src/database.py` contém lógica de conexão Oracle e operações de gerenciamento. Entretanto, os arquivos separados `src/main.py`, `src/crud.py`, `src/alertas.py` e `src/menu.py` estavam vazios no pacote recebido. Por isso, não se deve afirmar que existe uma arquitetura modular completa nesses arquivos sem implementá-los e testá-los.

## 4. Simulação computacional e modelagem matemática

A simulação da equipe considera 120 sóis marcianos, cada um com 24,66 horas, e passo temporal de 15 minutos. São modelados três módulos cadastrados no arquivo de teste, variações de temperatura externa, quantidade de tripulantes, geração solar, reator de 40 kW e bateria de 6.000 kWh inicialmente com 60% de carga.

A tempestade de poeira ocorre entre os sóis 70 e 79, reduzindo a luz solar incidente em 65%. Os valores são hipóteses didáticas e não medições reais.

A energia é calculada pela integração da potência no tempo. Como a série é discreta, utiliza-se a regra dos trapézios:

`E ≈ Σ [(P[k] + P[k+1]) / 2] × Δt`

A bateria acumula o saldo entre geração e consumo, respeitando seus limites mínimo e máximo.

### 4.1 Resultados consolidados

| Indicador | Resultado |
|---|---:|
| Consumo total | 749,8 MWh |
| Geração total | 802,1 MWh |
| Consumo médio por sol | 6.248 kWh |
| Pico de potência | 313,9 kW |
| Energia não suprida | 23,1 MWh |
| Energia desperdiçada com bateria cheia | 74,8 MWh |
| Sóis com falta de energia | 10 |
| Horas em alerta | 231,8 h |
| Saldo médio durante a tempestade | −2.632 kWh/sol |

Embora a geração total seja superior ao consumo total, ocorre falta de energia em determinados momentos. Isso mostra que o balanço acumulado positivo não garante disponibilidade contínua: a energia precisa estar disponível no momento em que a demanda ocorre.

### 4.2 Comparação de cenários

A análise compara diferentes alterações nos parâmetros de geração e armazenamento. No cenário-base, a energia não suprida é de aproximadamente 23,1 MWh. Aumentar a área de painéis em 20% reduz esse valor para aproximadamente 18,6 MWh. Dobrar a bateria reduz para aproximadamente 17,1 MWh. O cenário de reator de 160 kW elimina a energia não suprida na simulação executada.

Esses resultados servem para comparar hipóteses dentro do modelo. Não constituem recomendação de dimensionamento real sem análise de massa, segurança, redundância, manutenção, combustível, eficiência e condições de missão.

## 5. Regressão linear

O modelo de regressão linear múltipla estima o consumo diário a partir da temperatura externa média e do número de tripulantes:

`consumo_kwh = 4321,3 − 26,67 × temp_media_c + 35,07 × tripulantes`

O coeficiente negativo da temperatura indica que, nas hipóteses da simulação, temperaturas médias mais altas reduzem a demanda de aquecimento. O coeficiente positivo de tripulantes indica aumento de consumo com mais pessoas na colônia.

No conjunto de teste, o modelo apresentou R² de aproximadamente 0,81, RMSE de 103,4 kWh e MAPE de 1,38%. Como os dados são sintéticos e gerados a partir de hipóteses conhecidas, o modelo aprende relações presentes no próprio simulador. Seu desempenho não deve ser generalizado diretamente para dados reais.

## 6. Lógica booleana e alerta energético

A regra de alerta utiliza duas entradas:

- A = 1 quando o SOC está abaixo de 20%.
- B = 1 quando a energia não suprida é maior que zero.

A saída L é dada por `L = A OR B`. Portanto, o alerta é acionado quando pelo menos uma das condições ocorre. A tabela-verdade e a representação de circuito com porta OR estão documentadas em `circuito_e_arquitetura.md`.

A regra é consistente com a expressão utilizada na simulação e na função `alerta_energia()` do módulo de resultados.

## 7. Proposta de integração de inteligência artificial

Propõe-se uma arquitetura multiagente formada por um agente triador e agentes especialistas em energia, previsão, manutenção e conformidade. Os agentes especialistas consultariam fontes autorizadas por ferramentas determinísticas, como os indicadores JSON, os módulos cadastrados e a função de previsão já existente.

O uso de RAG poderia recuperar trechos da documentação e dos dados autorizados para fundamentar as respostas. Guardrails de entrada validariam solicitações e permissões; guardrails de saída verificariam a origem dos números, reduziriam respostas sem evidência e protegeriam dados pessoais. Decisões críticas permaneceriam sob supervisão humana.

Essa arquitetura é conceitual nesta versão do repositório: não foi identificada implementação de agentes ou integração com modelo de IA.

## 8. Arquitetura computacional

A CPU é suficiente para coordenar o programa, executar o CRUD, aplicar regras booleanas e controlar a simulação atual. A GPU poderia acelerar operações paralelas em cenários muito maiores. NPU ou TPU poderiam acelerar inferência ou treinamento de modelos de IA, caso esses recursos fossem incorporados futuramente.

RAM mantém temporariamente séries, matrizes e DataFrames; armazenamento persistente mantém o banco, JSONs, CSVs e resultados. HBM, empilhamento 3D e chiplets são tecnologias relevantes para sistemas de maior desempenho, mas não são necessárias nem utilizadas pelo protótipo apresentado.

A escolha de hardware deve equilibrar desempenho e consumo energético. Para a escala atual, a aceleração especializada não está justificada por evidências de gargalo.

## 9. Sustentabilidade e impacto socioambiental

A simulação permite testar cenários antes de alterar a infraestrutura física. Os resultados apontam que a distribuição temporal da energia é tão importante quanto o total produzido. A gestão inteligente poderia, como evolução, priorizar cargas essenciais e deslocar cargas flexíveis para períodos de maior disponibilidade.

A infraestrutura de computação e IA também deve ser dimensionada considerando seu próprio consumo energético. O sistema deve aplicar minimização de dados, controle de acesso, proteção de credenciais e agregação de informações quando a identificação individual não for necessária.

A automação deve ser transparente e auditável. A IA pode apoiar a análise, mas decisões que afetem suporte à vida, habitação, agricultura ou manutenção precisam de validação humana.

## 10. Limitações

- Os dados são sintéticos e os parâmetros são hipóteses didáticas.
- O modelo de consumo simplifica fenômenos térmicos, eficiência, perdas e comportamento humano.
- A simulação não considera todas as restrições de engenharia de uma missão real.
- A IA multiagente e os aceleradores especializados são propostas conceituais.
- O menu principal foi integrado ao CRUD e aos resultados energéticos.
- As consultas do CRUD utilizam parâmetros e validação básica de entradas; a conexão real requer credenciais válidas e tabela criada.

## 11. Conclusão

O SIFSM demonstra como dados operacionais, simulação, integração matemática, regressão linear e regras booleanas podem apoiar a análise energética de uma colônia. O principal achado é que a geração total superior ao consumo não impede episódios de falta de energia, especialmente durante uma tempestade de poeira. A comparação de cenários permite estudar alternativas e explicitar os compromissos entre geração, armazenamento e disponibilidade.

As propostas de IA, arquitetura computacional e sustentabilidade ampliam a visão do protótipo sem confundir conceitos futuros com funcionalidades já implementadas. A evolução do projeto deve priorizar a validação do código de gerenciamento, a integração das partes e a documentação fiel ao que pode ser executado e demonstrado.
