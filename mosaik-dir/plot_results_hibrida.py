"""
plot_results_hibrida.py — Dashboard da topologia Híbrida multi-camada.

Lê results.csv, posicoes.json, config.json e links.json (todos produzidos na
mesma rodada de simulação) e gera grafico_hibrida.png com quatro painéis:

  1. Mapa da rede  — nós coloridos por camada (CCO / sub / con / med)
                    e arestas coloridas por tipo de canal
  2. PDR por camada — taxa de entrega agregada por nível
  3. Latência por tipo de canal (Fibra / Celular / RF Mesh)
  4. PDR global  — barra empilhada Entregues / Dropados

Filtro de origem: nós do tipo 'OmnetSim-0.cco', 'OmnetSim-0.sub*',
    'OmnetSim-0.con*', 'OmnetSim-0.med*'
"""

import json
import os

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.patches as mpatches
import pandas as pd

# ── Paleta por tipo de canal ──────────────────────────────────────────────────
CORES_CANAL = {
    'Fibra':       '#1f77b4',
    'Celular5G':   '#2ca02c',
    'Celular4G':   '#17becf',
    'Celular3G':   '#ff7f0e',
    'Celular2G':   '#9467bd',
    'PLC':         '#8c564b',
    'RFMesh':      '#bcbd22',
}
NOMES_CANAL = {
    'Fibra':       'Fibra (1 Gbps)',
    'Celular5G':   '5G (200 Mbps)',
    'Celular4G':   '4G (50 Mbps)',
    'Celular3G':   '3G (2 Mbps)',
    'Celular2G':   '2G (100 kbps)',
    'PLC':         'PLC (100 kbps)',
    'RFMesh':      'RF Mesh (150 kbps)',
}

# Paleta por camada
CORES_CAMADA = {
    'controle':     '#007024',   # cco   — verde vivo
    'subestacao':   '#1f77b4',   # subs  — azul
    'concentrador': '#ff7f0e',   # cons  — laranja
    'medidor':      '#d62728',   # meds  — vermelho
}
TAMANHO_CAMADA = {
    'controle':     220,
    'subestacao':   130,
    'concentrador': 70,
    'medidor':      30,
}
CAMADAS_ORDEM = ['controle', 'subestacao', 'concentrador', 'medidor']


# ── Utilitários I/O ──────────────────────────────────────────────────────────

def _path(nome):
    full = f'/omnet-dir/{nome}'
    return full if os.path.exists(full) else nome


def carregar():
    try:
        df = pd.read_csv(_path('results.csv'))
    except FileNotFoundError:
        raise FileNotFoundError("results.csv não encontrado.")

    try:
        with open(_path('posicoes.json')) as f:
            posicoes = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("posicoes.json não encontrado.")

    try:
        with open(_path('config.json')) as f:
            config = json.load(f)
    except Exception:
        config = {}

    try:
        with open(_path('links.json')) as f:
            links = json.load(f)
    except Exception:
        links = []

    return df, posicoes, config, links


def _camada(nid):
    if nid == 'cco':
        return 'controle'
    if nid.startswith('sub'):
        return 'subestacao'
    if nid.startswith('con'):
        return 'concentrador'
    return 'medidor'


# ── Função principal ──────────────────────────────────────────────────────────

