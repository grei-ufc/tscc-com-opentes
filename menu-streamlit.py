#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu_streamlit.py — Configurador web da co-simulação PADE + OMNeT++ + Mosaik.

Topologias suportadas:
  - estrela  : 1 agente central conectado a N periféricos
  - anel     : N agentes em ciclo fechado (bidirecional)
  - arvore   : árvore radial IEC 61850 com fan-out configurável
  - hibrida  : hierarquia CCO → fibra → celular → RF mesh
"""

import base64, json, math, os, re, subprocess, tempfile, threading, time
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

TOPOLOGIAS = {
    "estrela": {"label": "Estrela",  "desc": "1 agente central conectado a N periféricos."},
    "anel":    {"label": "Anel",     "desc": "Cada agente conectado apenas ao próximo, em ciclo fechado."},
    "arvore":  {"label": "Árvore",   "desc": "Árvore radial IEC 61850: raiz → subestações → concentradores → medidores."},
    "hibrida": {"label": "Híbrida",  "desc": "Backbone fibra (anel) + estrela celular + malha RF mesh por cluster."},
}
REDES = {
    "Link_Wired":    ("Cabeada",  "1 Gbps · delay 1ms · 0% perda"),
    "Link_5G":       ("5G",       "500 Mbps · ~5ms · 0.001% perda"),
    "Link_Wireless": ("Wireless", "100 Mbps · ~15ms · 3% perda"),
    "Link_4G":       ("4G",       "50 Mbps · ~35ms · 0.5% perda"),
    "Link_2G":       ("2G",       "250 kbps · ~200ms · 15% perda"),
}
CORES_REDE = {
    "Link_Wired": "#1f77b4", "Link_5G": "#2ca02c",
    "Link_Wireless": "#17becf", "Link_4G": "#ff7f0e", "Link_2G": "#9467bd",
}
# Canais novos (árvore / híbrida)
CORES_CANAL = {
    "Fibra": "#1f77b4", "Celular5G": "#2ca02c", "Celular4G": "#17becf",
    "Celular3G": "#ff7f0e", "Celular2G": "#9467bd",
    "PLC": "#8c564b", "RFMesh": "#bcbd22",
}
NOMES_CANAL = {
    "Fibra": "Fibra (1 Gbps)", "Celular5G": "5G (200 Mbps)",
    "Celular4G": "4G (50 Mbps)", "Celular3G": "3G (2 Mbps)",
    "Celular2G": "2G (100 kbps)", "PLC": "PLC (100 kbps)",
    "RFMesh": "RF Mesh (150 kbps)",
}
CELULAR_OPTIONS = ["2g", "3g", "4g", "5g"]
CELULAR_MAP     = {"2g": "Celular2G", "3g": "Celular3G", "4g": "Celular4G", "5g": "Celular5G"}
CORES_CAMADA    = {
    "controle":     "#007024",
    "subestacao":   "#1f77b4",
    "concentrador": "#ff7f0e",
    "medidor":      "#d62728",
}

RAIZ_PROJETO  = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO  = os.path.join(RAIZ_PROJETO, "LOGO.png")
MOSAIK_DIR    = os.path.join(RAIZ_PROJETO, "mosaik-dir")
VERDE_ESCURO  = "#2F5D4B"
VERDE_VIVO    = "#007024"
FUNDO_CLARO   = "#F4FFEB"

# ── SVG embutidos de fallback ────────────────────────────────
_SVG_SERVER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="9" width="56" height="14" rx="3" fill="#2F5D4B"/><rect x="4" y="25" width="56" height="14" rx="3" fill="#2F5D4B"/><rect x="4" y="41" width="56" height="14" rx="3" fill="#2F5D4B"/><circle cx="53" cy="16" r="3.5" fill="#00e676"/><circle cx="53" cy="32" r="3.5" fill="#ffeb3b"/><circle cx="53" cy="48" r="3.5" fill="#ff5252"/></svg>'
_SVG_PC     = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="4" width="56" height="40" rx="3" fill="#2F5D4B"/><rect x="8" y="8" width="48" height="32" rx="2" fill="#1a3a2a"/><text x="32" y="29" text-anchor="middle" fill="#00e676" font-size="16" font-family="monospace">&gt;_</text><rect x="24" y="44" width="16" height="8" fill="#1a3a2a"/><rect x="14" y="52" width="36" height="5" rx="2.5" fill="#2F5D4B"/></svg>'
_SVG_ROUTER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="22" width="56" height="20" rx="10" fill="#2F5D4B"/><line x1="18" y1="22" x2="14" y2="10" stroke="#2F5D4B" stroke-width="4" stroke-linecap="round"/><line x1="32" y1="22" x2="32" y2="8" stroke="#2F5D4B" stroke-width="4" stroke-linecap="round"/><line x1="46" y1="22" x2="50" y2="10" stroke="#2F5D4B" stroke-width="4" stroke-linecap="round"/><circle cx="54" cy="32" r="4" fill="#00e676"/></svg>'

def _svg_img(svg, size=52):
    b64 = base64.b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" style="width:{size}px;height:{size}px;object-fit:contain;">'

def _load_svg_colored(filename, color=VERDE_ESCURO):
    if not filename:
        return None
    path = os.path.join(RAIZ_PROJETO, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            svg = f.read()
        svg = re.sub(r'fill="(?!none)[^"]*"',   f'fill="{color}"',   svg)
        svg = re.sub(r'stroke="(?!none)[^"]*"', f'stroke="{color}"', svg)
        return svg
    except Exception:
        return None

def _svg_from_file_or_fallback(filename, fallback_svg, size=52):
    svg_text = _load_svg_colored(filename)
    if svg_text:
        b64 = base64.b64encode(svg_text.encode()).decode()
        return f'<img src="data:image/svg+xml;base64,{b64}" style="width:{size}px;height:{size}px;object-fit:contain;">'
    return _svg_img(fallback_svg, size)

def get_b64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def _strip(html):
    return "\n".join(l.strip() for l in html.strip().split("\n") if l.strip())

# ── CSS ────────────────────────────────────────────────────────
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
    .terminal-titulo{{background-color:#1e1e1e;color:#d4d4d4;padding:.5rem 1rem;border-radius:10px 10px 0 0;font-family:"Consolas","Menlo",monospace;font-size:.8rem;display:flex;align-items:center;gap:.4rem;}}
    .terminal-titulo .bolinha{{width:11px;height:11px;border-radius:50%;display:inline-block;}}
    [data-testid="stCodeBlock"]{{border-radius:0 0 10px 10px!important;}}
    [data-testid="stCodeBlock"] pre{{min-height:520px!important;max-height:620px!important;overflow-y:auto!important;font-size:.82rem!important;border-radius:0 0 10px 10px!important;}}
    .icon-card{{background:white;border:1.5px solid #c8e6c9;border-radius:12px;padding:14px 10px;text-align:center;font-size:.8rem;color:{VERDE_ESCURO};}}
    </style>""", unsafe_allow_html=True)

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

