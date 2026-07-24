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
        if sender: return sender.split('@')[0]
        return "Rede"
    except: return "Rede"

def classificar_rede(agente):
    if 'Central' in agente or 'central' in agente: return 'Central'
    try:
        num = int(agente.split('_')[-1])
        tipos = ['5G', '4G', 'Cabeada', 'IoT']
        return tipos[(num - 1) % 4]
    except:
        return 'Desconhecido'

def descobrir_rede_do_link(origem, sender):
    # Se o log for do Central (Broadcast), a rede depende de quem está respondendo/recebendo
    if 'central' in origem.lower():
        return classificar_rede(sender)
    # Se o log for do Periférico (Resposta), a rede depende dele mesmo
    else:
        return classificar_rede(origem)

def gerar_graficos():
    print("📊 Iniciando geração de Dashboards filtrados...")
    df = pd.read_csv('results.csv')
    
    node_data = df[df['Origem'].str.startswith('OmnetSim-0.agent_')].copy()
    node_data['TipoRedeOrigem'] = node_data['Origem'].apply(classificar_rede)
    
    time_data = node_data.pivot_table(index=['Tempo', 'Origem', 'TipoRedeOrigem'], columns='Atributo', values='Valor', aggfunc='first').reset_index()

    for col in ['packets_sent', 'packets_received', 'packets_dropped']:
        if col not in time_data.columns: time_data[col] = 0.0
        time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

    dados_expandidos = []
    for index, row in time_data.iterrows():
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
                rede_do_link = descobrir_rede_do_link(origem, sender)
                
                # Para saber se é Broadcast ou Resposta
                is_broadcast = ('central' in sender.lower())
                
                dados_expandidos.append({
                    'Tempo': t, 'Nó_Físico': origem, 'Sender': sender, 'RedeLink': rede_do_link,
                    'IsBroadcast': is_broadcast,
                    'last_packet_size': size, 'last_latency': lat, 'current_jitter': jit
                })

    df_expandido = pd.DataFrame(dados_expandidos)
    if df_expandido.empty:
        print("⚠️ Nenhuma mensagem encontrada no CSV.")
        return

    np.random.seed(42)
    df_expandido['Tempo_Visual'] = df_expandido['Tempo'] + np.random.uniform(-0.25, 0.25, size=len(df_expandido))

    estilos = {
        'Cabeada': {'cor': '#1f77b4', 'marker': 'o', 's': 70,  'label': 'Rede Cabeada'},
        '5G':      {'cor': '#2ca02c', 'marker': 's', 's': 60,  'label': 'Rede 5G'},
        '4G':      {'cor': '#ff7f0e', 'marker': '^', 's': 80,  'label': 'Rede 4G'},
        'IoT':     {'cor': '#9467bd', 'marker': 'D', 's': 60,  'label': 'Rede IoT'}
    }

    p_enviados = time_data.groupby('Origem')['packets_sent'].max().sum()
    p_recebidos = time_data.groupby('Origem')['packets_received'].max().sum()
    p_descartados = time_data.groupby('Origem')['packets_dropped'].max().sum()
    
    # Resolve o mistério da caixa branca!
    drops_central = time_data[time_data['TipoRedeOrigem'] == 'Central']['packets_dropped'].max()
    if pd.isna(drops_central): drops_central = 0
    drops_perif = p_descartados - drops_central
    
    texto_drops = f"Contabilidade de Drops:\n• Antena Central: {int(drops_central)} perdidos\n• Antenas Periféricas: {int(drops_perif)} perdidos"

    # =================================================================
    # LOOP MÁGICO: Gera os 5 gráficos separados!
    # =================================================================
    redes_para_plotar = ['Geral', 'Cabeada', '5G', '4G', 'IoT']
    
    for rede_foco in redes_para_plotar:
        fig = plt.figure(figsize=(24, 12))
        
        titulo = f"Dashboard Cyber-Físico: Visão {rede_foco}" if rede_foco != 'Geral' else "Dashboard Cyber-Físico: Topologia Geral"
        fig.suptitle(titulo, fontsize=20, fontweight='bold')
        gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1, 1, 1.2]) 
        
        ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
        ax3, ax4 = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])
        ax_map = fig.add_subplot(gs[:, 2])

        redes_ativas = ['Cabeada', '5G', '4G', 'IoT'] if rede_foco == 'Geral' else [rede_foco]

        for tipo in redes_ativas:
            st = estilos[tipo]
            
            # Filtra Broadcasts (Estrelas Vermelhas, ligadas APENAS à rede que estamos analisando)
            df_broad = df_expandido[(df_expandido['RedeLink'] == tipo) & (df_expandido['IsBroadcast'] == True)]
            if not df_broad.empty:
                ax1.scatter(df_broad['Tempo_Visual'], df_broad['last_latency'], color='#d62728', marker='*', s=200, alpha=0.7, edgecolors='black', linewidth=0.5, label='Broadcast Central' if tipo == redes_ativas[0] else "")
                ax3.scatter(df_broad['Tempo_Visual'], df_broad['last_packet_size'], color='#d62728', marker='*', s=150, alpha=0.7, edgecolors='black', linewidth=0.5, label='Tx Central' if tipo == redes_ativas[0] else "")
            
            # Filtra Respostas dos Periféricos
            df_resp = df_expandido[(df_expandido['RedeLink'] == tipo) & (df_expandido['IsBroadcast'] == False)]
            if not df_resp.empty:
                ax1.scatter(df_resp['Tempo_Visual'], df_resp['last_latency'], color=st['cor'], marker=st['marker'], s=st['s'], alpha=0.7, edgecolors='black', linewidth=0.5, label=f"Resposta {tipo}")
                ax2.scatter(df_resp['Tempo_Visual'], df_resp['current_jitter'], color=st['cor'], marker=st['marker'], s=st['s'], alpha=0.7, edgecolors='black', linewidth=0.5, label=tipo)
                ax3.scatter(df_resp['Tempo_Visual'], df_resp['last_packet_size'], color=st['cor'], marker=st['marker'], s=st['s'], alpha=0.7, edgecolors='black', linewidth=0.5, label=f"Tx {tipo}")

        ax1.set_title('1. Latência Temporal (Swarm Plot)', fontweight='bold'); ax1.set_ylabel('Segundos'); ax1.legend(); ax1.grid(ls=':', alpha=0.5)
        ax2.set_title('2. Jitter Distribuído', fontweight='bold'); ax2.set_ylabel('Segundos Extra'); ax2.legend(loc='upper right'); ax2.grid(ls=':', alpha=0.5)
        ax3.set_title('3. Tamanho do Envelope na Nuvem', fontweight='bold'); ax3.set_xlabel('Tempo (Passos)'); ax3.set_ylabel('Bytes'); ax3.legend(); ax3.grid(ls=':', alpha=0.5)

        # 4. Integridade (Pizza)
        labels_f = ['Entregues', 'Dropados', 'Em Trânsito']
        tamanhos_f = [p_recebidos, p_descartados, max(0, p_enviados - p_recebidos - p_descartados)]
        if sum(tamanhos_f) > 0: ax4.pie(tamanhos_f, labels=labels_f, colors=['#2ca02c', '#d62728', '#7f7f7f'], autopct='%1.1f%%', wedgeprops={'ec': 'black'})
        ax4.set_title(f'4. Integridade Total ({int(p_enviados)} msgs)', fontweight='bold')
        ax4.text(1.2, 0.5, texto_drops, transform=ax4.transAxes, fontsize=12, fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # 5. Mapa Espacial
        caminho_posicoes = '/omnet-dir/posicoes.json' if os.path.exists('/omnet-dir/posicoes.json') else 'posicoes.json'
        if os.path.exists(caminho_posicoes):
            with open(caminho_posicoes, 'r') as f: posicoes = json.load(f)
            pos_df = pd.DataFrame(posicoes)

            avg_lats = df_expandido.groupby('Sender')['last_latency'].mean().reset_index()
            avg_lats['id'] = avg_lats['Sender'].apply(lambda x: 'agent_central' if x == 'AgenteCentral' else x.lower())
            pos_df = pos_df.merge(avg_lats, on='id', how='left').fillna(0.0)
            pos_df['TipoRedeOrigem'] = pos_df['id'].apply(classificar_rede)

            central = pos_df[pos_df['tipo'] == 'Central']
            ax_map.scatter(central['x'], central['y'], color='blue', s=800, marker='*', zorder=10, edgecolors='black', label='Antena Central')

            perif = pos_df[pos_df['tipo'] != 'Central']
            vmin, vmax = perif['last_latency'].min(), perif['last_latency'].max()
            if vmin == vmax: vmax = vmin + 0.0001
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cmap = cm.RdYlGn_r

            for tipo in ['Cabeada', '5G', '4G', 'IoT']:
                subset = perif[perif['TipoRedeOrigem'] == tipo]
                if not subset.empty:
                    st = estilos[tipo]
                    # Logica de transparência: apaga do mapa as redes que não são o foco
                    if rede_foco == 'Geral' or rede_foco == tipo:
                        ax_map.scatter(subset['x'], subset['y'], c=subset['last_latency'], cmap=cmap, norm=norm, 
                                       s=250, marker=st['marker'], edgecolors='black', linewidth=1.5, zorder=5, label=f"Nó {tipo}")
                    else:
                        ax_map.scatter(subset['x'], subset['y'], color='lightgray', s=100, marker=st['marker'], alpha=0.3, zorder=2)

            cx, cy = central.iloc[0]['x'], central.iloc[0]['y']
            for _, row in perif.iterrows():
                linha_alpha = 0.4 if (rede_foco == 'Geral' or row['TipoRedeOrigem'] == rede_foco) else 0.1
                ax_map.plot([cx, row['x']], [cy, row['y']], color='gray', linestyle='--', alpha=linha_alpha, zorder=1)

            sm = cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax_map, fraction=0.046, pad=0.04)
            cbar.set_label('Latência Média Observada (Segundos)', rotation=270, labelpad=20, fontsize=12)

            ax_map.set_title('5. Disposição Geográfica & Heatmap', fontsize=15, fontweight='bold')
            ax_map.set_xlabel('Coordenada X (Metros)'); ax_map.set_ylabel('Coordenada Y (Metros)')
            ax_map.grid(True, linestyle=':', alpha=0.7); ax_map.legend(loc='upper right')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        nome_arquivo = f'grafico_trafego_{rede_foco}.png'
        plt.savefig(nome_arquivo, dpi=300)
        print(f"✅ Salvo: {nome_arquivo}")
        plt.close(fig) # Fecha a figura da memória

if __name__ == '__main__':
    gerar_graficos()