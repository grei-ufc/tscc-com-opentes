#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ieee13_plot.py — Painel Executivo Científico dedicado à rede elétrica IEEE 13 Barras
(co-simulation-opentes acoplado ao tscc-com-opentes).

Trata:
  - Coordenadas negativas do alimentador IEEE 13 (X: -244m a +154m, Y: -1526m a 0m)
  - Identificação de 'agent_0' como Concentrador (Central), 'agent_dso' e 'agent_market'
  - Canais LPWA Link_6TiSCH e Link_WiSUN além de Link_Wired, Link_5G, Link_4G, Link_2G, Link_Wireless
  - Deslocamento visual (offset) para nós co-localizados na subestação (0,0) e barras vizinhas (1m)
  - Traçado de fundo da árvore elétrica do alimentador IEEE 13 barras + enlaces de comunicação
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

# =================================================================
# TIPOS DE REDE — lidos dinamicamente de config.json e links.json
# =================================================================
NED_PARA_LABEL = {
    'Link_6TiSCH':   '6TiSCH',
    'Link_WiSUN':    'Wi-SUN',
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
    'Link_Wireless': 'Wireless',
}

# Segmentos físicos da rede elétrica IEEE 13 barras (para desenhar o alimentador no mapa)
IEEE13_FEEDER_LINES = [
    ('agent_650', 'agent_660'),
    ('agent_660', 'agent_632'),
    ('agent_632', 'agent_645'),
    ('agent_645', 'agent_646'),
    ('agent_632', 'agent_633'),
    ('agent_633', 'agent_634'),
    ('agent_632', 'agent_670'),
    ('agent_670', 'agent_671'),
    ('agent_671', 'agent_680'),
    ('agent_671', 'agent_684'),
    ('agent_684', 'agent_611'),
    ('agent_684', 'agent_652'),
    ('agent_671', 'agent_692'),
    ('agent_692', 'agent_675'),
]

# Offsets visuais (dx, dy em metros) APENAS para o plot não sobrepor nós na mesma coordenada
VISUAL_OFFSETS_M = {
    'agent_0':      (  0.0,   0.0),   # Concentrador permanece no centro da subestação (0,0)
    'agent_dso':    (-65.0,  55.0),   # Deslocado para cima-esquerda da subestação
    'agent_market': ( 65.0,  55.0),   # Deslocado para cima-direita da subestação
    'agent_650':    (-40.0, -35.0),   # Separado de (0, -1)
    'agent_660':    ( 40.0, -35.0),   # Separado de (0, -2)
    'agent_634':    ( 35.0, -45.0),   # Separado da barra 633 (distância real é 1m)
    'agent_692':    ( 45.0,  45.0),   # Separado da barra 671 (distância real é 1m)
}


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