def exibir_titulo_terminal():
    st.markdown('<div class="terminal-titulo"><span class="bolinha" style="background:#ff5f56;"></span><span class="bolinha" style="background:#ffbd2e;"></span><span class="bolinha" style="background:#27c93f;"></span>&nbsp;docker compose up --build</div>', unsafe_allow_html=True)

def exibir_secao_icones():
    st.subheader("Ícones dos Agentes (OMNeT++)")
    icones = [
        ("server-svgrepo-com.svg",             _SVG_SERVER, "Server"),
        ("laptop-minimalistic-svgrepo-com.svg", _SVG_PC,     "Periférico"),
        ("router-bottom-1112-svgrepo-com.svg",  _SVG_ROUTER, "Roteador"),
    ]
    cols = st.columns(len(icones))
    for col, (svg_file, svg_fb, desc) in zip(cols, icones):
        with col:
            img = _svg_from_file_or_fallback(svg_file, svg_fb, 52)
            st.markdown(
                f'<div class="icon-card">{img}<br>'
                f'<span style="font-size:.78rem;color:{VERDE_ESCURO}">{desc}</span></div>',
                unsafe_allow_html=True)


# ── Preview de topologia ───────────────────────────────────────────────────────

def _posicoes(topologia, n_total, fan=None, n_subs=3, n_cons=3, n_meds=4):
    """Calcula posições (x, y) dos nós para o preview Plotly."""
    raio = 350
    if topologia == "estrela":
        pos = {"agent_central": (500, 500)}
        for i in range(n_total - 1):
            ang = 2 * math.pi * i / (n_total - 1)
            pos[f"agent_p_{i+1}"] = (500 + raio*math.cos(ang), 500 + raio*math.sin(ang))
        return pos
    elif topologia == "anel":
        pos = {}
        for i in range(n_total):
            ang = 2 * math.pi * i / n_total
            pos[f"agente_{i+1}"] = (500 + raio*math.cos(ang), 500 + raio*math.sin(ang))
        return pos
    elif topologia == "arvore":
        # Preview simplificado: raiz no centro, filhos em cada nível
        fan_list = [int(v) for v in (fan or "3,2,4").split(",")]
        pos = {"raiz": (500, 80)}
        nivel_atual = ["raiz"]
        for d, f in enumerate(fan_list):
            prefixo = ["sub", "con", "med"][min(d, 2)]
            nivel_prox = []
            for pai in nivel_atual:
                for _ in range(f):
                    nid = f"{prefixo}{d+1}_{len(nivel_prox)}"
                    nivel_prox.append(nid)
            n_nivel = len(nivel_prox)
            y_pos = 80 + (d + 1) * 220
            for p, nid in enumerate(nivel_prox):
                x_pos = (p + 0.5) * (1000.0 / n_nivel)
                pos[nid] = (x_pos, y_pos)
            nivel_atual = nivel_prox
        return pos
    else:  # hibrida — preview esquemático
        pos = {"cco": (500, 500)}
        for i in range(n_subs):
            ang = 2 * math.pi * i / n_subs
            sid = f"sub{i}"
            pos[sid] = (500 + 300*math.cos(ang), 500 + 300*math.sin(ang))
            for j in range(min(n_cons, 2)):  # máx 2 cons por sub no preview
                ang2 = ang + (j - 0.5) * 0.5
                cid = f"con{i}_{j}"
                pos[cid] = (500 + 500*math.cos(ang2), 500 + 500*math.sin(ang2))
        return pos


