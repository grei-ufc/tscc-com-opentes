import mosaik
import json
import os

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim': {'connect': 'pade:5678'} 
}

def gerar_topologia_ned(agentes_info, links, arquivo_saida="/omnet-dir/DynamicNetwork.ned"):
    with open(arquivo_saida, 'w') as f:
        f.write("network DynamicNetwork\n{\n    submodules:\n        mosaikBridge: MosaikBridge;\n\n")
        
        # Instancia os nós já injetando a coordenada X e Y (Mapeamento Espacial)
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
    print("🌍 Montando topologia Ponto-a-Ponto Espacial: Agente 1 <-> Agente 2")
    
    # Define as coordenadas: Distantes 600m um do outro no plano cartesiano
    agentes_info = [
        {'id': 'agent_1', 'x': 200.0, 'y': 500.0, 'tipo': 'Agente_1'},
        {'id': 'agent_2', 'x': 800.0, 'y': 500.0, 'tipo': 'Agente_2'}
    ]
    
    # Salva o mapa para o Plotter (Dashboard)
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)

    # Conecta eles usando o perfil 5G
    links = [{'origem': 'agent_1', 'destino': 'agent_2', 'tipo': 'Link_5G'}]
    gerar_topologia_ned(agentes_info, links)

    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    monitor = coletor_sim.Monitor()
    
    # Instanciando e conectando o Agente 1
    ag1_pade = pade_sim.PadeAgent(agent_id='Agente_1')
    ag1_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid='agent_1')
    world.connect(ag1_pade, ag1_omnet, ('val_out', 'val_in'))
    world.connect(ag1_omnet, ag1_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
    world.connect(ag1_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

    # Instanciando e conectando o Agente 2
    ag2_pade = pade_sim.PadeAgent(agent_id='Agente_2')
    ag2_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid='agent_2')
    world.connect(ag2_pade, ag2_omnet, ('val_out', 'val_in'))
    world.connect(ag2_omnet, ag2_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
    world.connect(ag2_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)