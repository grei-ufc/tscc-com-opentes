import pandas as pd
import matplotlib.pyplot as plt

def gerar_grafico():
    try:
        df = pd.read_csv('results.csv')
        
        # 1. CORREÇÃO: Força a coluna 'Valor' a ser tratada como número (Float)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

        plt.figure(figsize=(10, 6))

        # Dados do Hub
        hub_data = df[(df['Origem'] == 'OmnetSim-0.node_0') & (df['Atributo'] == 'packets_sent')]
        total_enviados = hub_data['Valor'].iloc[-1] if not hub_data.empty else 0
        total_recebidos = 0
        
        # 2. CORREÇÃO: Usar int(float()) para evitar o erro do terminal
        plt.plot(hub_data['Tempo'], hub_data['Valor'], label=f'Hub (TOTAL Enviados: {int(float(total_enviados))})', 
                 color='black', marker='o', linewidth=2, linestyle='--')

        cores = ['red', 'green', 'blue']
        for i in range(1, 4):
            node_name = f'OmnetSim-0.node_{i}'
            recv_data = df[(df['Origem'] == node_name) & (df['Atributo'] == 'packets_received')]
            
            recebidos_neste_no = recv_data['Valor'].iloc[-1] if not recv_data.empty else 0
            total_recebidos += recebidos_neste_no
            
            plt.plot(recv_data['Tempo'], recv_data['Valor'], label=f'Cliente {i} (Recebidos: {int(float(recebidos_neste_no))})', 
                     color=cores[i-1], marker='x')

        perda_pct = 0.0
        if total_enviados > 0:
            perda_pct = ((float(total_enviados) - float(total_recebidos)) / float(total_enviados)) * 100

        plt.title(f'Broadcast em Estrela (Perda Total de Pacotes: {perda_pct:.1f}%)')
        plt.xlabel('Tempo (s)')
        plt.ylabel('Quantidade de Pacotes')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        plt.savefig('grafico_trafego.png')
        print("Sucesso! Gráfico gerado perfeitamente.")
        
    except Exception as e:
        print(f"Erro ao gerar o grafico: {e}")

if __name__ == '__main__':
    gerar_grafico()