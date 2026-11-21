#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_anel.py — Dashboard Científico para Topologia em Anel P2P.

Restaura o plotador original da topologia em anel (sobrescrito acidentalmente
no commit edbb07c) e o generaliza para N >= 2 agentes dinâmicos utilizando
links.json, posicoes.json e config.json.

Arquivos gerados:
  - grafico_trafego_Anel.svg           (visão por Agente Roteador P2P no anel)
  - grafico_trafego_Geral.svg          (visão global por Tecnologia de Enlace)
  - grafico_trafego_{Tecnologia}.svg   (visão individual por Tecnologia de Enlace)
"""

import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from matplotlib.transforms import Bbox

# ── Saída vetorial (SVG) ───────────────────────────────────────────────────────
# 'none' mantém o texto editável (Inkscape / Illustrator / Canva). Use 'path' para
# converter o texto em curvas (aparência idêntica em qualquer máquina, sem edição).
matplotlib.rcParams['svg.fonttype'] = 'none'


_TOPO_ROTULO = 'Topologia em Anel'      # aparece no título de cada gráfico individual
_TOPO_ARQ = 'Anel'                  # sufixo do nome do arquivo (evita colisão entre topologias)


def _exportar_paineis_separados(fig, paineis, prefixo='grafico_trafego_Geral', pad_px=12):
    """Salva cada painel do dashboard como um SVG próprio (título, legenda e colorbar
    inclusos). O título ganha uma linha com o nome da topologia, para o gráfico fazer
    sentido isolado. `paineis` = lista de (sufixo, [axes que compõem o painel])."""
    inv = fig.dpi_scale_trans.inverted()
    for sufixo, axs in paineis:
        ax0 = axs[0]
        titulo_orig = ax0.get_title()
        ax0.set_title(f'{_TOPO_ROTULO}\n{titulo_orig}', fontweight='bold',
                      fontsize=ax0.title.get_fontsize())
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bb = Bbox.union([a.get_tightbbox(renderer) for a in axs])
        bb = Bbox.from_extents(bb.x0 - pad_px, bb.y0 - pad_px, bb.x1 + pad_px, bb.y1 + pad_px)
        nome = f'{prefixo}_{sufixo}_{_TOPO_ARQ}.svg'
        fig.savefig(nome, format='svg', bbox_inches=bb.transformed(inv))
        ax0.set_title(titulo_orig, fontweight='bold', fontsize=ax0.title.get_fontsize())
        print(f'Salvo: {nome}')


NED_PARA_LABEL = {
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_Wireless': 'Wireless',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
}
_PALETA = ['#1f77b4', '#2ca02c', '#17becf', '#ff7f0e', '#9467bd', '#8c564b', '#d62728', '#e377c2']


def _path(nome):
    omnet_env = os.environ.get('OMNET_DIR')
    candidatos = []
    if omnet_env:
        candidatos.append(os.path.join(omnet_env, nome))
    candidatos.extend([
        f'/omnet-dir/{nome}',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'omnet-dir', nome),
        nome,
    ])
    for c in candidatos:
        if os.path.exists(c):
            return c
    return nome


def _reconstruir_links_anel(posicoes, config):
    ids = [ag['id'] for ag in posicoes]
    tipos = config.get('tipos_rede', ['Link_Wired', 'Link_5G', 'Link_4G', 'Link_2G', 'Link_Wireless'])
    n = len(ids)
    links = []
    for i in range(n):
        if n == 2 and i == 1:
            break
        links.append({
            'origem': ids[i],
            'destino': ids[(i + 1) % n],
            'tipo': tipos[i % len(tipos)],
        })
    return links


def carregar():
    if not os.path.exists('results.csv'):
        raise FileNotFoundError("results.csv não encontrado.")
    df = pd.read_csv('results.csv')
    with open(_path('posicoes.json'), encoding='utf-8') as f:
        posicoes = json.load(f)
    with open(_path('config.json'), encoding='utf-8') as f:
        config = json.load(f)
    p = _path('links.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            links = json.load(f)
    else:
        links = _reconstruir_links_anel(posicoes, config)
    return df, posicoes, config, links


def _build_link_map(links):
    lmap = {}
    for lk in links:
        o = lk['origem']
        d = lk['destino']
        label = NED_PARA_LABEL.get(lk.get('tipo', 'Link_Wired'), lk.get('tipo', ''))
        lmap[(o, d)] = label
        lmap[(d, o)] = label
    return lmap


def extrair_remetente(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == "":
            return ""
        msg_json = json.loads(msg_str)
        sender = msg_json.get("sender", "")
        return sender.split('@')[0] if sender else ""
    except Exception:
        return ""


def _desenhar_mapa_anel(ax_map, posicoes, links, avg_lat_no, cores_tech, rede_foco=None):
    pos_dict = {ag['id']: (ag['x'], ag['y']) for ag in posicoes}
    ids_nos = [ag['id'] for ag in posicoes]

    for lk in links:
        o, d = lk['origem'], lk['destino']
        if o not in pos_dict or d not in pos_dict:
            continue
        tech_lbl = NED_PARA_LABEL.get(lk.get('tipo', ''), lk.get('tipo', ''))
        x0, y0 = pos_dict[o]
        x1, y1 = pos_dict[d]
        eh_foco = (rede_foco is None or rede_foco == 'Geral' or tech_lbl == rede_foco)
        cor_aresta = cores_tech.get(tech_lbl, '#333333') if eh_foco else '#cccccc'
        ax_map.plot(
            [x0, x1], [y0, y1],
            color=cor_aresta,
            linestyle='--' if rede_foco is None else '-',
            alpha=0.85 if eh_foco else 0.2,
            linewidth=2.5 if eh_foco else 1.0,
            zorder=1,
        )
        if eh_foco:
            mid_x, mid_y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            ax_map.text(
                mid_x, mid_y + 15, tech_lbl,
                fontsize=9, fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor=cor_aresta, alpha=0.85),
                zorder=4,
            )

    lat_nos = [avg_lat_no.get(nid, 0.0) for nid in ids_nos if nid in pos_dict]
    xs_nos = [pos_dict[nid][0] for nid in ids_nos if nid in pos_dict]
    ys_nos = [pos_dict[nid][1] for nid in ids_nos if nid in pos_dict]
    nids_v = [nid for nid in ids_nos if nid in pos_dict]

    vmin = min(lat_nos) if lat_nos else 0.0
    vmax = max(lat_nos) if lat_nos else 1.0
    if vmin == vmax:
        vmax = vmin + 0.0001
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.RdYlGn_r

    sc = ax_map.scatter(
        xs_nos, ys_nos, c=lat_nos, cmap=cmap, norm=norm,
        s=500, marker='o', edgecolors='black', linewidth=2, zorder=5
    )

    for nid in nids_v:
        x, y = pos_dict[nid]
        ax_map.text(
            x, y - 38, nid.replace('_', ' ').title(),
            fontsize=10, fontweight='bold', ha='center', zorder=6
        )

    cbar = plt.colorbar(sc, ax=ax_map, fraction=0.046, pad=0.04)
    cbar.set_label('Latência Média Operacional (Segundos)', rotation=270, labelpad=20, fontsize=11)
    ax_map.set_title('6. Disposição Geográfica (Anel Bidirecional & Heatmap)', fontsize=14, fontweight='bold')
    ax_map.set_xlabel('Coordenada X (Metros)')
    ax_map.set_ylabel('Coordenada Y (Metros)')
    ax_map.grid(True, linestyle=':', alpha=0.7)
    if xs_nos and ys_nos:
        ax_map.set_xlim(min(xs_nos) - 110, max(xs_nos) + 110)
        ax_map.set_ylim(min(ys_nos) - 110, max(ys_nos) + 110)


def gerar_graficos():
    print("📊 Lendo dados de results.csv e montando Dashboards da Topologia em Anel P2P...")

    try:
        df, posicoes, config, links = carregar()
    except Exception as e:
        print(f"❌ Erro ao carregar arquivos: {e}")
        return

    brutos = config.get('tipos_rede', [])
    labels = [NED_PARA_LABEL.get(t, t) for t in brutos]
    vistos = set()
    TIPOS_REDE_ATIVOS = [x for x in labels if not (x in vistos or vistos.add(x))] or list(NED_PARA_LABEL.values())
    CORES_TECH = {t: _PALETA[i % len(_PALETA)] for i, t in enumerate(TIPOS_REDE_ATIVOS)}
    link_map = _build_link_map(links)

    node_data = df[df['Origem'].str.startswith('OmnetSim-0.agente_')].copy()
    if node_data.empty:
        node_data = df[df['Origem'].str.startswith('OmnetSim-0.')].copy()
    node_data['NodeId'] = node_data['Origem'].str.replace('OmnetSim-0.', '', regex=False)

    time_data = node_data.pivot_table(
        index=['Tempo', 'Origem', 'NodeId'],
        columns='Atributo',
        values='Valor',
        aggfunc='first'
    ).reset_index()

    for col in ['packets_sent', 'packets_received', 'packets_dropped']:
        if col not in time_data.columns:
            time_data[col] = 0.0
        time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

    dados_expandidos = []
    for _, row in time_data.iterrows():
        t, origem, node_id = row['Tempo'], row['Origem'], row['NodeId']
        val_out = str(row.get('val_out', ''))
        sizes_str = str(row.get('packet_sizes_out', ''))
        lats_str = str(row.get('latencies_out', ''))
        jits_str = str(row.get('jitters_out', ''))

        if val_out and val_out != 'nan':
            msgs = val_out.split('|||')
            sizes = sizes_str.split('|||') if sizes_str and sizes_str != 'nan' else []
            lats = lats_str.split('|||') if lats_str and lats_str != 'nan' else []
            jits = jits_str.split('|||') if jits_str and jits_str != 'nan' else []

            for i in range(len(msgs)):
                size = float(sizes[i]) if i < len(sizes) and sizes[i] else 0.0
                lat = float(lats[i]) if i < len(lats) and lats[i] else 0.0
                jit = float(jits[i]) if i < len(jits) and jits[i] else 0.0
                sender = extrair_remetente(msgs[i])
                sender_id = sender.lower() if sender else ''
                tech = (
                    link_map.get((node_id, sender_id))
                    or link_map.get((sender_id, node_id))
                    or 'Desconhecido'
                )
                nome_formatado = node_id.replace('_', ' ').title()

                dados_expandidos.append({
                    'Tempo': t,
                    'Nó_Físico': origem,
                    'NodeId': node_id,
                    'Agente': nome_formatado,
                    'Sender': sender_id,
                    'RedeLink': tech,
                    'Tamanho': size,
                    'Latencia': lat,
                    'Jitter': jit,
                })

    df_exp = pd.DataFrame(dados_expandidos)
    if df_exp.empty:
        print("⚠️ Nenhuma mensagem encontrada no CSV.")
        return

    # ── Métricas Globais ──────────────────────────────────────
    p_env = time_data.groupby('NodeId')['packets_sent'].max().sum()
    p_rec = time_data.groupby('NodeId')['packets_received'].max().sum()
    p_drop = time_data.groupby('NodeId')['packets_dropped'].max().sum()

    pdr_global = (p_rec / p_env * 100) if p_env > 0 else 0.0
    drop_rate_global = (p_drop / p_env * 100) if p_env > 0 else 0.0

    lat_media = df_exp['Latencia'].mean() * 1000
    lat_p95 = df_exp['Latencia'].quantile(0.95) * 1000
    jit_media = df_exp['Jitter'].mean() * 1e6
    avg_lat_no = df_exp.groupby('NodeId')['Latencia'].mean().to_dict()

    # ══════════════════════════════════════════════════════════
    # 1. DASHBOARD POR AGENTE ROTEADOR (grafico_trafego_Anel.svg)
    # ══════════════════════════════════════════════════════════
    agentes_list = sorted(
        df_exp['Agente'].unique(),
        key=lambda s: int(s.split()[-1]) if s.split()[-1].isdigit() else 0
    )
    cores_agentes = {ag: _PALETA[i % len(_PALETA)] for i, ag in enumerate(agentes_list)}

    tabela_agentes = []
    for ag in agentes_list:
        df_ag = df_exp[df_exp['Agente'] == ag]
        if not df_ag.empty:
            l_mean = df_ag['Latencia'].mean() * 1000
            j_mean = df_ag['Jitter'].mean() * 1e6
            nid = ag.replace(' ', '_').lower()
            df_omnet = time_data[time_data['NodeId'] == nid]
            drops_local = df_omnet['packets_dropped'].max() if not df_omnet.empty else 0.0
            recebidos_local = len(df_ag)
            tentativas_local = recebidos_local + drops_local
            pdr_ag = (recebidos_local / tentativas_local * 100) if tentativas_local > 0 else 100.0
            tabela_agentes.append([ag, f"{l_mean:.1f} ms", f"{j_mean:.1f} μs", f"{pdr_ag:.1f} %", recebidos_local])

    fig = plt.figure(figsize=(26, 14))
    fig.suptitle("Painel Executivo CPS: Topologia em Anel P2P (Por Agente Roteador)", fontsize=22, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(4, 3, figure=fig, height_ratios=[0.3, 2, 1.5, 1], width_ratios=[1, 1, 1.5])

    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis('off')
    kpi_text = (
        f"  |  Total Mensagens: {int(p_env)}  |  "
        f"Delivery Ratio (PDR): {pdr_global:.1f}%  |  "
        f"Drop Rate: {drop_rate_global:.1f}%  |  "
        f"Latência Média: {lat_media:.2f} ms  |  "
        f"Latência P95: {lat_p95:.2f} ms  |  "
        f"Jitter Médio: {jit_media:.2f} μs  |"
    )
    ax_kpi.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=15, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', edgecolor='black'))

    ax_lat = fig.add_subplot(gs[1, 0])
    ax_pay = fig.add_subplot(gs[1, 1])
    ax_jit = fig.add_subplot(gs[2, 0])
    ax_int = fig.add_subplot(gs[2, 1])
    ax_tab = fig.add_subplot(gs[3, 0:2])
    ax_map = fig.add_subplot(gs[1:, 2])

    for ag in agentes_list:
        df_sub = df_exp[df_exp['Agente'] == ag]
        if not df_sub.empty:
            agg = df_sub.groupby('Tempo')['Latencia'].agg(['mean', 'min', 'max']).reset_index()
            cor = cores_agentes[ag]
            ax_lat.plot(agg['Tempo'], agg['mean'] * 1000, color=cor, label=ag, linewidth=2)
            ax_lat.fill_between(agg['Tempo'], agg['min'] * 1000, agg['max'] * 1000, color=cor, alpha=0.15)
    ax_lat.set_title('1. Latência Temporal por Agente (ms)', fontweight='bold', fontsize=13)
    ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Tempo (s)'); ax_lat.legend(fontsize=9); ax_lat.grid(ls='--', alpha=0.5)

    pay_vals = [df_exp[df_exp['Agente'] == ag]['Tamanho'].mean() for ag in agentes_list]
    bars = ax_pay.bar(agentes_list, pay_vals, color=[cores_agentes[ag] for ag in agentes_list], edgecolor='black', alpha=0.85)
    for bar, val in zip(bars, pay_vals):
        ax_pay.text(bar.get_x() + bar.get_width() / 2, val + 3, f"{val:.0f} B", ha='center', fontsize=9, fontweight='bold')
    ax_pay.set_title('2. Payload Médio Recebido por Agente (Bytes)', fontweight='bold', fontsize=13)
    ax_pay.set_ylabel('Bytes'); ax_pay.grid(axis='y', ls='--', alpha=0.5)

    dados_jit = [df_exp[df_exp['Agente'] == ag]['Jitter'] * 1e6 for ag in agentes_list]
    if dados_jit:
        ax_jit.boxplot(dados_jit, orientation='horizontal', patch_artist=True,
                       boxprops=dict(facecolor='#ffbf0e', color='black'), medianprops=dict(color='red', linewidth=2))
        ax_jit.set_yticks(range(1, len(agentes_list) + 1))
        ax_jit.set_yticklabels(agentes_list)
    ax_jit.set_title('3. Distribuição de Jitter por Agente (μs)', fontweight='bold', fontsize=13)
    ax_jit.set_xlabel('Jitter (μs)'); ax_jit.grid(axis='x', ls='--', alpha=0.5)

    transito_pct = max(0, 100 - pdr_global - drop_rate_global)
    ax_int.barh(['Global'], [pdr_global], color='#2ca02c', edgecolor='black', label='Entregues')
    ax_int.barh(['Global'], [drop_rate_global], left=[pdr_global], color='#d62728', edgecolor='black', label='Dropados')
    ax_int.barh(['Global'], [transito_pct], left=[pdr_global + drop_rate_global], color='#7f7f7f', edgecolor='black')
    ax_int.text(pdr_global / 2, 0, f"{pdr_global:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=13)
    if drop_rate_global >= 1.0:
        ax_int.text(pdr_global + drop_rate_global / 2, 0, f"{drop_rate_global:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=11)
    ax_int.set_title('4. Taxa de Entrega de Pacotes (PDR Global)', fontweight='bold', fontsize=13)
    ax_int.set_xlim(0, 100); ax_int.set_xticks([0, 25, 50, 75, 100]); ax_int.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax_int.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=2)

    ax_tab.axis('tight'); ax_tab.axis('off')
    if tabela_agentes:
        tabela = ax_tab.table(
            cellText=tabela_agentes,
            colLabels=['Agente Roteador', 'Latência (Média)', 'Jitter (Média)', 'PDR', 'Mensagens Recebidas'],
            cellLoc='center', loc='center', colColours=['#f0f0f0'] * 5
        )
        tabela.auto_set_font_size(False); tabela.set_fontsize(11); tabela.scale(1, 1.5)
    ax_tab.set_title('5. Tabela Comparativa de Desempenho (Por Nó)', fontweight='bold', fontsize=13)

    _desenhar_mapa_anel(ax_map, posicoes, links, avg_lat_no, CORES_TECH, rede_foco=None)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.savefig('grafico_trafego_Anel.svg')
    print("✅ Salvo: grafico_trafego_Anel.svg")
    plt.close(fig)

    # ══════════════════════════════════════════════════════════
    # 2. DASHBOARDS POR TECNOLOGIA (Geral + cada tecnologia ativa)
    # ══════════════════════════════════════════════════════════
    tabela_tech = []
    for tipo in TIPOS_REDE_ATIVOS:
        df_t = df_exp[df_exp['RedeLink'] == tipo]
        if not df_t.empty:
            l_m = df_t['Latencia'].mean() * 1000
            j_m = df_t['Jitter'].mean() * 1e6
            n_am = len(df_t)
            nids_t = {nid for (a, b), tech in link_map.items() if tech == tipo for nid in (a, b)}
            sub_td = time_data[time_data['NodeId'].isin(nids_t)]
            d_t = sub_td.groupby('NodeId')['packets_dropped'].max().sum() if not sub_td.empty else 0.0
            tot = n_am + d_t
            pdr_t = (n_am / tot * 100) if tot > 0 else 100.0
            tabela_tech.append([tipo, f"{l_m:.1f} ms", f"{j_m:.1f} μs", f"{pdr_t:.1f}%", n_am])

    for rede_foco in ['Geral'] + TIPOS_REDE_ATIVOS:
        fig = plt.figure(figsize=(26, 14))
        titulo = (
            f"Painel Executivo CPS — Anel: Visão {rede_foco}"
            if rede_foco != 'Geral'
            else "Painel Executivo CPS — Topologia em Anel: Visão Geral"
        )
        fig.suptitle(titulo, fontsize=22, fontweight='bold', y=0.98)
        gs = gridspec.GridSpec(4, 3, figure=fig, height_ratios=[0.3, 2, 1.5, 1], width_ratios=[1, 1, 1.5])

        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis('off')
        ax_kpi.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=15, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', edgecolor='black'))

        ax_lat = fig.add_subplot(gs[1, 0])
        ax_pay = fig.add_subplot(gs[1, 1])
        ax_jit = fig.add_subplot(gs[2, 0])
        ax_int = fig.add_subplot(gs[2, 1])
        ax_tab = fig.add_subplot(gs[3, 0:2])
        ax_map = fig.add_subplot(gs[1:, 2])

        redes_ativas = TIPOS_REDE_ATIVOS if rede_foco == 'Geral' else [rede_foco]

        for tipo in redes_ativas:
            df_sub = df_exp[df_exp['RedeLink'] == tipo]
            if df_sub.empty:
                continue
            agg = df_sub.groupby('Tempo')['Latencia'].agg(['mean', 'min', 'max']).reset_index()
            cor = CORES_TECH.get(tipo, '#888')
            ax_lat.plot(agg['Tempo'], agg['mean'] * 1000, color=cor, label=tipo, linewidth=2)
            ax_lat.fill_between(agg['Tempo'], agg['min'] * 1000, agg['max'] * 1000, color=cor, alpha=0.15)
        ax_lat.set_title('1. Latência Temporal (Média e Variação)', fontweight='bold', fontsize=13)
        ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Tempo (s)'); ax_lat.legend(fontsize=9); ax_lat.grid(ls='--', alpha=0.5)

        tipos_c = [t for t in redes_ativas if not df_exp[df_exp['RedeLink'] == t].empty]
        pay_vals = [df_exp[df_exp['RedeLink'] == t]['Tamanho'].mean() for t in tipos_c]
        pay_cores = [CORES_TECH.get(t, '#888') for t in tipos_c]
        if tipos_c:
            bars = ax_pay.bar(tipos_c, pay_vals, color=pay_cores, edgecolor='black', alpha=0.85)
            for bar, val in zip(bars, pay_vals):
                ax_pay.text(bar.get_x() + bar.get_width() / 2, val + 3, f'{val:.0f} B', ha='center', fontsize=9, fontweight='bold')
        ax_pay.set_title('2. Payload Médio por Tecnologia (Bytes)', fontweight='bold', fontsize=13)
        ax_pay.set_ylabel('Bytes'); ax_pay.grid(axis='y', ls='--', alpha=0.5)

        dados_j, labels_j = [], []
        for tipo in redes_ativas:
            jits = df_exp[df_exp['RedeLink'] == tipo]['Jitter'] * 1e6
            if not jits.empty:
                dados_j.append(jits); labels_j.append(tipo)
        if dados_j:
            ax_jit.boxplot(dados_j, orientation='horizontal', patch_artist=True,
                           boxprops=dict(facecolor='#ffbf0e', color='black'), medianprops=dict(color='red', linewidth=2))
            ax_jit.set_yticks(range(1, len(labels_j) + 1))
            ax_jit.set_yticklabels(labels_j, fontsize=9)
        ax_jit.set_title('3. Distribuição de Jitter (Boxplot)', fontweight='bold', fontsize=13)
        ax_jit.set_xlabel('Jitter (μs)'); ax_jit.grid(axis='x', ls='--', alpha=0.5)

        if rede_foco == 'Geral':
            ent_pct, drp_pct = pdr_global, drop_rate_global
            label_b, titulo_i = 'Global', '4. Taxa de Entrega Global (PDR)'
        else:
            df_sub = df_exp[df_exp['RedeLink'] == rede_foco]
            n_am = len(df_sub)
            nids_f = {nid for (a, b), tech in link_map.items() if tech == rede_foco for nid in (a, b)}
            sub_td = time_data[time_data['NodeId'].isin(nids_f)]
            d_f = sub_td.groupby('NodeId')['packets_dropped'].max().sum() if not sub_td.empty else 0.0
            tot = n_am + d_f
            ent_pct = (n_am / tot * 100) if tot > 0 else 0.0
            drp_pct = (d_f / tot * 100) if tot > 0 else 0.0
            label_b, titulo_i = rede_foco, f'4. Taxa de Entrega — {rede_foco}'

        rem_pct = max(0, 100 - ent_pct - drp_pct)
        ax_int.barh([label_b], [ent_pct], color='#2ca02c', edgecolor='black', label='Entregues')
        ax_int.barh([label_b], [drp_pct], left=[ent_pct], color='#d62728', edgecolor='black', label='Dropados')
        ax_int.barh([label_b], [rem_pct], left=[ent_pct + drp_pct], color='#7f7f7f', edgecolor='black')
        ax_int.text(ent_pct / 2, 0, f'{ent_pct:.1f}%', va='center', ha='center', color='white', fontweight='bold', fontsize=13)
        if drp_pct >= 1.0:
            ax_int.text(ent_pct + drp_pct / 2, 0, f'{drp_pct:.1f}%', va='center', ha='center', color='white', fontweight='bold', fontsize=11)
        ax_int.set_title(titulo_i, fontweight='bold', fontsize=13)
        ax_int.set_xlim(0, 100); ax_int.set_xticks([0, 25, 50, 75, 100]); ax_int.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_int.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=2)

        ax_tab.axis('tight'); ax_tab.axis('off')
        if tabela_tech:
            tab = ax_tab.table(
                cellText=tabela_tech,
                colLabels=['Rede', 'Latência Média', 'Jitter Médio', 'PDR', 'Amostras'],
                cellLoc='center', loc='center', colColours=['#f0f0f0'] * 5
            )
            tab.auto_set_font_size(False); tab.set_fontsize(11); tab.scale(1, 1.5)
        ax_tab.set_title('5. Tabela Comparativa de Desempenho (Por Tecnologia)', fontweight='bold', fontsize=13)

        _desenhar_mapa_anel(ax_map, posicoes, links, avg_lat_no, CORES_TECH, rede_foco=rede_foco)

        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        nome = f'grafico_trafego_{rede_foco}.svg'
        plt.savefig(nome)
        print(f"✅ Salvo: {nome}")
        if rede_foco == 'Geral':
            _extra = [a for a in fig.axes if a not in (ax_kpi, ax_lat, ax_pay, ax_jit, ax_int, ax_tab, ax_map)]
            _exportar_paineis_separados(fig, [
                ('heatmap',  [ax_map] + _extra),
                ('latencia', [ax_lat]),
                ('payload',  [ax_pay]),
                ('pdr',      [ax_int]),
                ('jitter',   [ax_jit]),
            ])
        plt.close(fig)


if __name__ == '__main__':
    gerar_graficos()