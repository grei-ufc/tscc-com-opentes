"""
Orquestrador Principal da Co-Simulação Mosaik-OMNeT++.

CICLO DE DADOS:
  Gerador ──(sinal_saida → data_in)──→ node_0 (OMNeT++)
  node_0  ──(data_out → retroalimentacao) ──→ Gerador  [time_shifted=True]
  nodes   ──(data_out, status, …)──────────→ Coletor (CSV)

  A conexão time_shifted=True é o que permite o ciclo sem violar a
  causalidade do Mosaik: os dados do passo t chegam ao Gerador no passo t+1.
"""

import plot_results
import mosaik
import os

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'Gerador':  {'python': 'controller:Controlador'},
    'Coletor':  {'python': 'collector:Coletor'},
}


def main():
    world = mosaik.World(sim_config)

    omnet_host = os.getenv('OMNET_HOST', 'localhost')
    omnet_port = int(os.getenv('OMNET_PORT', 5555))

    # 1. Inicia os 3 simuladores
    omnet_sim  = world.start('OmnetSim', host=omnet_host, port=omnet_port)
    gerador_sim = world.start('Gerador')
    coletor_sim = world.start('Coletor')

    # 2. Cria entidades na memória (Agora 4 nós!)
    nodes = omnet_sim.NetworkNode.create(4, node_type='NetworkNode')

    # Desenha a Topologia em Estrela (Hub -> Clientes)
    omnet_sim.Connection.create(1, src='node_0', dest='node_1')
    omnet_sim.Connection.create(1, src='node_0', dest='node_2')
    omnet_sim.Connection.create(1, src='node_0', dest='node_3')

    gen_entity = gerador_sim.TrafficGen.create(1, valor_injecao=15.0)
    monitor    = coletor_sim.Monitor.create(1)

    # 3. Ligar os fios (Data Flow)
    
    # Injeção: Do Gerador para a porta 'data_in' do node_0 
    world.connect(gen_entity[0], nodes[0], ('sinal_saida', 'data_in'))

    # Recolha: Dos dois nós do OMNeT++ para o Monitor CSV
    for node in nodes:
        world.connect(
            node, monitor[0],
            'data_out', 'status',
            'packets_sent', 'packets_received',
            'last_latency', 'last_packet_size',
        )

    # *** CICLO DE FEEDBACK ***
    # Os dados de saída do node_0 (hub) retroalimentam o Gerador no passo seguinte.
    # time_shifted=True evita o ciclo causal no mesmo passo — os dados chegam
    # com 1 passo de atraso, que é o comportamento correto em co-simulação.
    world.connect(
        nodes[0], gen_entity[0],
        ('data_out', 'retroalimentacao'),
        time_shifted=True,
        initial_data={'data_out': 0.0}
    )

    # 4. Executa a simulação
    print("\nIniciando co-simulação cíclica Mosaik ↔ OMNeT++...")
    world.run(until=10)
    print("Simulação finalizada! Verifique results.csv")

    print("Gerando gráfico...")
    plot_results.gerar_grafico()


if __name__ == '__main__':
    main()