def _links_preview(topologia, pos, tipos, fan=None, celular_code="4g",
                   n_subs=3, n_cons=3):
    """Gera lista de (origem, destino, canal) para o preview."""
    ids = list(pos.keys())
    n   = len(ids)
    links = []
    if topologia == "estrela":
        central = ids[0]
        for i, pid in enumerate(ids[1:]):
            links.append((central, pid, tipos[i % len(tipos)]))
    elif topologia == "anel":
        for i in range(n):
            links.append((ids[i], ids[(i+1) % n], tipos[i % len(tipos)]))
    elif topologia == "arvore":
        fan_list = [int(v) for v in (fan or "3,2,4").split(",")]
        canais = ["Fibra", CELULAR_MAP.get(celular_code, "Celular4G"), "PLC"]
        nivel_atual = ["raiz"]
        for d, f in enumerate(fan_list):
            prefixo = ["sub", "con", "med"][min(d, 2)]
            canal   = canais[min(d, 2)]
            nivel_prox = []
            for pai in nivel_atual:
                for _ in range(f):
                    nid = f"{prefixo}{d+1}_{len(nivel_prox)}"
                    if pai in pos and nid in pos:
                        links.append((pai, nid, canal))
                    nivel_prox.append(nid)
            nivel_atual = nivel_prox
    else:  # hibrida
        celular = CELULAR_MAP.get(celular_code, "Celular4G")
        subs = [k for k in pos if k.startswith("sub")]
        n_s = len(subs)
        # Anel de subs (Fibra)
        if n_s >= 3:
            for i in range(n_s):
                links.append((subs[i], subs[(i+1)%n_s], "Fibra"))
        elif n_s == 2:
            links.append((subs[0], subs[1], "Fibra"))
        for s in subs[:2]:
            links.append(("cco", s, "Fibra"))
        # Estrela celular subs → cons (preview)
        for k in pos:
            if k.startswith("con"):
                parts = k[3:].split("_")
                sid = f"sub{parts[0]}"
                if sid in pos:
                    links.append((sid, k, celular))
    return links


