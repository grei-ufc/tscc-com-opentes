import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import json
import os

def gerar_dashboard_ponto_a_ponto():
    print("📊 Iniciando Painel Executivo CPS Ponto-a-Ponto...")
    
    try: df = pd.read_csv('results.csv')
    except: 
        print("❌ Arquivo 'results.csv' não encontrado.")
        return

    node_data = df[df['Origem'].str.startswith('OmnetSim-0.agent_')].copy()
    time_data = node_data.pivot_table(index=['Tempo', 'Origem'], columns='Atributo', values='Valor', aggfunc='first').reset_index()

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
                
                # Classifica quem enviou
                agente_nome = 'Agente 1' if 'agent_1' in origem else 'Agente 2'
                cor = '#1f77b4' if agente_nome == 'Agente 1' else '#ff7f0e'
                
                dados_expandidos.append({
                    'Tempo': t, 'Agente': agente_nome, 'Cor': cor,
                    'Tamanho': size, 'Latencia': lat, 'Jitter': jit
                })

    df_expandido = pd.DataFrame(dados_expandidos)
    if df_expandido.empty:
        print("⚠️ Nenhuma mensagem encontrada no CSV.")
        return

    # Cálculos Globais
    p_enviados = time_data.groupby('Origem')['packets_sent'].max().sum()
    p_recebidos = time_data.groupby('Origem')['packets_received'].max().sum()
    p_descartados = time_data.groupby('Origem')['packets_dropped'].max().sum()
    
    pdr_global = (p_recebidos / p_enviados * 100) if p_enviados > 0 else 0
    drop_rate_global = (p_descartados / p_enviados * 100) if p_enviados > 0 else 0
    lat_media = df_expandido['Latencia'].mean() * 1000
    jit_media = df_expandido['Jitter'].mean() * 1000000 

    # ================= PLOTAGEM =================
    fig = plt.figure(figsize=(22, 12))
    fig.suptitle("Painel Executivo CPS: Enlace Ponto-a-Ponto (Point-to-Point)", fontsize=24, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(3, 3, figure=fig, height_ratios=[0.3, 2, 1.5], width_ratios=[1, 1, 1.5]) 
    
    # --- Header ---
    ax_kpi = fig.add_subplot(gs[0, :]); ax_kpi.axis('off')
    kpi_text = (f"  |  Total Mensagens: {int(p_enviados)}  |  Delivery Ratio: {pdr_global:.1f}%  |  "
                f"Drop Rate: {drop_rate_global:.1f}%  |  Latência Média: {lat_media:.2f} ms  |  Jitter Médio: {jit_media:.2f} μs  |")
    ax_kpi.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=16, fontweight='bold', bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0'))

    ax_lat = fig.add_subplot(gs[1, 0]); ax_pay = fig.add_subplot(gs[1, 1])
    ax_int = fig.add_subplot(gs[2, 0:2]); ax_map = fig.add_subplot(gs[1:, 2])

    # --- 1. Latência ---
    for ag in ['Agente 1', 'Agente 2']:
        df_sub = df_expandido[df_expandido['Agente'] == ag]
        if not df_sub.empty:
            agg = df_sub.groupby('Tempo')['Latencia'].mean().reset_index()
            ax_lat.plot(agg['Tempo'], agg['Latencia'] * 1000, color=df_sub['Cor'].iloc[0], label=f'Tx {ag}', marker='o')
    ax_lat.set_title('1. Latência Temporal do Link', fontweight='bold', fontsize=14)
    ax_lat.set_ylabel('Latência (ms)'); ax_lat.set_xlabel('Tempo (s)'); ax_lat.legend(); ax_lat.grid(ls='--', alpha=0.5)

    # --- 2. Payload ---
    pay_1 = df_expandido[df_expandido['Agente'] == 'Agente 1']['Tamanho'].mean()
    pay_2 = df_expandido[df_expandido['Agente'] == 'Agente 2']['Tamanho'].mean()
    pay_1 = pay_1 if not pd.isna(pay_1) else 0; pay_2 = pay_2 if not pd.isna(pay_2) else 0
    ax_pay.bar(['Agente 1', 'Agente 2'], [pay_1, pay_2], color=['#1f77b4', '#ff7f0e'])
    ax_pay.set_title('2. Payload Médio (Bytes)', fontweight='bold', fontsize=14); ax_pay.grid(axis='y', ls='--', alpha=0.5)

    # --- 3. Integridade ---
    ax_int.barh(['Global'], [pdr_global], color='#2ca02c', edgecolor='black', label='Entregues')
    ax_int.barh(['Global'], [drop_rate_global], left=[pdr_global], color='#d62728', edgecolor='black', label='Dropados')
    ax_int.text(pdr_global/2, 0, f"{pdr_global:.1f}%", va='center', ha='center', color='white', fontweight='bold', fontsize=14)
    if drop_rate_global >= 1.0: ax_int.text(pdr_global + drop_rate_global/2, 0, f"{drop_rate_global:.1f}%", va='center', ha='center', color='white', fontweight='bold')
    ax_int.set_title('3. Taxa de Entrega de Pacotes (PDR)', fontweight='bold', fontsize=14); ax_int.set_xlim(0, 100)

    # --- 4. Mapa Espacial ---
    caminho_posicoes = '/omnet-dir/posicoes.json' if os.path.exists('/omnet-dir/posicoes.json') else 'posicoes.json'
    if os.path.exists(caminho_posicoes):
        with open(caminho_posicoes, 'r') as f: posicoes = json.load(f)
        pos_df = pd.DataFrame(posicoes)
        
        ax_map.scatter(pos_df['x'], pos_df['y'], color=['#1f77b4', '#ff7f0e'], s=800, zorder=10, edgecolors='black')
        ax_map.plot(pos_df['x'], pos_df['y'], color='black', linestyle='--', linewidth=2, zorder=1, label="Link 5G Físico")
        
        for i, row in pos_df.iterrows():
            ax_map.text(row['x'], row['y'] + 30, row['tipo'].replace('_', ' '), fontsize=14, fontweight='bold', ha='center')

        ax_map.set_title('4. Disposição Geográfica (600 Metros)', fontsize=16, fontweight='bold')
        ax_map.set_xlabel('Coordenada X (Metros)'); ax_map.set_ylabel('Coordenada Y (Metros)')
        ax_map.grid(True, linestyle=':', alpha=0.7); ax_map.legend()

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.savefig('grafico_ponto_a_ponto.png', dpi=300)
    print("✅ Salvo: grafico_ponto_a_ponto.png")

if __name__ == '__main__':
    gerar_dashboard_ponto_a_ponto()