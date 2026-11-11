# Parte da Sistema SIFSM — Integração, arquitetura e sustentabilidade do SIFSM

## Lógica booleana e regra de alerta energético

### Contextualização

O protótipo simula o balanço energético da colônia Aurora Siger. A simulação acompanha o consumo dos módulos, a geração dos painéis solares e do reator, o estado de carga da bateria (*State of Charge* — SOC) e a energia que deixa de ser atendida quando a bateria não consegue suprir a demanda.

A própria simulação da simulação energética já utiliza uma regra booleana para identificar situações críticas. A regra escolhida para a documentação é, portanto, a mesma utilizada no código, evitando criar uma decisão desconectada do protótipo.

### Variáveis de entrada e saída

| Símbolo | Variável | Valor lógico 1 (verdadeiro) | Valor lógico 0 (falso) |
|---|---|---|---|
| A | Bateria em nível crítico | SOC abaixo de 20% | SOC igual ou acima de 20% |
| B | Falta de energia | Energia não suprida maior que 0 kWh | Energia não suprida igual a 0 kWh |
| L | Alerta energético | O sistema deve emitir alerta | Não há alerta por esta regra |

### Expressão booleana

**L = A + B**

O operador `+` representa a operação lógica OR (OU). Assim, o alerta é ativado quando pelo menos uma das condições é verdadeira:

- a bateria está abaixo de 20% de carga; **ou**
- existe energia não suprida.

Em Python, a regra corresponde a:

```python
def alerta_energia(soc, energia_nao_suprida_kwh=0.0, limite_soc=0.20):
    return soc < limite_soc or energia_nao_suprida_kwh > 0
```

Essa mesma regra aparece na série temporal da simulação como a coluna `alerta_energia` e também na função `alerta_energia()` do módulo `src/resultados_simulacao.py`.

### Tabela-verdade

| A | B | L = A OR B |
|---:|---:|---:|
| 0 | 0 | 0 |
| 0 | 1 | 1 |
| 1 | 0 | 1 |
| 1 | 1 | 1 |

### Representação do circuito

O circuito pode ser representado por uma única porta lógica OR, como a família 74HC32. As entradas A e B são conectadas à porta; a saída L representa o alerta. Para uma demonstração física ou virtual, um LED pode representar a saída lógica, acendendo quando L = 1. O circuito é uma representação didática da regra e não controla diretamente equipamentos reais da colônia.

```text
A (SOC < 20%) --------\
                       ) OR ---- L (alerta energético)
B (energia > 0) ------/
```

**Interpretação:** a lógica prioriza a segurança energética. Não é necessário que as duas condições ocorram simultaneamente para que o alerta seja emitido. A regra também não substitui uma avaliação humana nem define, sozinha, o desligamento de módulos.

---

## Proposta de integração de inteligência artificial

### Objetivo

A IA é proposta como uma camada de apoio à interpretação dos dados operacionais e dos resultados da simulação. O protótipo atual já produz dados estruturados e resultados em JSON, mas não contém uma integração funcional com um modelo de IA ou uma implementação multiagente. Portanto, esta seção descreve uma arquitetura conceitual compatível com os arquivos existentes, e não uma funcionalidade já executada.

### Arquitetura multiagente proposta

| Agente | Responsabilidade | Dados consultados | Resultado esperado |
|---|---|---|---|
| Agente triador | Identificar o tipo de solicitação e encaminhá-la ao especialista adequado | Pergunta do operador e contexto da sessão | Roteamento para o agente correto |
| Agente de energia | Interpretar consumo, geração, SOC, alertas e cenários | `resultados_simulacao.json`, indicadores diários e série temporal | Explicação do estado energético e dos riscos |
| Agente de previsão | Explicar a estimativa de consumo e suas limitações | Coeficientes, métricas e faixa de treino da regressão | Interpretação da previsão, sem extrapolação indevida |
| Agente de manutenção | Relacionar o status dos módulos com registros operacionais | Cadastro de módulos e status do banco/arquivo | Lista de pontos que precisam de verificação |
| Agente de conformidade | Verificar se a resposta respeita as regras de segurança e privacidade | Resposta proposta e política de acesso | Aprovação, bloqueio ou solicitação de revisão |

### Fluxo de funcionamento

1. O operador envia uma pergunta ao sistema.
2. O agente triador identifica se o assunto é energia, previsão, manutenção ou outro tema operacional.
3. O agente especialista consulta somente as fontes autorizadas por ferramentas específicas.
4. Os dados retornados são usados para elaborar uma resposta contextualizada.
5. A camada de guardrails verifica a solicitação e a resposta.
6. Se a decisão envolver alteração operacional relevante, a recomendação é encaminhada para validação humana.

### Ferramentas e RAG

A arquitetura pode disponibilizar ferramentas determinísticas, por exemplo:

- `consultar_indicadores_energia()`: lê os indicadores consolidados de `data/simulacao/resultados_simulacao.json`.
- `consultar_modulos()`: consulta os módulos cadastrados no banco Oracle ou no arquivo de teste.
- `prever_consumo(temp_media_c, tripulantes)`: utiliza a função de previsão já disponível em `src/resultados_simulacao.py`.
- `consultar_alertas()`: recupera o estado de alerta calculado pela regra booleana.

O conceito de RAG (*Retrieval-Augmented Generation*) pode ser aplicado à documentação técnica: antes de responder, o agente recupera trechos autorizados do relatório de simulação, do README e das regras operacionais. Isso ajuda a fundamentar a resposta em informações do projeto. A recuperação de documentos e a chamada das ferramentas são propostas; não estão implementadas como agentes no código atual.

### Guardrails

**Input guardrails (entrada):**
- rejeitar tentativas de substituir as instruções do sistema ou acessar dados sem autorização;
- validar tipo, formato e faixa de valores recebidos;
- impedir comandos que solicitem ações perigosas ou não autorizadas;
- limitar o acesso às informações de acordo com o perfil do operador.

**Output guardrails (saída):**
- exigir que números e previsões sejam associados a uma fonte consultada;
- impedir que o agente invente medições, alertas ou resultados;
- informar quando os dados forem sintéticos ou estiverem fora da faixa de treinamento;
- ocultar dados pessoais e informações sensíveis da tripulação;
- não permitir que a IA execute diretamente decisões críticas sem confirmação humana.

### Handoff e supervisão humana

O *handoff* ocorre quando o agente triador encaminha a solicitação a um agente especialista. Caso a solicitação envolva alteração de parâmetros, priorização de recursos ou resposta a uma condição crítica, o fluxo deve ser transferido a um responsável humano. A IA explica evidências e alternativas; a autoridade final permanece com a equipe de operação.

---

## Arquitetura computacional: CPU, GPU, NPU/TPU e memória

### Aplicação ao SIFSM

O protótipo foi desenvolvido em Python e utiliza processamento numérico com NumPy, manipulação de dados com pandas, geração de gráficos com Matplotlib e persistência em Oracle/arquivos estruturados. Para o escopo acadêmico, uma CPU convencional é suficiente para executar as operações atuais. A discussão de GPU, NPU e TPU representa possibilidades de expansão, não requisitos do protótipo.

| Componente | Função geral | Aplicação possível no SIFSM |
|---|---|---|
| CPU | Executar instruções gerais, controlar o fluxo do programa e operações sequenciais | Menu, CRUD, regras booleanas, leitura de arquivos, controle da simulação |
| GPU | Executar grande quantidade de operações paralelas | Simulações com muitos cenários, processamento de grandes matrizes e visualizações complexas |
| NPU | Acelerar operações típicas de redes neurais e inferência de IA | Executar localmente modelos de IA para classificação ou interpretação, se futuramente adotados |
| TPU | Acelerador especializado em operações de aprendizado de máquina, especialmente tensores | Treinamento ou inferência de modelos maiores, caso a demanda futura justifique |
| RAM | Manter temporariamente dados e programas em uso | DataFrames, séries temporais, variáveis da simulação e resultados intermediários |
| Armazenamento | Preservar dados e resultados de forma persistente | Banco Oracle, arquivos JSON/CSV, código, relatórios e gráficos |

### Computação heterogênea

Em uma infraestrutura futura, as unidades podem trabalhar em conjunto: a CPU coordena a aplicação e controla as operações; a GPU executa tarefas altamente paralelizáveis; e uma NPU/TPU pode acelerar a inferência de modelos de IA. A escolha depende do volume de dados, da latência exigida, do consumo elétrico e da necessidade real de aceleração.

No protótipo atual, a simulação possui 11.837 instantes por execução, distribuídos em 120 sóis com passo de 15 minutos. As operações vetorizadas de NumPy e pandas são adequadas para esse porte. Não há evidência no repositório de uso de GPU, NPU ou TPU.

### Memória, movimentação de dados e eficiência

O desempenho não depende apenas da velocidade do processador. A movimentação de dados entre armazenamento, RAM, cache e unidades de processamento também pode gerar atrasos e consumo energético. Em sistemas de grande escala, tecnologias como HBM (*High Bandwidth Memory*), empilhamento 3D e chiplets podem aumentar a largura de banda ou aproximar componentes, mas possuem custos de fabricação, integração, energia e dissipação térmica.

Para a Aurora Siger, a decisão deve considerar o benefício operacional por watt consumido. Um acelerador só deve ser adotado se a redução de tempo ou o ganho de capacidade justificar seu custo energético e de manutenção. Para a versão atual, uma CPU eficiente, memória suficiente e armazenamento confiável são escolhas proporcionais ao escopo.

---

## Sustentabilidade, cidadania digital e impacto socioambiental

O SIFSM relaciona sustentabilidade à disponibilidade de energia ao longo do tempo, e não apenas ao total produzido. Os resultados da simulação demonstram essa diferença: em 120 sóis, a geração total foi de aproximadamente 802,1 MWh e o consumo de 749,8 MWh. Mesmo com geração acumulada superior ao consumo, houve aproximadamente 23,1 MWh de energia não suprida, concentrada durante a tempestade de poeira e no período logo após ela. Também foram contabilizados cerca de 74,8 MWh de energia desperdiçada quando a bateria atingiu sua capacidade máxima.