def exibir_preview_topologia(topologia, num_perifericos, tipos_selecionados,
                              fan="3,2,4", celular_code="4g",
                              n_subs=3, n_cons=3, n_meds=4):
    st.subheader("Preview da Topologia")
    if topologia in ("estrela", "anel"):
        n_total = num_perifericos + 1 if topologia == "estrela" else num_perifericos
    elif topologia == "arvore":
        # conta nós da árvore
        fan_list = [int(v) for v in fan.split(",")]
        total_nos = 1
        nivel = 1
        for f in fan_list:
            nivel *= f
            total_nos += nivel
        n_total = total_nos
    else:
        n_total = 1 + n_subs + n_subs * min(n_cons, 2)

    pos = _posicoes(topologia, n_total, fan=fan, n_subs=n_subs, n_cons=n_cons)
    links = _links_preview(topologia, pos, tipos_selecionados, fan=fan,
                            celular_code=celular_code, n_subs=n_subs, n_cons=n_cons)
    fig   = go.Figure()

    # ── Traça enlaces ─────────────────────────────────────────────────────────
    por_canal: dict = {}
    for orig, dest, canal in links:
        if orig not in pos or dest not in pos:
            continue
        por_canal.setdefault(canal, {"x": [], "y": []})
        x0, y0 = pos[orig]; x1, y1 = pos[dest]
        por_canal[canal]["x"].extend([x0, x1, None])
        por_canal[canal]["y"].extend([y0, y1, None])

    for canal, dados in por_canal.items():
        if canal in CORES_REDE:
            cor  = CORES_REDE[canal]
            nome = REDES[canal][0] if canal in REDES else canal.replace("Link_", "")
        else:
            cor  = CORES_CANAL.get(canal, "#888")
            nome = NOMES_CANAL.get(canal, canal)
        fig.add_trace(go.Scatter(
            x=dados["x"], y=dados["y"], mode="lines",
            line=dict(color=cor, width=3),
            name=nome, showlegend=True, legendgroup=canal, hoverinfo="skip",
        ))

    # ── Traça nós ─────────────────────────────────────────────────────────────
    def _camada_cor(nid):
        if nid in ("agent_central", "raiz", "cco"):
            return VERDE_VIVO
        if nid.startswith("sub"):
            return CORES_CAMADA["subestacao"]
        if nid.startswith("con"):
            return CORES_CAMADA["concentrador"]
        if nid.startswith("med"):
            return CORES_CAMADA["medidor"]
        return VERDE_ESCURO

    ids    = list(pos.keys())
    raiz_ids = {"agent_central", "raiz", "cco"} | {ids[0]} if topologia == "anel" else {"agent_central", "raiz", "cco"}
    cores  = [_camada_cor(n) for n in ids]
    tams   = [26 if n in raiz_ids else (20 if n.startswith("sub") else 14) for n in ids]
    labs   = []
    for n in ids:
        if n == "agent_central": labs.append("Central")
        elif n == "cco":         labs.append("CCO")
        elif n == "raiz":        labs.append("Raiz")
        else:                    labs.append(n.replace("agent_p_", "P").replace("agente_", "A"))

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in ids], y=[pos[n][1] for n in ids],
        mode="markers+text",
        marker=dict(size=tams, color=cores, line=dict(width=2, color="white")),
        text=labs, textposition="top center",
        textfont=dict(size=9, color="#1a3a2a"),
        name="Agentes", showlegend=False,
        hovertext=ids, hoverinfo="text",
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>Topologia: {TOPOLOGIAS[topologia]['label']}</b> — {len(pos)} nós · {len(links)} enlaces",
            font=dict(size=15, color=VERDE_ESCURO)),
        paper_bgcolor=FUNDO_CLARO, plot_bgcolor=FUNDO_CLARO,
        font=dict(color=VERDE_ESCURO, family="Inter, Segoe UI, sans-serif"),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False,
                   scaleanchor="x", scaleratio=1),
        legend=dict(
            title=dict(text="Canal / Tecnologia", font=dict(size=12, color=VERDE_ESCURO)),
            font=dict(size=11, color=VERDE_ESCURO),
            bgcolor="rgba(244,255,235,0.92)", bordercolor="#a5d6a7", borderwidth=1,
        ),
        margin=dict(t=60, b=20, l=20, r=20), height=460,
    )
    st.plotly_chart(fig, width='stretch')

    # ── Notas de topologia ────────────────────────────────────────────────────
    if topologia == "anel":
        st.info(
            "**Anel bidirecional**: cada enlace físico permite envio e recebimento "
            "simultâneos. O ciclo fechado garante agente₁ ↔ … ↔ agente_N ↔ agente₁."
        )
    elif topologia == "arvore":
        fan_list = [int(v) for v in fan.split(",")]
        st.info(
            f"**Árvore IEC 61850**: raiz → subestações (Fibra) → "
            f"concentradores ({CELULAR_MAP.get(celular_code, 'Celular4G')}) → "
            f"medidores (PLC). Fan-out por nível: {fan_list}."
        )
    elif topologia == "hibrida":
        st.info(
            f"**Híbrida multi-camada**: backbone em anel de fibra entre "
            f"{n_subs} subestações, estrela celular "
            f"({CELULAR_MAP.get(celular_code, 'Celular4G')}) até {n_cons} "
            "concentradores por sub, e malha RF mesh nos clusters de medidores."
        )


# ── Resultados ────────────────────────────────────────────────────────────────

_EXT_GRAFICO = (".svg", ".png")          # os plot_results_*.py geram SVG; PNG = legado


def _listar_graficos():
    """Todos os grafico_*.svg (ou .png) de mosaik-dir/. Não depende do nome que cada
    plot_results_*.py usa. Inclui os gráficos individuais (grafico_trafego_Geral_*)."""
    if not os.path.isdir(MOSAIK_DIR):
        return []
    return sorted(f for f in os.listdir(MOSAIK_DIR)
                  if f.startswith("grafico_") and f.endswith(_EXT_GRAFICO))


def _limpar_graficos():
    """Remove gráficos de rodadas anteriores para nunca exibir dados velhos."""
    for f in _listar_graficos():
        try:
            os.remove(os.path.join(MOSAIK_DIR, f))
        except OSError:
            pass


_ROTULO_INDIVIDUAL = {
    "heatmap":  "Heatmap de latência (mapa)",
    "latencia": "Latência temporal",
    "payload":  "Payload médio por tecnologia",
    "pdr":      "Taxa de entrega global (PDR)",
    "jitter":   "Distribuição de jitter",
}


def _eh_individual(nome_arquivo):
    return nome_arquivo.startswith("grafico_trafego_Geral_")


def _rotulo_grafico(nome_arquivo):
    nome = os.path.splitext(nome_arquivo)[0][len("grafico_"):]
    if nome.startswith("trafego_Geral_"):
        chave = nome[len("trafego_Geral_"):].split("_")[0]   # …_<grafico>_<Topologia>
        return _ROTULO_INDIVIDUAL.get(chave, chave)
    return nome.replace("trafego_", "").replace("_", " ").strip().capitalize() or nome


