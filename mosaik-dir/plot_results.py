import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json

def extrair_remetente(msg_str):
    """Lê a string JSON desempacotada para extrair quem enviou a mensagem."""
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == "":
            return "Rede"
        msg_json = json.loads(msg_str)
        sender = msg_json.get("sender", "")
        if sender: 
            return sender.split('@')[0] # Extrai "AgenteA" ou "AgenteB"
        return "Rede"
    except: 
        return "Rede"

def gerar_grafico():
    try:
        print("📊 Desempacotando dados multiplexados e montando Dashboard (Ponto-a-Ponto)...")
        df = pd.read_csv('results.csv')
        
        # 1. FILTRAR O NÓ OMNeT++
        node_data = df[df['Origem'] == 'OmnetSim-0.node_0'].copy()

        # 2. PIVOTAR OS DADOS
        time_data = node_data.pivot_table(index='Tempo', columns='Atributo', values='Valor', aggfunc='first').reset_index()

        # Garantir colunas globais de pacotes
        for col in ['packets_sent', 'packets_received', 'packets_dropped']:
            if col not in time_data.columns: time_data[col] = 0.0
            time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

        # =================================================================
        # 3. DESEMPACOTAMENTO CIRÚRGICO DA TELEMETRIA
        # =================================================================
        dados_expandidos = []
        
        for index, row in time_data.iterrows():
            t = row['Tempo']
            
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
                    msg = msgs[i]
                    size = float(sizes[i]) if i < len(sizes) and sizes[i] else 0.0
                    lat = float(lats[i]) if i < len(lats) and lats[i] else 0.0
                    jit = float(jits[i]) if i < len(jits) and jits[i] else 0.0
                    
                    agente = extrair_remetente(msg)
                    
                    dados_expandidos.append({
                        'Tempo': t,
                        'Agente': agente,
                        'last_packet_size': size,
                        'last_latency': lat,
                        'current_jitter': jit
                    })

        df_expandido = pd.DataFrame(dados_expandidos)

        if df_expandido.empty:
            print("⚠️ Nenhuma mensagem FIPA registada no CSV. O gráfico estará vazio.")
            return

        # Sub-tabelas para colorir os pontos (Cenário de 2 Agentes)
        df_a = df_expandido[df_expandido['Agente'] == 'AgenteA']
        df_b = df_expandido[df_expandido['Agente'] == 'AgenteB']

        # ==========================================
        # 4. PREPARAR A FIGURA (Dashboard 2x2)
        # ==========================================
        fig = plt.figure(figsize=(16, 11))
        fig.suptitle('Dashboard Analítico: Co-simulação FIPA-ACL (Agente A <-> Agente B)', fontsize=18, fontweight='bold')
        gs = gridspec.GridSpec(2, 2, figure=fig)

        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        # ----------------------------------------------------
        # PAINEL 1: Latência Total
        # ----------------------------------------------------
        # Agrupamento para gerar a linha e a área sombreada do Jitter
        df_resumo = df_expandido.groupby('Tempo').agg({'last_latency': 'mean', 'current_jitter': 'mean'}).reset_index()
        limite_inferior = (df_resumo['last_latency'] - df_resumo['current_jitter']).clip(lower=0)
        limite_superior = df_resumo['last_latency'] + df_resumo['current_jitter']
        
        ax1.fill_between(df_resumo['Tempo'], limite_inferior, limite_superior, color='#ff7f0e', alpha=0.2, label='Flutuação Estocástica')
        ax1.plot(df_resumo['Tempo'], df_resumo['last_latency'], color='gray', linestyle='--', alpha=0.5)
        
        ax1.scatter(df_a['Tempo'], df_a['last_latency'], color='#1f77b4', s=90, marker='o', label='Agente A (Requests)', zorder=5)
        ax1.scatter(df_b['Tempo'], df_b['last_latency'], color='#2ca02c', s=90, marker='s', label='Agente B (Informs)', zorder=5)
        
        ax1.set_title('1. Latência Temporal por Agente', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Tempo (Passos do Mosaik)')
        ax1.set_ylabel('Latência Exata (Segundos)')
        ax1.legend()
        ax1.grid(True, linestyle=':', alpha=0.7)

        # ----------------------------------------------------
        # PAINEL 2: Picos de Jitter (Barras)
        # ----------------------------------------------------
        jitter_plot = df_expandido.groupby('Tempo')['current_jitter'].mean().reset_index()
        ax2.bar(jitter_plot['Tempo'], jitter_plot['current_jitter'], color='#ff7f0e', edgecolor='black', alpha=0.7)
        
        ax2.set_title('2. Saturação de Jitter Exponencial por Passo', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Tempo (Passos do Mosaik)')
        ax2.set_ylabel('Atraso Adicional (Segundos)')
        ax2.grid(axis='y', linestyle=':', alpha=0.7)

        # ----------------------------------------------------
        # PAINEL 3: Tamanho do Pacote FIPA (Dispersão)
        # ----------------------------------------------------
        size_plot = df_expandido.groupby('Tempo')['last_packet_size'].mean().reset_index()
        ax3.plot(size_plot['Tempo'], size_plot['last_packet_size'], color='gray', linestyle='-', alpha=0.3)
        
        ax3.scatter(df_a['Tempo'], df_a['last_packet_size'], color='#1f77b4', s=100, marker='^', label='Payload Agente A', zorder=5)
        ax3.scatter(df_b['Tempo'], df_b['last_packet_size'], color='#2ca02c', s=100, marker='v', label='Payload Agente B', zorder=5)

        ax3.set_title('3. Tamanho das Mensagens FIPA-ACL (Bytes)', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Tempo (Passos do Mosaik)')
        ax3.set_ylabel('Tamanho do Envelope (Bytes)')
        
        min_y, max_y = df_expandido['last_packet_size'].min(), df_expandido['last_packet_size'].max()
        if min_y != max_y: ax3.set_ylim(min_y - 20, max_y + 20)
        ax3.legend()
        ax3.grid(True, linestyle=':', alpha=0.7)

        # ----------------------------------------------------
        # PAINEL 4: Gráfico de Pizza de Confiabilidade
        # ----------------------------------------------------
        p_enviados = time_data['packets_sent'].max() if 'packets_sent' in time_data.columns else 0
        p_recebidos = time_data['packets_received'].max() if 'packets_received' in time_data.columns else 0
        p_descartados = time_data['packets_dropped'].max() if 'packets_dropped' in time_data.columns else 0
        em_transito = max(0, p_enviados - p_recebidos - p_descartados)

        labels = ['Entregues com Sucesso', 'Perdidos (Dropados)', 'Em Trânsito no Cabo']
        tamanhos = [p_recebidos, p_descartados, em_transito]
        cores = ['#2ca02c', '#d62728', '#7f7f7f']

        labels_filtrados = [l for l, s in zip(labels, tamanhos) if s > 0]
        tamanhos_filtrados = [s for s in tamanhos if s > 0]
        cores_filtradas = [c for c, s in zip(cores, tamanhos) if s > 0]

        if sum(tamanhos_filtrados) > 0:
            wedges, texts, autotexts = ax4.pie(tamanhos_filtrados, labels=labels_filtrados, colors=cores_filtradas, 
                                               autopct='%1.1f%%', startangle=140, 
                                               wedgeprops={'edgecolor': 'black', 'linewidth': 1})
            for text in texts + autotexts:
                text.set_fontsize(11)
                text.set_fontweight('bold')
        
        ax4.set_title(f'4. Eficiência de Rede OMNeT++ (Total: {int(p_enviados)} pacotes)', fontsize=14, fontweight='bold')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig('grafico_trafego.png', dpi=300)
        print("✅ Sucesso! Dashboard perfeitamente adaptado salvo como 'grafico_trafego.png'.")
        
    except FileNotFoundError:
        print("❌ Erro: O arquivo 'results.csv' não foi encontrado.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == '__main__':
    gerar_grafico()