def gerar_grafico_hibrida():
    print(" Gerando dashboard da topologia Híbrida (PNG)...")
    try:
        df, posicoes, config, links = carregar()
    except Exception as e:
        print(f"X {e}")
        return

    pos = {ag['id']: (ag['x'], ag['y']) for ag in posicoes}

    # Camada de cada nó
    camada_no = {ag['id']: ag.get('camada', _camada(ag['id'])) for ag in posicoes}

    # ── Filtra CSV ────────────────────────────────────────────────────────────
    prefixos_hibrida = ('cco', 'sub', 'con', 'med')
    nd = df[df['Origem'].str.startswith(
        tuple(f'OmnetSim-0.{p}' for p in prefixos_hibrida)
    )].copy()

    if nd.empty:
        nd = df[df['Origem'].str.startswith('OmnetSim-0.')].copy()

    nd['NodeId'] = nd['Origem'].str.replace('OmnetSim-0.', '', regex=False)

    td = nd.pivot_table(
        index=['Tempo', 'NodeId'],
        columns='Atributo',
        values='Valor',
        aggfunc='first',
    ).reset_index()

    for col in ('packets_sent', 'packets_received', 'packets_dropped'):
        if col not in td.columns:
            td[col] = 0.0
        td[col] = pd.to_numeric(td[col], errors='coerce').fillna(0)

    # ── Expande latências ─────────────────────────────────────────────────────
    rows = []
    for _, row in td.iterrows():
        lats  = str(row.get('latencies_out', ''))
        jits  = str(row.get('jitters_out',   ''))
        sizes = str(row.get('packet_sizes_out', ''))
        if not lats or lats == 'nan':
            continue
        for i, lat in enumerate(lats.split('|||')):
            if not lat.strip():
                continue
            jit_parts  = jits.split('|||')
            size_parts = sizes.split('|||')
            jit  = jit_parts[i]  if i < len(jit_parts)  else '0'
            size = size_parts[i] if i < len(size_parts) else '0'
            try:
                rows.append({
                    'NodeId':   row['NodeId'],
                    'Camada':   camada_no.get(row['NodeId'], _camada(row['NodeId'])),
                    'Latencia': float(lat),
                    'Jitter':   float(jit)  if jit  else 0.0,
                    'Tamanho':  float(size) if size else 0.0,
                })
            except ValueError:
                pass

    df_exp = (pd.DataFrame(rows) if rows
              else pd.DataFrame(columns=['NodeId', 'Camada', 'Latencia',
                                         'Jitter', 'Tamanho']))

    # Mapa nó → canal de saída
    nid2canal = {}
    for lk in links:
        nid2canal.setdefault(lk['origem'], lk.get('tipo', 'Fibra'))

    # ── KPI globais ───────────────────────────────────────────────────────────
    p_env  = td.groupby('NodeId')['packets_sent'].max().sum()
    p_rec  = td.groupby('NodeId')['packets_received'].max().sum()
    p_drop = td.groupby('NodeId')['packets_dropped'].max().sum()
    pdr    = (p_rec  / p_env * 100) if p_env > 0 else 0
    drop_r = (p_drop / p_env * 100) if p_env > 0 else 0
    lat_m  = df_exp['Latencia'].mean() * 1000 if not df_exp.empty else 0
    jit_m  = df_exp['Jitter'].mean()   * 1e6  if not df_exp.empty else 0

    # Parâmetros da rodada (para o título)
    n_subs  = config.get('subestacoes',       '?')
    n_cons  = config.get('concentradores',    '?')
    n_meds  = config.get('medidores_cluster', '?')
    celular = config.get('celular_hibrida',   '?')

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(22, 13))
    fig.suptitle(
        f"Painel Executivo CPS: Topologia Híbrida  "
        f"[{n_subs} subs · {n_cons} cons/sub · {n_meds} meds/con · celular={celular}]",
        fontsize=18, fontweight='bold', y=0.99,
    )
    gs = gridspec.GridSpec(
        3, 3, figure=fig,
        height_ratios=[0.25, 2, 1.6],
        width_ratios=[1.6, 1, 1],
        hspace=0.45, wspace=0.35,
    )

    # ── KPI header ────────────────────────────────────────────────────────────
    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis('off')
    kpi = (
        f"  |  Total Pacotes: {int(p_env)}  |  "
        f"PDR: {pdr:.1f}%  |  "
        f"Drop Rate: {drop_r:.1f}%  |  "
        f"Latência Média: {lat_m:.2f} ms  |  "
        f"Jitter Médio: {jit_m:.2f} μs  |"
    )
    ax_kpi.text(0.5, 0.5, kpi, ha='center', va='center',
                fontsize=14, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0'))

    # ── 1. Mapa multi-camada ──────────────────────────────────────────────────
    ax_map = fig.add_subplot(gs[1:, 0])

    # Desenha enlaces coloridos por canal
    plotted_canais: set = set()
    for lk in links:
        o     = lk['origem']
        d     = lk['destino']
        canal = lk.get('tipo', 'Fibra')
        if o not in pos or d not in pos:
            continue
        x0, y0 = pos[o]
        x1, y1 = pos[d]
        cor    = CORES_CANAL.get(canal, '#aaa')
        label  = NOMES_CANAL.get(canal, canal) if canal not in plotted_canais else '_'
        lw     = 2.0 if canal == 'Fibra' else (1.2 if 'Celular' in canal else 0.7)
        alpha  = 0.7 if canal == 'Fibra' else (0.5 if 'Celular' in canal else 0.35)
        ax_map.plot([x0, x1], [y0, y1], color=cor, alpha=alpha,
                    linewidth=lw, label=label, zorder=1)
        plotted_canais.add(canal)

    # Heatmap de latência
    if not df_exp.empty:
        avg_lat = df_exp.groupby('NodeId')['Latencia'].mean()
        vmin, vmax = avg_lat.min(), avg_lat.max()
        if vmin == vmax:
            vmax = vmin + 1e-9
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = cm.RdYlGn_r
    else:
        avg_lat = pd.Series(dtype=float)
        norm = mcolors.Normalize(vmin=0, vmax=1)
        cmap = cm.RdYlGn_r

    # Plotagem por camada (controle por último, para ficar em cima)
    for camada in reversed(CAMADAS_ORDEM):
        nos_c = [ag for ag in posicoes
                 if ag.get('camada', _camada(ag['id'])) == camada]
        if not nos_c:
            continue
        xs = [ag['x'] for ag in nos_c]
        ys = [ag['y'] for ag in nos_c]
        lat_vals = [float(avg_lat.get(ag['id'], 0)) for ag in nos_c]
        s_size   = TAMANHO_CAMADA.get(camada, 50)
        cor_bord = CORES_CAMADA.get(camada, '#888')
        ax_map.scatter(xs, ys, s=s_size,
                       c=lat_vals, cmap=cmap, norm=norm,
                       zorder=10 if camada == 'controle' else 5,
                       edgecolors=cor_bord, linewidth=1.5)

    # Label apenas CCO e subestações
    for ag in posicoes:
        c = ag.get('camada', _camada(ag['id']))
        if c in ('controle', 'subestacao'):
            x, y = pos.get(ag['id'], (0, 0))
            ax_map.text(x, y + 80, ag['id'], ha='center', fontsize=7,
                        color='#1a3a2a', fontweight='bold')

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax_map, fraction=0.046, pad=0.04)
    cbar.set_label('Latência Média (s)', rotation=270, labelpad=18, fontsize=10)

    # Legenda de camadas (patches manuais)
    patches_camada = [
        mpatches.Patch(facecolor=CORES_CAMADA[c], edgecolor='black',
                       label=c.capitalize())
        for c in CAMADAS_ORDEM if any(
            ag.get('camada', _camada(ag['id'])) == c for ag in posicoes)
    ]
    leg1 = ax_map.legend(handles=patches_camada, title='Camada', loc='lower left',
                         fontsize=8, framealpha=0.85)
    ax_map.add_artist(leg1)
    ax_map.legend(title='Canal', loc='upper right', fontsize=7)

    ax_map.set_title('1. Mapa da Rede — Híbrida e Heatmap de Latência',
                     fontweight='bold', fontsize=13)
    ax_map.set_xlabel('Coordenada X (metros)')
    ax_map.set_ylabel('Coordenada Y (metros)')
    ax_map.grid(True, linestyle=':', alpha=0.4)

    # ── 2. PDR por camada ─────────────────────────────────────────────────────
    ax_pdr = fig.add_subplot(gs[1, 1])

    pdr_camadas, pdr_vals, pdr_cores = [], [], []
    for camada in CAMADAS_ORDEM:
        prefixo = 'cco' if camada == 'controle' else camada[:3]
        nos_c = td[td['NodeId'].str.startswith(prefixo)]
        s = nos_c['packets_sent'].max() if not nos_c.empty else 0
        r = nos_c['packets_received'].max() if not nos_c.empty else 0
        if s > 0:
            pdr_camadas.append(camada.capitalize())
            pdr_vals.append(r / s * 100)
            pdr_cores.append(CORES_CAMADA.get(camada, '#888'))

    if pdr_camadas:
        bars = ax_pdr.barh(pdr_camadas, pdr_vals, color=pdr_cores,
                           edgecolor='black')
        for bar, val in zip(bars, pdr_vals):
            ax_pdr.text(min(val + 1, 98), bar.get_y() + bar.get_height() / 2,
                        f'{val:.1f}%', va='center', fontsize=9)
        ax_pdr.set_xlim(0, 105)
        ax_pdr.set_xlabel('PDR (%)')
        ax_pdr.set_title('2. PDR por Camada', fontweight='bold', fontsize=13)
        ax_pdr.grid(axis='x', ls='--', alpha=0.5)

    # ── 3. Latência por canal ─────────────────────────────────────────────────
    ax_lat = fig.add_subplot(gs[1, 2])

    if not df_exp.empty:
        df_exp2 = df_exp.copy()
        df_exp2['Canal'] = df_exp2['NodeId'].map(
            lambda n: nid2canal.get(n, 'Fibra'))

        canais_usados = sorted(set(lk.get('tipo', 'Fibra') for lk in links))
        lat_vals_c, lat_labs_c, lat_cores_c = [], [], []
        for canal in canais_usados:
            df_c = df_exp2[df_exp2['Canal'] == canal]
            if df_c.empty:
                continue
            lat_vals_c.append(df_c['Latencia'].mean() * 1000)
            lat_labs_c.append(NOMES_CANAL.get(canal, canal))
            lat_cores_c.append(CORES_CANAL.get(canal, '#888'))

        if lat_vals_c:
            x_pos = range(len(lat_labs_c))
            ax_lat.bar(x_pos, lat_vals_c, color=lat_cores_c,
                       alpha=0.85, edgecolor='black')
            ax_lat.set_xticks(list(x_pos))
            ax_lat.set_xticklabels(lat_labs_c, rotation=20, ha='right', fontsize=8)
            ax_lat.set_ylabel('Latência Média (ms)')
            ax_lat.set_title('3. Latência por Canal',
                             fontweight='bold', fontsize=13)
            ax_lat.grid(axis='y', ls='--', alpha=0.5)
        else:
            ax_lat.set_title('3. Latência por Canal', fontweight='bold', fontsize=13)
            ax_lat.text(0.5, 0.5, 'Sem dados de latência',
                        ha='center', va='center', transform=ax_lat.transAxes)
    else:
        ax_lat.set_title('3. Latência por Canal', fontweight='bold', fontsize=13)
        ax_lat.text(0.5, 0.5, 'Sem dados de latência',
                    ha='center', va='center', transform=ax_lat.transAxes)

    # ── 4. PDR global ─────────────────────────────────────────────────────────
    ax_int = fig.add_subplot(gs[2, 1:])
    ax_int.barh(['Global'], [pdr], color='#2ca02c', edgecolor='black',
                label='Entregues')
    ax_int.barh(['Global'], [drop_r], left=[pdr], color='#d62728',
                edgecolor='black', label='Dropados')
    rem = max(0, 100 - pdr - drop_r)
    ax_int.barh(['Global'], [rem], left=[pdr + drop_r], color='#7f7f7f',
                edgecolor='black', label='Em trânsito')
    ax_int.text(pdr / 2, 0, f'{pdr:.1f}%', va='center', ha='center',
                color='white', fontweight='bold', fontsize=13)
    if drop_r >= 1.0:
        ax_int.text(pdr + drop_r / 2, 0, f'{drop_r:.1f}%', va='center',
                    ha='center', color='white', fontweight='bold', fontsize=11)
    ax_int.set_xlim(0, 100)
    ax_int.set_title('4. Taxa de Entrega Global (PDR)',
                     fontweight='bold', fontsize=13)
    ax_int.set_xticks([0, 25, 50, 75, 100])
    ax_int.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax_int.legend(loc='lower center', bbox_to_anchor=(0.5, -0.5), ncol=3)

    plt.savefig('grafico_hibrida.png', dpi=300, bbox_inches='tight')
    print("Salvo: grafico_hibrida.png")
    plt.close(fig)


if __name__ == '__main__':
    gerar_grafico_hibrida()