def _mostrar_imagem(caminho):
    if caminho.lower().endswith(".svg"):
        # <img> com data-URI: renderiza qualquer SVG do matplotlib (st.image só aceita
        # SVG que começa em "<svg", e o do matplotlib começa em "<?xml").
        try:
            with open(caminho, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError:
            st.warning(f"Não foi possível abrir {os.path.basename(caminho)}.")
            return
        st.markdown(f'<img src="data:image/svg+xml;base64,{b64}" style="width:100%">',
                    unsafe_allow_html=True)
        return
    try:
        st.image(caminho, width="stretch")
    except TypeError:                       # versões antigas do Streamlit
        st.image(caminho, use_container_width=True)


def exibir_resultados():
    """
    Conteúdo da aba Resultados. NÃO depende do código de saída do docker compose:
    mostra os gráficos que existirem em mosaik-dir/ e informa o status da execução.
    """
    st.subheader("Resultados da Simulação")

    executada = st.session_state.get("sim_executada", False)
    codigo    = st.session_state.get("sim_codigo")
    topologia = st.session_state.get("sim_topologia")
    rotulo    = TOPOLOGIAS.get(topologia, {}).get("label", topologia)
    graficos  = _listar_graficos()

    if em_execucao():
        st.info("Co-simulação em andamento… os gráficos aparecem aqui quando ela terminar.")
        return

    if executada:
        if codigo == 0:
            st.success(f"Última execução ({rotulo}): concluída com sucesso.")
        else:
            st.error(f"Última execução ({rotulo}): o docker compose encerrou com erro "
                     f"(código {codigo}). Veja o terminal na aba Configuração.")
    elif graficos:
        st.info("Gráficos da última execução encontrada em mosaik-dir/.")
    else:
        st.info("Nenhuma co-simulação executada ainda. Configure e clique em "
                "**Iniciar simulação** na aba **Configuração**.")
        return

    if not graficos:
        st.warning("Nenhum gráfico foi gerado nesta execução (os gráficos só são criados "
                   "depois que a co-simulação termina).")
        return

    if executada and codigo != 0:
        st.warning("A execução terminou com erro, mas estes gráficos foram gerados:")

    principais  = [g for g in graficos if not _eh_individual(g)]
    individuais = [g for g in graficos if _eh_individual(g)]

    for arq in principais:
        st.caption(f"Visão: **{_rotulo_grafico(arq)}**")
        _mostrar_imagem(os.path.join(MOSAIK_DIR, arq))
        st.write("")

    if individuais:
        with st.expander("Gráficos individuais — Visão Geral (SVG separados)", expanded=False):
            for i in range(0, len(individuais), 2):
                cols = st.columns(2)
                for col, arq in zip(cols, individuais[i:i + 2]):
                    with col:
                        st.caption(f"**{_rotulo_grafico(arq)}**")
                        _mostrar_imagem(os.path.join(MOSAIK_DIR, arq))


# ── Docker ────────────────────────────────────────────────────────────────────

# A execução roda em SEGUNDO PLANO, desacoplada do ciclo de re-execução do Streamlit.
# Assim, abrir/fechar o painel do terminal, trocar de aba, mexer em qualquer widget ou
# até recarregar a página NÃO interrompe a co-simulação: o processo `docker compose`
# continua e a saída é lida de um arquivo de log (a interface só "assiste").

LOG_PATH = os.path.join(tempfile.gettempdir(), "grei_cosim_docker.log")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


@st.cache_resource
def _execucao():
    """Estado único (compartilhado entre re-execuções e sessões do navegador)."""
    return {"proc": None, "topologia": None, "total": None, "inicio": None,
            "interrompida": False, "lock": threading.Lock()}


def em_execucao():
    p = _execucao()["proc"]
    return p is not None and p.poll() is None


def codigo_saida():
    """None enquanto roda (ou se nunca rodou); código de saída depois."""
    p = _execucao()["proc"]
    return None if p is None else p.poll()


def iniciar_docker_compose(env_extra, topologia, total):
    """Dispara `docker compose up` em segundo plano. Devolve False se já há uma execução."""
    ex = _execucao()
    with ex["lock"]:
        if em_execucao():
            return False
        env = os.environ.copy(); env.update(env_extra)
        with open(LOG_PATH, "w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                ["docker", "compose", "up", "--build",
                 "--abort-on-container-exit",
                 "--exit-code-from", "mosaik_master"],
                cwd=RAIZ_PROJETO, env=env,
                stdout=log, stderr=subprocess.STDOUT, text=True)
        ex.update(proc=proc, topologia=topologia, total=total,
                  inicio=time.time(), interrompida=False)
    return True


def parar_docker_compose():
    ex = _execucao()
    if em_execucao():
        ex["interrompida"] = True
    subprocess.run(["docker", "compose", "down"], cwd=RAIZ_PROJETO)
    p = ex["proc"]
    if p is not None:
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()