def _carregar_config_e_links():
    config = {}
    links = []
    try:
        with open(_path('config.json'), 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception:
        pass
    try:
        with open(_path('links.json'), 'r', encoding='utf-8') as f:
            links = json.load(f)
    except Exception:
        pass
    return config, links


def _carregar_tipos_rede(config=None):
    if config is None:
        config, _ = _carregar_config_e_links()
    brutos = config.get('tipos_rede', [])
    labels = [NED_PARA_LABEL.get(t, t) for t in brutos]
    vistos = set()
    labels_unicos = [x for x in labels if not (x in vistos or vistos.add(x))]
    if labels_unicos:
        return labels_unicos
    return ['6TiSCH', 'Wi-SUN', 'Cabeada', '5G', '4G', '2G', 'Wireless']


def _eh_concentrador(nid):
    n = str(nid).lower()
    return n in ('agent_0', 'agent_central', 'agentecentral')


def _construir_mapa_no_rede(config, links, tipos_ativos):
    """Mapeia cada agente da IEEE 13 (ex: 'agent_634', 'agent_dso') para o label da sua tecnologia."""
    mapa = {'agent_0': 'Central', 'agent_central': 'Central'}
    for lk in links:
        orig = lk.get('origem', '')
        dest = lk.get('destino', '')
        label = NED_PARA_LABEL.get(lk.get('tipo', ''), lk.get('tipo', ''))
        if _eh_concentrador(orig) and dest:
            mapa[dest] = label
        elif _eh_concentrador(dest) and orig:
            mapa[orig] = label

    brutos = [NED_PARA_LABEL.get(t, t) for t in config.get('tipos_rede', [])] or tipos_ativos
    return mapa, brutos


_PALETA = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#17becf', '#e377c2']


def extrair_remetente(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == "":
            return "Rede"
        msg_json = json.loads(msg_str)
        sender = msg_json.get("sender", "")
        return sender.split('@')[0] if sender else "Rede"
    except Exception:
        return "Rede"


def _normalizar_id_agente(agente):
    n = str(agente).split('.')[-1].split('@')[0]
    if n in ('AgenteCentral', 'agent_central'):
        return 'agent_central'
    if n.startswith('AgenteP_'):
        return 'agent_p_' + n[len('AgenteP_'):]
    return n.lower()


def _rotulo_curto_ieee13(agent_id):
    if agent_id == 'agent_0':
        return 'Conc (0)'
    if agent_id == 'agent_dso':
        return 'DSO'
    if agent_id == 'agent_market':
        return 'Market'
    return agent_id.replace('agent_', '')


def gerar_graficos():
    print("Iniciando geração do Painel Executivo IEEE 13 Barras (OpenTES)...")

    try:
        df = pd.read_csv('results.csv')
    except Exception:
        print("Arquivo 'results.csv' não encontrado.")
        return

    config, links = _carregar_config_e_links()
    TIPOS_REDE_ATIVOS = _carregar_tipos_rede(config)
    CORES_POR_TIPO = {tipo: _PALETA[i % len(_PALETA)] for i, tipo in enumerate(TIPOS_REDE_ATIVOS)}
    mapa_no_rede, lista_bruta = _construir_mapa_no_rede(config, links, TIPOS_REDE_ATIVOS)

    def classificar_rede(agente):
        nid = _normalizar_id_agente(agente)
        if _eh_concentrador(nid):
            return 'Central'
        if nid in mapa_no_rede:
            return mapa_no_rede[nid]
        return lista_bruta[0] if lista_bruta else 'Desconhecido'

    def descobrir_rede_do_link(origem, sender):
        nid_origem = _normalizar_id_agente(origem)
        if _eh_concentrador(nid_origem):
            return classificar_rede(sender)
        return classificar_rede(nid_origem)

    node_data = df[df['Origem'].str.startswith('OmnetSim-0.agent_')].copy()
    if node_data.empty:
        print("Nenhum nó 'agent_*' encontrado em results.csv.")
        return
    node_data['TipoRedeOrigem'] = node_data['Origem'].apply(classificar_rede)

    time_data = node_data.pivot_table(
        index=['Tempo', 'Origem', 'TipoRedeOrigem'],
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
        t, origem = row['Tempo'], row['Origem']
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

                dados_expandidos.append({
                    'Tempo': t,
                    'Nó_Físico': origem,
                    'Sender': sender,
                    'RedeLink': descobrir_rede_do_link(origem, sender),
                    'IsBroadcast': _eh_concentrador(sender),
                    'Tamanho': size,
                    'Latencia': lat,
                    'Jitter': jit,
                })

    df_expandido = pd.DataFrame(dados_expandidos)
    if df_expandido.empty:
        print("Nenhuma mensagem encontrada no CSV.")
        return

    # =================================================================
    # CÁLCULO DE MÉTRICAS GLOBAIS E POR REDE (BENCHMARKING)
    # =================================================================
    p_enviados = time_data.groupby('Origem')['packets_sent'].max().sum()
    p_recebidos = time_data.groupby('Origem')['packets_received'].max().sum()
    p_descartados = time_data.groupby('Origem')['packets_dropped'].max().sum()

    pdr_global = (p_recebidos / p_enviados * 100) if p_enviados > 0 else 0
    drop_rate_global = (p_descartados / p_enviados * 100) if p_enviados > 0 else 0

    lat_media = df_expandido['Latencia'].mean() * 1000  # em ms
    lat_p95 = df_expandido['Latencia'].quantile(0.95) * 1000
    jit_media = df_expandido['Jitter'].mean() * 1000000  # em us

    tabela_resumo = []
    for tipo in TIPOS_REDE_ATIVOS:
        df_tipo = df_expandido[df_expandido['RedeLink'] == tipo]
        if not df_tipo.empty:
            l_mean = df_tipo['Latencia'].mean() * 1000
            j_mean = df_tipo['Jitter'].mean() * 1000000
            amostras_rede = len(df_tipo)
            sub_td = time_data[time_data['TipoRedeOrigem'] == tipo]
            drops_rede = sub_td.groupby('Origem')['packets_dropped'].max().sum() if not sub_td.empty else 0.0
            total_tentativas = amostras_rede + drops_rede
            pdr = (amostras_rede / total_tentativas * 100) if total_tentativas > 0 else 100.0
            tabela_resumo.append([tipo, f"{l_mean:.1f} ms", f"{j_mean:.1f} μs", f"{pdr:.1f} %", amostras_rede])

    # =================================================================
    # PLOTAGEM DO PAINEL EXECUTIVO IEEE 13
    # =================================================================
    redes_para_plotar = ['Geral'] + TIPOS_REDE_ATIVOS
    cores = CORES_POR_TIPO

    for rede_foco in redes_para_plotar:
        fig = plt.figure(figsize=(26, 14))
        titulo = (
            f"Painel Executivo IEEE 13 Barras (OpenTES): Visão {rede_foco}"
            if rede_foco != 'Geral'
            else "Painel Executivo IEEE 13 Barras (OpenTES): Mercado Transativo & Rede"
        )
        fig.suptitle(titulo, fontsize=24, fontweight='bold', y=0.98)

        gs = gridspec.GridSpec(4, 3, figure=fig, height_ratios=[0.3, 2, 1.5, 1], width_ratios=[1, 1, 1.5])

        # --- LINHA 0: KPIs (Header) ---
        ax_kpi = fig.add_subplot(gs[0, :])
        ax_kpi.axis('off')
        kpi_text = (
            f"  |  Total Mensagens: {int(p_enviados)}  |  "
            f"Delivery Ratio (PDR): {pdr_global:.1f}%  |  "
            f"Drop Rate: {drop_rate_global:.1f}%  |  "
            f"Latência Média: {lat_media:.2f} ms  |  "
            f"Latência P95: {lat_p95:.2f} ms  |  "
            f"Jitter Médio: {jit_media:.2f} μs  |"
        )
        ax_kpi.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=16, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', edgecolor='black'))

        ax_lat = fig.add_subplot(gs[1, 0])
        ax_pay = fig.add_subplot(gs[1, 1])
        ax_jit = fig.add_subplot(gs[2, 0])
        ax_int = fig.add_subplot(gs[2, 1])
        ax_tab = fig.add_subplot(gs[3, 0:2])
        ax_map = fig.add_subplot(gs[1:, 2])

        redes_ativas = TIPOS_REDE_ATIVOS if rede_foco == 'Geral' else [rede_foco]

        # --- PAINEL 1: Latência ---
        for tipo in redes_ativas:
            df_sub = df_expandido[df_expandido['RedeLink'] == tipo]
            if not df_sub.empty:
                agg = df_sub.groupby('Tempo')['Latencia'].agg(['mean', 'min', 'max']).reset_index()
                ax_lat.plot(agg['Tempo'], agg['mean'] * 1000, color=cores[tipo], label=f'{tipo} (Média)', linewidth=2)
                ax_lat.fill_between(agg['Tempo'], agg['min'] * 1000, agg['max'] * 1000, color=cores[tipo], alpha=0.2)

        ax_lat.set_title('1. Latência por Rodada Dual (Média e Variação)', fontweight='bold', fontsize=14)
        ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Passo Mosaik'); ax_lat.legend(); ax_lat.grid(ls='--', alpha=0.5)

        # --- PAINEL 2: Tamanho do Envelope (CFP Preço Sombra vs PROPOSE Prosumidores) ---
        if rede_foco == 'Geral':
            broad_mean = df_expandido[df_expandido['IsBroadcast'] == True]['Tamanho'].mean()
            resp_mean = df_expandido[df_expandido['IsBroadcast'] == False]['Tamanho'].mean()
            broad_mean = broad_mean if not pd.isna(broad_mean) else 0
            resp_mean = resp_mean if not pd.isna(resp_mean) else 0
            ax_pay.bar(['CFP Preço Sombra\n(Concentrador)', 'PROPOSE / INFORM\n(Barras + DSO/MKT)'],
                       [broad_mean, resp_mean], color=['#d62728', '#2ca02c'])
            ax_pay.text(0, broad_mean + 5, f"{broad_mean:.0f} B", ha='center', fontweight='bold')
            ax_pay.text(1, resp_mean + 5, f"{resp_mean:.0f} B", ha='center', fontweight='bold')
        else:
            df_sub = df_expandido[df_expandido['RedeLink'] == rede_foco]
            if not df_sub.empty:
                b_mean = df_sub[df_sub['IsBroadcast'] == True]['Tamanho'].mean()
                r_mean = df_sub[df_sub['IsBroadcast'] == False]['Tamanho'].mean()
                b_mean = b_mean if not pd.isna(b_mean) else 0
                r_mean = r_mean if not pd.isna(r_mean) else 0
                ax_pay.bar(['CFP Preço', f'Respostas ({rede_foco})'], [b_mean, r_mean],
                           color=[cores[rede_foco], cores[rede_foco]], alpha=0.8)

        ax_pay.set_title('2. Payload Médio FIPA-ACL (Bytes)', fontweight='bold', fontsize=14)
        ax_pay.set_ylabel('Bytes'); ax_pay.grid(axis='y', ls='--', alpha=0.5)

        # --- PAINEL 3: Jitter ---
        dados_jitter = []
        labels_jitter = []
        for tipo in redes_ativas:
            jits = df_expandido[(df_expandido['RedeLink'] == tipo) & (~df_expandido['IsBroadcast'])]['Jitter'] * 1000000
            if jits.empty:
                jits = df_expandido[df_expandido['RedeLink'] == tipo]['Jitter'] * 1000000
            if not jits.empty:
                dados_jitter.append(jits)
                labels_jitter.append(tipo)

        if dados_jitter:
            ax_jit.boxplot(dados_jitter, orientation='horizontal', patch_artist=True,
                           boxprops=dict(facecolor='#ffbf0e', color='black'), medianprops=dict(color='red', linewidth=2))
            ax_jit.set_yticks(range(1, len(labels_jitter) + 1))
            ax_jit.set_yticklabels(labels_jitter)

        ax_jit.set_title('3. Distribuição de Jitter (Outliers)', fontweight='bold', fontsize=14)
        ax_jit.set_xlabel('Jitter (μs)'); ax_jit.grid(axis='x', ls='--', alpha=0.5)

        # --- PAINEL 4: Integridade (Barra Horizontal Stacked) ---
        if rede_foco == 'Geral':
            entregues_pct = pdr_global
            drops_pct = drop_rate_global
            transito_pct = max(0, 100 - entregues_pct - drops_pct)
            titulo_int = '4. Taxa de Entrega de Pacotes (PDR Global)'
        else:
            df_sub_rede = df_expandido[df_expandido['RedeLink'] == rede_foco]
            amostras = len(df_sub_rede)
            sub_td = time_data[time_data['TipoRedeOrigem'] == rede_foco]
            drops_locais = sub_td.groupby('Origem')['packets_dropped'].max().sum() if not sub_td.empty else 0.0

            total_tentativas = amostras + drops_locais
            entregues_pct = (amostras / total_tentativas * 100) if total_tentativas > 0 else 0
            drops_pct = (drops_locais / total_tentativas * 100) if total_tentativas > 0 else 0
            transito_pct = max(0, 100 - entregues_pct - drops_pct)
            titulo_int = f'4. Taxa de Entrega de Pacotes ({rede_foco})'

        ax_int.barh(['Global' if rede_foco == 'Geral' else rede_foco], [entregues_pct], color='#2ca02c', edgecolor='black', label='Entregues')
        ax_int.barh(['Global' if rede_foco == 'Geral' else rede_foco], [drops_pct], left=[entregues_pct], color='#d62728', edgecolor='black', label='Dropados')
        ax_int.barh(['Global' if rede_foco == 'Geral' else rede_foco], [transito_pct], left=[entregues_pct + drops_pct], color='#7f7f7f', edgecolor='black')

        ax_int.text(entregues_pct / 2, 0, f"{entregues_pct:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=14)
        if drops_pct >= 1.0:
            ax_int.text(entregues_pct + drops_pct / 2, 0, f"{drops_pct:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=12)

        ax_int.set_title(titulo_int, fontweight='bold', fontsize=14)
        ax_int.set_xlim(0, 100); ax_int.set_xticks([0, 25, 50, 75, 100]); ax_int.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_int.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=2)

        # --- PAINEL 5: Tabela ---
        ax_tab.axis('tight'); ax_tab.axis('off')
        if tabela_resumo:
            tabela = ax_tab.table(cellText=tabela_resumo, colLabels=['Rede', 'Latência (Média)', 'Jitter (Média)', 'PDR', 'Amostras'],
                                  cellLoc='center', loc='center', colColours=['#f0f0f0'] * 5)
            tabela.auto_set_font_size(False); tabela.set_fontsize(12); tabela.scale(1, 1.5)
            ax_tab.set_title('5. Tabela Comparativa de Desempenho', fontweight='bold', fontsize=14)

        # --- PAINEL 6: Mapa Espacial do Alimentador IEEE 13 Barras ---
        caminho_posicoes = _path('posicoes.json')
        if os.path.exists(caminho_posicoes):
            with open(caminho_posicoes, 'r', encoding='utf-8') as f:
                posicoes = json.load(f)
            pos_df = pd.DataFrame(posicoes)

            # Calcula latência média por agente (tanto como remetente quanto como receptor)
            lats_sender = df_expandido.groupby('Sender')['Latencia'].mean().reset_index()
            lats_sender['id'] = lats_sender['Sender'].apply(_normalizar_id_agente)

            lats_rx = df_expandido.copy()
            lats_rx['id'] = lats_rx['Nó_Físico'].apply(_normalizar_id_agente)
            lats_rx = lats_rx.groupby('id')['Latencia'].mean().reset_index()

            avg_lats = pd.concat([lats_sender[['id', 'Latencia']], lats_rx[['id', 'Latencia']]]).groupby('id')['Latencia'].mean().reset_index()
            pos_df = pos_df.merge(avg_lats, on='id', how='left').fillna(0.0)
            pos_df['TipoRedeOrigem'] = pos_df['id'].apply(classificar_rede)

            # Aplica offset visual para não empilhar nós co-localizados em (0,0) e barras a 1m
            pos_df['x_plot'] = pos_df.apply(lambda r: r['x'] + VISUAL_OFFSETS_M.get(r['id'], (0.0, 0.0))[0], axis=1)
            pos_df['y_plot'] = pos_df.apply(lambda r: r['y'] + VISUAL_OFFSETS_M.get(r['id'], (0.0, 0.0))[1], axis=1)

            coord_map = {r['id']: (r['x_plot'], r['y_plot']) for _, r in pos_df.iterrows()}

            # 1. Desenha as linhas elétricas do alimentador IEEE 13 em azul-claro contínuo ao fundo
            first_feeder = True
            for u, v in IEEE13_FEEDER_LINES:
                if u in coord_map and v in coord_map:
                    x1, y1 = coord_map[u]
                    x2, y2 = coord_map[v]
                    ax_map.plot([x1, x2], [y1, y2], color='#1f77b4', linestyle='-', alpha=0.28,
                                linewidth=3.0, zorder=1, label='Alimentador Elétrico IEEE 13' if first_feeder else None)
                    first_feeder = False

            central = pos_df[pos_df['tipo'] == 'Central']
            if not central.empty:
                ax_map.scatter(central['x_plot'], central['y_plot'], color='blue', s=750, marker='*',
                               zorder=10, edgecolors='black', label='Concentrador (Barra 0)')

            perif = pos_df[pos_df['tipo'] != 'Central']
            vmin = perif['Latencia'].min() if not perif.empty else 0.0
            vmax = perif['Latencia'].max() if not perif.empty else 1.0
            if vmin == vmax:
                vmax = vmin + 0.0001
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cmap = cm.RdYlGn_r

            # 2. Plota nós periféricos (Barras Prosumidoras + DSO + Market)
            for tipo in TIPOS_REDE_ATIVOS:
                subset = perif[perif['TipoRedeOrigem'] == tipo]
                if not subset.empty:
                    if rede_foco == 'Geral' or rede_foco == tipo:
                        ax_map.scatter(subset['x_plot'], subset['y_plot'], c=subset['Latencia'], cmap=cmap, norm=norm,
                                       s=260, marker='o', edgecolors='black', linewidth=1.5, zorder=5, label=f"Rede {tipo}")
                    else:
                        ax_map.scatter(subset['x_plot'], subset['y_plot'], color='lightgray', s=120, marker='o', alpha=0.35, zorder=2)

            # 3. Enlaces de comunicação entre Concentrador (agent_0) e cada agente
            if not central.empty:
                cx, cy = central.iloc[0]['x_plot'], central.iloc[0]['y_plot']
                for _, row in perif.iterrows():
                    ativo = (rede_foco == 'Geral' or row['TipoRedeOrigem'] == rede_foco)
                    linha_alpha = 0.45 if ativo else 0.08
                    lw = 1.6 if row['TipoRedeOrigem'] == rede_foco else 1.0
                    ax_map.plot([cx, row['x_plot']], [cy, row['y_plot']], color='gray',
                                linestyle='--', alpha=linha_alpha, linewidth=lw, zorder=2)

            # 4. Rótulos das barras (634, 671, DSO, Market...) ao lado de cada nó
            for _, row in pos_df.iterrows():
                rotulo = _rotulo_curto_ieee13(row['id'])
                ax_map.annotate(
                    rotulo,
                    (row['x_plot'], row['y_plot']),
                    xytext=(6, 6),
                    textcoords='offset points',
                    fontsize=9,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.18', facecolor='white', edgecolor='none', alpha=0.75),
                    zorder=12
                )

            # Limites explícitos com margem para coordenadas negativas da IEEE 13
            xmin, xmax = pos_df['x_plot'].min(), pos_df['x_plot'].max()
            ymin, ymax = pos_df['y_plot'].min(), pos_df['y_plot'].max()
            ax_map.set_xlim(xmin - 80.0, xmax + 90.0)
            ax_map.set_ylim(ymin - 100.0, ymax + 110.0)

            sm = cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax_map, fraction=0.046, pad=0.04)
            cbar.set_label('Latência Média (Segundos)', rotation=270, labelpad=20, fontsize=12)

            ax_map.set_title('6. Topologia Geográfica IEEE 13 Barras & Heatmap de Latência', fontsize=15, fontweight='bold')
            ax_map.set_xlabel('Coordenada X (Metros)'); ax_map.set_ylabel('Coordenada Y (Metros)')
            ax_map.grid(True, linestyle=':', alpha=0.7)
            ax_map.legend(loc='lower left', fontsize=10, framealpha=0.9)

        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        nome_arquivo = f'grafico_trafego_{rede_foco}.png'
        plt.savefig(nome_arquivo, dpi=300)
        print(f"Salvo: {nome_arquivo}")
        plt.close(fig)


if __name__ == '__main__':
    gerar_graficos()