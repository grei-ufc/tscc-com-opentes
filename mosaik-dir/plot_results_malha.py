#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_malha.py — Dashboard em PNG para topologia Malha Completa.
Gera grafico_malha.png usando matplotlib (sem Plotly/HTML).
"""

import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd

CORES = {
    'Link_Wired':    '#1f77b4',
    'Link_5G':       '#2ca02c',
    'Link_Wireless': '#17becf',
    'Link_4G':       '#ff7f0e',
    'Link_2G':       '#9467bd',
}
NOMES = {
    'Link_Wired': 'Cabeada', 'Link_5G': '5G',
    'Link_Wireless': 'Wireless', 'Link_4G': '4G', 'Link_2G': '2G',
}

def _path(nome):
    p = f'/omnet-dir/{nome}'
    return p if os.path.exists(p) else nome

def _reconstruir_links(posicoes, config):
    ids   = [ag['id'] for ag in posicoes]
    tipos = config.get('tipos_rede', ['Link_Wired'])
    links = []; c = 0
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            links.append({'origem': ids[i], 'destino': ids[j],
                          'tipo': tipos[c % len(tipos)]})
            c += 1
    print(f"   ↳ {len(links)} enlaces reconstruídos.")
    return links

def carregar():
    if not os.path.exists('results.csv'):
        raise FileNotFoundError("results.csv não encontrado.")
    df = pd.read_csv('results.csv')
    with open(_path('posicoes.json')) as f: posicoes = json.load(f)
    with open(_path('config.json'))  as f: config   = json.load(f)
    p = _path('links.json')
    if os.path.exists(p):
        with open(p) as f: links = json.load(f)
        print(f"links.json carregado ({len(links)} enlaces).")
    else:
        print("links.json não encontrado — reconstruindo para malha completa.")
        links = _reconstruir_links(posicoes, config)
    return df, posicoes, config, links

def gerar_grafico_malha():
    print(" Gerando dashboard da topologia Malha (PNG)...")
    try:
        df, posicoes, config, links = carregar()
    except Exception as e:
        print(f"X{e}"); return

    pos = {ag['id']: (ag['x'], ag['y']) for ag in posicoes}

    # ── Processa CSV ──────────────────────────────────────────
    nd = df[df['Origem'].str.startswith('OmnetSim-0.')].copy()
    nd['NodeId'] = nd['Origem'].str.replace('OmnetSim-0.', '', regex=False)
    td = nd.pivot_table(index=['Tempo','NodeId'], columns='Atributo',
                        values='Valor', aggfunc='first').reset_index()
    for col in ['packets_sent','packets_received','packets_dropped']:
        if col not in td.columns: td[col] = 0.0
        td[col] = pd.to_numeric(td[col], errors='coerce').fillna(0)

    # Expande latências/jitters por mensagem
    rows = []
    for _, row in td.iterrows():
        for campo, chave in [('latencies_out','Latencia'),
                              ('jitters_out','Jitter'),
                              ('packet_sizes_out','Tamanho')]:
            pass  # vamos juntar abaixo
        lats = str(row.get('latencies_out',''))
        jits = str(row.get('jitters_out',''))
        sizes = str(row.get('packet_sizes_out',''))
        if lats and lats != 'nan':
            for i, lat in enumerate(lats.split('|||')):
                if not lat.strip(): continue
                jit  = jits.split('|||')[i]  if i < len(jits.split('|||'))  else '0'
                size = sizes.split('|||')[i] if i < len(sizes.split('|||')) else '0'
                try:
                    rows.append({'NodeId': row['NodeId'],
                                 'Latencia': float(lat),
                                 'Jitter': float(jit) if jit else 0.0,
                                 'Tamanho': float(size) if size else 0.0})
                except: pass
    df_exp = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=['NodeId','Latencia','Jitter','Tamanho'])

    # Métricas globais
    p_env  = td.groupby('NodeId')['packets_sent'].max().sum()
    p_rec  = td.groupby('NodeId')['packets_received'].max().sum()
    p_drop = td.groupby('NodeId')['packets_dropped'].max().sum()
    pdr    = (p_rec / p_env * 100) if p_env > 0 else 0
    drop_r = (p_drop / p_env * 100) if p_env > 0 else 0
    lat_m  = df_exp['Latencia'].mean() * 1000 if not df_exp.empty else 0
    jit_m  = df_exp['Jitter'].mean() * 1e6  if not df_exp.empty else 0

    # Mapa nó → tecnologia (primeira ocorrência de link)
    nid2tech = {}
    for lk in links:
        for k in ('origem','destino'):
            if lk[k] not in nid2tech:
                nid2tech[lk[k]] = lk.get('tipo','Link_Wired')

    techs_usadas = sorted(set(lk.get('tipo','Link_Wired') for lk in links))

    # ── Figura ────────────────────────────────────────────────
    fig = plt.figure(figsize=(22, 13))
    fig.suptitle("Painel Executivo CPS: Topologia Malha Completa (Full Mesh)",
                 fontsize=22, fontweight='bold', y=0.99)
    gs = gridspec.GridSpec(3, 3, figure=fig,
                           height_ratios=[0.25, 2, 1.6],
                           width_ratios=[1.6, 1, 1],
                           hspace=0.45, wspace=0.35)

    # ── KPI header ────────────────────────────────────────────
    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis('off')
    kpi = (f"  |  Total Pacotes: {int(p_env)}  |  "
           f"PDR: {pdr:.1f}%  |  "
           f"Drop Rate: {drop_r:.1f}%  |  "
           f"Latência Média: {lat_m:.2f} ms  |  "
           f"Jitter Médio: {jit_m:.2f} μs  |")
    ax_kpi.text(0.5, 0.5, kpi, ha='center', va='center',
                fontsize=14, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0'))

    # ── 1. Mapa da rede ───────────────────────────────────────
    ax_map = fig.add_subplot(gs[1:, 0])
    plotted_techs = set()
    for lk in links:
        o = lk['origem']; d = lk['destino']
        tech = lk.get('tipo','Link_Wired')
        if o not in pos or d not in pos: continue
        x0,y0 = pos[o]; x1,y1 = pos[d]
        cor   = CORES.get(tech,'#888')
        label = NOMES.get(tech, tech.replace('Link_','')) if tech not in plotted_techs else '_'
        ax_map.plot([x0,x1],[y0,y1], color=cor, alpha=0.35,
                    linewidth=1.2, label=label, zorder=1)
        plotted_techs.add(tech)

    for ag in posicoes:
        nid = ag['id']
        if nid not in pos: continue
        x,y  = pos[nid]
        eh_c = 'central' in nid
        ax_map.scatter(x, y, s=220 if eh_c else 100,
                       color='#007024' if eh_c else '#2F5D4B',
                       zorder=10, edgecolors='white', linewidth=2)
        lbl = 'Central' if eh_c else nid.replace('agent_p_','P').replace('agente_','A')
        ax_map.text(x, y+22, lbl, ha='center', fontsize=7, color='#1a3a2a')

    ax_map.set_title('1. Mapa da Rede — Arestas por Tecnologia',
                     fontweight='bold', fontsize=13)
    ax_map.set_xlabel('Coordenada X (metros)')
    ax_map.set_ylabel('Coordenada Y (metros)')
    ax_map.grid(True, linestyle=':', alpha=0.5)
    ax_map.legend(title='Tecnologia', loc='upper right', fontsize=9)

    # ── 2. PDR por tecnologia ─────────────────────────────────
    ax_pdr = fig.add_subplot(gs[1, 1])
    pdrs_t, labels_t, cores_t = [], [], []
    for tech in techs_usadas:
        nos = [n for n,t in nid2tech.items() if t == tech]
        env_t  = td[td['NodeId'].isin(nos)].groupby('NodeId')['packets_sent'].max().sum()
        rec_t  = td[td['NodeId'].isin(nos)].groupby('NodeId')['packets_received'].max().sum()
        drop_t = td[td['NodeId'].isin(nos)].groupby('NodeId')['packets_dropped'].max().sum()
        pdr_t  = (rec_t/env_t*100) if env_t > 0 else 0
        pdrs_t.append(pdr_t)
        labels_t.append(NOMES.get(tech, tech.replace('Link_','')))
        cores_t.append(CORES.get(tech,'#888'))

    if pdrs_t:
        bars = ax_pdr.barh(labels_t, pdrs_t, color=cores_t, edgecolor='black')
        for bar, val in zip(bars, pdrs_t):
            ax_pdr.text(min(val+1,98), bar.get_y()+bar.get_height()/2,
                        f'{val:.1f}%', va='center', fontsize=9)
        ax_pdr.set_xlim(0,105)
        ax_pdr.set_xlabel('PDR (%)')
        ax_pdr.set_title('2. PDR por Tecnologia', fontweight='bold', fontsize=13)
        ax_pdr.grid(axis='x', ls='--', alpha=0.5)

    # ── 3. Latência por tecnologia ────────────────────────────
    ax_lat = fig.add_subplot(gs[1, 2])
    if not df_exp.empty:
        lat_vals, lat_labs, lat_cores = [], [], []
        for tech in techs_usadas:
            nos   = [n for n,t in nid2tech.items() if t == tech]
            df_t  = df_exp[df_exp['NodeId'].isin(nos)]
            if df_t.empty: continue
            lat_vals.append(df_t['Latencia'].mean()*1000)
            lat_labs.append(NOMES.get(tech, tech.replace('Link_','')))
            lat_cores.append(CORES.get(tech,'#888'))
        if lat_vals:
            x_pos = range(len(lat_labs))
            ax_lat.bar(x_pos, lat_vals, color=lat_cores, alpha=0.85, edgecolor='black')
            ax_lat.set_xticks(list(x_pos))
            ax_lat.set_xticklabels(lat_labs, rotation=15, fontsize=9)
            ax_lat.set_ylabel('Latência Média (ms)')
            ax_lat.set_title('3. Latência por Tecnologia', fontweight='bold', fontsize=13)
            ax_lat.grid(axis='y', ls='--', alpha=0.5)

    # ── 4. PDR global (barra empilhada) ──────────────────────
    ax_int = fig.add_subplot(gs[2, 1:])
    ax_int.barh(['Global'], [pdr],    color='#2ca02c', edgecolor='black', label='Entregues')
    ax_int.barh(['Global'], [drop_r], left=[pdr], color='#d62728',
                edgecolor='black', label='Dropados')
    rem = max(0, 100-pdr-drop_r)
    ax_int.barh(['Global'], [rem], left=[pdr+drop_r], color='#7f7f7f', edgecolor='black')
    ax_int.text(pdr/2, 0, f'{pdr:.1f}%', va='center', ha='center',
                color='white', fontweight='bold', fontsize=13)
    if drop_r >= 1.0:
        ax_int.text(pdr+drop_r/2, 0, f'{drop_r:.1f}%', va='center', ha='center',
                    color='white', fontweight='bold', fontsize=11)
    ax_int.set_xlim(0,100)
    ax_int.set_title('4. Taxa de Entrega Global (PDR)', fontweight='bold', fontsize=13)
    ax_int.set_xticks([0,25,50,75,100])
    ax_int.set_xticklabels(['0%','25%','50%','75%','100%'])
    ax_int.legend(loc='lower center', bbox_to_anchor=(0.5,-0.5), ncol=3)

    plt.savefig('grafico_malha.png', dpi=300, bbox_inches='tight')
    print("Salvo: grafico_malha.png")
    plt.close(fig)

if __name__ == '__main__':
    gerar_grafico_malha()