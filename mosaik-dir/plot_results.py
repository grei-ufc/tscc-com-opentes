import pandas as pd
import matplotlib.pyplot as plt

def gerar_grafico():
    try:
        print("📊 Lendo dados de results.csv...")
        df = pd.read_csv('results.csv')
        
        # 1. TRATAMENTO DE DADOS: 
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        
        df = df.dropna(subset=['Valor'])

        # 2. FILTRAR O NÓ DA NUVEM:
        node_data = df[df['Origem'] == 'OmnetSim-0.node_0']

        # Separar as métricas que queremos estudar
        latencia = node_data[node_data['Atributo'] == 'last_latency']
        tamanho = node_data[node_data['Atributo'] == 'last_packet_size']
        pacotes_totais = node_data[node_data['Atributo'] == 'packets_sent']['Valor'].max()

        # 3. GERAR OS GRÁFICOS (2 Painéis)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

        # Painel Superior: O Efeito Ping-Pong (Tamanho do Pacote a oscilar)
        ax1.plot(tamanho['Tempo'], tamanho['Valor'], marker='o', color='#1f77b4', linewidth=2)
        ax1.set_title(f'Tamanho do Pacote (Total Processado na Nuvem: {int(pacotes_totais)} pacotes)')
        ax1.set_ylabel('Tamanho (Bytes)')
        ax1.grid(True, linestyle=':', alpha=0.7)

        # Painel Inferior: A Física da Rede (Latência Dinâmica que programámos em C++)
        ax2.plot(latencia['Tempo'], latencia['Valor'], marker='s', color='#d62728', linestyle='--', linewidth=2)
        ax2.set_title('Latência da Rede (Atraso de Propagação Fixo + Tempo de Transmissão)')
        ax2.set_xlabel('Tempo da Simulação (Passos do Mosaik)')
        ax2.set_ylabel('Latência (Segundos)')
        ax2.grid(True, linestyle=':', alpha=0.7)

        plt.tight_layout()
        plt.savefig('grafico_trafego.png', dpi=300)
        print("✅ Sucesso! Gráfico gerado perfeitamente e salvo como 'grafico_trafego.png'.")
        
    except FileNotFoundError:
        print("❌ Erro: O arquivo 'results.csv' não foi encontrado. Rode a simulação primeiro.")
    except Exception as e:
        print(f"❌ Erro inesperado ao gerar o grafico: {e}")

if __name__ == '__main__':
    gerar_grafico()