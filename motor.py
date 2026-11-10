"""Motor de dados e recomendação (100% pandas, sem IA).

Regras do pré-projeto aplicadas aqui:
- só quem vive no Brasil e é CLT, PJ, servidor ou freelancer;
- gênero, cor/raça e deficiência NÃO são carregados;
- UF NÃO é carregada: a análise regional usa só macrorregião;
- nenhum grupo com menos de MIN_N respondentes é exibido.
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).parent
MIN_N = 20

URL_GEOJSON = (
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
    "master/public/data/brazil-states.geojson"
)

TIPO_FAIXA = "de R$ 25.001/mês a R$ 3000/mês"  # erro de digitação na base
PONTO_MEDIO = {
    "Menos de R$ 1.000/mês": 500,
    "de R$ 1.001/mês a R$ 2.000/mês": 1500,
    "de R$ 2.001/mês a R$ 3.000/mês": 2500,
    "de R$ 3.001/mês a R$ 4.000/mês": 3500,
    "de R$ 4.001/mês a R$ 6.000/mês": 5000,
    "de R$ 6.001/mês a R$ 8.000/mês": 7000,
    "de R$ 8.001/mês a R$ 12.000/mês": 10000,
    "de R$ 12.001/mês a R$ 16.000/mês": 14000,
    "de R$ 16.001/mês a R$ 20.000/mês": 18000,
    "de R$ 20.001/mês a R$ 25.000/mês": 22500,
    "de R$ 25.001/mês a R$ 30.000/mês": 27500,
    "de R$ 30.001/mês a R$ 40.000/mês": 35000,
    "Acima de R$ 40.001/mês": 45000,
}
ORDEM_FAIXAS = list(PONTO_MEDIO)
ORDEM_NIVEL = ["Júnior", "Pleno", "Sênior", "Especialista/Staff+"]
ORDEM_EXP = ["Menos de 1 ano", "de 1 a 2 anos", "de 3 a 4 anos", "de 5 a 6 anos",
             "de 7 a 10 anos", "Mais de 10 anos"]
REGIOES = ["Norte", "Nordeste", "Centro-oeste", "Sudeste", "Sul"]
PORTE = {
    "de 1 a 5": "Micro (1–10)", "de 6 a 10": "Micro (1–10)",
    "de 11 a 50": "Pequena (11–50)", "de 51 a 100": "Média (51–100)",
    "de 101 a 500": "Grande (100+)", "de 501 a 1.000": "Grande (100+)",
    "de 1.001 a 3.000": "Grande (100+)", "Acima de 3.000": "Grande (100+)",
}
ORDEM_PORTE = ["Micro (1–10)", "Pequena (11–50)", "Média (51–100)", "Grande (100+)"]
VINCULOS = ["Empregado (CLT)", "Empreendedor ou Empregado (CNPJ)", "Servidor Público", "Freelancer"]

# rótulo curto -> valor na base
CARGOS = {
    "Analista de Dados": "Analista de Dados/Data Analyst",
    "Analista de BI": "Analista de BI/BI Analyst",
    "Analista de Negócios": "Analista de Negócios/Business Analyst",
    "Analytics Engineer": "Analytics Engineer",
    "Engenheiro de Dados": "Engenheiro de Dados/Data Engineer/Data Architect",
    "Cientista de Dados": "Cientista de Dados/Data Scientist",
    "Engenheiro de ML/IA": "Engenheiro de Machine Learning/ML Engineer/AI Engineer",
}
GRUPO = {
    "Analista de Dados": "Análise/BI", "Analista de BI": "Análise/BI",
    "Analista de Negócios": "Análise/BI", "Analytics Engineer": "Ciência/Eng. de dados/ML",
    "Engenheiro de Dados": "Ciência/Eng. de dados/ML", "Cientista de Dados": "Ciência/Eng. de dados/ML",
    "Engenheiro de ML/IA": "Ciência/Eng. de dados/ML",
}

COLUNAS = {
    "1.g_vive_no_brasil": "vive_brasil",
    "1.i.2_regiao_onde_mora": "regiao",
    "2.a_situação_de_trabalho": "contrato",
    "2.c_numero_de_funcionarios": "tamanho_empresa",
    "2.f_cargo_atual": "cargo",
    "2.g_nivel": "senioridade",
    "2.h_faixa_salarial": "faixa_salarial",
    "2.i_tempo_de_experiencia_em_dados": "experiencia",
    "2.q_modelo_de_trabalho_atual": "modelo_trabalho",
}
# blocos de habilidades perguntados a todos os profissionais não gestores
BLOCOS = {"4.c.": "Linguagens", "4.d.": "Bancos de dados", "4.e.": "Nuvem", "4.g.": "BI"}
EXCLUIR = ("Não utilizo", "apenas Excel", "On Premise", "Cloud Própria")


@dataclass
class Base:
    df: pd.DataFrame          # uma linha por respondente no escopo
    categorias: dict          # categoria -> lista de habilidades
    freq: pd.DataFrame        # cargo x habilidade (% que usa)
    freq_geral: pd.Series     # habilidade -> % geral
    n_hab: pd.Series          # cargo -> nº de respondentes do bloco de habilidades

    @property
    def habilidades(self):
        return [h for hs in self.categorias.values() for h in hs]


def carregar_base() -> Base:
    csv = next((PASTA / "dados").glob("*.csv"), None)
    if csv is None:
        raise FileNotFoundError("Coloque o CSV do State of Data dentro da pasta 'dados/'.")
    cab = pd.read_csv(csv, nrows=0).columns
    cols_hab = [c for c in cab if c.startswith(tuple(BLOCOS)) and not any(x in c for x in EXCLUIR)]
    rot = {c: c.split("_", 1)[1].strip() for c in cols_hab}
    cat_de = {rot[c]: BLOCOS[c[:4]] for c in cols_hab}
    assert len(set(rot.values())) == len(rot), "rótulos de habilidade duplicados"

    df = pd.read_csv(csv, usecols=list(COLUNAS) + cols_hab).rename(columns={**COLUNAS, **rot})
    df = df[(df["vive_brasil"] == 1) & df["contrato"].isin(VINCULOS)]
    df = df.dropna(subset=["faixa_salarial", "cargo", "senioridade", "regiao"])
    df = df[df["cargo"].isin(CARGOS.values())].copy()
    df["cargo"] = df["cargo"].map({v: k for k, v in CARGOS.items()})
    df["faixa_salarial"] = df["faixa_salarial"].replace({TIPO_FAIXA: "de R$ 25.001/mês a R$ 30.000/mês"})
    df["salario"] = df["faixa_salarial"].map(PONTO_MEDIO)
    df = df.dropna(subset=["salario"])
    df["tamanho_empresa"] = df["tamanho_empresa"].replace({"de 501 a 100": "de 501 a 1.000"}).map(PORTE)
    df["modelo_trabalho"] = (df["modelo_trabalho"].str.replace("Modelo ", "", regex=False)
                             .str.replace(r"\s*\(.*\)", "", regex=True).str.capitalize())
    habs = list(rot.values())
    df["resp_hab"] = df[habs].notna().any(axis=1)
    df[habs] = df[habs].fillna(0)

    hab = df[df["resp_hab"]]
    prev = hab[habs].mean()
    habs = [h for h in habs if prev[h] >= 0.03]  # descarta habilidades raríssimas
    categorias = {c: [h for h in habs if cat_de[h] == c] for c in BLOCOS.values()}
    return Base(df=df, categorias=categorias, freq=hab.groupby("cargo")[habs].mean(),
                freq_geral=hab[habs].mean(), n_hab=hab.groupby("cargo").size())


# ----------------------------------------------------------------------
# Recomendação
# ----------------------------------------------------------------------
INTERESSES = {
    "Análise e visualização": ["Analista de Dados", "Analista de BI", "Analista de Negócios"],
    "Engenharia e pipelines": ["Engenheiro de Dados", "Analytics Engineer"],
    "Modelagem e ML": ["Cientista de Dados", "Engenheiro de ML/IA"],
    "Sem preferência": [],
}


def ranking(base: Base, hab_usuario, interesse="Sem preferência", top_k=12) -> pd.DataFrame:
    """Afinidade = 85% ferramentas (média de similaridade do perfil com o cargo e
    com o que o cargo tem de distintivo) + 15% interesse declarado.
    Não é previsão de sucesso: é um índice de afinidade entre o perfil e a pesquisa."""
    meu = [h for h in hab_usuario if h in base.habilidades]
    u = pd.Series(0.0, index=base.freq.columns)
    u[meu] = 1.0
    linhas = []
    for cargo, f in base.freq.iterrows():
        if base.n_hab[cargo] < MIN_N:
            continue
        tipicas = f[f >= 0.25].nlargest(top_k)
        cobertura = tipicas[tipicas.index.isin(meu)].sum() / tipicas.sum() if len(tipicas) else 0
        d = f - base.freq_geral
        cos = float(u @ f / ((u @ u) ** .5 * (f @ f) ** .5 + 1e-9))
        lift = float(u @ d / (((u @ u) ** .5) * ((d @ d) ** .5) + 1e-9))
        ferr = .5 * cos + .5 * max(lift, 0) if meu else 0
        bonus = 1.0 if cargo in INTERESSES.get(interesse, []) else 0.0
        linhas.append({"cargo": cargo, "adequacao": .85 * ferr + .15 * bonus,
                       "cobertura": cobertura, "n": int(base.n_hab[cargo])})
    return pd.DataFrame(linhas).sort_values("adequacao", ascending=False).reset_index(drop=True)


def habilidades_cargo(base: Base, cargo, hab_usuario, top=12) -> pd.DataFrame:
    f = base.freq.loc[cargo].nlargest(top)
    return pd.DataFrame({"habilidade": f.index, "pct": f.values,
                         "tem": [h in set(hab_usuario) for h in f.index]})


# ----------------------------------------------------------------------
# Salários
# ----------------------------------------------------------------------
def resumo(df, por) -> pd.DataFrame:
    cols = (por if isinstance(por, list) else [por]) + ["n", "mediana", "media", "p25", "p75"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    r = df.groupby(por)["salario"].agg(
        n="size", mediana="median", media="mean",
        p25=lambda s: s.quantile(.25), p75=lambda s: s.quantile(.75)).reset_index()
    return r[r["n"] >= MIN_N]


def _ordenar(r, col, ordem):
    r = r.copy()
    r[col] = pd.Categorical(r[col], ordem, ordered=True)
    return r.sort_values(col).reset_index(drop=True)


def tabelas_cargo(base: Base, cargo, regiao=None) -> dict:
    d = base.df[base.df["cargo"] == cargo]
    dr = d[d["regiao"] == regiao] if regiao in REGIOES else d.iloc[0:0]
    return {
        "nivel_br": _ordenar(resumo(d, "senioridade"), "senioridade", ORDEM_NIVEL),
        "nivel_reg": _ordenar(resumo(dr, "senioridade"), "senioridade", ORDEM_NIVEL),
        "exp_br": _ordenar(resumo(d, "experiencia"), "experiencia", ORDEM_EXP),
        "exp_reg": _ordenar(resumo(dr, "experiencia"), "experiencia", ORDEM_EXP),
        "regioes": resumo(d, "regiao"),
    }


def eta2(df, col) -> float:
    """Parcela da variação salarial explicada por `col` (0 a 1)."""
    g = df.groupby(col)["salario"]
    media = df["salario"].mean()
    return float((g.size() * (g.mean() - media) ** 2).sum() / ((df["salario"] - media) ** 2).sum())


def sumario(base: Base, perfil: dict, rk: pd.DataFrame, top=3) -> dict:
    """Números já calculados que a IA recebe para explicar (ela não vê microdados)."""
    def tab(t):
        return {str(r[t.columns[0]]): {"mediana": int(r.mediana), "n": int(r.n)} for _, r in t.iterrows()}
    areas = []
    for _, r in rk.head(top).iterrows():
        t = tabelas_cargo(base, r.cargo, perfil.get("regiao"))
        hab = habilidades_cargo(base, r.cargo, perfil["habilidades"])
        areas.append({
            "cargo": r.cargo, "adequacao_pct": round(r.adequacao * 100),
            "habilidades_que_voce_tem": [{"habilidade": h.habilidade, "pct_profissionais": round(h.pct * 100)}
                                         for h in hab.itertuples() if h.tem],
            "habilidades_a_desenvolver": [{"habilidade": h.habilidade, "pct_profissionais": round(h.pct * 100)}
                                          for h in hab.itertuples() if not h.tem][:6],
            "salario_mediano_por_senioridade_brasil": tab(t["nivel_br"]),
            "salario_mediano_por_senioridade_na_sua_regiao": tab(t["nivel_reg"]),
            "salario_mediano_por_experiencia_brasil": tab(t["exp_br"]),
        })
    return {"perfil": perfil, "areas": areas,
            "limitacoes": ["salário informado em faixas (usamos o ponto médio)",
                           "amostra voluntária, concentrada no Sudeste",
                           "dados de fim de 2025",
                           f"grupos com menos de {MIN_N} respondentes não são exibidos",
                           "a pesquisa não tem cidade: só macrorregião (não há dado por capital)"]}
