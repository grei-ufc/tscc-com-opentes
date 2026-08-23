#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu_streamlit.py — Configurador interativo da co-simulação PADE + OMNeT++ + Mosaik.

Versão web (Streamlit) do menu.py original: mesma lógica, mesmas variáveis
de ambiente (TOPOLOGY, NUM_PERIFERICOS, TIPOS_REDE), com identidade visual
do GREI (verde escuro #2F5D4B, verde vivo #007024, fundo claro #F4FFEB).

Como rodar:
    pip install streamlit
    streamlit run menu_streamlit.py
"""

import base64
import os
import subprocess

import streamlit as st

# ══════════════════════════════════════════════════════════════
# MAPEAMENTOS DE OPÇÕES
# ══════════════════════════════════════════════════════════════

TOPOLOGIAS = {
    "estrela": {"label": "Estrela", "desc": "1 agente central conectado a N periféricos."},
    "malha":   {"label": "Malha",   "desc": "Todos os agentes conectados entre si (full mesh)."},
    "anel":    {"label": "Anel",    "desc": "Cada agente conectado apenas ao próximo, em ciclo fechado."},
}

REDES = {
    "Link_Wired":    ("Cabeada",  "1 Gbps · delay 1ms · 0% perda"),
    "Link_5G":       ("5G",       "500 Mbps · ~5ms · 0.001% perda"),
    "Link_4G":       ("4G",       "50 Mbps · ~35ms · 0.5% perda"),
    "Link_2G":       ("2G",       "250 kbps · ~200ms · 15% perda"),
    "Link_Wireless": ("Wireless", "300 Mbps · ~2ms · 0.1% perda"),
}

RAIZ_PROJETO = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO = os.path.join(RAIZ_PROJETO, "LOGO.png")

VERDE_ESCURO = "#2F5D4B"
VERDE_VIVO   = "#007024"
FUNDO_CLARO  = "#F4FFEB"


# ══════════════════════════════════════════════════════════════
# ESTÉTICA
# ══════════════════════════════════════════════════════════════

def get_base64_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


def aplicar_estilo():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {FUNDO_CLARO};
            --primary-color: {VERDE_VIVO};   /* radio, slider, tags e botão primário usam essa variável */
        }}

        header[data-testid="stHeader"] {{ display: none; }}

        html, body, [class*="css"] {{ font-family: "Inter", "Segoe UI", sans-serif; }}

        .block-container {{
            max-width: 900px !important;
            padding-top: 1.2rem !important;
            padding-bottom: 2rem !important;
        }}

        /* Cabeçalhos numéricos ("1.", "2.", "3.") do CONTEÚDO — não mexe no
           cabeçalho GREI, que usa classes próprias abaixo. */
        .stApp .block-container h1,
        .stApp .block-container h2,
        .stApp .block-container h3 {{
            color: {VERDE_ESCURO};
            font-weight: 700;
            margin-top: 1.6rem;
            margin-bottom: 0.4rem;
        }}

        /* Texto normal (labels, captions, markdown) — SEM incluir botões,
           pra não deixar o texto do botão invisível */
        .stApp p, .stApp label, .stCaption, .stMarkdown {{ color: {VERDE_ESCURO}; }}

        /* ── Cabeçalho GREI — ocupa a largura inteira da tela (full-bleed),
           mesmo truque usado por sites reais: a faixa colorida escapa do
           .block-container central, mas o conteúdo de dentro dela fica
           alinhado com uma largura máxima, como no site oficial do GREI. */
        .grei-header {{
            background-color: {VERDE_ESCURO};
            width: 100vw;
            position: relative;
            left: 50%;
            right: 50%;
            margin-left: -50vw;
            margin-right: -50vw;
            margin-top: -1.2rem;   /* cancela o padding-top do block-container, encostando no topo */
            margin-bottom: 2.2rem;
            padding: 1.6rem clamp(20px, 5vw, 70px) 2.6rem;
        }}
        .grei-header-inner {{ max-width: 1000px; margin: 0 auto; }}

        .grei-header-topo {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.8rem;
        }}
        .grei-header img {{ height: 70px; flex-shrink: 0; }}

        .grei-social {{ display: flex; gap: 0.7rem; }}
        .grei-social a {{
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background-color: rgba(255, 255, 255, 0.14);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.15s ease;
        }}
        .grei-social a:hover {{ background-color: rgba(255, 255, 255, 0.28); }}
        .grei-social svg {{ width: 19px; height: 19px; fill: #ffffff; }}

        .grei-header .titulo-principal {{
            color: #ffffff !important;
            font-size: clamp(1.6rem, 2.8vw, 2.2rem);
            font-weight: 700;
            line-height: 1.25;
            margin: 0;
        }}
        .grei-header .subtitulo {{
            color: #cfe8dc !important;
            font-size: 1rem;
            font-weight: 500;
            margin: 0.35rem 0 0 0;
            letter-spacing: 0.02em;
        }}

        /* ── Rodapé GREI (também em fluxo normal) ─────────────────────── */
        .grei-footer {{
            background-color: {VERDE_ESCURO};
            border-radius: 16px;
            padding: 1rem 1.5rem;
            margin-top: 2rem;
            text-align: center;
        }}
        .grei-footer p {{ color: #dff2e6 !important; margin: 0; font-size: 0.85rem; }}

        .resumo-linha {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #dce8d5;
            font-size: 1rem;
        }}
        .resumo-linha:last-child {{ border-bottom: none; }}
        .resumo-chave {{ color: #5a7566; }}
        .resumo-valor {{ font-weight: 600; color: {VERDE_ESCURO}; }}

        /* ── Botões ────────────────────────────────────────────────── */
        div.stButton > button {{
            border-radius: 8px;
            padding: 0.6rem 1.4rem;
            font-weight: 600;
            border: 2px solid {VERDE_ESCURO};
            background-color: transparent;
        }}
        div.stButton > button p {{ color: {VERDE_ESCURO} !important; margin: 0; }}
        div.stButton > button:hover {{ background-color: rgba(47, 93, 75, 0.08); }}

        div.stButton > button[kind="primary"] {{
            background-color: {VERDE_VIVO};
            border-color: {VERDE_VIVO};
        }}
        div.stButton > button[kind="primary"] p {{ color: #ffffff !important; }}
        div.stButton > button[kind="primary"]:hover {{ background-color: {VERDE_ESCURO}; border-color: {VERDE_ESCURO}; }}

        /* ── Tags do multiselect (versão atual do Streamlit usa [data-tag], não [data-baseweb="tag"]) ── */
        span[data-tag] {{
            background-color: {VERDE_VIVO} !important;
            color: #ffffff !important;
        }}

        /* ── Bolinha do radio selecionado ─────────────────────────── */
        /* :first-child é essencial aqui: sem ele, o seletor também pega a
           div do texto da opção (irmã do círculo) e pinta o rótulo de verde
           sobre verde, deixando o texto invisível. */
        label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child {{
            background-color: {VERDE_VIVO} !important;
            border-color: {VERDE_VIVO} !important;
        }}
        label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child > div {{
            background-color: #ffffff !important;
        }}

        /* ── Terminal / log do docker compose — bem maior e com cara de terminal ── */
        .terminal-titulo {{
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 0.5rem 1rem;
            border-radius: 10px 10px 0 0;
            font-family: "Consolas", "Menlo", monospace;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .terminal-titulo .bolinha {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; }}
        [data-testid="stCodeBlock"] {{
            border-radius: 0 0 10px 10px !important;
        }}
        [data-testid="stCodeBlock"] pre {{
            min-height: 520px !important;
            max-height: 620px !important;
            overflow-y: auto !important;
            font-size: 0.82rem !important;
            border-radius: 0 0 10px 10px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sem_linhas_em_branco(html):
    """Remove linhas em branco/indentação de um bloco de HTML antes de
    passar pro st.markdown. Necessário porque uma linha em branco no meio
    de um bloco de HTML faz o parser markdown do Streamlit "sair" do modo
    HTML bruto e voltar a interpretar o resto como markdown — e aí
    qualquer linha indentada vira um bloco de código (aparece cru na tela)."""
    linhas = [linha.strip() for linha in html.strip().split("\n")]
    return "\n".join(linha for linha in linhas if linha)


GITHUB_URL = "https://github.com/grei-ufc"
LINKEDIN_URL = "https://www.linkedin.com/company/grei-ufc/"

_ICONE_GITHUB = _sem_linhas_em_branco("""
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
<path d="M12 .5C5.73.5.5 5.73.5 12c0 5.09 3.29 9.4 7.86 10.93.58.11.79-.25.79-.56
0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08
-.71.08-.71 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.71 1.25 3.37.96.1-.75.4-1.25.73-1.54
-2.55-.29-5.23-1.28-5.23-5.7 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.04 0 0 .97-.31
3.18 1.18a11.1 11.1 0 0 1 2.9-.39c.98 0 1.97.13 2.9.39 2.2-1.49 3.17-1.18 3.17-1.18.64 1.58
.24 2.75.12 3.04.74.8 1.19 1.83 1.19 3.09 0 4.43-2.69 5.4-5.25 5.69.41.36.78 1.07.78 2.15
0 1.55-.01 2.8-.01 3.18 0 .31.21.68.8.56A10.51 10.51 0 0 0 23.5 12c0-6.27-5.23-11.5-11.5-11.5z"/>
</svg>
""")

_ICONE_LINKEDIN = _sem_linhas_em_branco("""
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
<path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.15 1.45-2.15 2.95v5.66h
-3.55V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.59 0 4.25 2.36 4.25 5.44v6.3zM5.34 7.43a
2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45z"/>
</svg>
""")


def exibir_cabecalho_grei():
    logo_b64 = get_base64_image(CAMINHO_LOGO)
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="GREI">' if logo_b64 else ""
    st.markdown(
        _sem_linhas_em_branco(f"""
        <div class="grei-header">
            <div class="grei-header-inner">
                <div class="grei-header-topo">
                    {logo_html}
                    <div class="grei-social">
                        <a href="{GITHUB_URL}" target="_blank" rel="noopener noreferrer" title="GitHub do GREI">
                            {_ICONE_GITHUB}
                        </a>
                        <a href="{LINKEDIN_URL}" target="_blank" rel="noopener noreferrer" title="LinkedIn do GREI">
                            {_ICONE_LINKEDIN}
                        </a>
                    </div>
                </div>
                <p class="titulo-principal">Co-Simulação PADE + OMNeT++ + Mosaik</p>
                <p class="subtitulo">GRUPO DE REDES ELÉTRICAS INTELIGENTES (GREI) · UFC</p>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def exibir_rodape_grei():
    st.markdown(
        _sem_linhas_em_branco("""
        <div class="grei-footer">
            <p>Desenvolvido pelo Grupo de Redes Elétricas Inteligentes (GREI) — Universidade Federal do Ceará (UFC)</p>
        </div>
        """),
        unsafe_allow_html=True,
    )


def exibir_titulo_terminal():
    st.markdown(
        _sem_linhas_em_branco("""
        <div class="terminal-titulo">
            <span class="bolinha" style="background:#ff5f56;"></span>
            <span class="bolinha" style="background:#ffbd2e;"></span>
            <span class="bolinha" style="background:#27c93f;"></span>
            &nbsp;docker compose up --build
        </div>
        """),
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# EXECUÇÃO DO DOCKER COMPOSE (com streaming de log)
# ══════════════════════════════════════════════════════════════

def rodar_docker_compose(env_extra, placeholder_log):
    env = os.environ.copy()
    env.update(env_extra)

    processo = subprocess.Popen(
        ["docker", "compose", "up", "--build"],
        cwd=RAIZ_PROJETO,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    linhas = []
    for linha in processo.stdout:
        linhas.append(linha.rstrip())
        placeholder_log.code("\n".join(linhas[-500:]) or "…", language="bash")

    processo.wait()
    return processo.returncode


def parar_docker_compose():
    subprocess.run(["docker", "compose", "down"], cwd=RAIZ_PROJETO)


# ══════════════════════════════════════════════════════════════
# INTERFACE
# ══════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="Co-Simulação GREI - TSCC",
        page_icon=CAMINHO_LOGO if os.path.exists(CAMINHO_LOGO) else None,
        initial_sidebar_state="collapsed",
    )
    aplicar_estilo()
    exibir_cabecalho_grei()

    # ── 1. Topologia ─────────────────────────────────────────
    st.subheader("1. Topologia de rede")
    topologia = st.radio(
        "Topologia",
        options=list(TOPOLOGIAS.keys()),
        format_func=lambda k: TOPOLOGIAS[k]["label"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.caption(TOPOLOGIAS[topologia]["desc"])

    # ── 2. Número de periféricos ─────────────────────────────
    st.subheader("2. Número de agentes periféricos")
    num_perifericos = st.number_input(
        "Periféricos", min_value=1, max_value=200, value=4, step=1,
        label_visibility="collapsed",
    )
    total_agentes = num_perifericos + 1

    # Texto do total varia conforme a topologia escolhida, em vez de
    # sempre mencionar as três variações (central/malha/anel) juntas.
    if topologia == "estrela":
        detalhe_total = f"1 central + {num_perifericos} periféricos"
    elif topologia == "malha":
        detalhe_total = f"{total_agentes} agentes, todos conectados entre si"
    else:  # anel
        detalhe_total = f"{total_agentes} agentes em ciclo fechado"

    st.caption(f"Total de agentes na simulação: **{total_agentes}** ({detalhe_total}).")

    # Aviso de desempenho: na malha o número de enlaces cresce em
    # (N+1)*N/2, então N grande deixa a compilação/execução do OMNeT++
    # bem mais pesada. Estrela e anel escalam de forma linear (não têm
    # esse problema), então o aviso só aparece pra malha.
    if topologia == "malha" and num_perifericos > 50:
        n_enlaces = total_agentes * num_perifericos // 2
        st.warning(
            f"Malha com {num_perifericos} periféricos gera **{n_enlaces:,}".replace(",", ".") +
            f"** enlaces (cresce em N²). A compilação do OMNeT++ e a simulação "
            f"ficam bem mais lentas — considere reduzir, a não ser que seja isso mesmo que você quer testar."
        )

    # ── 3. Tipos de enlace ────────────────────────────────────
    st.subheader("3. Tipos de enlace")
    chaves_rede = list(REDES.keys())
    tipos_selecionados = st.multiselect(
        "Redes",
        options=chaves_rede,
        default=chaves_rede,
        format_func=lambda k: REDES[k][0],
        label_visibility="collapsed",
    )

    if not tipos_selecionados:
        st.warning("Selecione ao menos um tipo de enlace para continuar.")
        st.stop()

    # ── Resumo ────────────────────────────────────────────────
    nomes_redes = ", ".join(REDES[t][0] for t in tipos_selecionados)
    st.markdown(
        _sem_linhas_em_branco(f"""
        <div style="margin-top: 1.8rem; margin-bottom: 1.5rem;">
            <h3 style="margin-top: 0; color: {VERDE_ESCURO}; font-weight: 700;">Resumo da configuração</h3>
            <div class="resumo-linha"><span class="resumo-chave">Topologia</span>
                <span class="resumo-valor">{TOPOLOGIAS[topologia]['label']}</span></div>
            <div class="resumo-linha"><span class="resumo-chave">Periféricos</span>
                <span class="resumo-valor">{num_perifericos}</span></div>
            <div class="resumo-linha"><span class="resumo-chave">Redes</span>
                <span class="resumo-valor">{nomes_redes}</span></div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # ── Ações ─────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    iniciar = col1.button("Iniciar simulação", type="primary", use_container_width=True)
    parar = col2.button("Parar / limpar containers", use_container_width=True)

    if parar:
        with st.spinner("Derrubando containers..."):
            parar_docker_compose()
        st.success("Containers parados.")

    if iniciar:
        env_extra = {
            "TOPOLOGY": topologia,
            "NUM_PERIFERICOS": str(num_perifericos),
            "TIPOS_REDE": ",".join(tipos_selecionados),
        }

        st.write("")
        st.markdown(f"**Iniciando co-simulação** ({topologia} · {num_perifericos} periféricos)…")
        exibir_titulo_terminal()
        placeholder_log = st.empty()

        codigo = rodar_docker_compose(env_extra, placeholder_log)

        if codigo == 0:
            st.success("Co-simulação concluída.")
        else:
            st.error(f"docker compose encerrou com erro (código {codigo}).")

    exibir_rodape_grei()


if __name__ == "__main__":
    main()