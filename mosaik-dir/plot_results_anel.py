import mosaik
import os
import json
import math

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
    NUM_AGENTES = int(os.environ.get('NUM_PERIFERICOS', 4))
    
    # Captura os tipos de rede selecionados no Menu Streamlit
    tipos_env = os.environ.get('TIPOS_REDE', '')
    if tipos_env:
        TIPOS_REDE = [t.strip() for t in tipos_env.split(',') if t.strip()]
    else:
        # Fallback de segurança
        TIPOS_REDE = ['Link_Wired', 'Link_5G', 'Link_4G', 'Link_2G', 'Link_Wireless']
    
    print(f"🌍 Montando topologia ANEL Dinâmica: {NUM_AGENTES} Agentes Interligados...")
    print(f"📡 Redes ativas no ciclo: {', '.join(TIPOS_REDE)}")
    
    agentes_info = []
    centro_x, centro_y, raio = 500.0, 500.0, 350.0

    for i in range(NUM_AGENTES):
        angulo = 2 * math.pi * i / NUM_AGENTES
        agentes_info.append({
            'id': f'agente_{i+1}',
            'x': round(centro_x + raio * math.cos(angulo), 2),
            'y': round(centro_y + raio * math.sin(angulo), 2),
            'tipo': 'Anel'
        })
    
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)
        
    with open('/omnet-dir/config.json', 'w') as f:
        json.dump({'tipos_rede': TIPOS_REDE}, f)
        
    links = []
    for i in range(NUM_AGENTES):
        origem = f'agente_{i+1}'
        destino = f'agente_{(i+1) % NUM_AGENTES + 1}'
        tipo = TIPOS_REDE[i % len(TIPOS_REDE)]
        links.append({'origem': origem, 'destino': destino, 'tipo': tipo})

    print("⚙️ Gerando DynamicNetwork.ned...")
    gerar_topologia_ned(agentes_info, links)

    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    monitor = coletor_sim.Monitor()
    
    for ag in agentes_info:
        ag_id = ag['id'] 
        agente_pade = pade_sim.PadeAgent(agent_id=ag_id)
        node_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid=ag_id)
        
        world.connect(agente_pade, node_omnet, ('val_out', 'val_in'))
        world.connect(node_omnet, agente_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)