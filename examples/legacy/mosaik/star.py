import mosaik
import os
import random
import json

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim': {'connect': 'pade:5678'} 
}

def gerar_topologia_ned(agentes_info, links, arquivo_saida="/omnet-dir/DynamicNetwork.ned"):
    with open(arquivo_saida, 'w') as f:
        f.write("network DynamicNetwork\n{\n")
        f.write("    submodules:\n")
        f.write("        mosaikBridge: MosaikBridge;\n\n")
        
        # Instancia os nós já injetando a coordenada X e Y neles!
        for ag in agentes_info:
            f.write(f"        {ag['id']}: AgentNode {{\n")
            f.write(f"            xPos = {ag['x']};\n")
            f.write(f"            yPos = {ag['y']};\n")
            f.write("        }\n")
            
        f.write("\n    connections:\n")
        for link in links:
            f.write(f"        {link['origem']}.port++ <--> {link['tipo']} <--> {link['destino']}.port++;\n")
            
        f.write("}\n")

def create_scenario(world):
    print(f"🌍 Montando topologia ESTRELA ESPACIAL: 1 Central <-> {NUM_PERIFERICOS} Periféricos...")
    
    agente_central_id = 'agent_central'
    perifericos_ids = [f'agent_p_{i}' for i in range(1, NUM_PERIFERICOS + 1)]
    
    # ================================================================
    # GEOLOCALIZAÇÃO: Espalhando agentes num Grid 1000x1000
    # ================================================================
    agentes_info = []
    # A Antena Central fica exatamente no meio do mapa
    agentes_info.append({'id': agente_central_id, 'x': 500.0, 'y': 500.0, 'tipo': 'Central'})
    
    for pid in perifericos_ids:
        agentes_info.append({
            'id': pid, 
            'x': round(random.uniform(0, 1000), 2), 
            'y': round(random.uniform(0, 1000), 2), 
            'tipo': 'Periferico'
        })
        
    # Salva o mapa para o Dashboard desenhar depois
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)

    tipos_redes = ['Link_5G', 'Link_4G', 'Link_Wired', 'Link_IoT']
    links = []
    
    for i, pid in enumerate(perifericos_ids):
        tipo_escolhido = tipos_redes[i % len(tipos_redes)] 
        links.append({'origem': agente_central_id, 'destino': pid, 'tipo': tipo_escolhido})

    gerar_topologia_ned(agentes_info, links)

    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    monitor = coletor_sim.Monitor()
    agente_central_pade = pade_sim.PadeAgent(agent_id='AgenteCentral')
    node_central_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid=agente_central_id)
    
    world.connect(agente_central_pade, node_central_omnet, ('val_out', 'val_in'))
    world.connect(node_central_omnet, agente_central_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
    world.connect(node_central_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

    for i in range(1, NUM_PERIFERICOS + 1):
        pid = f'agent_p_{i}'
        agente_p_pade = pade_sim.PadeAgent(agent_id=f'AgenteP_{i}')
        node_p_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid=pid)
        
        world.connect(agente_p_pade, node_p_omnet, ('val_out', 'val_in'))
        world.connect(node_p_omnet, agente_p_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_p_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)