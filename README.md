# SIFSM — Sistema Integrado de Futuro Sustentável em Marte

Protótipo acadêmico da colônia Aurora Siger: CRUD Oracle, simulação energética de 120 sóis, regressão linear, regra de alerta e documentação conceitual de IA e arquitetura.

## Instalação (PowerShell, na pasta principal)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Banco de dados

1. Copie `.env.example` para `.env` e preencha usuário e senha (não compartilhe o arquivo).
2. No SQL Developer, execute `sql/script_banco.sql` **apenas se a tabela MODULOS ainda não existir**. O script inclui dois registros de exemplo.
3. O acesso FIAP configurado usa `oracle.fiap.com.br`, porta 1521 e **SID ORCL**; ajuste as variáveis caso seu ambiente seja diferente.

## Execução

```powershell
python src/main.py
```

O menu principal: 1 cadastrar, 2 consultar, 3 alterar, 4 excluir, 5 excluir todos, 6 sair. A opção 5 exige confirmação explícita e deve ser evitada na demonstração. As opções 7 a 10 oferecem simulação, previsão e alertas. O menu de simulação pode ser usado sem Oracle; apenas o CRUD depende de conexão.

Também é possível executar a análise separadamente:

```powershell
python src/analise_simulacao.py
python -m pytest tests -v
```

## Arquivos de entrega

- `src/codigo_fonte.py`: entrada principal alternativa; `src/main.py` é a entrada recomendada.
- `sql/script_banco.sql`: estrutura e dados iniciais da tabela Oracle.
- `data/dados_aurora_siger.json`: dados sintéticos de módulos para a simulação.
- `src/simulacao_computacional.py`: atalho para simulação e geração dos gráficos.
- `docs/circuito_logico.png`: representação da porta OU para alerta energético.
- `docs/relatorio_tecnico.md`: documentação integrada, hipóteses, resultados e limitações.
- `docs/circuito_e_arquitetura.md`: explicação complementar da lógica e arquitetura.
- `docs/graficos/`: gráficos produzidos pela simulação.
- `link_video.txt`: link do video do Youtube

