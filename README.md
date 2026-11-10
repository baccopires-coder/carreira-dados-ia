# carreira-dados-ia — Quanto vale uma carreira em dados? (State of Data 2025-2026)

Projeto **novo e independente** (não altera o repositório antigo `salarios_por_senioridade`).
O app entrevista a pessoa (com IA), recomenda áreas de dados, mostra salários por cargo, senioridade,
experiência e macrorregião, e aponta habilidades a desenvolver.

| Arquivo | Papel |
|---|---|
| `motor.py` | Carrega/trata o CSV; ranking de áreas, lacunas de habilidades e salários (pandas, **sem IA**) |
| `ia.py` | Claude conduz a entrevista e **explica** números já calculados (não vê microdados) |
| `app.py` | Interface: Descobrir minha área · Painel geral · Hipóteses H1–H3 |

Sem chave de API o app continua funcionando (formulário no lugar do chat).

## 1. Criar o projeto novo (sem tocar no antigo)
```bash
# fora da pasta do projeto antigo
mkdir carreira_dados_ia && cd carreira_dados_ia
# extraia aqui o conteúdo deste zip
cp "../salarios_por_senioridade/dados/"*.csv dados/            # o mesmo CSV que você já usa
cp ../salarios_por_senioridade/dados/brasil_estados.geojson dados/   # opcional
```

## 2. Testar localmente
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # cole sua ANTHROPIC_API_KEY
streamlit run app.py
```
A API da Anthropic (https://console.anthropic.com) é cobrada por uso, à parte da assinatura do Claude.

## 3. Repositório novo no GitHub
```bash
git init
git add .
git commit -m "Versão com entrevista de IA"
gh repo create carreira-dados-ia --public --source=. --push
```
Confira antes que `.streamlit/secrets.toml` **não** aparece em `git status` (o `.gitignore` já o protege).
Sobre o CSV, veja o comentário no `.gitignore`.

## 4. Publicar como segundo app
Streamlit Community Cloud → **Create app** (não mexa no app antigo) → repositório `carreira-dados-ia`,
branch `main`, arquivo `app.py` → *Advanced settings → Secrets*:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Decisões de método (para o relatório)
- **Escopo:** vive no Brasil; CLT, PJ, servidor ou freelancer; cargos de dados com amostra suficiente.
- **Salário:** ponto médio da faixa; mediana (e média/quartis) sempre com `n`.
- **Amostra mínima:** 20 por grupo (`MIN_N` em `motor.py`); abaixo disso o app avisa.
- **Região:** só macrorregião; UF nem é carregada. **Não há dado por capital** (a pesquisa não tem cidade).
- **LGPD:** gênero, cor/raça e deficiência não são carregados nem usados pela IA; só resultados agregados.
- **Habilidades:** linguagens, bancos de dados, nuvem e BI (perguntados a todos os não gestores); uso < 3% descartado.
- **Ranking:** 85% similaridade de ferramentas + 15% interesse declarado. É índice de afinidade, não previsão.
- **IA:** saída da entrevista validada contra listas fechadas; limite de 25 chamadas por sessão.

## Limitações
Amostra voluntária (62% Sudeste; Norte pequeno), salário em faixas, dados de fim de 2025, sem cidade.

Fonte: Data Hackers + Bain & Company, *State of Data Brazil 2025-2026*.
