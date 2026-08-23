import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import json
import os

# =================================================================
# TIPOS DE REDE — lidos dinamicamente de config.json
# =================================================================
# O scenario.py grava, a cada rodada, quais tipos de enlace (TIPOS_REDE)
# foram realmente usados e em que ordem. É essa MESMA ordem que
# gerar_links_estrela() usa para ciclar os enlaces (agent_p_1 recebe o
# tipo[0], agent_p_2 o tipo[1], ...). Antes esse mapeamento estava
# hardcoded aqui (['5G','4G','Cabeada','IoT']) e SÓ funcionava por
# coincidência com a ordem fixa do antigo star.py — com o menu agora
# permitindo escolher subconjuntos/ordens diferentes de redes, um
# mapeamento fixo rotula os gráficos errado. Por isso lemos o
# config.json gerado na mesma rodada.
NED_PARA_LABEL = {
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
    'Link_Wireless': 'Wireless',
}

def _carregar_tipos_rede():
    caminho = '/omnet-dir/config.json' if os.path.exists('/omnet-dir/config.json') else 'config.json'
    try:
        with open(caminho, 'r') as f:
            config = json.load(f)
        brutos = config.get('tipos_rede', [])
        labels = [NED_PARA_LABEL.get(t, t) for t in brutos]
        # remove duplicatas mantendo a ordem
        vistos = set()
        labels_unicos = [x for x in labels if not (x in vistos or vistos.add(x))]
        if labels_unicos:
            return labels_unicos
    except Exception:
        pass
    # fallback (compatibilidade com execuções sem config.json)
    return ['Cabeada', '5G', '4G', '2G', 'Wireless']

TIPOS_REDE_ATIVOS = _carregar_tipos_rede()

# Paleta fixa por tipo de enlace, com cor extra reservada para o caso de
# o usuário adicionar um tipo de rede novo no futuro.
_PALETA = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#17becf']
CORES_POR_TIPO = {tipo: _PALETA[i % len(_PALETA)] for i, tipo in enumerate(TIPOS_REDE_ATIVOS)}