### Temas socioambientais relacionados ao projeto

**1. Otimização de recursos por simulação**

A simulação permite avaliar previamente o impacto de mudanças na geração e no armazenamento, sem construir ou modificar fisicamente a infraestrutura. No cenário-base, houve 23,1 MWh de energia não suprida. O cenário com reator de 160 kW eliminou a falta de energia dentro das hipóteses simuladas. Esse resultado permite comparar alternativas antes de uma decisão de engenharia, embora não seja uma recomendação de implantação real sem estudo técnico adicional.

**2. Redes elétricas inteligentes e gestão de demanda**

A análise do saldo energético, do SOC e dos alertas permite identificar períodos em que a geração não acompanha a demanda. Como evolução, o sistema poderia priorizar cargas essenciais, programar cargas flexíveis e reservar energia para períodos de baixa geração. Qualquer política de priorização deve ser transparente, documentada e validada pela equipe responsável, especialmente quando afetar habitação, agricultura ou suporte à vida.

**3. Pegada ecológica da infraestrutura computacional e da IA**

O processamento, armazenamento e transmissão de dados também consomem energia e exigem equipamentos. Por isso, a colônia deve evitar processamento desnecessário, limitar a retenção de dados, reutilizar resultados já calculados e escolher hardware proporcional à carga de trabalho. Modelos de IA mais complexos não devem ser adotados sem demonstrar benefício operacional que justifique seu custo energético.

**4. Cidadania e privacidade digital da tripulação**

Dados operacionais podem revelar rotinas, localização, presença e hábitos da tripulação. O sistema deve coletar apenas o necessário, restringir acessos por função, proteger credenciais, registrar consultas relevantes e evitar expor informações pessoais em relatórios ou respostas de IA. Indicadores agregados devem ser preferidos quando a identificação individual não for necessária.

**5. Inovação responsável e supervisão humana**

A automação pode acelerar a identificação de problemas, mas erros de sensores, hipóteses simplificadas ou previsões imprecisas podem influenciar decisões importantes. A equipe humana deve validar decisões críticas, revisar limites de alerta e manter procedimentos alternativos. A IA deve atuar como apoio à decisão, com justificativas e fontes verificáveis.

### Limitações ambientais e metodológicas

Os valores utilizados são didáticos e sintéticos, definidos por parâmetros da simulação. Eles não representam medições reais de Marte nem dimensionamento de uma instalação habitável. O resultado de um cenário deve ser interpretado dentro das hipóteses adotadas, e não como garantia de desempenho em uma missão real.

---

## Integração no relatório técnico

O relatório final deve apresentar o SIFSM como um único protótipo, conectando:

1. **Gestão dos módulos:** cadastro e consulta de módulos, banco Oracle e arquivo JSON de teste, conforme a implementação disponível.
2. **Organização e tratamento dos dados:** estruturas utilizadas no código e justificativa de seu uso.
3. **Lógica booleana:** alerta energético com base no SOC e na energia não suprida.
4. **Simulação e matemática:** consumo, geração, bateria, tempestade de poeira e integração numérica.
5. **Regressão linear:** estimativa do consumo diário a partir da temperatura média e do número de tripulantes.
6. **IA:** arquitetura multiagente proposta, com ferramentas, recuperação de informações e guardrails.
7. **Arquitetura computacional:** relação entre o processamento atual e possíveis expansões.
8. **Sustentabilidade:** interpretação dos resultados, privacidade e supervisão humana.

A descrição deve distinguir funcionalidades executáveis de propostas conceituais. A arquitetura multiagente e o uso de aceleradores, por exemplo, são propostas, não recursos comprovadamente implementados no repositório.

---

## README e execução

O arquivo `README.md` na raiz apresenta a visão geral, os requisitos, a configuração do ambiente, os comandos de execução e a estrutura dos diretórios. O arquivo `READM.md` que veio no repositório foi preservado, mas o README padronizado deve ser usado como porta de entrada do projeto.

---

## Organização da entrega

Estrutura recomendada:

```text
fiap-aurora-siger-fase-07/
├── data/
│   ├── dados_teste.json
│   └── simulacao/
│       ├── cenarios.csv
│       ├── indicadores_diarios.csv
│       ├── resultados_simulacao.json
│       └── serie_temporal.csv
├── docs/
│   ├── analise_simulacao.md
│   ├── planejamento.md
│   ├── circuito_e_arquitetura.md
│   ├── relatorio_tecnico_sifsm.md
│   └── graficos/
├── notebooks/
│   └── simulacao_energia.ipynb
├── sql/
│   └── criar_tabelas.sql
├── src/
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

Antes da entrega, conferir se todos os módulos referenciados estão preenchidos, se as instruções de execução correspondem ao código e se o ZIP não contém credenciais, arquivos temporários ou ambientes virtuais.
