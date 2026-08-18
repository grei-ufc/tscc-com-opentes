import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import json
import os

def extrair_remetente(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == "": return "Rede"
        msg_json = json.loads(msg_str)
        sender = msg_json.get("sender", "")
        return sender.split('@')[0] if sender else "Rede"
    except: return "Rede"

def gerar_graficos():
    print("📊 Lendo dados de results.csv e montando Dashboard Anel P2P...")
    
    try: df = pd.read_csv('results.csv')
    except: 
        print("❌ Arquivo 'results.csv' não encontrado.")
        return

    # No anel, as origens são os agentes 1 a 4
    node_data = df[df['Origem'].str.startswith('OmnetSim-0.agente_')].copy()
    time_data = node_data.pivot_table(index=['Tempo', 'Origem'], columns='Atributo', values='Valor', aggfunc='first').reset_index()

    for col in ['packets_sent', 'packets_received', 'packets_dropped']:
        if col not in time_data.columns: time_data[col] = 0.0
        time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

    dados_expandidos = []
    for index, row in time_data.iterrows():
        t, origem = row['Tempo'], row['Origem']
        val_out, sizes_str = str(row.get('val_out', '')), str(row.get('packet_sizes_out', ''))
        lats_str, jits_str = str(row.get('latencies_out', '')), str(row.get('jitters_out', ''))
        
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
                
                # Formata o nome para ficar limpo (ex: "agente_1" -> "Agente 1")
                nome_formatado = origem.split('.')[-1].replace('_', ' ').title()
                
                dados_expandidos.append({
                    'Tempo': t, 'Nó_Físico': origem, 'Agente': nome_formatado,
                    'Tamanho': size, 'Latencia': lat, 'Jitter': jit
                })

    df_expandido = pd.DataFrame(dados_expandidos)
    if df_expandido.empty:
        print("⚠️ Nenhuma mensagem encontrada no CSV.")
        return

    # =================================================================
    # CÁLCULO DE MÉTRICAS GLOBAIS
    # =================================================================
    p_enviados = time_data.groupby('Origem')['packets_sent'].max().sum()
    p_recebidos = time_data.groupby('Origem')['packets_received'].max().sum()
    p_descartados = time_data.groupby('Origem')['packets_dropped'].max().sum()
    
    total_tentativas = p_recebidos + p_descartados
    pdr_global = (p_recebidos / total_tentativas * 100) if total_tentativas > 0 else 0.0
    drop_rate_global = (p_descartados / total_tentativas * 100) if total_tentativas > 0 else 0.0
    
    lat_media = df_expandido['Latencia'].mean() * 1000
    lat_p95 = df_expandido['Latencia'].quantile(0.95) * 1000
    jit_media = df_expandido['Jitter'].mean() * 1000000

    tabela_resumo = []
    agentes_list = sorted(df_expandido['Agente'].unique())
    for ag in agentes_list:
        df_ag = df_expandido[df_expandido['Agente'] == ag]
        if not df_ag.empty:
            l_mean = df_ag['Latencia'].mean() * 1000
            j_mean = df_ag['Jitter'].mean() * 1000000
            nome_original = f"OmnetSim-0.{ag.replace(' ', '_').lower()}"
            df_omnet = time_data[time_data['Origem'] == nome_original]
            
            # Cálculo de perdas por nó (Roteador P2P)
            drops_local = df_omnet['packets_dropped'].max().sum() if not df_omnet.empty else 0
            recebidos_local = len(df_ag)
            tentativas_local = recebidos_local + drops_local
            pdr_ag = (recebidos_local / tentativas_local * 100) if tentativas_local > 0 else 100.0
            
            tabela_resumo.append([ag, f"{l_mean:.1f} ms", f"{j_mean:.1f} μs", f"{pdr_ag:.1f} %", recebidos_local])

    # =================================================================
    # PLOTAGEM DO PAINEL EXECUTIVO
    # =================================================================
    cores_agentes = {'Agente 1': '#1f77b4', 'Agente 2': '#ff7f0e', 'Agente 3': '#2ca02c', 'Agente 4': '#d62728'}
    
    fig = plt.figure(figsize=(26, 14))
    fig.suptitle("Painel Executivo CPS: Topologia em Anel (Malha P2P)", fontsize=24, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(4, 3, figure=fig, height_ratios=[0.3, 2, 1.5, 1], width_ratios=[1, 1, 1.5]) 
    
    # --- LINHA 0: KPIs ---
    ax_kpi = fig.add_subplot(gs[0, :]); ax_kpi.axis('off')
    kpi_text = (f"  |  Total Mensagens: {int(p_enviados)}  |  Delivery Ratio (PDR): {pdr_global:.1f}%  |  Drop Rate: {drop_rate_global:.1f}%  |  "
                f"Latência Média: {lat_media:.2f} ms  |  Latência P95: {lat_p95:.2f} ms  |  Jitter Médio: {jit_media:.2f} μs  |")
    ax_kpi.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=16, fontweight='bold', bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', edgecolor='black'))

    # Eixos
    ax_lat = fig.add_subplot(gs[1, 0]); ax_pay = fig.add_subplot(gs[1, 1])
    ax_jit = fig.add_subplot(gs[2, 0]); ax_int = fig.add_subplot(gs[2, 1])
    ax_tab = fig.add_subplot(gs[3, 0:2]); ax_map = fig.add_subplot(gs[1:, 2])

    # --- 1. Latência Temporal ---
    for ag in agentes_list:
        df_sub = df_expandido[df_expandido['Agente'] == ag]
        if not df_sub.empty:
            agg = df_sub.groupby('Tempo')['Latencia'].agg(['mean', 'min', 'max']).reset_index()
            ax_lat.plot(agg['Tempo'], agg['mean'] * 1000, color=cores_agentes.get(ag, 'black'), label=f'{ag} (Média)', linewidth=2)
            ax_lat.fill_between(agg['Tempo'], agg['min'] * 1000, agg['max'] * 1000, color=cores_agentes.get(ag, 'black'), alpha=0.2)
            
    ax_lat.set_title('1. Latência Temporal (Média e Variação)', fontweight='bold', fontsize=14)
    ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Tempo (s)'); ax_lat.legend(); ax_lat.grid(ls='--', alpha=0.5)

    # --- 2. Payload Médio ---
    medias_payload = [df_expandido[df_expandido['Agente'] == ag]['Tamanho'].mean() for ag in agentes_list]
    cores_barras = [cores_agentes.get(ag, 'black') for ag in agentes_list]
    barras = ax_pay.bar(agentes_list, medias_payload, color=cores_barras, alpha=0.8)
    for barra, media in zip(barras, medias_payload):
        if not pd.isna(media): ax_pay.text(barra.get_x() + barra.get_width()/2, media, f"{media:.0f} B", ha='center', va='bottom', fontweight='bold')
    ax_pay.set_title('2. Payload Médio Transmitido (Bytes)', fontweight='bold', fontsize=14)
    ax_pay.set_ylabel('Bytes'); ax_pay.grid(axis='y', ls='--', alpha=0.5)

    # --- 3. Jitter Boxplot ---
    dados_jitter = []
    for ag in agentes_list:
        jits = df_expandido[df_expandido['Agente'] == ag]['Jitter'] * 1000000
        if not jits.empty: dados_jitter.append(jits)
            
    if dados_jitter:
        ax_jit.boxplot(dados_jitter, vert=False, patch_artist=True, 
                       boxprops=dict(facecolor='#ffbf0e', color='black'), medianprops=dict(color='red', linewidth=2))
        ax_jit.set_yticks(range(1, len(agentes_list) + 1))
        ax_jit.set_yticklabels(agentes_list)
    ax_jit.set_title('3. Distribuição de Jitter (Outliers)', fontweight='bold', fontsize=14)
    ax_jit.set_xlabel('Jitter (μs)'); ax_jit.grid(axis='x', ls='--', alpha=0.5)

    # --- 4. Integridade PDR ---
    transito_pct = max(0, 100 - pdr_global - drop_rate_global)
    ax_int.barh(['Global'], [pdr_global], color='#2ca02c', edgecolor='black', label='Entregues')
    ax_int.barh(['Global'], [drop_rate_global], left=[pdr_global], color='#d62728', edgecolor='black', label='Dropados')
    ax_int.barh(['Global'], [transito_pct], left=[pdr_global + drop_rate_global], color='#7f7f7f', edgecolor='black')
    ax_int.text(pdr_global/2, 0, f"{pdr_global:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=14)
    if drop_rate_global > 2: ax_int.text(pdr_global + drop_rate_global/2, 0, f"{drop_rate_global:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=12)
    ax_int.set_title('4. Taxa de Entrega de Pacotes (PDR Global)', fontweight='bold', fontsize=14)
    ax_int.set_xlim(0, 100); ax_int.set_xticks([0, 25, 50, 75, 100]); ax_int.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax_int.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=2)

    # --- 5. Tabela Comparativa ---
    ax_tab.axis('tight'); ax_tab.axis('off')
    if tabela_resumo:
        tabela = ax_tab.table(cellText=tabela_resumo, colLabels=['Agente Roteador', 'Latência (Média)', 'Jitter (Média)', 'PDR', 'Mensagens Recebidas'],
                              cellLoc='center', loc='center', colColours=['#f0f0f0']*5)
        tabela.auto_set_font_size(False); tabela.set_fontsize(12); tabela.scale(1, 1.5)
        ax_tab.set_title('5. Tabela Comparativa de Desempenho (Por Nó)', fontweight='bold', fontsize=14)

    # --- 6. Mapa Espacial (Anel) ---
    caminho_posicoes = '/omnet-dir/posicoes.json' if os.path.exists('/omnet-dir/posicoes.json') else 'posicoes.json'
    if os.path.exists(caminho_posicoes):
        with open(caminho_posicoes, 'r') as f: posicoes = json.load(f)
        pos_df = pd.DataFrame(posicoes)

        avg_lats = df_expandido.groupby('Agente')['Latencia'].mean().reset_index()
        avg_lats['id'] = avg_lats['Agente'].apply(lambda x: x.replace(' ', '_').lower())
        pos_df = pos_df.merge(avg_lats, on='id', how='left').fillna(0.0)

        # Escala de cores do Heatmap
        vmin, vmax = pos_df['Latencia'].min(), pos_df['Latencia'].max()
        if vmin == vmax: vmax = vmin + 0.0001
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = cm.RdYlGn_r

        # Ligações do Anel (Baseado na topologia de mosaik_anel.py)
        linhas_anel = [('agente_1', 'agente_2', 'Cabeada'), ('agente_2', 'agente_3', '4G'), 
                       ('agente_3', 'agente_4', '5G'), ('agente_4', 'agente_1', '2G/GPRS')]
                       
        for p1, p2, label in linhas_anel:
            row1 = pos_df[pos_df['id'] == p1]
            row2 = pos_df[pos_df['id'] == p2]
            if not row1.empty and not row2.empty:
                x_vals = [row1.iloc[0]['x'], row2.iloc[0]['x']]
                y_vals = [row1.iloc[0]['y'], row2.iloc[0]['y']]
                ax_map.plot(x_vals, y_vals, color='black', linestyle='--', linewidth=2, zorder=1)
                mid_x, mid_y = sum(x_vals)/2, sum(y_vals)/2
                ax_map.text(mid_x, mid_y + 15, label, fontsize=12, fontweight='bold', ha='center', va='center', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Desenha os nós
        sc = ax_map.scatter(pos_df['x'], pos_df['y'], c=pos_df['Latencia'], cmap=cmap, norm=norm, 
                            s=800, marker='o', edgecolors='black', linewidth=2, zorder=5)

        for _, row in pos_df.iterrows():
            ax_map.text(row['x'], row['y'] - 40, row['id'].replace('_', ' ').title(), fontsize=12, fontweight='bold', ha='center')

        sm = cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax_map, fraction=0.046, pad=0.04)
        cbar.set_label('Latência Média Operacional (Segundos)', rotation=270, labelpad=20, fontsize=12)

        ax_map.set_title('6. Disposição Geográfica (Anel & Heatmap)', fontsize=16, fontweight='bold')
        ax_map.set_xlabel('Coordenada X (Metros)'); ax_map.set_ylabel('Coordenada Y (Metros)')
        ax_map.grid(True, linestyle=':', alpha=0.7)
        
        # Corrige os limites do mapa para evitar corte dos nós
        ax_map.set_xlim(pos_df['x'].min() - 100, pos_df['x'].max() + 100)
        ax_map.set_ylim(pos_df['y'].min() - 100, pos_df['y'].max() + 100)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    nome_arquivo = 'grafico_trafego_Anel.png'
    plt.savefig(nome_arquivo, dpi=300)
    print(f"✅ Salvo: {nome_arquivo}")
    plt.close(fig) 

if __name__ == '__main__':
    gerar_graficos()