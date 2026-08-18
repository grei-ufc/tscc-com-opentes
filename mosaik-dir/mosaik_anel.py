import mosaik
import os
import json

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
        
        for ag in agentes_info:
            f.write(f"        {ag['id']}: AgentNode {{\n")
            f.write(f"            agent_id = \"{ag['id']}\";\n")
            f.write(f"            xPos = {ag['x']};\n")
            f.write(f"            yPos = {ag['y']};\n")
            f.write("        }\n")
            
        f.write("\n    connections:\n")
        for link in links:
            f.write(f"        {link['origem']}.port++ <--> {link['tipo']} <--> {link['destino']}.port++;\n")
        f.write("}\n")

def create_scenario(world):
    print("🌍 Montando topologia ANEL (Malha Parcial): 4 Agentes Interligados...")
    
    # 1. Posicionamento espacial em formato de quadrado/anel
    agentes_info = [
        {'id': 'agente_1', 'x': 200.0, 'y': 500.0},
        {'id': 'agente_2', 'x': 500.0, 'y': 800.0},
        {'id': 'agente_3', 'x': 800.0, 'y': 500.0},
        {'id': 'agente_4', 'x': 500.0, 'y': 200.0}
    ]
    
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)
        
    # 2. Definição rígida das vizinhanças e dos canais, conforme o seu diagrama
    links = [
    {'origem': 'agente_1', 'destino': 'agente_2', 'tipo': 'Link_Wired'},
    {'origem': 'agente_2', 'destino': 'agente_3', 'tipo': 'Link_4G'},
    {'origem': 'agente_3', 'destino': 'agente_4', 'tipo': 'Link_5G'},
    {'origem': 'agente_4', 'destino': 'agente_1', 'tipo': 'Link_2G'} # <--- Correção aqui
    ]

    print("⚙️ Gerando DynamicNetwork.ned...")
    gerar_topologia_ned(agentes_info, links)

    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    monitor = coletor_sim.Monitor()
    
    # 3. Conexão e injeção
    # 3. Conexão e injeção
    for ag in agentes_info:
        ag_id = ag['id'] # ex: 'Agente_1'
        agente_pade = pade_sim.PadeAgent(agent_id=ag_id)
        node_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid=ag_id.lower())
        
        world.connect(agente_pade, node_omnet, ('val_out', 'val_in'))
        world.connect(node_omnet, agente_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)