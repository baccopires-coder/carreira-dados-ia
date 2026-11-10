import json
import urllib.request

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ia
import motor
from motor import MIN_N, ORDEM_EXP, ORDEM_NIVEL

st.set_page_config(page_title="Quanto vale uma carreira em dados?", page_icon="📊", layout="wide")

AZUL, AZUL_CLARO, ROXO, ROXO_ESCURO = "#3B82F6", "#60A5FA", "#8B5CF6", "#6D28D9"
ESCALA = [[0.0, "#2563EB"], [0.5, "#6366F1"], [1.0, "#A855F7"]]
CORES_CAT = [AZUL, ROXO, AZUL_CLARO, "#6366F1", "#A78BFA", "#38BDF8", "#C084FC"]
UF_REGIAO = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

st.markdown(
    f"""<style>
    .stApp {{ background: radial-gradient(circle at 10% 0%, #1B2350 0%, #0B1020 45%); }}
    h1.titulo {{ background: linear-gradient(90deg, {AZUL_CLARO}, {ROXO}); -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; font-weight: 800; margin-bottom: 0; line-height: 1.15; }}
    h1.titulo span.sub {{ display:block; font-size:1.1rem; font-weight:500; margin-top:6px; opacity:.9; }}
    [data-testid="stMetric"] {{ background: linear-gradient(135deg, rgba(59,130,246,.18), rgba(139,92,246,.22));
        border: 1px solid rgba(139,92,246,.35); border-radius: 16px; padding: 16px 20px; min-height: 112px;
        box-shadow: 0 6px 24px rgba(99,102,241,.15); overflow: hidden; }}
    [data-testid="stMetricLabel"] {{ color: #B8C1EC; }}
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ white-space: normal !important;
        overflow: visible !important; line-height: 1.2 !important; overflow-wrap: anywhere !important; }}
    [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #141B34 0%, #1B1540 100%);
        border-right: 1px solid rgba(139,92,246,.25); }}
    button[data-testid^="stBaseButton-pills"] {{ border-radius: 999px !important;
        border: 1px solid rgba(139,92,246,.35) !important; }}
    button[data-testid="stBaseButton-pillsActive"] {{ background: linear-gradient(135deg, rgba(59,130,246,.5),
        rgba(139,92,246,.6)) !important; color: #fff !important; }}
    span[data-baseweb="tag"] {{ background-color: {ROXO_ESCURO} !important; }}
    </style>""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Dados e utilidades
# ----------------------------------------------------------------------
@st.cache_resource
def get_base():
    return motor.carregar_base()


@st.cache_resource
def get_geojson():
    local = motor.PASTA / "dados" / "brasil_estados.geojson"
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    with urllib.request.urlopen(motor.URL_GEOJSON, timeout=15) as r:
        return json.load(r)


def moeda(v):
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def estilizar(fig, titulo):
    fig.update_layout(title=titulo, title_x=0.02, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#E8ECFF", margin=dict(l=10, r=10, t=60, b=10), coloraxis_showscale=False)
    fig.update_xaxes(gridcolor="rgba(139,92,246,.15)")
    fig.update_yaxes(gridcolor="rgba(139,92,246,.15)")
    return fig


def mostrar(fig, titulo):
    st.plotly_chart(estilizar(fig, titulo), width="stretch")


try:
    base = get_base()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

with st.sidebar:
    st.header("ℹ️ Sobre os dados")
    st.markdown(
        "**Fonte:** State of Data Brazil 2025-2026 (Data Hackers + Bain & Company), microdados no Kaggle.\n\n"
        "**Escopo:** quem vive no Brasil e é CLT, PJ, servidor ou freelancer.\n\n"
        f"**Privacidade:** só resultados agregados; grupos com menos de {MIN_N} pessoas não aparecem; "
        "região = macrorregião; gênero, cor/raça e deficiência não são usados.\n\n"
        "**Limites:** salário em faixas (usamos o ponto médio), amostra voluntária concentrada no Sudeste, "
        "dados de fim de 2025. A pesquisa não tem cidade, então **não há dado por capital**."
    )

st.markdown(
    '<h1 class="titulo">📊 Quanto vale uma carreira em dados?'
    '<span class="sub">Descubra a área que mais combina com você e quanto ela paga '
    "(State of Data 2025-2026)</span></h1>",
    unsafe_allow_html=True,
)
aba1, aba2, aba3 = st.tabs(["🧭 Descobrir minha área", "📊 Painel geral", "🔬 Hipóteses do projeto"])


# ----------------------------------------------------------------------
# ABA 1 — Entrevista, recomendação e salários
# ----------------------------------------------------------------------
def chat():
    ss = st.session_state
    ss.setdefault("msgs", [{"role": "assistant", "content": ia.SAUDACAO}])
    for m in ss.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    texto_usuario = st.chat_input("Digite sua resposta…")
    if texto_usuario:
        ss.msgs.append({"role": "user", "content": texto_usuario})
        try:
            with st.spinner("Pensando…"):
                resposta, perfil = ia.proxima(base, ss.msgs)
        except Exception as e:
            ss.msgs.pop()
            st.error(f"Não consegui falar com a IA ({type(e).__name__}). Tente de novo ou use o formulário.")
            return
        if resposta:
            ss.msgs.append({"role": "assistant", "content": resposta})
        if perfil:
            ss.perfil = perfil
        st.rerun()


def formulario():
    with st.form("form_perfil"):
        escolhidas = []
        for cat, hs in base.categorias.items():
            escolhidas += st.multiselect(f"{cat} que você usa", hs, key=f"f_{cat}")
        c1, c2, c3, c4 = st.columns(4)
        exp = c1.selectbox("Experiência em dados", ["Nenhuma"] + ORDEM_EXP)
        nivel = c2.selectbox("Nível atual", ia.NIVEIS)
        regiao = c3.selectbox("Macrorregião onde mora", motor.REGIOES + ["Não informado"])
        interesse = c4.selectbox("O que mais gosta de fazer", list(motor.INTERESSES))
        if st.form_submit_button("Ver minha recomendação", type="primary"):
            st.session_state.perfil = ia.validar_perfil(
                dict(habilidades=escolhidas, experiencia=exp, nivel=nivel, regiao=regiao, interesse=interesse), base)
            st.rerun()


def comparativo(br, rg, col, ordem, titulo, regiao, linha=False):
    partes = [br.assign(Onde="Brasil")]
    if not rg.empty:
        partes.append(rg.assign(Onde=regiao))
    d = pd.concat(partes)
    d[col] = d[col].astype(str)
    if d.empty:
        st.info("Sem amostra mínima para este recorte.")
        return
    kw = dict(x=col, y="mediana", color="Onde", custom_data=["n"], category_orders={col: ordem},
              color_discrete_sequence=[AZUL_CLARO, ROXO], labels={"mediana": "Mediana (R$/mês)", col: ""})
    fig = px.line(d, markers=True, **kw) if linha else px.bar(d, barmode="group", **kw)
    fig.update_traces(hovertemplate="%{x}<br>Mediana: R$ %{y:,.0f}<br>n = %{customdata[0]}<extra></extra>")
    mostrar(fig, titulo)
    if regiao in motor.REGIOES and rg.empty:
        st.caption(f"Sem amostra mínima ({MIN_N}) em {regiao} neste recorte.")


def resultado(perfil):
    ss = st.session_state
    rk = motor.ranking(base, perfil["habilidades"], perfil["interesse"])
    reg = perfil["regiao"]
    st.subheader("Seu perfil")
    st.caption(
        f"**Habilidades:** {', '.join(perfil['habilidades']) or 'nenhuma informada'} · **Experiência:** "
        f"{perfil['experiencia']} · **Nível:** {perfil['nivel']} · **Região:** {reg} · **Interesse:** {perfil['interesse']}"
    )
    if not perfil["habilidades"]:
        st.warning("Sem habilidades informadas, o ranking usa apenas o seu interesse. Refaça para um resultado melhor.")
    if rk.empty:
        st.error("Sem amostra suficiente para recomendar.")
        return

    st.subheader("Áreas com mais afinidade")
    cols = st.columns(3)
    for i, r in rk.head(3).iterrows():
        cols[i].metric(f"{i + 1}º {r.cargo}", f"{r.adequacao:.0%}",
                       help=f"Você cobre {r.cobertura:.0%} do conjunto de ferramentas típico do cargo "
                            f"(amostra de {r.n} profissionais).")
    st.caption("O índice compara suas ferramentas com as de cada cargo e considera seu interesse. "
               "É um guia de afinidade, não uma previsão: várias áreas usam as mesmas ferramentas.")
    fig = px.bar(rk.sort_values("adequacao"), x="adequacao", y="cargo", orientation="h", color="adequacao",
                 color_continuous_scale=ESCALA, labels={"adequacao": "Afinidade", "cargo": ""})
    fig.update_xaxes(tickformat=".0%")
    mostrar(fig, "Afinidade por área")

    st.subheader("Análise personalizada")
    sm = motor.sumario(base, perfil, rk)
    chave = json.dumps(perfil, sort_keys=True)
    if ss.get("analise_chave") != chave:
        with st.spinner("Gerando análise…"):
            ss.analise = ia.explicar(sm) if ia.disponivel() else ia.explicar_local(sm)
        ss.analise_chave = chave
    st.markdown(ss.analise)

    st.subheader("Explore uma área")
    cargo = st.selectbox("Área", list(rk.cargo), key="cargo_sel")
    t = motor.tabelas_cargo(base, cargo, reg)
    g1, g2 = st.columns(2)
    with g1:
        hab = motor.habilidades_cargo(base, cargo, perfil["habilidades"])
        hab["Situação"] = hab["tem"].map({True: "Você já usa", False: "Para desenvolver"})
        fig = px.bar(hab.sort_values("pct"), x="pct", y="habilidade", orientation="h", color="Situação",
                     color_discrete_map={"Você já usa": AZUL_CLARO, "Para desenvolver": ROXO},
                     labels={"pct": "% dos profissionais do cargo que usam", "habilidade": ""})
        fig.update_xaxes(tickformat=".0%")
        mostrar(fig, f"Habilidades mais usadas: {cargo}")
    with g2:
        comparativo(t["nivel_br"], t["nivel_reg"], "senioridade", ORDEM_NIVEL, "Salário mediano por senioridade", reg)
    g3, g4 = st.columns(2)
    with g3:
        comparativo(t["exp_br"], t["exp_reg"], "experiencia", ORDEM_EXP, "Salário mediano por tempo de experiência",
                    reg, linha=True)
    with g4:
        r = t["regioes"]
        if r.empty:
            st.info("Sem amostra mínima por região para este cargo.")
        else:
            fig = px.bar(r, x="regiao", y="mediana", color="mediana", color_continuous_scale=ESCALA,
                         custom_data=["n", "media"], labels={"mediana": "Mediana (R$/mês)", "regiao": ""})
            fig.update_traces(hovertemplate="%{x}<br>Mediana: R$ %{y:,.0f}<br>Média: R$ %{customdata[1]:,.0f}"
                                            "<br>n = %{customdata[0]}<extra></extra>")
            mostrar(fig, "Salário por macrorregião")
    with st.expander("Ver valores (mediana e quartis) por senioridade"):
        x = t["nivel_br"].rename(columns={"senioridade": "Senioridade", "n": "Respondentes", "mediana": "Mediana",
                                          "media": "Média", "p25": "25%", "p75": "75%"})
        st.dataframe(x.style.format({c: moeda for c in ["Mediana", "Média", "25%", "75%"]}), hide_index=True)


with aba1:
    ss = st.session_state
    ss.setdefault("perfil", None)
    if ss.perfil is None:
        if ia.disponivel():
            modo = st.radio("Como prefere responder?", ["💬 Entrevista com IA", "📝 Formulário rápido"],
                            horizontal=True)
        else:
            modo = "📝 Formulário rápido"
            st.info("A entrevista com IA precisa de uma chave (ANTHROPIC_API_KEY) configurada. "
                    "Enquanto isso, use o formulário — o resultado usa os mesmos dados.")
        if modo.startswith("💬"):
            chat()
        else:
            formulario()
    else:
        if st.button("↩️ Refazer entrevista"):
            for k in ("perfil", "msgs", "analise", "analise_chave", "cargo_sel"):
                ss.pop(k, None)
            st.rerun()
        resultado(ss.perfil)


# ----------------------------------------------------------------------
# ABA 2 — Painel geral
# ----------------------------------------------------------------------
def filtro(col_ui, rotulo, coluna, ordem=None):
    opcoes = [o for o in ordem if o in base.df[coluna].unique()] if ordem else sorted(base.df[coluna].dropna().unique())
    sel = col_ui.pills(rotulo, opcoes, selection_mode="multi", key=f"filtro_{coluna}")
    return sel if sel else opcoes


with aba2:
    st.caption("Salário informado em faixas mensais; os valores usam o ponto médio de cada faixa. "
               "Sem seleção nos filtros, todos os valores são considerados.")
    f1, f2, f3, f4 = st.columns(4)
    sel_reg = filtro(f1, "Região", "regiao", motor.REGIOES)
    sel_niv = filtro(f2, "Senioridade", "senioridade", ORDEM_NIVEL)
    sel_con = filtro(f3, "Tipo de contrato", "contrato")
    sel_por = filtro(f4, "Porte da empresa", "tamanho_empresa", motor.ORDEM_PORTE)
    d = base.df[base.df.regiao.isin(sel_reg) & base.df.senioridade.isin(sel_niv)
                & base.df.contrato.isin(sel_con) & base.df.tamanho_empresa.isin(sel_por)]

    k1, k2, k3, k4 = st.columns(4)
    if d.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
    elif len(d) < MIN_N:
        st.warning(f"Menos de {MIN_N} respondentes com esses filtros; amplie a seleção.")
    else:
        k1.metric("Salário médio", moeda(d.salario.mean()))
        k2.metric("Salário mediano", moeda(d.salario.median()))
        k3.metric("Dados analisados", f"{len(d):,}".replace(",", "."), help=f"{len(d) / len(base.df):.1%} da base no escopo.")
        k4.metric("Cargo mais frequente", d.cargo.mode()[0])

        a, b = st.columns(2)
        with a:
            pc = motor.resumo(d, "cargo").sort_values("media")
            fig = px.bar(pc, x="media", y="cargo", orientation="h", color="media", color_continuous_scale=ESCALA,
                         custom_data=["n"], labels={"media": "Salário médio (R$/mês)", "cargo": ""})
            fig.update_traces(hovertemplate="%{y}<br>Média: R$ %{x:,.0f}<br>n = %{customdata[0]}<extra></extra>")
            mostrar(fig, f"Salário médio por cargo (mín. {MIN_N} respondentes)")
        with b:
            fx = d.faixa_salarial.value_counts().reindex(motor.ORDEM_FAIXAS, fill_value=0).reset_index()
            fx.columns = ["faixa", "quantidade"]
            fx["faixa"] = (fx.faixa.str.replace("/mês", "", regex=False).str.replace("de R$ ", "", regex=False)
                           .str.replace(" a R$ ", " – ", regex=False))
            fig = px.bar(fx, x="faixa", y="quantidade", color="quantidade", color_continuous_scale=ESCALA,
                         labels={"faixa": "Faixa salarial (R$/mês)", "quantidade": "Respondentes"})
            fig.update_xaxes(tickangle=-45)
            mostrar(fig, "Distribuição por faixa salarial")
        c, e = st.columns(2)
        with c:
            mt = d.modelo_trabalho.value_counts().reset_index()
            mt.columns = ["modelo", "quantidade"]
            fig = px.pie(mt, names="modelo", values="quantidade", hole=0.55, color_discrete_sequence=CORES_CAT)
            fig.update_traces(textinfo="percent", marker=dict(line=dict(color="#0B1020", width=2)))
            fig = estilizar(fig, "Proporção por modelo de trabalho")
            fig.update_layout(legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig, width="stretch")
        with e:
            try:
                gj = get_geojson()
                pr = motor.resumo(d, "regiao").set_index("regiao")
                ufs = [u for u in UF_REGIAO if UF_REGIAO[u] in pr.index]
                fig = go.Figure(go.Choropleth(
                    geojson=gj, locations=list(UF_REGIAO), z=[0] * len(UF_REGIAO), featureidkey="properties.sigla",
                    showscale=False, hoverinfo="skip", colorscale=[[0, "#232B4D"], [1, "#232B4D"]],
                    marker_line_color="#0B1020", marker_line_width=0.8))
                if ufs:
                    fig.add_trace(go.Choropleth(
                        geojson=gj, locations=ufs, featureidkey="properties.sigla", colorscale=ESCALA,
                        z=[pr.loc[UF_REGIAO[u], "media"] for u in ufs], text=[UF_REGIAO[u] for u in ufs],
                        customdata=[[int(pr.loc[UF_REGIAO[u], "n"])] for u in ufs],
                        hovertemplate="<b>%{text}</b><br>Média: R$ %{z:,.0f}<br>n = %{customdata[0]}<extra></extra>",
                        marker_line_color="#0B1020", marker_line_width=0.8,
                        colorbar=dict(title="R$/mês", thickness=12, len=0.7)))
                fig.update_geos(fitbounds="geojson", visible=False, bgcolor="rgba(0,0,0,0)")
                fig = estilizar(fig, "Salário médio por macrorregião")
                st.plotly_chart(fig, width="stretch")
                st.caption("Cada estado mostra a média da sua macrorregião (não há dado por estado). "
                           f"Cinza: região com menos de {MIN_N} respondentes.")
            except Exception:
                st.info("Não foi possível carregar o mapa (GeoJSON indisponível).")
        h, i = st.columns(2)
        with h:
            pn = motor.resumo(d, "senioridade").pipe(motor._ordenar, "senioridade", ORDEM_NIVEL)
            fig = px.bar(pn, x="senioridade", y="media", color="media", color_continuous_scale=ESCALA,
                         labels={"senioridade": "", "media": "Salário médio (R$/mês)"})
            mostrar(fig, "Salário médio por senioridade")
        with i:
            pe = motor.resumo(d, "experiencia").pipe(motor._ordenar, "experiencia", ORDEM_EXP)
            fig = px.line(pe, x="experiencia", y="media", markers=True,
                          labels={"experiencia": "Experiência em dados", "media": "Salário médio (R$/mês)"})
            fig.update_traces(line=dict(color=ROXO, width=4), marker=dict(size=11, color=AZUL_CLARO))
            mostrar(fig, "Salário médio por tempo de experiência")
    st.caption("Por privacidade (LGPD), a tabela de microdados não é exibida: apenas resultados agregados.")


# ----------------------------------------------------------------------
# ABA 3 — Hipóteses do pré-projeto (análise exploratória)
# ----------------------------------------------------------------------
with aba3:
    df = base.df
    st.caption("Análise exploratória sobre o escopo do projeto. Não substitui a regressão ordinal prevista no cronograma.")
    st.markdown("#### H1 — A senioridade explica mais diferença salarial do que a região?")
    e2 = pd.DataFrame({"Fator": ["Senioridade", "Cargo", "Experiência em dados", "Região"],
                       "pct": [motor.eta2(df, c) for c in ["senioridade", "cargo", "experiencia", "regiao"]]})
    fig = px.bar(e2.sort_values("pct"), x="pct", y="Fator", orientation="h", color="pct", color_continuous_scale=ESCALA,
                 labels={"pct": "% da variação salarial explicada (η²)", "Fator": ""})
    fig.update_xaxes(tickformat=".0%")
    mostrar(fig, "Quanto cada fator explica da variação salarial")

    st.markdown("#### H2 — No mesmo nível, ciência/engenharia/ML pagam mais que análise/BI?")
    dg = df.assign(grupo=df.cargo.map(motor.GRUPO))
    r2 = motor.resumo(dg, ["senioridade", "grupo"]).pipe(motor._ordenar, "senioridade", ORDEM_NIVEL)
    r2["senioridade"] = r2["senioridade"].astype(str)
    if r2.empty:
        st.info("Sem amostra mínima.")
    else:
        fig = px.bar(r2, x="senioridade", y="mediana", color="grupo", barmode="group", custom_data=["n"],
                     color_discrete_sequence=[AZUL_CLARO, ROXO], labels={"mediana": "Mediana (R$/mês)", "senioridade": ""})
        fig.update_traces(hovertemplate="%{x}<br>Mediana: R$ %{y:,.0f}<br>n = %{customdata[0]}<extra></extra>")
        mostrar(fig, "Mediana por nível e grupo de cargos")

    st.markdown("#### H3 — A vantagem do Sudeste aparece na cauda de salários altos?")
    r3 = motor.resumo(df, "regiao")
    alto = df.assign(alto=df.salario >= 14000).groupby("regiao")["alto"].mean()
    r3["% com salário ≥ R$ 14.000"] = r3["regiao"].map(alto)
    st.dataframe(r3[["regiao", "n", "media", "mediana", "% com salário ≥ R$ 14.000"]].rename(
        columns={"regiao": "Região", "n": "Respondentes", "media": "Média", "mediana": "Mediana"}).style.format(
        {"Média": moeda, "Mediana": moeda, "% com salário ≥ R$ 14.000": "{:.1%}"}), hide_index=True)
    st.caption("Se as medianas são parecidas mas a média e a fatia de salários altos são maiores no Sudeste, "
               "a vantagem está na cauda e não no salário típico.")
