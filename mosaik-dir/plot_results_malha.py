#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_malha.py — Plot ISOLADO da topologia MALHA (full mesh).

Diferente de plot_results_star.py e plot_results_anel.py (que montam um
painel executivo completo de métricas de tráfego), este script tem uma
única responsabilidade: reconstruir e desenhar visualmente a topologia
MALHA a partir dos artefatos gerados pelo scenario.py:

    - links.json     -> lista de enlaces (origem, destino, tipo_de_canal),
                         persistida por scenario.py::_persistir_links().
    - posicoes.json   -> lista de agentes (id, x, y, tipo), persistida por
                         scenario.py::_persistir_mapa_e_config().

Como a malha é full mesh (N*(N+1)/2 enlaces), o desenho usa parâmetros
adequados a essa densidade: linhas finas e semitransparentes (para não
"encobrir" a figura com N² enlaces sobrepostos), nós maiores para
compensar, e o nó Central destacado com um marcador em formato de
estrela — igual à convenção usada no restante do projeto.

Cada tecnologia de enlace (Cabeada, 5G, 4G, 2G, Wireless...) recebe uma
cor distinta, com legenda, para que fique claro qual tecnologia carrega
qual conexão na malha.
"""

import json
import os

import plotly.graph_objects as go

# =================================================================
# CAMINHOS DE ENTRADA (com fallback local, mesmo padrão dos outros
# scripts de plot deste projeto)
# =================================================================
CAMINHO_LINKS = '/omnet-dir/links.json' if os.path.exists('/omnet-dir/links.json') else 'links.json'
CAMINHO_POSICOES = '/omnet-dir/posicoes.json' if os.path.exists('/omnet-dir/posicoes.json') else 'posicoes.json'
CAMINHO_CONFIG = '/omnet-dir/config.json' if os.path.exists('/omnet-dir/config.json') else 'config.json'

# Tradução do nome do canal NED para um rótulo amigável de legenda —
# mesmo mapeamento usado em plot_results_star.py, para manter a
# identidade visual consistente entre os painéis do projeto.
NED_PARA_LABEL = {
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
    'Link_Wireless': 'Wireless',
}

# Paleta fixa por tecnologia (uma cor extra reservada caso surja um
# tipo de rede novo no futuro).
_PALETA = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#17becf', '#d62728']


def _carregar_json(caminho, padrao):
    try:
        with open(caminho, 'r') as f:
            return json.load(f)
    except Exception:
        print(f"⚠️ Não foi possível ler '{caminho}'.")
        return padrao


def _rotulo_tecnologia(tipo_de_canal):
    return NED_PARA_LABEL.get(tipo_de_canal, tipo_de_canal)


def gerar_plot_malha():
    print("Lendo links.json e posicoes.json para plotar a topologia MALHA...")

    links = _carregar_json(CAMINHO_LINKS, [])
    posicoes = _carregar_json(CAMINHO_POSICOES, [])
    config = _carregar_json(CAMINHO_CONFIG, {})

    if not links or not posicoes:
        print("❌ links.json e/ou posicoes.json ausentes/vazios. Rode scenario.py primeiro.")
        return

    topologia = config.get('topologia', 'malha')
    if topologia != 'malha':
        print(f"⚠️ Aviso: config.json indica topologia '{topologia}', não 'malha'. "
              f"Plotando mesmo assim com os dados disponíveis.")

    # ── Mapa id -> {x, y, tipo} para lookup rápido ───────────────
    pos_por_id = {ag['id']: ag for ag in posicoes}

    # ── Descobre as tecnologias presentes nos links, na ordem em
    #    que aparecem, para montar a paleta e a legenda ───────────
    tecnologias_vistas = []
    for link in links:
        rotulo = _rotulo_tecnologia(link['tipo_de_canal'])
        if rotulo not in tecnologias_vistas:
            tecnologias_vistas.append(rotulo)
    cores_por_tecnologia = {
        tec: _PALETA[i % len(_PALETA)] for i, tec in enumerate(tecnologias_vistas)
    }

    fig = go.Figure()

    # ── ENLACES: uma trace Scatter por tecnologia, para que a
    #    legenda mostre corretamente cada cor/tecnologia uma única
    #    vez (uma trace por link duplicaria a legenda N vezes) ─────
    for tecnologia in tecnologias_vistas:
        xs_linhas, ys_linhas = [], []
        for link in links:
            if _rotulo_tecnologia(link['tipo_de_canal']) != tecnologia:
                continue
            origem = pos_por_id.get(link['origem'])
            destino = pos_por_id.get(link['destino'])
            if not origem or not destino:
                continue
            xs_linhas += [origem['x'], destino['x'], None]
            ys_linhas += [origem['y'], destino['y'], None]

        if not xs_linhas:
            continue

        # Malha completa = muitos enlaces sobrepostos visualmente;
        # linhas finas e semitransparentes evitam que a figura vire
        # um emaranhado ilegível, mas ainda deixam a tecnologia
        # identificável pela cor na legenda.
        fig.add_trace(go.Scatter(
            x=xs_linhas, y=ys_linhas,
            mode='lines',
            line=dict(color=cores_por_tecnologia[tecnologia], width=1.4),
            opacity=0.55,
            name=tecnologia,
            legendgroup=tecnologia,
            hoverinfo='skip',
        ))

    # ── NÓS: Central (estrela azul, maior) e Periféricos (círculos
    #    cinza com contorno) — mesma convenção visual das outras
    #    topologias do projeto, sem entrar na legenda de tecnologia ──
    centrais = [ag for ag in posicoes if ag.get('tipo') == 'Central']
    perifericos = [ag for ag in posicoes if ag.get('tipo') != 'Central']

    if perifericos:
        fig.add_trace(go.Scatter(
            x=[ag['x'] for ag in perifericos],
            y=[ag['y'] for ag in perifericos],
            mode='markers+text',
            marker=dict(size=22, color='#f0f0f0', line=dict(color='black', width=1.5)),
            text=[ag['id'] for ag in perifericos],
            textposition='bottom center',
            name='Periféricos',
            hovertext=[ag['id'] for ag in perifericos],
            hoverinfo='text',
            showlegend=True,
        ))

    if centrais:
        fig.add_trace(go.Scatter(
            x=[ag['x'] for ag in centrais],
            y=[ag['y'] for ag in centrais],
            mode='markers+text',
            marker=dict(size=32, color='#1f4e8c', symbol='star', line=dict(color='black', width=1.5)),
            text=[ag['id'] for ag in centrais],
            textposition='bottom center',
            name='Central',
            hovertext=[ag['id'] for ag in centrais],
            hoverinfo='text',
            showlegend=True,
        ))

    n_nos = len(posicoes)
    n_links = len(links)
    fig.update_layout(
        title=dict(
            text=f"Topologia MALHA (Full Mesh) — {n_nos} nós · {n_links} enlaces",
            x=0.5, xanchor='center', font=dict(size=22),
        ),
        xaxis=dict(title='Coordenada X (metros)', showgrid=True, zeroline=False),
        yaxis=dict(title='Coordenada Y (metros)', showgrid=True, zeroline=False, scaleanchor='x'),
        legend=dict(title='Tecnologia do enlace', bgcolor='rgba(255,255,255,0.85)'),
        plot_bgcolor='white',
        width=1200,
        height=900,
    )

    # PNG (via kaleido) — mesmo formato de saída (.png) dos demais
    # scripts de plot do projeto — e HTML interativo como extra.
    nome_png = 'topologia_malha.png'
    nome_html = 'topologia_malha.html'
    try:
        fig.write_image(nome_png, scale=2)
        print(f"Salvo: {nome_png}")
    except Exception as e:
        print(f"⚠️ Não foi possível exportar PNG (kaleido instalado?): {e}")

    fig.write_html(nome_html)
    print(f"Salvo: {nome_html}")


if __name__ == '__main__':
    gerar_plot_malha()