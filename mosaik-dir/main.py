import mosaik
import os

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'Gerador':  {'python': 'controller:Controlador'},
    'Coletor':  {'python': 'collector:Coletor'}
}

def main():
    world = mosaik.World(sim_config)

    omnet_host = os.getenv('OMNET_HOST', 'localhost')
    omnet_port = int(os.getenv('OMNET_PORT', 5555))

    # 1. Inicia os 3 simuladores
    omnet_sim = world.start('OmnetSim', host=omnet_host, port=omnet_port)
    gerador_sim = world.start('Gerador')
    coletor_sim = world.start('Coletor')
    
    # 2. Cria as entidades na memória
    nodes = omnet_sim.NetworkNode.create(2, node_type='NetworkNode')
    omnet_sim.Connection.create(1, src='node_0', dest='node_1')
    
    gen_entity = gerador_sim.TrafficGen.create(1, valor_injecao=15.0)
    monitor = coletor_sim.Monitor.create(1)

    # 3. Ligar os fios (Data Flow)
    
    # Injeção: Do Gerador para a porta 'data_in' do node_0
    world.connect(gen_entity[0], nodes[0], ('sinal_saida', 'data_in'))

    # Recolha: Dos dois nós do OMNeT++ para o Monitor CSV
    for node in nodes:
        world.connect(node, monitor[0], 'data_out', 'status')

    print("\nIniciando co-simulacao com injecao e gravacao CSV...")
    # Executa a simulação inteira de uma vez, do tempo 0 ao 10
    world.run(until=10)
    print("Simulacao finalizada! Verifique o ficheiro results.csv")

if __name__ == '__main__':
    main()