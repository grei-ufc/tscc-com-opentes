#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_malha.py — Dashboard estilo star para topologia Malha Completa.

Gera os mesmos arquivos que plot_results_star.py:
  grafico_trafego_Geral.png  + grafico_trafego_{Tecnologia}.png

Diferenças em relação ao star:
  - Classificação de tecnologia: usa links.json (mapeamento par→tech real)
    em vez de classificar pelo número do agente; fallback reconstrói a
    malha completa se links.json estiver ausente.
  - Mapa espacial: desenha TODOS os enlaces da malha; os da tecnologia em
    foco ficam coloridos e os demais ficam em cinza transparente.
  - Sem distinção Broadcast/Respostas: todos os agentes são peers na malha.
    O Painel 2 exibe o payload médio por tecnologia.
"""

import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import pandas as pd

# ── Mapeamento NED → label legível ────────────────────────────
NED_PARA_LABEL = {
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_Wireless': 'Wireless',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
}
_PALETA = ['#1f77b4', '#2ca02c', '#17becf', '#ff7f0e', '#9467bd', '#8c564b']


# ══════════════════════════════════════════════════════════════
# CARREGAMENTO
# ══════════════════════════════════════════════════════════════

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


def _carregar_tipos_rede():
    try:
        with open(_path('config.json'), encoding='utf-8') as f:
            config = json.load(f)
        brutos = config.get('tipos_rede', [])
        labels = [NED_PARA_LABEL.get(t, t) for t in brutos]
        vistos = set()
        return [x for x in labels if not (x in vistos or vistos.add(x))]
    except Exception:
        return list(NED_PARA_LABEL.values())


def _reconstruir_links(posicoes, config):
    ids   = [ag['id'] for ag in posicoes]
    tipos = config.get('tipos_rede', ['Link_Wired'])
    links = []; c = 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            links.append({'origem': ids[i], 'destino': ids[j],
                          'tipo': tipos[c % len(tipos)]})
            c += 1
    return links


def carregar():
    if not os.path.exists('results.csv'):
        raise FileNotFoundError("results.csv não encontrado.")
    df = pd.read_csv('results.csv')
    with open(_path('posicoes.json'), encoding='utf-8') as f: posicoes = json.load(f)
    with open(_path('config.json'), encoding='utf-8')  as f: config   = json.load(f)
    p = _path('links.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f: links = json.load(f)
        print(f"links.json carregado ({len(links)} enlaces).")
    else:
        print("links.json ausente — reconstruindo malha completa.")
        links = _reconstruir_links(posicoes, config)
    return df, posicoes, config, links


# ══════════════════════════════════════════════════════════════
# CLASSIFICAÇÃO DE TECNOLOGIA POR ENLACE
# ══════════════════════════════════════════════════════════════

def _build_link_map(links):
    """Mapa bidirecional (nó_a, nó_b) → label de tecnologia."""
    lmap = {}
    for lk in links:
        o = lk['origem']; d = lk['destino']
        label = NED_PARA_LABEL.get(lk.get('tipo', 'Link_Wired'), lk.get('tipo', ''))
        lmap[(o, d)] = label
        lmap[(d, o)] = label
    return lmap


def _pade_para_omnet(pade_name):
    """Converte nome PADE → nome OMNeT++ (suporta nomenclatura antiga e nova)."""
    n = pade_name.split('@')[0]
    if n == 'AgenteCentral':       return 'agent_central'
    if n.startswith('AgenteP_'):   return 'agent_p_' + n[len('AgenteP_'):]
    return n.lower()               # agente_1, agente_2 → ficam iguais


def _tech_da_mensagem(omnet_node, sender_str, link_map):
    """Determina a tecnologia que transportou esta mensagem, via link_map."""
    sender_omnet = _pade_para_omnet(sender_str)
    tech = (link_map.get((omnet_node, sender_omnet)) or
            link_map.get((sender_omnet, omnet_node)))
    return tech or 'Desconhecido'


def _extrair_sender(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == '': return ''
        return json.loads(msg_str).get('sender', '')
    except Exception: return ''


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DOS GRÁFICOS
# ══════════════════════════════════════════════════════════════

def gerar_graficos():
    print("Iniciando geração de Painel Executivo Científico (Malha)...")

    try:
        df, posicoes, config, links = carregar()
    except Exception as e:
        print(f"x {e}"); return

    TIPOS_REDE_ATIVOS = _carregar_tipos_rede()
    CORES             = {t: _PALETA[i % len(_PALETA)] for i, t in enumerate(TIPOS_REDE_ATIVOS)}
    link_map          = _build_link_map(links)
    pos_dict          = {ag['id']: (ag['x'], ag['y']) for ag in posicoes}
    ids_nos           = [ag['id'] for ag in posicoes]

    # ── Processa CSV ──────────────────────────────────────────
    nd = df[df['Origem'].str.startswith('OmnetSim-0.')].copy()
    nd['NodeId'] = nd['Origem'].str.replace('OmnetSim-0.', '', regex=False)

    td = nd.pivot_table(index=['Tempo', 'NodeId'], columns='Atributo',
                        values='Valor', aggfunc='first').reset_index()
    for col in ['packets_sent', 'packets_received', 'packets_dropped']:
        if col not in td.columns: td[col] = 0.0
        td[col] = pd.to_numeric(td[col], errors='coerce').fillna(0)

    # ── Expande mensagens individuais ─────────────────────────
    rows = []
    for _, row in td.iterrows():
        t       = row['Tempo']
        node_id = row['NodeId']
        val_out   = str(row.get('val_out',          ''))
        sizes_str = str(row.get('packet_sizes_out', ''))
        lats_str  = str(row.get('latencies_out',    ''))
        jits_str  = str(row.get('jitters_out',      ''))

        if not val_out or val_out == 'nan': continue
        msgs  = val_out.split('|||')
        sizes = sizes_str.split('|||') if sizes_str and sizes_str != 'nan' else []
        lats  = lats_str.split('|||')  if lats_str  and lats_str  != 'nan' else []
        jits  = jits_str.split('|||')  if jits_str  and jits_str  != 'nan' else []

        for i, msg in enumerate(msgs):
            sender = _extrair_sender(msg)
            if not sender: continue
            tech = _tech_da_mensagem(node_id, sender, link_map)
            rows.append({
                'Tempo':    t,
                'NodeId':   node_id,
                'Sender':   sender,
                'RedeLink': tech,
                'Tamanho':  float(sizes[i]) if i < len(sizes) and sizes[i] else 0.0,
                'Latencia': float(lats[i])  if i < len(lats)  and lats[i]  else 0.0,
                'Jitter':   float(jits[i])  if i < len(jits)  and jits[i]  else 0.0,
            })

    df_exp = pd.DataFrame(rows)
    if df_exp.empty:
        print("Nenhuma mensagem encontrada no CSV."); return

    # ── Métricas globais ──────────────────────────────────────
    p_env  = td.groupby('NodeId')['packets_sent'].max().sum()
    p_rec  = td.groupby('NodeId')['packets_received'].max().sum()
    p_drop = td.groupby('NodeId')['packets_dropped'].max().sum()
    pdr_g  = (p_rec  / p_env * 100) if p_env > 0 else 0
    drp_g  = (p_drop / p_env * 100) if p_env > 0 else 0
    lat_m  = df_exp['Latencia'].mean() * 1000
    lat_p95= df_exp['Latencia'].quantile(0.95) * 1000
    jit_m  = df_exp['Jitter'].mean() * 1e6

    # Latência média por nó (para heatmap do mapa)
    avg_lat_no = df_exp.groupby('NodeId')['Latencia'].mean().to_dict()

    # ── Tabela resumo por tecnologia ──────────────────────────
    tabela_resumo = []
    for tipo in TIPOS_REDE_ATIVOS:
        df_t = df_exp[df_exp['RedeLink'] == tipo]
        if not df_t.empty:
            l_m = df_t['Latencia'].mean() * 1000
            j_m = df_t['Jitter'].mean() * 1e6
            n   = len(df_t)
            nids_t = {nid for (a, b), tech in link_map.items()
                      if tech == tipo for nid in [a, b]}
            sub_td = td[td['NodeId'].isin(nids_t)]
            d_t = sub_td.groupby('NodeId')['packets_dropped'].max().sum() if not sub_td.empty else 0.0
            tot = n + d_t
            pdr_t = 100 - ((d_t / tot * 100) if tot > 0 else 0)
            tabela_resumo.append([tipo, f'{l_m:.1f} ms', f'{j_m:.1f} μs',
                                   f'{pdr_t:.1f}%', n])

    # ══════════════════════════════════════════════════════════
    # LOOP DE PLOTAGEM — idêntico em estrutura ao plot_results_star.py
    # ══════════════════════════════════════════════════════════
    redes_para_plotar = ['Geral'] + TIPOS_REDE_ATIVOS

    for rede_foco in redes_para_plotar:
        fig = plt.figure(figsize=(26, 14))
        titulo = (f"Painel Executivo CPS — Malha: Visão {rede_foco}"
                  if rede_foco != 'Geral' else
                  "Painel Executivo CPS — Topologia Malha Completa: Visão Geral")
        fig.suptitle(titulo, fontsize=22, fontweight='bold', y=0.98)

        gs = gridspec.GridSpec(4, 3, figure=fig,
                               height_ratios=[0.3, 2, 1.5, 1],
                               width_ratios=[1, 1, 1.5])

        ax_lat = fig.add_subplot(gs[1, 0])
        ax_pay = fig.add_subplot(gs[1, 1])
        ax_jit = fig.add_subplot(gs[2, 0])
        ax_int = fig.add_subplot(gs[2, 1])
        ax_tab = fig.add_subplot(gs[3, 0:2])
        ax_map = fig.add_subplot(gs[1:,  2])

        redes_ativas = TIPOS_REDE_ATIVOS if rede_foco == 'Geral' else [rede_foco]

        # ── 0. KPI Header ─────────────────────────────────────
        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis('off')
        kpi = (f"  |  Total Pacotes: {int(p_env)}  |  "
               f"PDR: {pdr_g:.1f}%  |  "
               f"Drop Rate: {drp_g:.1f}%  |  "
               f"Latência Média: {lat_m:.2f} ms  |  "
               f"Latência P95: {lat_p95:.2f} ms  |  "
               f"Jitter Médio: {jit_m:.2f} μs  |")
        ax_kpi.text(0.5, 0.5, kpi, ha='center', va='center', fontsize=14,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5',
                              facecolor='#f0f0f0', edgecolor='black'))

        # ── 1. Latência Temporal ──────────────────────────────
        for tipo in redes_ativas:
            df_sub = df_exp[df_exp['RedeLink'] == tipo]
            if df_sub.empty: continue
            agg = df_sub.groupby('Tempo')['Latencia'].agg(['mean','min','max']).reset_index()
            cor = CORES.get(tipo, '#888')
            ax_lat.plot(agg['Tempo'], agg['mean']*1000, color=cor,
                        label=tipo, linewidth=2)
            ax_lat.fill_between(agg['Tempo'], agg['min']*1000, agg['max']*1000,
                                color=cor, alpha=0.15)
        ax_lat.set_title('1. Latência Temporal (Média e Variação)',
                         fontweight='bold', fontsize=13)
        ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Tempo (s)')
        ax_lat.legend(fontsize=9); ax_lat.grid(ls='--', alpha=0.5)

        # ── 2. Payload Médio por Tecnologia ──────────────────
        tipos_c = [t for t in redes_ativas
                   if not df_exp[df_exp['RedeLink']==t].empty]
        pay_vals  = [df_exp[df_exp['RedeLink']==t]['Tamanho'].mean() for t in tipos_c]
        pay_cores = [CORES.get(t, '#888') for t in tipos_c]
        if tipos_c:
            bars = ax_pay.bar(tipos_c, pay_vals, color=pay_cores,
                              edgecolor='black', alpha=0.85)
            for bar, val in zip(bars, pay_vals):
                ax_pay.text(bar.get_x() + bar.get_width()/2, val + 5,
                            f'{val:.0f} B', ha='center', fontsize=9,
                            fontweight='bold')
        ax_pay.set_title('2. Payload Médio por Tecnologia (Bytes)',
                         fontweight='bold', fontsize=13)
        ax_pay.set_ylabel('Bytes'); ax_pay.grid(axis='y', ls='--', alpha=0.5)
        ax_pay.tick_params(axis='x', rotation=15)

        # ── 3. Jitter Boxplot ─────────────────────────────────
        dados_j, labels_j = [], []
        for tipo in redes_ativas:
            jits = df_exp[df_exp['RedeLink']==tipo]['Jitter'] * 1e6
            if not jits.empty:
                dados_j.append(jits); labels_j.append(tipo)
        if dados_j:
            ax_jit.boxplot(dados_j, orientation='horizontal', patch_artist=True,
                           boxprops=dict(facecolor='#ffbf0e', color='black'),
                           medianprops=dict(color='red', linewidth=2))
            ax_jit.set_yticks(range(1, len(labels_j)+1))
            ax_jit.set_yticklabels(labels_j, fontsize=9)
        ax_jit.set_title('3. Distribuição de Jitter (Boxplot)',
                         fontweight='bold', fontsize=13)
        ax_jit.set_xlabel('Jitter (μs)'); ax_jit.grid(axis='x', ls='--', alpha=0.5)

        # ── 4. PDR / Integridade ──────────────────────────────
        if rede_foco == 'Geral':
            ent_pct = pdr_g; drp_pct = drp_g
            label_b = 'Global'; titulo_i = '4. Taxa de Entrega Global (PDR)'
        else:
            df_sub = df_exp[df_exp['RedeLink'] == rede_foco]
            n_am   = len(df_sub)
            nids_f = {nid for (a,b), tech in link_map.items()
                      if tech == rede_foco for nid in [a,b]}
            sub_td = td[td['NodeId'].isin(nids_f)]
            d_f    = sub_td.groupby('NodeId')['packets_dropped'].max().sum() if not sub_td.empty else 0.0
            tot    = n_am + d_f
            ent_pct = (n_am / tot * 100) if tot > 0 else 0
            drp_pct = (d_f  / tot * 100) if tot > 0 else 0
            label_b = rede_foco; titulo_i = f'4. Taxa de Entrega — {rede_foco}'

        rem_pct = max(0, 100 - ent_pct - drp_pct)
        ax_int.barh([label_b], [ent_pct], color='#2ca02c',
                    edgecolor='black', label='Entregues')
        ax_int.barh([label_b], [drp_pct], left=[ent_pct],
                    color='#d62728', edgecolor='black', label='Dropados')
        ax_int.barh([label_b], [rem_pct], left=[ent_pct+drp_pct],
                    color='#7f7f7f', edgecolor='black')
        ax_int.text(ent_pct/2, 0, f'{ent_pct:.1f}%',
                    va='center', ha='center', color='white',
                    fontweight='bold', fontsize=13)
        if drp_pct >= 1.0:
            ax_int.text(ent_pct+drp_pct/2, 0, f'{drp_pct:.1f}%',
                        va='center', ha='center', color='white',
                        fontweight='bold', fontsize=11)
        ax_int.set_title(titulo_i, fontweight='bold', fontsize=13)
        ax_int.set_xlim(0, 100)
        ax_int.set_xticks([0,25,50,75,100])
        ax_int.set_xticklabels(['0%','25%','50%','75%','100%'])
        ax_int.legend(loc='lower center', bbox_to_anchor=(0.5,-0.4), ncol=2)

        # ── 5. Tabela Comparativa ─────────────────────────────
        ax_tab.axis('tight'); ax_tab.axis('off')
        if tabela_resumo:
            tab = ax_tab.table(
                cellText=tabela_resumo,
                colLabels=['Rede','Latência Média','Jitter Médio','PDR','Amostras'],
                cellLoc='center', loc='center', colColours=['#f0f0f0']*5)
            tab.auto_set_font_size(False); tab.set_fontsize(11); tab.scale(1, 1.5)
        ax_tab.set_title('5. Tabela Comparativa de Desempenho',
                         fontweight='bold', fontsize=13)

        # ── 6. Mapa Espacial da Malha ──────────────────────────
        for lk in links:
            o = lk['origem']; d = lk['destino']
            if o not in pos_dict or d not in pos_dict: continue
            tech_lbl = NED_PARA_LABEL.get(lk.get('tipo',''), '')
            x0,y0 = pos_dict[o]; x1,y1 = pos_dict[d]
            eh_foco = (rede_foco == 'Geral' or tech_lbl == rede_foco)
            ax_map.plot([x0,x1],[y0,y1],
                        color=CORES.get(tech_lbl,'#888') if eh_foco else '#cccccc',
                        alpha=0.70 if eh_foco else 0.12,
                        linewidth=1.8 if eh_foco else 0.7, zorder=1)

        for tipo in (TIPOS_REDE_ATIVOS if rede_foco == 'Geral' else [rede_foco]):
            ax_map.plot([], [], color=CORES.get(tipo,'#888'),
                        linewidth=2.5, label=tipo)

        lat_nos = [avg_lat_no.get(nid, 0) for nid in ids_nos if nid in pos_dict]
        xs_nos  = [pos_dict[nid][0] for nid in ids_nos if nid in pos_dict]
        ys_nos  = [pos_dict[nid][1] for nid in ids_nos if nid in pos_dict]
        nids_v  = [nid for nid in ids_nos if nid in pos_dict]

        vmin = min(lat_nos) if lat_nos else 0
        vmax = max(lat_nos) if lat_nos else 1
        if vmin == vmax: vmax = vmin + 0.0001
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = cm.RdYlGn_r

        sc = ax_map.scatter(xs_nos, ys_nos, c=lat_nos, cmap=cmap, norm=norm,
                            s=260, edgecolors='black', linewidth=1.5, zorder=5)
        for nid in nids_v:
            x, y = pos_dict[nid]
            lbl = (nid.replace('agent_central','C')
                      .replace('agent_p_','P')
                      .replace('agente_','A'))
            ax_map.text(x, y+22, lbl, ha='center', fontsize=7, color='#1a3a2a')

        cbar = plt.colorbar(sc, ax=ax_map, fraction=0.046, pad=0.04)
        cbar.set_label('Latência Média (s)', rotation=270, labelpad=20, fontsize=11)
        ax_map.set_title('6. Mapa Espacial — Full Mesh', fontsize=14, fontweight='bold')
        ax_map.set_xlabel('Coordenada X (metros)')
        ax_map.set_ylabel('Coordenada Y (metros)')
        ax_map.grid(True, ls=':', alpha=0.6)
        ax_map.legend(loc='upper right', fontsize=9, title='Tecnologia')

        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        nome = f'grafico_trafego_{rede_foco}.png'
        plt.savefig(nome, dpi=300)
        print(f"✅ Salvo: {nome}")
        plt.close(fig)


if __name__ == '__main__':
    gerar_graficos()
