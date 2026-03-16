import pandas as pd
import matplotlib.pyplot as plt

def gerar_grafico():
    try:
        # 1. Carrega o CSV
        df = pd.read_csv('results.csv')

        # 2. Filtra os dados: Queremos os 'packets_sent' do node_0 e 'packets_received' do node_1
        sent_data = df[(df['Origem'] == 'OmnetSim-0.node_0') & (df['Atributo'] == 'packets_sent')]
        recv_data = df[(df['Origem'] == 'OmnetSim-0.node_1') & (df['Atributo'] == 'packets_received')]

        # 3. Cria o gráfico
        plt.figure(figsize=(10, 6))

        # Linha de pacotes enviados
        plt.plot(sent_data['Tempo'], sent_data['Valor'], label='Pacotes Enviados (node_0)', 
                 color='blue', marker='o', linestyle='--')

        # Linha de pacotes recebidos
        plt.plot(recv_data['Tempo'], recv_data['Valor'], label='Pacotes Recebidos (node_1)', 
                 color='green', marker='x', linestyle='-')

        # 4. Formata e exibe o gráfico
        plt.title('Simulação de Tráfego: Mosaik -> OMNeT++')
        plt.xlabel('Tempo (s)')
        plt.ylabel('Quantidade de Pacotes')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        # Salva o gráfico como imagem
        plt.savefig('grafico_trafego.png')
        print("Sucesso! O ficheiro 'grafico_trafego.png' foi guardado na pasta.")
        
    except Exception as e:
        print(f"Erro ao gerar o grafico: {e}")

# (Esta linha permite que o ficheiro seja executado sozinho se quiser)
if __name__ == '__main__':
    gerar_grafico()