def ler_log(max_bytes=200_000, max_linhas=500):
    """Últimas linhas do log (sem códigos de cor ANSI). Lê só o final do arquivo."""
    try:
        with open(LOG_PATH, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - max_bytes))
            txt = f.read().decode("utf-8", "replace")
    except OSError:
        return ""
    txt = _ANSI.sub("", txt).replace("\r", "\n")
    return "\n".join(txt.splitlines()[-max_linhas:])


def sincronizar_estado():
    """Reflete a execução em segundo plano no session_state (inclusive após recarregar a página)."""
    ex = _execucao()
    if ex["proc"] is None:
        return
    st.session_state.sim_topologia = ex["topologia"]
    cod = codigo_saida()
    st.session_state.sim_executada = cod is not None
    st.session_state.sim_codigo = cod


def _corpo_terminal():
    st.code(ler_log() or "Aguardando saída do docker compose…", language="bash")


@st.fragment(run_every=1)
def _terminal_ao_vivo():
    """Atualiza SÓ o log a cada 1 s enquanto roda; ao terminar, recarrega a página uma vez
    para liberar os botões e preencher a aba Resultados."""
    _corpo_terminal()
    if not em_execucao():
        st.rerun()


@st.fragment
def _terminal_estatico():
    _corpo_terminal()


def exibir_painel_terminal():
    """Painel do terminal recolhível. Abrir/fechar é só front-end e não afeta a simulação."""
    ex = _execucao()
    if ex["proc"] is None:
        return
    rodando = em_execucao()
    cod = codigo_saida()
    rotulo = TOPOLOGIAS.get(ex["topologia"], {}).get("label", ex["topologia"])
    if rodando:
        st.info(f"Co-simulação **{rotulo}** em andamento. "
                "Pode abrir/fechar o terminal, trocar de aba ou rolar a página: nada disso "
                "interrompe a execução.")
    elif ex["interrompida"]:
        st.warning(f"Co-simulação **{rotulo}** interrompida pelo usuário.")
    elif cod == 0:
        st.success(f"Co-simulação **{rotulo}** concluída com sucesso. Confira a aba **Resultados**.")
    else:
        st.error(f"docker compose encerrou com erro (código {cod}). "
                 "Se algum gráfico foi gerado, ele aparece na aba **Resultados**.")
    with st.expander("Terminal — docker compose up --build", expanded=True):
        exibir_titulo_terminal()
        (_terminal_ao_vivo if rodando else _terminal_estatico)()


# ── Main ──────────────────────────────────────────────────────────────────────

_AUTO = "Auto (cíclico)"
_MAX_AGENTES_VISIVEIS = 20


def selecionar_tecnologias(topologia, num_enlaces):
    """
    Estrela / Anel: pool de tecnologias + atribuição OPCIONAL de uma tecnologia a cada
    agente. Retorna a lista de ned-ids na ordem dos enlaces (o scenario.py usa
    TIPOS_REDE[i % len]), de modo que a posição i da lista é o enlace do agente i.
      - Todos em "Auto"  → devolve o próprio pool (distribuição cíclica padrão).
      - Algum escolhido  → devolve uma tecnologia por enlace.
    """
    st.subheader("3. Tipos de enlace")
    chaves = list(REDES.keys())
    pool = st.multiselect(
        "Pool de tecnologias disponíveis", options=chaves, default=chaves,
        format_func=lambda k: REDES[k][0], label_visibility="collapsed")
    if not pool:
        st.warning("Selecione ao menos um tipo de enlace."); st.stop()

    opcoes = [_AUTO] + [REDES[k][0] for k in pool]
    ned_por_rotulo = {_AUTO: None}
    ned_por_rotulo.update({REDES[k][0]: k for k in pool})

    if topologia == "estrela":
        rotulos = [f"Periférico {i}" for i in range(1, num_enlaces + 1)]
    else:
        rotulos = [f"Agente {i} → Agente {(i % num_enlaces) + 1}"
                   for i in range(1, num_enlaces + 1)]
    n_mostrar = min(len(rotulos), _MAX_AGENTES_VISIVEIS)
    chave = lambda i: f"tech_agente_{topologia}_{i}"

    # Se a tecnologia escolhida saiu do pool, volta para Auto (evita valor inválido).
    for i in range(n_mostrar):
        if st.session_state.get(chave(i), _AUTO) not in opcoes:
            st.session_state[chave(i)] = _AUTO

    with st.expander("Definir tecnologia por agente (opcional)", expanded=False):
        if topologia == "estrela":
            st.caption("Cada linha é o enlace daquele periférico com o nó central.")
        else:
            st.caption("Cada linha é o enlace agente_i → agente_{i+1} (cíclico).")
        st.caption("“Auto (cíclico)” segue a ordem do pool; escolha uma tecnologia para "
                   "fixá-la naquele agente.")

        tipos_finais = []
        for i in range(n_mostrar):
            col_a, col_b = st.columns([2, 3])
            col_a.markdown(
                f'<div style="padding-top:.45rem;font-size:.95rem;">{rotulos[i]}</div>',
                unsafe_allow_html=True)
            escolha = col_b.selectbox("tecnologia", options=opcoes, key=chave(i),
                                      label_visibility="collapsed")
            tipos_finais.append(ned_por_rotulo[escolha] or pool[i % len(pool)])

        if len(rotulos) > n_mostrar:
            st.caption(f"… {len(rotulos) - n_mostrar} agente(s) restantes usam a "
                       "distribuição cíclica do pool.")
            for i in range(n_mostrar, len(rotulos)):
                tipos_finais.append(pool[i % len(pool)])

    todos_auto = all(st.session_state.get(chave(i), _AUTO) == _AUTO for i in range(n_mostrar))
    return pool if todos_auto else tipos_finais


