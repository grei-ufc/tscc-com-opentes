import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json

def extrair_remetente(val_out_str):
    try:
        if pd.isna(val_out_str) or str(val_out_str).strip() == "":
            return "Rede"
            
        # Cortamos as mensagens multiplexadas e olhamos para a primeira
        primeira_msg = str(val_out_str).split("|||")[0]
        
        msg = json.loads(primeira_msg)
        sender = msg.get("sender", "")
        if sender: return sender.split('@')[0]
        return "Rede"
    except: return "Rede"

def gerar_grafico():
    try:
        print("📊 Lendo dados e montando Dashboard Estrela (N-Agentes)...")
        df = pd.read_csv('results.csv')
        
        node_data = df[df['Origem'] == 'OmnetSim-0.node_0'].copy()
        time_data = node_data.pivot_table(index='Tempo', columns='Atributo', values='Valor', aggfunc='first').reset_index()

        cols_esperadas = ['last_latency', 'current_jitter', 'last_packet_size', 'packets_sent', 'packets_received', 'packets_dropped']
        for col in cols_esperadas:
            if col not in time_data.columns:
                time_data[col] = 0.0
            time_data[col] = pd.to_numeric(time_data[col], errors='coerce').fillna(0)

        # Extrai os agentes, agora sabendo lidar com o |||
        if 'val_out' in time_data.columns:
            time_data['Agente'] = time_data['val_out'].apply(extrair_remetente)
        else:
            time_data['Agente'] = 'Rede'

        # Separar Agente Central dos Periféricos
        df_central = time_data[time_data['Agente'] == 'AgenteCentral']
        df_perifericos = time_data[time_data['Agente'].str.startswith('AgenteP_')]

        fig = plt.figure(figsize=(16, 11))
        fig.suptitle('Dashboard Analítico: Topologia em Estrela FIPA-ACL', fontsize=18, fontweight='bold')
        gs = gridspec.GridSpec(2, 2, figure=fig)
        ax1, ax2, ax3, ax4 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

        # PAINEL 1: Latência
        limite_inferior = (time_data['last_latency'] - time_data['current_jitter']).clip(lower=0)
        limite_superior = time_data['last_latency'] + time_data['current_jitter']
        ax1.fill_between(time_data['Tempo'], limite_inferior, limite_superior, color='#ff7f0e', alpha=0.2, label='Jitter na Fila')
        
        ax1.plot(time_data['Tempo'], time_data['last_latency'], color='gray', linestyle='--', alpha=0.4)
        ax1.scatter(df_central['Tempo'], df_central['last_latency'], color='#d62728', s=120, marker='*', label='Broadcast (Central)', zorder=5)
        ax1.scatter(df_perifericos['Tempo'], df_perifericos['last_latency'], color='#2ca02c', s=80, marker='o', alpha=0.9, label='Respostas (Periféricos)', zorder=4)
        
        ax1.set_title('1. Latência e Gargalos de Convergência', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Tempo (Passos do Mosaik)')
        ax1.set_ylabel('Latência Total (Segundos)')
        ax1.legend(); ax1.grid(True, linestyle=':', alpha=0.7)

        # PAINEL 2: Jitter
        ax2.bar(time_data['Tempo'], time_data['current_jitter'], color='#ff7f0e', edgecolor='black', alpha=0.7)
        ax2.set_title('2. Picos de Atraso Estocástico (Jitter)', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', linestyle=':', alpha=0.7)

        # PAINEL 3: Payload
        ax3.plot(time_data['Tempo'], time_data['last_packet_size'], color='gray', linestyle='-', alpha=0.3)
        ax3.scatter(df_central['Tempo'], df_central['last_packet_size'], color='#d62728', s=120, marker='*', label='Tamanho do Broadcast', zorder=5)
        ax3.scatter(df_perifericos['Tempo'], df_perifericos['last_packet_size'], color='#2ca02c', s=80, marker='o', alpha=0.9, label='Tamanho da Resposta', zorder=4)
        
        ax3.set_title('3. Tamanho do Envelope na Nuvem (Bytes)', fontsize=14, fontweight='bold')
        min_y, max_y = time_data['last_packet_size'].min(), time_data['last_packet_size'].max()
        if min_y != max_y: ax3.set_ylim(min_y - 20, max_y + 20)
        ax3.legend(); ax3.grid(True, linestyle=':', alpha=0.7)

        # PAINEL 4: Confiabilidade
        p_enviados = time_data['packets_sent'].max()
        p_recebidos = time_data['packets_received'].max()
        p_descartados = time_data['packets_dropped'].max()
        em_transito = max(0, p_enviados - p_recebidos - p_descartados)

        labels = ['Entregues', 'Dropados (Física)', 'Em Trânsito']
        tamanhos = [p_recebidos, p_descartados, em_transito]
        cores = ['#2ca02c', '#d62728', '#7f7f7f']
        labels_f = [l for l, s in zip(labels, tamanhos) if s > 0]
        tamanhos_f = [s for s in tamanhos if s > 0]
        cores_f = [c for c, s in zip(cores, tamanhos) if s > 0]

        if sum(tamanhos_f) > 0:
            ax4.pie(tamanhos_f, labels=labels_f, colors=cores_f, autopct='%1.1f%%', startangle=140, wedgeprops={'edgecolor': 'black'})
        
        ax4.set_title(f'4. Integridade da Estrela (Total: {int(p_enviados)} pacotes)', fontsize=14, fontweight='bold')
        
        # Pega a contagem real de agentes detectados (Central + Periféricos)
        qtd_agentes = len(df_perifericos['Agente'].unique())
        if qtd_agentes == 0: qtd_agentes = 3 # fallback 
        
        kpi_text = (f"Escala: 1 Central -> {qtd_agentes} Periféricos\n\n"
                    f"Enviados: {int(p_enviados)}\nEntregues: {int(p_recebidos)}\nDropados: {int(p_descartados)}\n\n"
                    f"Drop Rate: {(p_descartados/p_enviados*100) if p_enviados>0 else 0:.1f}%")
        ax4.text(0.85, 0.5, kpi_text, ha='center', va='center', transform=ax4.transAxes, fontsize=11, fontweight='bold', bbox=dict(fc="#f9f9f9", ec="#b0b0b0", lw=2))

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig('grafico_trafego.png', dpi=300)
        print("✅ Sucesso! Dashboard de Topologia Estrela salvo como 'grafico_trafego.png'.")
        
    except Exception as e: print(f"❌ Erro inesperado ao gerar o gráfico: {e}")

if __name__ == '__main__':
    gerar_grafico()