def extrair_remetente(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == "": return "Rede"
        msg_json = json.loads(msg_str)
        sender = msg_json.get("sender", "")
        return sender.split('@')[0] if sender else "Rede"
    except: return "Rede"

def classificar_rede(agente):
    if 'Central' in agente or 'central' in agente: return 'Central'
    try:
        num = int(agente.split('_')[-1])
        return TIPOS_REDE_ATIVOS[(num - 1) % len(TIPOS_REDE_ATIVOS)]
    except: return 'Desconhecido'

def descobrir_rede_do_link(origem, sender):
    if 'central' in origem.lower(): return classificar_rede(sender)
    else: return classificar_rede(origem)

def gerar_graficos():
    print("Iniciando geração de Painel Executivo Científico...")
    
    try: df = pd.read_csv('results.csv')
    except: 
        print("Arquivo 'results.csv' não encontrado.")
        return

    node_data = df[df['Origem'].str.startswith('OmnetSim-0.agent_')].copy()
    node_data['TipoRedeOrigem'] = node_data['Origem'].apply(classificar_rede)
    
    time_data = node_data.pivot_table(index=['Tempo', 'Origem', 'TipoRedeOrigem'], columns='Atributo', values='Valor', aggfunc='first').reset_index()

    for col in ['packets_sent', 'packets_received', 'packets_dropped']:
        if col not in time_data.columns: time_data[col] = 0.0
        time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

    dados_expandidos = []
    for index, row in time_data.iterrows():
        t, origem = row['Tempo'], row['Origem']
        val_out, sizes_str, lats_str, jits_str = str(row.get('val_out', '')), str(row.get('packet_sizes_out', '')), str(row.get('latencies_out', '')), str(row.get('jitters_out', ''))
        
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
                    'Tempo': t, 'Nó_Físico': origem, 'Sender': sender, 
                    'RedeLink': descobrir_rede_do_link(origem, sender),
                    'IsBroadcast': ('central' in sender.lower()),
                    'Tamanho': size, 'Latencia': lat, 'Jitter': jit
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
    
    lat_media = df_expandido['Latencia'].mean() * 1000 # em ms
    lat_p95 = df_expandido['Latencia'].quantile(0.95) * 1000
    jit_media = df_expandido['Jitter'].mean() * 1000000 # em us

    tabela_resumo = []
    for tipo in TIPOS_REDE_ATIVOS:
        df_tipo = df_expandido[df_expandido['RedeLink'] == tipo]
        if not df_tipo.empty:
            l_mean = df_tipo['Latencia'].mean() * 1000
            j_mean = df_tipo['Jitter'].mean() * 1000000
            enviados_rede = len(df_tipo)
            drops_rede = time_data[time_data['TipoRedeOrigem'] == tipo]['packets_dropped'].max().sum()
            pdr = 100 - ((drops_rede / enviados_rede * 100) if enviados_rede > 0 else 0)
            tabela_resumo.append([tipo, f"{l_mean:.1f} ms", f"{j_mean:.1f} μs", f"{pdr:.1f} %", len(df_tipo)])

    # =================================================================
    # PLOTAGEM DO PAINEL EXECUTIVO
    # =================================================================
    redes_para_plotar = ['Geral'] + TIPOS_REDE_ATIVOS
    cores = CORES_POR_TIPO
    
    for rede_foco in redes_para_plotar:
        fig = plt.figure(figsize=(26, 14))
        titulo = f"Painel Executivo CPS: Visão {rede_foco}" if rede_foco != 'Geral' else "Painel Executivo CPS: Topologia Geral"
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
                
        ax_lat.set_title('1. Latência Temporal (Média e Variação)', fontweight='bold', fontsize=14)
        ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Tempo (s)'); ax_lat.legend(); ax_lat.grid(ls='--', alpha=0.5)

        # --- PAINEL 2: Tamanho do Envelope ---
        if rede_foco == 'Geral':
            broad_mean = df_expandido[df_expandido['IsBroadcast'] == True]['Tamanho'].mean()
            resp_mean = df_expandido[df_expandido['IsBroadcast'] == False]['Tamanho'].mean()
            ax_pay.bar(['Broadcast\n(Central)', 'Respostas\n(Periféricos)'], [broad_mean, resp_mean], color=['#d62728', '#2ca02c'])
            ax_pay.text(0, broad_mean + 10, f"{broad_mean:.0f} B", ha='center', fontweight='bold')
            ax_pay.text(1, resp_mean + 10, f"{resp_mean:.0f} B", ha='center', fontweight='bold')
        else:
            df_sub = df_expandido[df_expandido['RedeLink'] == rede_foco]
            if not df_sub.empty:
                b_mean = df_sub[df_sub['IsBroadcast'] == True]['Tamanho'].mean()
                r_mean = df_sub[df_sub['IsBroadcast'] == False]['Tamanho'].mean()
                b_mean = b_mean if not pd.isna(b_mean) else 0
                r_mean = r_mean if not pd.isna(r_mean) else 0
                ax_pay.bar(['Broadcast', f'Respostas ({rede_foco})'], [b_mean, r_mean], color=[cores[rede_foco], cores[rede_foco]], alpha=0.8)

        ax_pay.set_title('2. Payload Médio (Bytes)', fontweight='bold', fontsize=14)
        ax_pay.set_ylabel('Bytes'); ax_pay.grid(axis='y', ls='--', alpha=0.5)

        # --- PAINEL 3: Jitter ---
        dados_jitter = []
        labels_jitter = []
        for tipo in redes_ativas:
            jits = df_expandido[(df_expandido['RedeLink'] == tipo) & (~df_expandido['IsBroadcast'])]['Jitter'] * 1000000
            if not jits.empty:
                dados_jitter.append(jits)
                labels_jitter.append(tipo)
                
        if dados_jitter:
            # Correção Matplotlib: Removido 'labels' e inserido via set_yticklabels
            ax_jit.boxplot(dados_jitter, orientation='horizontal', patch_artist=True, 
                           boxprops=dict(facecolor='#ffbf0e', color='black'), medianprops=dict(color='red', linewidth=2))
            ax_jit.set_yticks(range(1, len(labels_jitter) + 1))
            ax_jit.set_yticklabels(labels_jitter)
            
        ax_jit.set_title('3. Distribuição de Jitter (Outliers)', fontweight='bold', fontsize=14)
        ax_jit.set_xlabel('Jitter (μs)'); ax_jit.grid(axis='x', ls='--', alpha=0.5)

       # --- PAINEL 4: Integridade (Barra Horizontal Stacked) ---
        if rede_foco == 'Geral':
            # Usa os dados globais da simulação inteira
            entregues_pct = pdr_global
            drops_pct = drop_rate_global
            transito_pct = max(0, 100 - entregues_pct - drops_pct)
            titulo_int = f'4. Taxa de Entrega de Pacotes (PDR Global)'
        else:
            # Filtra os dados apenas para a rede em foco (ex: 5G)
            df_sub_rede = df_expandido[df_expandido['RedeLink'] == rede_foco]
            amostras = len(df_sub_rede)
            drops_locais = time_data[time_data['TipoRedeOrigem'] == rede_foco]['packets_dropped'].max().sum()
            
            total_tentativas = amostras + drops_locais
            entregues_pct = (amostras / total_tentativas * 100) if total_tentativas > 0 else 0
            drops_pct = (drops_locais / total_tentativas * 100) if total_tentativas > 0 else 0
            transito_pct = max(0, 100 - entregues_pct - drops_pct)
            titulo_int = f'4. Taxa de Entrega de Pacotes ({rede_foco})'
        
        ax_int.barh(['Global' if rede_foco == 'Geral' else rede_foco], [entregues_pct], color='#2ca02c', edgecolor='black', label='Entregues')
        ax_int.barh(['Global' if rede_foco == 'Geral' else rede_foco], [drops_pct], left=[entregues_pct], color='#d62728', edgecolor='black', label='Dropados')
        ax_int.barh(['Global' if rede_foco == 'Geral' else rede_foco], [transito_pct], left=[entregues_pct + drops_pct], color='#7f7f7f', edgecolor='black')
        
        ax_int.text(entregues_pct/2, 0, f"{entregues_pct:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=14)
        if drops_pct >= 1.0: 
            ax_int.text(entregues_pct + drops_pct/2, 0, f"{drops_pct:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=12)

        ax_int.set_title(titulo_int, fontweight='bold', fontsize=14)
        ax_int.set_xlim(0, 100); ax_int.set_xticks([0, 25, 50, 75, 100]); ax_int.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_int.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=2)

        # --- PAINEL 5: Tabela ---
        ax_tab.axis('tight'); ax_tab.axis('off')
        if tabela_resumo:
            tabela = ax_tab.table(cellText=tabela_resumo, colLabels=['Rede', 'Latência (Média)', 'Jitter (Média)', 'PDR', 'Amostras'],
                                  cellLoc='center', loc='center', colColours=['#f0f0f0']*5)
            tabela.auto_set_font_size(False); tabela.set_fontsize(12); tabela.scale(1, 1.5)
            ax_tab.set_title('5. Tabela Comparativa de Desempenho', fontweight='bold', fontsize=14)

        # --- PAINEL 6: Mapa Espacial ---
        caminho_posicoes = '/omnet-dir/posicoes.json' if os.path.exists('/omnet-dir/posicoes.json') else 'posicoes.json'
        if os.path.exists(caminho_posicoes):
            with open(caminho_posicoes, 'r') as f: posicoes = json.load(f)
            pos_df = pd.DataFrame(posicoes)

            avg_lats = df_expandido.groupby('Sender')['Latencia'].mean().reset_index()
            avg_lats['id'] = avg_lats['Sender'].apply(lambda x: 'agent_central' if x == 'AgenteCentral' else x.lower())
            pos_df = pos_df.merge(avg_lats, on='id', how='left').fillna(0.0)
            pos_df['TipoRedeOrigem'] = pos_df['id'].apply(classificar_rede)

            central = pos_df[pos_df['tipo'] == 'Central']
            ax_map.scatter(central['x'], central['y'], color='blue', s=800, marker='*', zorder=10, edgecolors='black')

            perif = pos_df[pos_df['tipo'] != 'Central']
            vmin, vmax = perif['Latencia'].min(), perif['Latencia'].max()
            if vmin == vmax: vmax = vmin + 0.0001
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cmap = cm.RdYlGn_r

            for tipo in TIPOS_REDE_ATIVOS:
                subset = perif[perif['TipoRedeOrigem'] == tipo]
                if not subset.empty:
                    if rede_foco == 'Geral' or rede_foco == tipo:
                        ax_map.scatter(subset['x'], subset['y'], c=subset['Latencia'], cmap=cmap, norm=norm, 
                                       s=250, marker='o', edgecolors='black', linewidth=1.5, zorder=5, label=f"{tipo}")
                    else:
                        ax_map.scatter(subset['x'], subset['y'], color='lightgray', s=100, marker='o', alpha=0.3, zorder=2)

            cx, cy = central.iloc[0]['x'], central.iloc[0]['y']
            for _, row in perif.iterrows():
                linha_alpha = 0.5 if (rede_foco == 'Geral' or row['TipoRedeOrigem'] == rede_foco) else 0.1
                lw = 2 if row['TipoRedeOrigem'] == rede_foco else 1
                ax_map.plot([cx, row['x']], [cy, row['y']], color='gray', linestyle='--', alpha=linha_alpha, linewidth=lw, zorder=1)

            sm = cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax_map, fraction=0.046, pad=0.04)
            cbar.set_label('Latência Média (Segundos)', rotation=270, labelpad=20, fontsize=12)

            ax_map.set_title('6. Disposição Geográfica & Heatmap', fontsize=16, fontweight='bold')
            ax_map.set_xlabel('Coordenada X (Metros)'); ax_map.set_ylabel('Coordenada Y (Metros)')
            ax_map.grid(True, linestyle=':', alpha=0.7); ax_map.legend(loc='upper right')

        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        nome_arquivo = f'grafico_trafego_{rede_foco}.png'
        plt.savefig(nome_arquivo, dpi=300)
        print(f"Salvo: {nome_arquivo}")
        plt.close(fig) 

if __name__ == '__main__':
    gerar_graficos()