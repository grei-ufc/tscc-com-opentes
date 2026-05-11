import mosaik

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim': {'connect': 'pade:5678'} 
}

def create_scenario(world):
    print("🌍 Montando cenário: PADE (A <-> B) via OMNeT++ com Collector...")
    
    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    rede_omnet = omnet_sim.NetworkNode(node_type='NetworkNode')
    monitor = coletor_sim.Monitor()
    
    agente_a = pade_sim.PadeAgent(agent_id='AgenteA')
    agente_b = pade_sim.PadeAgent(agent_id='AgenteB')

    # ==========================================
    # ROTA 1: Agente A -> OMNeT++ -> Agente B
    # ==========================================
    world.connect(agente_a, rede_omnet, ('val_out', 'val_in'))
    world.connect(rede_omnet, agente_b, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})

    # ==========================================
    # ROTA 2: Agente B -> OMNeT++ -> Agente A
    # ==========================================
    world.connect(agente_b, rede_omnet, ('val_out', 'val_in'))
    world.connect(rede_omnet, agente_a, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})

    # ==========================================
    # ROTA 3: OMNeT++ -> Collector (Telemetria)
    # ==========================================
    # O Collector recolhe as métricas e também a mensagem que saiu da rede (val_out)
    world.connect(rede_omnet, monitor, 
                  'status', 'packets_sent', 'packets_received', 'packets_dropped', 
                  'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')


if __name__ == '__main__':
    print("🎬 Iniciando o Orquestrador Mosaik...")
    world = mosaik.World(sim_config)
    create_scenario(world)
    
    world.run(until=20) 
    print("✅ Co-simulação finalizada! Verifique o CSV gerado pelo Collector.")