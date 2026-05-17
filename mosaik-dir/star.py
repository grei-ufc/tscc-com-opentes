import mosaik
import os

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim': {'connect': 'pade:5678'} 
}

def create_scenario(world):
    print(f"🌍 Montando topologia ESTRELA: 1 Central <-> {NUM_PERIFERICOS} Periféricos...")
    
    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    rede_omnet = omnet_sim.NetworkNode(node_type='NetworkNode')
    monitor = coletor_sim.Monitor()
    
    agente_central = pade_sim.PadeAgent(agent_id='AgenteCentral')
    
    # Conexão Bidirecional do Central
    world.connect(agente_central, rede_omnet, ('val_out', 'val_in'))
    world.connect(rede_omnet, agente_central, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})

    # Conexão Dinâmica dos Periféricos
    for i in range(1, NUM_PERIFERICOS + 1):
        agente_p = pade_sim.PadeAgent(agent_id=f'AgenteP_{i}')
        world.connect(agente_p, rede_omnet, ('val_out', 'val_in'))
        world.connect(rede_omnet, agente_p, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})

    # Conexão da Telemetria (Coletor)
    world.connect(rede_omnet, monitor, 
                  'status', 'packets_sent', 'packets_received', 'packets_dropped', 
                  'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)