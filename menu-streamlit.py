#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu_streamlit.py — Configurador web da co-simulação PADE + OMNeT++ + Mosaik.

Novidades:
  - Atribuição de tecnologia POR AGENTE (estrela/anel) ou por sequência (malha)
  - Terminal colapsável dentro da interface (sem parar a simulação)
  - Gráficos exibidos somente ao final de cada co-simulação (sem resíduos de rodadas anteriores)
"""

import base64, json, math, os, re, subprocess
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════

TOPOLOGIAS = {
    "estrela": {"label": "Estrela", "desc": "1 agente central conectado a N periféricos."},
    "malha":   {"label": "Malha",   "desc": "Todos os agentes conectados entre si (full mesh)."},
    "anel":    {"label": "Anel",    "desc": "Cada agente conectado apenas ao próximo, em ciclo fechado."},
}

REDES = {
    "Link_Wired":    ("Cabeada",  "1 Gbps · delay 1ms · 0% perda"),
    "Link_5G":       ("5G",       "500 Mbps · ~5ms · 0.001% perda"),
    "Link_Wireless": ("Wireless", "300 Mbps · ~2ms · 0.1% perda"),
    "Link_4G":       ("4G",       "50 Mbps · ~35ms · 0.5% perda"),
    "Link_2G":       ("2G",       "250 kbps · ~200ms · 15% perda"),
}

CORES_REDE = {
    "Link_Wired": "#1f77b4", "Link_5G": "#2ca02c",
    "Link_Wireless": "#17becf", "Link_4G": "#ff7f0e", "Link_2G": "#9467bd",
}

RAIZ_PROJETO = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO = os.path.join(RAIZ_PROJETO, "LOGO.png")
MOSAIK_DIR   = os.path.join(RAIZ_PROJETO, "mosaik-dir")
OMNET_DIR    = os.path.join(RAIZ_PROJETO, "omnet-dir")

VERDE_ESCURO = "#2F5D4B"
VERDE_VIVO   = "#007024"
FUNDO_CLARO  = "#F4FFEB"

# ══════════════════════════════════════════════════════════════
# SVG ICONS
# ══════════════════════════════════════════════════════════════

_SVG_SERVER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="9" width="56" height="14" rx="3" fill="#2F5D4B"/><rect x="4" y="25" width="56" height="14" rx="3" fill="#2F5D4B"/><rect x="4" y="41" width="56" height="14" rx="3" fill="#2F5D4B"/><circle cx="53" cy="16" r="3.5" fill="#00e676"/><circle cx="53" cy="32" r="3.5" fill="#ffeb3b"/><circle cx="53" cy="48" r="3.5" fill="#ff5252"/></svg>'
_SVG_PC     = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="4" width="56" height="40" rx="3" fill="#2F5D4B"/><rect x="8" y="8" width="48" height="32" rx="2" fill="#1a3a2a"/><text x="32" y="29" text-anchor="middle" fill="#00e676" font-size="16" font-family="monospace">&gt;_</text><rect x="24" y="44" width="16" height="8" fill="#1a3a2a"/><rect x="14" y="52" width="36" height="5" rx="2.5" fill="#2F5D4B"/></svg>'
_SVG_ROUTER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="22" width="56" height="20" rx="10" fill="#2F5D4B"/><line x1="18" y1="22" x2="14" y2="10" stroke="#2F5D4B" stroke-width="4" stroke-linecap="round"/><line x1="32" y1="22" x2="32" y2="8" stroke="#2F5D4B" stroke-width="4" stroke-linecap="round"/><line x1="46" y1="22" x2="50" y2="10" stroke="#2F5D4B" stroke-width="4" stroke-linecap="round"/><circle cx="54" cy="32" r="4" fill="#00e676"/></svg>'

def _svg_img(svg, size=52):
    b64 = base64.b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" style="width:{size}px;height:{size}px;object-fit:contain;">'

def _load_svg_colored(filename):
    path = os.path.join(RAIZ_PROJETO, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            svg = f.read()
        svg = re.sub(r'fill="(?!none)[^"]*"',   f'fill="{VERDE_ESCURO}"',   svg)
        svg = re.sub(r'stroke="(?!none)[^"]*"', f'stroke="{VERDE_ESCURO}"', svg)
        return svg
    except Exception:
        return None

def _svg_from_file_or_fallback(filename, fallback, size=52):
    svg = _load_svg_colored(filename) if filename else None
    if svg:
        b64 = base64.b64encode(svg.encode()).decode()
        return f'<img src="data:image/svg+xml;base64,{b64}" style="width:{size}px;height:{size}px;object-fit:contain;">'
    return _svg_img(fallback, size)

def get_b64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def _strip(html):
    return "\n".join(l.strip() for l in html.strip().split("\n") if l.strip())

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════

def aplicar_estilo():
    st.markdown(f"""<style>
    .stApp{{background-color:{FUNDO_CLARO};}}
    header[data-testid="stHeader"]{{display:none;}}
    html,body,[class*="css"]{{font-family:"Inter","Segoe UI",sans-serif;}}
    .block-container{{max-width:960px!important;padding-top:1.2rem!important;padding-bottom:2rem!important;}}
    .stApp .block-container h1,.stApp .block-container h2,.stApp .block-container h3{{color:{VERDE_ESCURO};font-weight:700;margin-top:1.6rem;margin-bottom:.4rem;}}
    .stApp p,.stApp label,.stCaption,.stMarkdown{{color:{VERDE_ESCURO};}}
    .grei-header{{background-color:{VERDE_ESCURO};width:100vw;position:relative;left:50%;right:50%;margin-left:-50vw;margin-right:-50vw;margin-top:-1.2rem;margin-bottom:2.2rem;padding:1.6rem clamp(20px,5vw,70px) 2.6rem;}}
    .grei-header-inner{{max-width:1000px;margin:0 auto;}}
    .grei-header-topo{{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.8rem;}}
    .grei-header img{{height:70px;flex-shrink:0;}}
    .grei-social{{display:flex;gap:.7rem;}}
    .grei-social a{{width:38px;height:38px;border-radius:50%;background-color:rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;transition:background-color .15s;}}
    .grei-social a:hover{{background-color:rgba(255,255,255,.28);}}
    .grei-social svg{{width:19px;height:19px;fill:#fff;}}
    .grei-header .titulo-principal{{color:#fff!important;font-size:clamp(1.6rem,2.8vw,2.2rem);font-weight:700;line-height:1.25;margin:0;}}
    .grei-header .subtitulo{{color:#cfe8dc!important;font-size:1rem;font-weight:500;margin:.35rem 0 0;letter-spacing:.02em;}}
    .grei-footer{{background-color:{VERDE_ESCURO};border-radius:16px;padding:1rem 1.5rem;margin-top:2rem;text-align:center;}}
    .grei-footer p{{color:#dff2e6!important;margin:0;font-size:.85rem;}}
    .resumo-linha{{display:flex;justify-content:space-between;padding:.5rem 0;border-bottom:1px solid #dce8d5;font-size:1rem;}}
    .resumo-linha:last-child{{border-bottom:none;}}
    .resumo-chave{{color:#5a7566;}} .resumo-valor{{font-weight:600;color:{VERDE_ESCURO};}}
    div.stButton>button{{border-radius:8px;padding:.6rem 1.4rem;font-weight:600;border:2px solid {VERDE_ESCURO};background-color:transparent;}}
    div.stButton>button p{{color:{VERDE_ESCURO}!important;margin:0;}}
    div.stButton>button:hover{{background-color:rgba(47,93,75,.08);}}
    div.stButton>button[kind="primary"]{{background-color:{VERDE_VIVO};border-color:{VERDE_VIVO};}}
    div.stButton>button[kind="primary"] p{{color:#fff!important;}}
    div.stButton>button[kind="primary"]:hover{{background-color:{VERDE_ESCURO};border-color:{VERDE_ESCURO};}}
    span[data-tag]{{background-color:{VERDE_VIVO}!important;color:#fff!important;}}
    label[data-testid="stRadioOption"][data-selected="true"]>div>div>div:first-child{{background-color:{VERDE_VIVO}!important;border-color:{VERDE_VIVO}!important;}}
    label[data-testid="stRadioOption"][data-selected="true"]>div>div>div:first-child>div{{background-color:#fff!important;}}
    [data-testid="stCodeBlock"]{{border-radius:0 0 10px 10px!important;}}
    [data-testid="stCodeBlock"] pre{{min-height:400px!important;max-height:600px!important;overflow-y:auto!important;font-size:.82rem!important;}}
    .icon-card{{background:white;border:1.5px solid #c8e6c9;border-radius:12px;padding:14px 10px;text-align:center;font-size:.8rem;color:{VERDE_ESCURO};}}
    .tech-agente-label{{font-weight:600;color:{VERDE_ESCURO};font-size:.9rem;padding:.3rem 0;}}
    </style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CABEÇALHO / RODAPÉ
# ══════════════════════════════════════════════════════════════

_ICO_GH = _strip('<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 .5C5.73.5.5 5.73.5 12c0 5.09 3.29 9.4 7.86 10.93.58.11.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.71 1.25 3.37.96.1-.75.4-1.25.73-1.54-2.55-.29-5.23-1.28-5.23-5.7 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.04 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 2.9-.39c.98 0 1.97.13 2.9.39 2.2-1.49 3.17-1.18 3.17-1.18.64 1.58.24 2.75.12 3.04.74.8 1.19 1.83 1.19 3.09 0 4.43-2.69 5.4-5.25 5.69.41.36.78 1.07.78 2.15 0 1.55-.01 2.8-.01 3.18 0 .31.21.68.8.56A10.51 10.51 0 0 0 23.5 12c0-6.27-5.23-11.5-11.5-11.5z"/></svg>')
_ICO_LI = _strip('<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.15 1.45-2.15 2.95v5.66h-3.55V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.59 0 4.25 2.36 4.25 5.44v6.3zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45z"/></svg>')

def exibir_cabecalho_grei():
    logo_b64  = get_b64(CAMINHO_LOGO)
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="GREI">' if logo_b64 else ""
    st.markdown(_strip(f"""
    <div class="grei-header"><div class="grei-header-inner">
    <div class="grei-header-topo">{logo_html}
    <div class="grei-social">
    <a href="https://github.com/grei-ufc" target="_blank">{_ICO_GH}</a>
    <a href="https://www.linkedin.com/company/grei-ufc/" target="_blank">{_ICO_LI}</a>
    </div></div>
    <p class="titulo-principal">Co-Simulação PADE + OMNeT++ + Mosaik</p>
    <p class="subtitulo">GRUPO DE REDES ELÉTRICAS INTELIGENTES (GREI) · UFC</p>
    </div></div>"""), unsafe_allow_html=True)

def exibir_rodape_grei():
    st.markdown('<div class="grei-footer"><p>Desenvolvido pelo Grupo de Redes Elétricas Inteligentes (GREI) — Universidade Federal do Ceará (UFC)</p></div>', unsafe_allow_html=True)

def exibir_secao_icones():
    st.subheader("🖼 Ícones dos Agentes (OMNeT++)")
    icones = [
        ("server-svgrepo-com.svg",             _SVG_SERVER, "Central / Servidor"),
        ("laptop-minimalistic-svgrepo-com.svg", _SVG_PC,     "Periférico / PC"),
        ("router-bottom-1112-svgrepo-com.svg",  _SVG_ROUTER, "Roteador"),
    ]
    cols = st.columns(len(icones))
    for col, (svg_file, svg_fb, desc) in zip(cols, icones):
        with col:
            img = _svg_from_file_or_fallback(svg_file, svg_fb, 52)
            st.markdown(f'<div class="icon-card">{img}<br><span style="font-size:.78rem;color:{VERDE_ESCURO}">{desc}</span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PREVIEW DA TOPOLOGIA
# ══════════════════════════════════════════════════════════════

def _posicoes(topologia, n_total):
    raio = 350
    if topologia == "estrela":
        pos = {"agent_central": (500, 500)}
        for i in range(n_total - 1):
            ang = 2 * math.pi * i / (n_total - 1)
            pos[f"agent_p_{i+1}"] = (500 + raio*math.cos(ang), 500 + raio*math.sin(ang))
        return pos
    elif topologia == "malha":
        pos = {}
        for i in range(n_total):
            ang = 2 * math.pi * i / n_total
            pos[f"agente_{i+1}"] = (500 + raio*math.cos(ang), 500 + raio*math.sin(ang))
        return pos
    else:
        pos = {}
        for i in range(n_total):
            ang = 2 * math.pi * i / n_total
            pos[f"agente_{i+1}"] = (500 + raio*math.cos(ang), 500 + raio*math.sin(ang))
        return pos

def _links_preview(topologia, pos, tipos_lista):
    ids = list(pos.keys()); n = len(ids); links = []
    if topologia == "estrela":
        central = ids[0]
        for i, pid in enumerate(ids[1:]):
            links.append((central, pid, tipos_lista[i % len(tipos_lista)]))
    elif topologia == "malha":
        c = 0
        for i in range(n):
            for j in range(i+1, n):
                links.append((ids[i], ids[j], tipos_lista[c % len(tipos_lista)])); c += 1
    else:
        for i in range(n):
            links.append((ids[i], ids[(i+1)%n], tipos_lista[i % len(tipos_lista)]))
    return links

def exibir_preview_topologia(topologia, num_perifericos, tipos_lista):
    st.subheader("🗺 Preview da Topologia")
    n_total = num_perifericos + 1 if topologia == "estrela" else num_perifericos
    pos   = _posicoes(topologia, n_total)
    links = _links_preview(topologia, pos, tipos_lista)
    fig   = go.Figure()

    por_tech = {}
    for orig, dest, tech in links:
        por_tech.setdefault(tech, {"x": [], "y": []})
        x0,y0 = pos[orig]; x1,y1 = pos[dest]
        por_tech[tech]["x"].extend([x0, x1, None])
        por_tech[tech]["y"].extend([y0, y1, None])

    for tech, dados in por_tech.items():
        cor  = CORES_REDE.get(tech, "#888")
        nome = REDES[tech][0] if tech in REDES else tech.replace("Link_","")
        fig.add_trace(go.Scatter(x=dados["x"], y=dados["y"], mode="lines",
                                 line=dict(color=cor, width=3), name=nome,
                                 showlegend=True, legendgroup=tech, hoverinfo="skip"))

    ids   = list(pos.keys())
    cores = ["#007024" if ("central" in n) else "#2F5D4B" for n in ids]
    tams  = [26 if "central" in n else 18 for n in ids]
    labs  = ["Central" if "central" in n else n.replace("agent_p_","P").replace("agente_","A") for n in ids]
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in ids], y=[pos[n][1] for n in ids],
                             mode="markers+text",
                             marker=dict(size=tams, color=cores, line=dict(width=2, color="white")),
                             text=labs, textposition="top center",
                             textfont=dict(size=10, color="#1a3a2a"),
                             name="Agentes", showlegend=False, hovertext=ids, hoverinfo="text"))

    fig.update_layout(
        title=dict(text=f"<b>{TOPOLOGIAS[topologia]['label']}</b> — {n_total} agentes · {len(links)} enlaces",
                   font=dict(size=15, color=VERDE_ESCURO)),
        paper_bgcolor=FUNDO_CLARO, plot_bgcolor=FUNDO_CLARO,
        font=dict(color=VERDE_ESCURO),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1),
        legend=dict(title=dict(text="Tecnologia", font=dict(size=12, color=VERDE_ESCURO)),
                    font=dict(size=12, color=VERDE_ESCURO),
                    bgcolor="rgba(244,255,235,0.92)", bordercolor="#a5d6a7", borderwidth=1),
        margin=dict(t=50, b=20, l=20, r=20), height=440)

    st.plotly_chart(fig, use_container_width=True)

    if topologia == "anel":
        st.info("↔ **Anel bidirecional**: cada enlace permite envio e recebimento simultâneos. "
                "Agentes não-adjacentes não se comunicam diretamente.")
    if topologia == "malha" and num_perifericos > 30:
        n_e = n_total*(n_total-1)//2
        st.warning(f"⚠ Malha com {num_perifericos} agentes gera {n_e} enlaces — compilação do OMNeT++ ficará mais lenta.")

# ══════════════════════════════════════════════════════════════
# SELEÇÃO DE TECNOLOGIAS COM ATRIBUIÇÃO POR AGENTE
# ══════════════════════════════════════════════════════════════

def selecionar_tecnologias(topologia, num_perifericos):
    """
    Retorna a lista final de ned-ids de tecnologias (uma por agente/link ou pool).
    Para estrela/anel: permite atribuição individual por agente.
    Para malha:       usa pool com distribuição cíclica automática.
    """
    st.subheader("3. Tecnologias de enlace")
    chaves = list(REDES.keys())

    pool = st.multiselect("Pool de tecnologias disponíveis",
                          options=chaves, default=chaves,
                          format_func=lambda k: REDES[k][0],
                          label_visibility="collapsed")
    if not pool:
        st.warning("Selecione ao menos uma tecnologia.")
        st.stop()

    n_total = num_perifericos + 1 if topologia == "estrela" else num_perifericos

    # ── Atribuição por agente (estrela e anel) ──────────────
    if topologia in ("estrela", "anel"):
        with st.expander("Definir tecnologia por agente (opcional)", expanded=False):
            if topologia == "estrela":
                st.caption("Cada linha representa o enlace daquele periférico com o nó central.")
                agentes_labels = [f"Periférico {i}" for i in range(1, num_perifericos + 1)]
            else:
                st.caption("Cada linha representa o enlace agente_i → agente_{i+1} (cíclico).")
                agentes_labels = [f"Agente {i} → Agente {(i % n_total) + 1}"
                                  for i in range(1, n_total + 1)]

            opcoes = ["Auto (cíclico)"] + [REDES[k][0] for k in pool]
            ned_por_label = {"Auto (cíclico)": None}
            ned_por_label.update({REDES[k][0]: k for k in pool})

            tipos_finais = []
            MAX_VISIVEIS = 20
            n_mostrar = min(len(agentes_labels), MAX_VISIVEIS)

            for i in range(n_mostrar):
                col_a, col_b = st.columns([2, 3])
                col_a.markdown(f'<div class="tech-agente-label">{agentes_labels[i]}</div>',
                               unsafe_allow_html=True)
                escolha = col_b.selectbox("", options=opcoes,
                                          key=f"tech_agente_{topologia}_{i}",
                                          label_visibility="collapsed")
                ned = ned_por_label[escolha] or pool[i % len(pool)]
                tipos_finais.append(ned)

            if len(agentes_labels) > MAX_VISIVEIS:
                st.caption(f"… {len(agentes_labels) - MAX_VISIVEIS} agente(s) restantes "
                           f"usarão a distribuição cíclica do pool.")
                for i in range(MAX_VISIVEIS, len(agentes_labels)):
                    tipos_finais.append(pool[i % len(pool)])

            # Verifica se algum agente foi personalizado
            todos_auto = all(
                st.session_state.get(f"tech_agente_{topologia}_{i}", "Auto (cíclico)") == "Auto (cíclico)"
                for i in range(n_mostrar)
            )
            if todos_auto:
                return pool   # usa pool diretamente (cycling padrão)
            return tipos_finais

    # ── Malha: apenas pool cíclico ──────────────────────────
    else:
        n_e = n_total * (n_total - 1) // 2
        st.caption(f"As tecnologias do pool serão distribuídas ciclicamente sobre os {n_e} enlaces da malha.")
        return pool

# ══════════════════════════════════════════════════════════════
# RESULTADOS
# ══════════════════════════════════════════════════════════════

def exibir_resultados(topologia):
    st.divider()
    st.subheader("Resultados da Simulação")

    if topologia == "malha":
        png = os.path.join(MOSAIK_DIR, "grafico_trafego_Geral.png")
        # tenta também o nome legado
        if not os.path.exists(png):
            png = os.path.join(MOSAIK_DIR, "grafico_malha.png")
        if os.path.exists(png):
            pngs_malha = sorted([f for f in os.listdir(MOSAIK_DIR)
                                  if f.startswith("grafico_") and f.endswith(".png")])
            for pf in pngs_malha:
                label = pf.replace("grafico_trafego_","").replace("grafico_","").replace(".png","")
                st.caption(f"Visão: **{label}**")
                st.image(os.path.join(MOSAIK_DIR, pf), use_container_width=True)
                st.write("")
        else:
            st.warning("Gráfico da malha não encontrado em mosaik-dir/.")
    else:
        pngs = sorted([f for f in os.listdir(MOSAIK_DIR)
                       if f.startswith("grafico_trafego_") and f.endswith(".png")])
        if pngs:
            for pf in pngs:
                label = pf.replace("grafico_trafego_","").replace(".png","")
                st.caption(f"Visão: **{label}**")
                st.image(os.path.join(MOSAIK_DIR, pf), use_container_width=True)
                st.write("")
        else:
            st.warning("Nenhum gráfico encontrado em mosaik-dir/.")

# ══════════════════════════════════════════════════════════════
# DOCKER
# ══════════════════════════════════════════════════════════════

def rodar_docker_compose(env_extra, placeholder_log):
    env = os.environ.copy(); env.update(env_extra)
    ned_residual = os.path.join(OMNET_DIR, "DynamicNetwork.ned")
    if os.path.exists(ned_residual):
        try:
            os.remove(ned_residual)
        except OSError:
            pass
    proc = subprocess.Popen(
        ["docker", "compose", "up", "--build", "--force-recreate",
         "--abort-on-container-exit",
         "--exit-code-from", "mosaik_master"],
        cwd=RAIZ_PROJETO, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1)
    linhas = []
    for linha in proc.stdout:
        linhas.append(linha.rstrip())
        placeholder_log.code("\n".join(linhas[-500:]) or "…", language="bash")
    proc.wait()
    return proc.returncode

def parar_docker_compose():
    subprocess.run(["docker", "compose", "down"], cwd=RAIZ_PROJETO)

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    st.set_page_config(page_title="Co-Simulação GREI - TSCC",
                       page_icon=CAMINHO_LOGO if os.path.exists(CAMINHO_LOGO) else None,
                       layout="wide", initial_sidebar_state="collapsed")
    aplicar_estilo()
    exibir_cabecalho_grei()

    # Session state
    for k, v in [("sim_concluida", False), ("sim_topologia", "estrela")]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Abas: Configuração / Resultados ───────────────────────
    tab_config, tab_resultados = st.tabs(["Configuração", "Resultados"])

    with tab_config:
        # ── 1. Topologia ─────────────────────────────────────
        st.subheader("1. Topologia de rede")
        topologia = st.radio("Topologia", options=list(TOPOLOGIAS.keys()),
                             format_func=lambda k: TOPOLOGIAS[k]["label"],
                             horizontal=True, label_visibility="collapsed")
        st.caption(TOPOLOGIAS[topologia]["desc"])

        # ── 2. Número de agentes ─────────────────────────────
        if topologia == "estrela":
            st.subheader("2. Número de agentes periféricos")
            rotulo_resumo = "Periféricos"
        else:
            st.subheader("2. Número total de agentes")
            rotulo_resumo = "Agentes"

        min_val = 3 if topologia == "anel" else (2 if topologia == "malha" else 1)
        num_perifericos = st.number_input("Agentes", min_value=min_val, max_value=500,
                                          value=max(4, min_val), step=1,
                                          label_visibility="collapsed")
        total_agentes = num_perifericos + 1 if topologia == "estrela" else num_perifericos

        if topologia == "estrela":
            detalhe = f"1 central + {num_perifericos} periféricos"
        elif topologia == "malha":
            detalhe = f"{total_agentes} agentes peers, todos conectados entre si"
        else:
            detalhe = f"{total_agentes} agentes peers em ciclo fechado"
        st.caption(f"Total na simulação: **{total_agentes}** ({detalhe}).")

        # ── 3. Tecnologias (com atribuição por agente) ────────
        tipos_lista = selecionar_tecnologias(topologia, num_perifericos)

        # ── Ícones e Preview ──────────────────────────────────
        exibir_secao_icones()
        exibir_preview_topologia(topologia, num_perifericos, tipos_lista)

        # ── Resumo ──────────────────────────────────────────
        nomes_redes = ", ".join(dict.fromkeys(REDES[t][0] for t in tipos_lista if t in REDES))
        st.markdown(_strip(f"""
        <div style="margin-top:1.8rem;margin-bottom:1.5rem;">
        <h3 style="margin-top:0;color:{VERDE_ESCURO};font-weight:700;">Resumo da configuração</h3>
        <div class="resumo-linha"><span class="resumo-chave">Topologia</span>
            <span class="resumo-valor">{TOPOLOGIAS[topologia]['label']}</span></div>
        <div class="resumo-linha"><span class="resumo-chave">{rotulo_resumo}</span>
            <span class="resumo-valor">{num_perifericos}</span></div>
        <div class="resumo-linha"><span class="resumo-chave">Redes</span>
            <span class="resumo-valor">{nomes_redes}</span></div>
        </div>"""), unsafe_allow_html=True)

        # ── Botões ────────────────────────────────────────────
        col1, col2 = st.columns(2)
        iniciar = col1.button("Iniciar simulação", type="primary", use_container_width=True)
        parar   = col2.button("Parar / limpar containers", use_container_width=True)

        if parar:
            with st.spinner("Derrubando containers..."):
                parar_docker_compose()
            st.success("Containers parados.")
            st.session_state.sim_concluida = False

        if iniciar:
            st.session_state.sim_concluida = False
            st.session_state.sim_topologia = topologia

            # Limpa gráficos de rodadas anteriores para não exibir dados velhos
            # enquanto a nova co-simulação ainda está em andamento.
            if os.path.exists(MOSAIK_DIR):
                for f in os.listdir(MOSAIK_DIR):
                    if f.startswith("grafico_") and f.endswith(".png"):
                        try:
                            os.remove(os.path.join(MOSAIK_DIR, f))
                        except Exception:
                            pass

            env_extra = {
                "TOPOLOGY":        topologia,
                "NUM_PERIFERICOS": str(num_perifericos),
                "TIPOS_REDE":      ",".join(tipos_lista),
            }

            st.markdown(f"**Iniciando co-simulação** ({topologia} · {num_perifericos} agentes)…")

            # ── Terminal colapsável ──────────────────────────
            # O expander pode ser aberto/fechado pelo usuário a qualquer
            # momento sem parar a simulação — o log continua sendo
            # transmitido dentro do expander mesmo quando colapsado.
            with st.expander("Terminal", expanded=True):
                st.markdown(_strip("""
                <div style="background:#1e1e1e;color:#d4d4d4;padding:.5rem 1rem;
                            border-radius:6px 6px 0 0;font-family:Consolas,monospace;
                            font-size:.8rem;display:flex;align-items:center;gap:.4rem;">
                <span style="width:11px;height:11px;border-radius:50%;
                             background:#ff5f56;display:inline-block;"></span>
                <span style="width:11px;height:11px;border-radius:50%;
                             background:#ffbd2e;display:inline-block;"></span>
                <span style="width:11px;height:11px;border-radius:50%;
                             background:#27c93f;display:inline-block;"></span>
                &nbsp;docker compose up --build
                </div>"""), unsafe_allow_html=True)
                placeholder_log = st.empty()

            codigo = rodar_docker_compose(env_extra, placeholder_log)

            if codigo == 0:
                st.success("co-simulação concluída com sucesso!")
                st.info("Confira os gráficos na aba **Resultados**.")
                st.session_state.sim_concluida = True
            else:
                st.error(f"docker compose encerrou com erro (código {codigo}).")

    with tab_resultados:
        if st.session_state.sim_concluida:
            exibir_resultados(st.session_state.sim_topologia)
        else:
            st.info("Nenhuma co-simulação concluída ainda. Configure e clique em "
                    "**Iniciar simulação** na aba **Configuração**.")

    exibir_rodape_grei()

if __name__ == "__main__":
    main()