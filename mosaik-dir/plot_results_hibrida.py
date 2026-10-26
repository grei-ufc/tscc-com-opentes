#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_hibrida.py — Dashboard Científico para Topologia Híbrida.

Mesmo padrão visual do anel e da estrela. Arquivos gerados:
  - grafico_trafego_Hibrida.png      (visão por Camada: CCO / Subestação / Concentrador / Medidor)
  - grafico_trafego_Geral.png        (visão global por Tecnologia de Enlace)
  - grafico_trafego_{Tecnologia}.png (visão individual por Tecnologia de Enlace)

Notas de método
  * As tecnologias vêm de links.json (não de config.json, que nestas topologias
    traz só os padrões da estrela).
  * Com roteamento multi-salto o remetente de uma mensagem é a ORIGEM, não o
    vizinho. A tecnologia de cada amostra é a do ÚLTIMO SALTO (enlace por onde
    o pacote chegou ao receptor), obtida por busca no grafo de links.
  * Contadores (enviados, recebidos, dropados, encaminhados) são acumulados por
    nó: usa-se o máximo de cada nó e SOMA-SE entre nós.
  * "Entrega por salto" de uma camada = (recebidos + encaminhados) /
    (recebidos + encaminhados + descartados) nos nós da camada.
"""

import json
import os
from collections import deque

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

NED_PARA_LABEL = {
    'Fibra':         'Fibra',
    'Celular5G':     '5G',
    'Celular4G':     '4G',
    'Celular3G':     '3G',
    'Celular2G':     '2G',
    'RFMesh':        'RF Mesh',
    'PLC':           'PLC',
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
    'Link_Wireless': 'Wireless',
}

# Mesma cor para a mesma tecnologia em todas as topologias (Cabeada/5G/Wireless/4G/2G
# coincidem com a paleta do anel e da estrela).
_COR_TECH = {
    'Cabeada': '#1f77b4', '5G': '#2ca02c', 'Wireless': '#17becf',
    '4G': '#ff7f0e', '2G': '#9467bd', 'Fibra': '#08306b',
    'RF Mesh': '#d62728', 'PLC': '#8c564b', '3G': '#bcbd22',
}
_PALETA_RESERVA = ['#e377c2', '#7f7f7f', '#bcbd22', '#aec7e8']

_RAIZ = 'cco'
_PAPEIS_ORDEM = [_RAIZ, 'sub', 'con', 'med']
_PAPEL_LABEL  = {_RAIZ: 'CCO', 'sub': 'Subestação', 'con': 'Concentrador', 'med': 'Medidor'}
_PAPEL_COLOR  = {_RAIZ: '#1f4e79', 'sub': '#ff7f0e', 'con': '#9467bd', 'med': '#2ca02c'}
_PAPEL_MARKER = {_RAIZ: '*', 'sub': 's', 'con': 'D', 'med': 'o'}
_PAPEL_SIZE   = {_RAIZ: 900, 'sub': 420, 'con': 300, 'med': 200}


# ── Utilitários ────────────────────────────────────────────────────────────────

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


def _papel(nome):
    n = str(nome).lower()
    if n.startswith(_RAIZ):
        return _RAIZ
    if n.startswith('con'):
        return 'con'
    if n.startswith('med'):
        return 'med'
    return 'sub'


def _label(tipo):
    return NED_PARA_LABEL.get(tipo, tipo)


def carregar():
    if not os.path.exists('results.csv'):
        raise FileNotFoundError("results.csv não encontrado.")
    df = pd.read_csv('results.csv')
    with open(_path('posicoes.json'), encoding='utf-8') as f:
        posicoes = json.load(f)
    with open(_path('config.json'), encoding='utf-8') as f:
        config = json.load(f)
    p = _path('links.json')
    links = []
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            links = json.load(f)
    return df, posicoes, config, links


def _extremos(lk):
    return lk.get('origem', lk.get('src', '')), lk.get('destino', lk.get('dst', ''))


def _grafo(links):
    adj = {}
    for lk in links:
        o, d = _extremos(lk)
        if not o or not d:
            continue
        lab = _label(lk.get('tipo', ''))
        adj.setdefault(o, {})[d] = lab
        adj.setdefault(d, {})[o] = lab
    return adj


def _tech_ultimo_salto(adj, receptor, remetente, cache):
    """Tecnologia do enlace por onde o pacote chegou ao receptor (caminho mínimo)."""
    chave = (receptor, remetente)
    if chave in cache:
        return cache[chave]
    res = 'Desconhecido'
    if receptor in adj and remetente in adj:
        if remetente in adj[receptor]:
            res = adj[receptor][remetente]
        else:
            pai = {receptor: None}
            fila = deque([receptor])
            achou = False
            while fila and not achou:
                cur = fila.popleft()
                for nb in sorted(adj.get(cur, {})):
                    if nb in pai:
                        continue
                    pai[nb] = cur
                    if nb == remetente:
                        achou = True
                        break
                    fila.append(nb)
            if achou:
                no = remetente
                while pai[no] != receptor:
                    no = pai[no]
                res = adj[receptor][no]
    cache[chave] = res
    return res


def extrair_remetente(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == '':
            return ''
        msg_json = json.loads(msg_str)
        sender = msg_json.get('sender', '')
        return sender.split('@')[0] if sender else ''
    except Exception:
        return ''


def _soma(td, col, nodes=None):
    """Máximo por nó (contador acumulado) somado entre nós."""
    sub = td if nodes is None else td[td['NodeId'].isin(list(nodes))]
    if sub.empty or col not in sub.columns:
        return 0.0
    return float(sub.groupby('NodeId')[col].max().sum())


def _fmt(v, fmt):
    return '—' if v is None or (isinstance(v, float) and np.isnan(v)) else fmt.format(v)


# ── Mapa geográfico ─────────────────────────────────────────────────────────────

def _desenhar_mapa(ax_map, posicoes, links, avg_lat_no, cores_tech, rede_foco=None):
    pos_dict = {ag['id']: (ag['x'], ag['y']) for ag in posicoes}
    todas = rede_foco in (None, 'Geral')

    for lk in links:
        o, d = _extremos(lk)
        if o not in pos_dict or d not in pos_dict:
            continue
        tech = _label(lk.get('tipo', ''))
        x0, y0 = pos_dict[o]
        x1, y1 = pos_dict[d]
        eh_foco = todas or tech == rede_foco
        cor = cores_tech.get(tech, '#555555') if eh_foco else '#cccccc'
        ax_map.plot([x0, x1], [y0, y1], color=cor, linestyle='-',
                    alpha=0.85 if eh_foco else 0.2,
                    linewidth=2.5 if eh_foco else 1.0, zorder=1)
        if eh_foco and not todas:
            ax_map.text((x0 + x1) / 2.0, (y0 + y1) / 2.0, tech,
                        fontsize=8, fontweight='bold', ha='center', va='center',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                  edgecolor=cor, alpha=0.85), zorder=4)

    xs_all = [x for x, _ in pos_dict.values()]
    ys_all = [y for _, y in pos_dict.values()]
    span = max((max(xs_all) - min(xs_all)) if xs_all else 0,
               (max(ys_all) - min(ys_all)) if ys_all else 0, 100.0)
    off = 0.045 * span

    ids_med = [i for i in pos_dict if _papel(i) == 'med']
    if ids_med:
        lat_med = [avg_lat_no.get(i, 0.0) for i in ids_med]
        vmin, vmax = min(lat_med), max(lat_med)
        if vmin == vmax:
            vmax = vmin + 0.0001
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        sc = ax_map.scatter([pos_dict[i][0] for i in ids_med],
                            [pos_dict[i][1] for i in ids_med],
                            c=lat_med, cmap=cm.RdYlGn_r, norm=norm,
                            s=_PAPEL_SIZE['med'], marker='o',
                            edgecolors='black', linewidth=1.5, zorder=5)
        cbar = plt.colorbar(sc, ax=ax_map, fraction=0.046, pad=0.04)
        cbar.set_label('Latência Média Recebida — Medidores (Segundos)',
                       rotation=270, labelpad=20, fontsize=11)
        if len(ids_med) <= 20:
            for i in ids_med:
                ax_map.text(pos_dict[i][0], pos_dict[i][1] - off, i, fontsize=7,
                            ha='center', zorder=7)

    presentes = {'med'} if ids_med else set()
    for i, (x, y) in pos_dict.items():
        p = _papel(i)
        if p == 'med':
            continue
        presentes.add(p)
        ax_map.scatter([x], [y], color=_PAPEL_COLOR[p], marker=_PAPEL_MARKER[p],
                       s=_PAPEL_SIZE[p], edgecolors='black', linewidth=2, zorder=6)
        ax_map.text(x, y - off * 1.2, i.upper(), fontsize=9, fontweight='bold',
                    ha='center', zorder=7)

    handles = [Line2D([0], [0], marker=_PAPEL_MARKER[p], color='w',
                      markerfacecolor=('#cccccc' if p == 'med' else _PAPEL_COLOR[p]),
                      markeredgecolor='black', markersize=11 if p != _RAIZ else 15,
                      label=_PAPEL_LABEL[p])
               for p in _PAPEIS_ORDEM if p in presentes]
    if todas:
        techs = []
        for lk in links:
            t = _label(lk.get('tipo', ''))
            if t not in techs:
                techs.append(t)
        handles += [Line2D([0], [0], color=cores_tech.get(t, '#555555'), linewidth=3, label=t)
                    for t in techs]
    ax_map.legend(handles=handles, loc='upper center', fontsize=9, framealpha=0.9,
                  ncol=min(5, max(1, len(handles))))

    ax_map.set_title('6. Disposição Geográfica (Híbrida & Heatmap de Latência)',
                     fontsize=14, fontweight='bold')
    ax_map.set_xlabel('Coordenada X (Metros)')
    ax_map.set_ylabel('Coordenada Y (Metros)')
    ax_map.grid(True, linestyle=':', alpha=0.7)
    if xs_all:
        m = 0.10 * span + 40
        ax_map.set_xlim(min(xs_all) - m, max(xs_all) + m)
        ax_map.set_ylim(min(ys_all) - m, max(ys_all) + m + 0.16 * span)


# ── Função principal ────────────────────────────────────────────────────────────

def _kpi(ax, texto):
    ax.axis('off')
    ax.text(0.5, 0.5, texto, ha='center', va='center', fontsize=15, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', edgecolor='black'))


def _barra_pdr(ax, rotulo, ent, drp, titulo):
    rem = max(0, 100 - ent - drp)
    ax.barh([rotulo], [ent], color='#2ca02c', edgecolor='black', label='Entregues')
    ax.barh([rotulo], [drp], left=[ent], color='#d62728', edgecolor='black', label='Dropados')
    ax.barh([rotulo], [rem], left=[ent + drp], color='#7f7f7f', edgecolor='black')
    ax.text(ent / 2, 0, f'{ent:.1f}%', va='center', ha='center', color='white',
            fontweight='bold', fontsize=13)
    if drp >= 1.0:
        ax.text(ent + drp / 2, 0, f'{drp:.1f}%', va='center', ha='center', color='white',
                fontweight='bold', fontsize=11)
    ax.set_title(titulo, fontweight='bold', fontsize=13)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=2)


def _grade():
    fig = plt.figure(figsize=(26, 14))
    gs = gridspec.GridSpec(4, 3, figure=fig, height_ratios=[0.3, 2, 1.5, 1],
                           width_ratios=[1, 1, 1.5])
    return fig, {
        'kpi': fig.add_subplot(gs[0, :]),
        'lat': fig.add_subplot(gs[1, 0]),
        'pay': fig.add_subplot(gs[1, 1]),
        'jit': fig.add_subplot(gs[2, 0]),
        'int': fig.add_subplot(gs[2, 1]),
        'tab': fig.add_subplot(gs[3, 0:2]),
        'map': fig.add_subplot(gs[1:, 2]),
    }


def _tabela(ax, linhas, colunas, titulo):
    ax.axis('tight'); ax.axis('off')
    if linhas:
        t = ax.table(cellText=linhas, colLabels=colunas, cellLoc='center', loc='center',
                     colColours=['#f0f0f0'] * len(colunas))
        t.auto_set_font_size(False); t.set_fontsize(11); t.scale(1, 1.5)
    ax.set_title(titulo, fontweight='bold', fontsize=13)


def gerar_graficos():
    print('Lendo dados de results.csv e montando Dashboards da Topologia Híbrida...')

    try:
        df, posicoes, config, links = carregar()
    except Exception as e:
        print(f' Erro ao carregar arquivos: {e}')
        return

    # Tecnologias ativas: da topologia real (links.json), na ordem em que aparecem.
    TIPOS = []
    for lk in links:
        t = _label(lk.get('tipo', ''))
        if t and t not in TIPOS:
            TIPOS.append(t)
    if not TIPOS:
        TIPOS = list(dict.fromkeys(_label(t) for t in config.get('tipos_rede', [])))
    CORES = {}
    reserva = iter(_PALETA_RESERVA)
    for t in TIPOS:
        CORES[t] = _COR_TECH.get(t) or next(reserva, '#555555')
    adj = _grafo(links)
    cache_tech = {}

    node_data = df[df['Origem'].str.startswith('OmnetSim-0.')].copy()
    node_data['NodeId'] = node_data['Origem'].str.replace('OmnetSim-0.', '', regex=False)

    time_data = node_data.pivot_table(
        index=['Tempo', 'Origem', 'NodeId'], columns='Atributo',
        values='Valor', aggfunc='first').reset_index()

    for col in ['packets_sent', 'packets_received', 'packets_dropped', 'packets_forwarded']:
        if col not in time_data.columns:
            time_data[col] = 0.0
        time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

    dados = []
    for _, row in time_data.iterrows():
        t, node_id = row['Tempo'], row['NodeId']
        val_out   = str(row.get('val_out', ''))
        sizes_str = str(row.get('packet_sizes_out', ''))
        lats_str  = str(row.get('latencies_out', ''))
        jits_str  = str(row.get('jitters_out', ''))
        if not val_out or val_out == 'nan':
            continue
        msgs  = val_out.split('|||')
        sizes = sizes_str.split('|||') if sizes_str and sizes_str != 'nan' else []
        lats  = lats_str.split('|||')  if lats_str  and lats_str  != 'nan' else []
        jits  = jits_str.split('|||')  if jits_str  and jits_str  != 'nan' else []
        for i in range(len(msgs)):
            size = float(sizes[i]) if i < len(sizes) and sizes[i] else 0.0
            lat  = float(lats[i])  if i < len(lats)  and lats[i]  else 0.0
            jit  = float(jits[i])  if i < len(jits)  and jits[i]  else 0.0
            sender_id = extrair_remetente(msgs[i]).lower()
            dados.append({
                'Tempo': t, 'NodeId': node_id, 'Sender': sender_id,
                'Papel': _papel(node_id),
                'RedeLink': _tech_ultimo_salto(adj, node_id, sender_id, cache_tech),
                'Tamanho': size, 'Latencia': lat, 'Jitter': jit,
            })

    df_exp = pd.DataFrame(dados)
    if df_exp.empty:
        print('  Nenhuma mensagem encontrada no CSV.')
        return

    desconhecidas = int((df_exp['RedeLink'] == 'Desconhecido').sum())
    if desconhecidas:
        print(f' {desconhecidas} amostra(s) sem enlace identificado (ficam fora dos painéis por tecnologia).')

    todos_nos = sorted(time_data['NodeId'].unique())

    # Métricas globais (máximo por nó, somado entre nós)
    p_env  = _soma(time_data, 'packets_sent')
    p_rec  = _soma(time_data, 'packets_received')
    p_drop = _soma(time_data, 'packets_dropped')
    p_fwd  = _soma(time_data, 'packets_forwarded')
    pdr_global = min(100.0, p_rec / p_env * 100) if p_env > 0 else 0.0
    drop_global = min(100.0 - pdr_global, p_drop / p_env * 100) if p_env > 0 else 0.0

    lat_media = df_exp['Latencia'].mean() * 1000
    lat_p95   = df_exp['Latencia'].quantile(0.95) * 1000
    jit_media = df_exp['Jitter'].mean() * 1e6
    avg_lat_no = df_exp.groupby('NodeId')['Latencia'].mean().to_dict()

    kpi_text = (
        f"  |  Total Mensagens: {int(p_env)}  |  "
        f"Delivery Ratio (PDR): {pdr_global:.1f}%  |  "
        f"Drop Rate: {drop_global:.1f}%  |  "
        f"Encaminhados: {int(p_fwd)}  |  "
        f"Latência Média: {lat_media:.2f} ms  |  "
        f"Latência P95: {lat_p95:.2f} ms  |  "
        f"Jitter Médio: {jit_media:.2f} μs  |"
    )

    # ══════════════════════════════════════════════════════════
    # 1. DASHBOARD POR CAMADA (grafico_trafego_Hibrida.png)
    # ══════════════════════════════════════════════════════════
    papeis = [p for p in _PAPEIS_ORDEM if any(_papel(n) == p for n in todos_nos)]
    tabela_papeis = []
    for p in papeis:
        nos_p = [n for n in todos_nos if _papel(n) == p]
        df_p = df_exp[df_exp['Papel'] == p]
        rec = _soma(time_data, 'packets_received', nos_p)
        fwd = _soma(time_data, 'packets_forwarded', nos_p)
        drp = _soma(time_data, 'packets_dropped', nos_p)
        chegadas = rec + fwd + drp
        pdr_p = (rec + fwd) / chegadas * 100 if chegadas > 0 else 100.0
        l_m = df_p['Latencia'].mean() * 1000 if not df_p.empty else None
        j_m = df_p['Jitter'].mean() * 1e6 if not df_p.empty else None
        tabela_papeis.append([_PAPEL_LABEL[p], _fmt(l_m, '{:.1f} ms'), _fmt(j_m, '{:.1f} μs'),
                              f'{pdr_p:.1f}%', int(fwd), len(df_p)])

    fig, ax = _grade()
    fig.suptitle('Painel Executivo CPS: Topologia Híbrida (Por Camada)',
                 fontsize=22, fontweight='bold', y=0.98)
    _kpi(ax['kpi'], kpi_text)

    com_msg = [p for p in papeis if not df_exp[df_exp['Papel'] == p].empty]
    for p in com_msg:
        agg = df_exp[df_exp['Papel'] == p].groupby('Tempo')['Latencia'].agg(['mean', 'min', 'max']).reset_index()
        ax['lat'].plot(agg['Tempo'], agg['mean'] * 1000, color=_PAPEL_COLOR[p],
                       label=_PAPEL_LABEL[p], linewidth=2)
        ax['lat'].fill_between(agg['Tempo'], agg['min'] * 1000, agg['max'] * 1000,
                               color=_PAPEL_COLOR[p], alpha=0.15)
    ax['lat'].set_title('1. Latência Temporal por Camada (ms)', fontweight='bold', fontsize=13)
    ax['lat'].set_ylabel('Latência (ms)'); ax['lat'].set_xlabel('Tempo (s)')
    ax['lat'].legend(fontsize=9); ax['lat'].grid(ls='--', alpha=0.5)

    pay = [df_exp[df_exp['Papel'] == p]['Tamanho'].mean() for p in com_msg]
    bars = ax['pay'].bar([_PAPEL_LABEL[p] for p in com_msg], pay,
                         color=[_PAPEL_COLOR[p] for p in com_msg], edgecolor='black', alpha=0.85)
    for b, v in zip(bars, pay):
        ax['pay'].text(b.get_x() + b.get_width() / 2, v + 3, f'{v:.0f} B',
                       ha='center', fontsize=9, fontweight='bold')
    ax['pay'].set_title('2. Payload Médio Recebido por Camada (Bytes)', fontweight='bold', fontsize=13)
    ax['pay'].set_ylabel('Bytes'); ax['pay'].grid(axis='y', ls='--', alpha=0.5)

    if com_msg:
        ax['jit'].boxplot([df_exp[df_exp['Papel'] == p]['Jitter'] * 1e6 for p in com_msg],
                          orientation='horizontal', patch_artist=True,
                          boxprops=dict(facecolor='#ffbf0e', color='black'),
                          medianprops=dict(color='red', linewidth=2))
        ax['jit'].set_yticks(range(1, len(com_msg) + 1))
        ax['jit'].set_yticklabels([_PAPEL_LABEL[p] for p in com_msg])
    ax['jit'].set_title('3. Distribuição de Jitter por Camada (μs)', fontweight='bold', fontsize=13)
    ax['jit'].set_xlabel('Jitter (μs)'); ax['jit'].grid(axis='x', ls='--', alpha=0.5)

    _barra_pdr(ax['int'], 'Global', pdr_global, drop_global, '4. Taxa de Entrega de Pacotes (PDR Global)')
    _tabela(ax['tab'], tabela_papeis,
            ['Camada', 'Latência (Média)', 'Jitter (Média)', 'Entrega por salto', 'Encaminhados', 'Mensagens Recebidas'],
            '5. Tabela Comparativa de Desempenho (Por Camada)')
    _desenhar_mapa(ax['map'], posicoes, links, avg_lat_no, CORES, rede_foco=None)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.savefig('grafico_trafego_Hibrida.png', dpi=300)
    print('Salvo: grafico_trafego_Hibrida.png')
    plt.close(fig)

    # ══════════════════════════════════════════════════════════
    # 2. DASHBOARDS POR TECNOLOGIA (Geral + cada tecnologia ativa)
    # ══════════════════════════════════════════════════════════
    def _nos_da_tech(tipo):
        return {n for o, nb in adj.items() for n, lab in nb.items() if lab == tipo for n in (o, n)}

    tabela_tech = []
    for tipo in TIPOS:
        df_t = df_exp[df_exp['RedeLink'] == tipo]
        if df_t.empty:
            continue
        n_am = len(df_t)
        d_t = _soma(time_data, 'packets_dropped', _nos_da_tech(tipo))
        pdr_t = n_am / (n_am + d_t) * 100 if (n_am + d_t) > 0 else 100.0
        tabela_tech.append([tipo, f"{df_t['Latencia'].mean() * 1000:.1f} ms",
                            f"{df_t['Jitter'].mean() * 1e6:.1f} μs", f'{pdr_t:.1f}%', n_am])

    for rede_foco in ['Geral'] + TIPOS:
        fig, ax = _grade()
        titulo = (f'Painel Executivo CPS — Híbrida: Visão {rede_foco}' if rede_foco != 'Geral'
                  else 'Painel Executivo CPS — Topologia Híbrida: Visão Geral')
        fig.suptitle(titulo, fontsize=22, fontweight='bold', y=0.98)
        _kpi(ax['kpi'], kpi_text)

        ativas = TIPOS if rede_foco == 'Geral' else [rede_foco]
        for tipo in ativas:
            df_sub = df_exp[df_exp['RedeLink'] == tipo]
            if df_sub.empty:
                continue
            agg = df_sub.groupby('Tempo')['Latencia'].agg(['mean', 'min', 'max']).reset_index()
            ax['lat'].plot(agg['Tempo'], agg['mean'] * 1000, color=CORES[tipo], label=tipo, linewidth=2)
            ax['lat'].fill_between(agg['Tempo'], agg['min'] * 1000, agg['max'] * 1000,
                                   color=CORES[tipo], alpha=0.15)
        ax['lat'].set_title('1. Latência Temporal (Média e Variação)', fontweight='bold', fontsize=13)
        ax['lat'].set_ylabel('Latência (ms)'); ax['lat'].set_xlabel('Tempo (s)')
        if ax['lat'].get_legend_handles_labels()[0]:
            ax['lat'].legend(fontsize=9)
        ax['lat'].grid(ls='--', alpha=0.5)

        com = [t for t in ativas if not df_exp[df_exp['RedeLink'] == t].empty]
        if com:
            vals = [df_exp[df_exp['RedeLink'] == t]['Tamanho'].mean() for t in com]
            bars = ax['pay'].bar(com, vals, color=[CORES[t] for t in com], edgecolor='black', alpha=0.85)
            for b, v in zip(bars, vals):
                ax['pay'].text(b.get_x() + b.get_width() / 2, v + 3, f'{v:.0f} B',
                               ha='center', fontsize=9, fontweight='bold')
        ax['pay'].set_title('2. Payload Médio por Tecnologia (Bytes)', fontweight='bold', fontsize=13)
        ax['pay'].set_ylabel('Bytes'); ax['pay'].grid(axis='y', ls='--', alpha=0.5)

        if com:
            ax['jit'].boxplot([df_exp[df_exp['RedeLink'] == t]['Jitter'] * 1e6 for t in com],
                              orientation='horizontal', patch_artist=True,
                              boxprops=dict(facecolor='#ffbf0e', color='black'),
                              medianprops=dict(color='red', linewidth=2))
            ax['jit'].set_yticks(range(1, len(com) + 1))
            ax['jit'].set_yticklabels(com, fontsize=9)
        ax['jit'].set_title('3. Distribuição de Jitter (Boxplot)', fontweight='bold', fontsize=13)
        ax['jit'].set_xlabel('Jitter (μs)'); ax['jit'].grid(axis='x', ls='--', alpha=0.5)

        if rede_foco == 'Geral':
            _barra_pdr(ax['int'], 'Global', pdr_global, drop_global, '4. Taxa de Entrega Global (PDR)')
        else:
            n_am = len(df_exp[df_exp['RedeLink'] == rede_foco])
            d_f = _soma(time_data, 'packets_dropped', _nos_da_tech(rede_foco))
            tot = n_am + d_f
            ent = n_am / tot * 100 if tot > 0 else 0.0
            drp = d_f / tot * 100 if tot > 0 else 0.0
            _barra_pdr(ax['int'], rede_foco, ent, drp, f'4. Taxa de Entrega — {rede_foco}')

        _tabela(ax['tab'], tabela_tech, ['Rede', 'Latência Média', 'Jitter Médio', 'PDR', 'Amostras'],
                '5. Tabela Comparativa de Desempenho (Por Tecnologia)')
        _desenhar_mapa(ax['map'], posicoes, links, avg_lat_no, CORES, rede_foco=rede_foco)

        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        nome = f'grafico_trafego_{rede_foco}.png'
        plt.savefig(nome, dpi=300)
        print(f'Salvo: {nome}')
        plt.close(fig)


if __name__ == '__main__':
    gerar_graficos()