def aba_configuracao():
    """Aba 'Configuração': escolhe topologia/parâmetros, mostra o preview e roda o docker."""
    # ── 1. Topologia ──────────────────────────────────────────────────────────
    st.subheader("1. Topologia de rede")
    topologia = st.radio("Topologia", options=list(TOPOLOGIAS.keys()),
                         format_func=lambda k: TOPOLOGIAS[k]["label"],
                         horizontal=True, label_visibility="collapsed")
    st.caption(TOPOLOGIAS[topologia]["desc"])

    # ── 2. Número de agentes / dimensionamento ────────────────────────────────
    st.subheader("2. Dimensionamento")

    # Parâmetros por topologia
    num_perifericos = 4        # fallback
    fan             = "3,2,4"
    celular_code    = "4g"
    n_subs, n_cons, n_meds = 3, 3, 5
    semente_hibrida = 42
    tipos_selecionados = list(REDES.keys())

    if topologia == "estrela":
        num_perifericos = st.number_input(
            "Periféricos", min_value=1, max_value=500, value=4, step=1,
            label_visibility="collapsed")
        total_agentes = num_perifericos + 1
        st.caption(f"Total: **{total_agentes}** (1 central + {num_perifericos} periféricos).")

    elif topologia == "anel":
        num_perifericos = st.number_input(
            "Agentes no anel", min_value=3, max_value=500, value=5, step=1,
            label_visibility="collapsed")
        total_agentes = num_perifericos
        st.caption(f"Total: **{total_agentes}** agentes em ciclo fechado.")

    elif topologia == "arvore":
        col_fan, col_cel = st.columns(2)
        with col_fan:
            fan = st.text_input(
                "Fan-out por nível (ex.: 3,2,4)",
                value="3,2,4",
                help="Número de filhos por nó em cada nível da árvore, separados por vírgula.")
        with col_cel:
            celular_code = st.selectbox(
                "Tecnologia celular (nível concentrador)",
                options=CELULAR_OPTIONS,
                index=CELULAR_OPTIONS.index("4g"),
                format_func=lambda x: x.upper())
        # Valida fan-out
        try:
            fan_list = [int(v) for v in fan.split(",")]
            assert all(f > 0 for f in fan_list)
            total_nos = 1
            nivel = 1
            for f in fan_list:
                nivel *= f
                total_nos += nivel
            st.caption(f"Fan-out {fan_list} → **{total_nos}** nós totais na simulação.")
        except Exception:
            st.warning("Fan-out inválido. Use inteiros separados por vírgula (ex.: 3,2,4).")
            st.stop()
        total_agentes = total_nos
        num_perifericos = total_nos - 1

    else:  # hibrida
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            n_subs = st.number_input("Subestações", min_value=2, max_value=20,
                                     value=3, step=1)
        with c2:
            n_cons = st.number_input("Conc./sub", min_value=1, max_value=20,
                                     value=3, step=1,
                                     help="Concentradores por subestação")
        with c3:
            n_meds = st.number_input("Med./conc.", min_value=1, max_value=50,
                                     value=5, step=1,
                                     help="Medidores por concentrador")
        with c4:
            celular_code = st.selectbox(
                "Celular (backhaul)",
                options=CELULAR_OPTIONS,
                index=CELULAR_OPTIONS.index("4g"),
                format_func=lambda x: x.upper())
        semente_hibrida = st.number_input(
            "Semente aleatória", min_value=0, max_value=999999,
            value=42, step=1,
            help="Garante reprodutibilidade das posições dos medidores.")
        total_nos = 1 + n_subs + n_subs * n_cons + n_subs * n_cons * n_meds
        st.caption(
            f"Total estimado: **{total_nos}** nós "
            f"(1 CCO + {n_subs} subs + {n_subs*n_cons} cons + "
            f"{n_subs*n_cons*n_meds} meds)."
        )
        total_agentes   = total_nos
        num_perifericos = total_nos - 1

    # ── 3. Tipos de enlace (apenas para estrela e anel) ───────────────────────
    if topologia in ("estrela", "anel"):
        tipos_selecionados = selecionar_tecnologias(topologia, num_perifericos)
    else:
        # Árvore e Híbrida usam canais fixos por camada
        tipos_selecionados = ["Link_Wired"]  # não usado, mas mantém assinatura

    exibir_secao_icones()
    exibir_preview_topologia(
        topologia, num_perifericos, tipos_selecionados,
        fan=fan, celular_code=celular_code,
        n_subs=n_subs, n_cons=n_cons, n_meds=n_meds,
    )

    # ── Resumo ────────────────────────────────────────────────────────────────
    if topologia == "estrela":
        detalhe = f"1 central + {num_perifericos} periféricos"
        extra_rows = ""
    elif topologia == "anel":
        detalhe = f"{total_agentes} agentes em ciclo"
        extra_rows = ""
    elif topologia == "arvore":
        detalhe = f"{total_agentes} nós (fan-out {fan})"
        extra_rows = (
            f'<div class="resumo-linha"><span class="resumo-chave">Fan-out</span>'
            f'<span class="resumo-valor">{fan}</span></div>'
            f'<div class="resumo-linha"><span class="resumo-chave">Celular</span>'
            f'<span class="resumo-valor">{celular_code.upper()}</span></div>'
        )
    else:  # hibrida
        detalhe = f"{total_agentes} nós ({n_subs}S · {n_cons}C · {n_meds}M)"
        extra_rows = (
            f'<div class="resumo-linha"><span class="resumo-chave">Subs / Cons / Meds</span>'
            f'<span class="resumo-valor">{n_subs} / {n_cons} / {n_meds}</span></div>'
            f'<div class="resumo-linha"><span class="resumo-chave">Celular</span>'
            f'<span class="resumo-valor">{celular_code.upper()}</span></div>'
            f'<div class="resumo-linha"><span class="resumo-chave">Semente</span>'
            f'<span class="resumo-valor">{semente_hibrida}</span></div>'
        )

    nomes_redes = (", ".join(dict.fromkeys(REDES[t][0] for t in tipos_selecionados))
                   if topologia in ("estrela", "anel") else "Fibra / Celular / PLC-RF")

    st.markdown(_strip(f"""
    <div style="margin-top:1.8rem;margin-bottom:1.5rem;">
    <h3 style="margin-top:0;color:{VERDE_ESCURO};font-weight:700;">Resumo da configuração</h3>
    <div class="resumo-linha"><span class="resumo-chave">Topologia</span><span class="resumo-valor">{TOPOLOGIAS[topologia]['label']}</span></div>
    <div class="resumo-linha"><span class="resumo-chave">Agentes / Nós</span><span class="resumo-valor">{detalhe}</span></div>
    <div class="resumo-linha"><span class="resumo-chave">Redes</span><span class="resumo-valor">{nomes_redes}</span></div>
    {extra_rows}
    </div>"""), unsafe_allow_html=True)

    # ── Botões ────────────────────────────────────────────────────────────────
    rodando = em_execucao()
    col1, col2 = st.columns(2)
    iniciar = col1.button("Iniciar simulação", type="primary", use_container_width=True,
                          disabled=rodando)
    parar   = col2.button("Parar / limpar containers", use_container_width=True)

    if parar:
        with st.spinner("Derrubando containers..."):
            parar_docker_compose()
        sincronizar_estado()
        st.rerun()

    if iniciar:
        _limpar_graficos()
        env_extra = {
            "TOPOLOGY":        topologia,
            "NUM_PERIFERICOS": str(num_perifericos),
            "TIPOS_REDE":      ",".join(tipos_selecionados),
        }
        if topologia == "arvore":
            env_extra["ARVORE_FANOUT"]  = fan
            env_extra["CELULAR_ARVORE"] = celular_code
        elif topologia == "hibrida":
            env_extra["SUBESTACOES"]        = str(n_subs)
            env_extra["CONCENTRADORES"]     = str(n_cons)
            env_extra["MEDIDORES_CLUSTER"]  = str(n_meds)
            env_extra["CELULAR_HIBRIDA"]    = celular_code
            env_extra["SEMENTE_HIBRIDA"]    = str(semente_hibrida)
        iniciar_docker_compose(env_extra, topologia, total_agentes)
        sincronizar_estado()
        st.rerun()          # redesenha já com o painel do terminal e os botões travados

    exibir_painel_terminal()


def main():
    st.set_page_config(page_title="Co-Simulação GREI - TSCC",
                       page_icon=CAMINHO_LOGO if os.path.exists(CAMINHO_LOGO) else None,
                       layout="wide", initial_sidebar_state="collapsed")
    aplicar_estilo()
    exibir_cabecalho_grei()

    for chave, padrao in (("sim_executada", False), ("sim_codigo", None),
                          ("sim_topologia", "estrela")):
        if chave not in st.session_state:
            st.session_state[chave] = padrao

    sincronizar_estado()
    tab_config, tab_resultados = st.tabs(["Configuração", "Resultados"])
    with tab_config:
        aba_configuracao()
    with tab_resultados:
        exibir_resultados()

    exibir_rodape_grei()


if __name__ == "__main__":
    main()