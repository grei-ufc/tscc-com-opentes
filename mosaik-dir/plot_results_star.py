import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json

def extrair_remetente(msg_str):
    try:
        if pd.isna(msg_str) or str(msg_str).strip() == "":
            return "Rede"
        msg_json = json.loads(msg_str)
        sender = msg_json.get("sender", "")
        if sender: return sender.split('@')[0]
        return "Rede"
    except: return "Rede"

def gerar_grafico():
    try:
        print("📊 Desempacotando dados multiplexados e montando Dashboard Estrela...")
        df = pd.read_csv('results.csv')
        
        node_data = df[df['Origem'] == 'OmnetSim-0.node_0'].copy()
        time_data = node_data.pivot_table(index='Tempo', columns='Atributo', values='Valor', aggfunc='first').reset_index()

        # Garante que as colunas existem
        for col in ['packets_sent', 'packets_received', 'packets_dropped']:
            if col not in time_data.columns: time_data[col] = 0.0
            time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

        # =================================================================
        # DESEMPACOTAMENTO CIRÚRGICO DA TELEMETRIA
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
                
                # Para cada mensagem dentro do mesmo segundo, cria um ponto individual
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

        # Separa os agentes para cores diferentes
        df_central = df_expandido[df_expandido['Agente'] == 'AgenteCentral']
        df_perifericos = df_expandido[df_expandido['Agente'].str.startswith('AgenteP_')]

        # Prepara a Figura
        fig = plt.figure(figsize=(16, 11))
        fig.suptitle('Dashboard Analítico: Topologia em Estrela (Telemetria Alta Resolução)', fontsize=18, fontweight='bold')
        gs = gridspec.GridSpec(2, 2, figure=fig)
        ax1, ax2, ax3, ax4 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

        # PAINEL 1: Latência Exata
        ax1.scatter(df_central['Tempo'], df_central['last_latency'], color='#d62728', s=120, marker='*', label='Broadcast (Central)', zorder=5)
        ax1.scatter(df_perifericos['Tempo'], df_perifericos['last_latency'], color='#2ca02c', s=60, marker='o', alpha=0.6, label='Respostas (Periféricos)', zorder=4)
        ax1.set_title('1. Latência Temporal Resolvida', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Tempo (Passos do Mosaik)'); ax1.set_ylabel('Latência Exata (Segundos)')
        ax1.legend(); ax1.grid(True, linestyle=':', alpha=0.7)

        # PAINEL 2: Jitter Scatter
        ax2.scatter(df_expandido['Tempo'], df_expandido['current_jitter'], color='#ff7f0e', alpha=0.7)
        ax2.set_title('2. Jitter Distribuído (Por Pacote)', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Tempo'); ax2.set_ylabel('Atraso Estocástico Extra (s)')
        ax2.grid(True, linestyle=':', alpha=0.7)

        # PAINEL 3: Payload Desmistificado
        ax3.scatter(df_central['Tempo'], df_central['last_packet_size'], color='#d62728', s=120, marker='*', label='Tamanho do Broadcast', zorder=5)
        ax3.scatter(df_perifericos['Tempo'], df_perifericos['last_packet_size'], color='#2ca02c', s=60, marker='o', alpha=0.6, label='Tamanho da Resposta', zorder=4)
        ax3.set_title('3. Tamanho do Envelope na Nuvem (Bytes)', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Tempo'); ax3.set_ylabel('Tamanho (Bytes)')
        ax3.legend(); ax3.grid(True, linestyle=':', alpha=0.7)

        # PAINEL 4: Confiabilidade Global
        p_enviados = time_data['packets_sent'].max()
        p_recebidos = time_data['packets_received'].max()
        p_descartados = time_data['packets_dropped'].max()
        em_transito = max(0, p_enviados - p_recebidos - p_descartados)

        labels = ['Entregues', 'Dropados', 'Em Trânsito']
        tamanhos = [p_recebidos, p_descartados, em_transito]
        cores = ['#2ca02c', '#d62728', '#7f7f7f']
        labels_f = [l for l, s in zip(labels, tamanhos) if s > 0]
        tamanhos_f = [s for s in tamanhos if s > 0]
        cores_f = [c for c, s in zip(cores, tamanhos) if s > 0]

        if sum(tamanhos_f) > 0:
            ax4.pie(tamanhos_f, labels=labels_f, colors=cores_f, autopct='%1.1f%%', startangle=140, wedgeprops={'edgecolor': 'black'})
        
        ax4.set_title(f'4. Integridade da Estrela (Total: {int(p_enviados)} pacotes)', fontsize=14, fontweight='bold')
        
        qtd_agentes = len(df_perifericos['Agente'].unique())
        kpi_text = (f"Escala Analisada: 1 Central -> {qtd_agentes} Periféricos\n\n"
                    f"Mensagens: {len(df_expandido)} capturadas no gráfico\n\n"
                    f"Drop Rate Físico: {(p_descartados/p_enviados*100) if p_enviados>0 else 0:.1f}%")
        ax4.text(0.85, 0.5, kpi_text, ha='center', va='center', transform=ax4.transAxes, fontsize=11, fontweight='bold', bbox=dict(fc="#f9f9f9", ec="#b0b0b0", lw=2))

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig('grafico_trafego.png', dpi=300)
        print("✅ Sucesso! Dashboard Alta Resolução salvo como 'grafico_trafego.png'.")
        
    except Exception as e: print(f"❌ Erro inesperado ao gerar o gráfico: {e}")

if __name__ == '__main__':
    gerar_grafico()