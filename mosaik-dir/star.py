import mosaik
import os

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))

sim_config = {
    'OmnetSim': {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim': {'connect': 'pade:5678'} 
}

# ==============================================================================
# Escreve a topologia do OMNeT++ antes do simulador iniciar
# ==============================================================================
def gerar_topologia_ned(agentes, links, arquivo_saida="/omnet-dir/DynamicNetwork.ned"):
    with open(arquivo_saida, 'w') as f:
        f.write("network DynamicNetwork\n{\n")
        f.write("    submodules:\n")
        f.write("        mosaikBridge: MosaikBridge;\n\n") # Ponte de Socket
        
        # Instancia todos os nós clonados
        for ag in agentes:
            f.write(f"        {ag}: AgentNode {{\n")
            f.write(f"            agent_id = \"{ag}\";\n")
            f.write("        }\n")
            
        f.write("\n    connections:\n")
        # Cria os cabos físicos com as latências/perdas do 5G/4G
        for link in links:
            f.write(f"        {link['origem']}.port++ <--> {link['tipo']} <--> {link['destino']}.port++;\n")
            
        f.write("}\n")

def create_scenario(world):
    print(f"🌍 Montando topologia ESTRELA: 1 Central <-> {NUM_PERIFERICOS} Periféricos...")
    
    # 1. Definindo os IDs dos nós virtuais
    agente_central_id = 'agent_central'
    perifericos_ids = [f'agent_p_{i}' for i in range(1, NUM_PERIFERICOS + 1)]
    todos_agentes_omnet = [agente_central_id] + perifericos_ids
    
    # 2. Distribuindo as redes
    tipos_redes = ['Link_5G', 'Link_4G', 'Link_Wired', 'Link_IoT']
    links = []
    
    for i, pid in enumerate(perifericos_ids):
        # Vai rotacionando: O P_1 fica no 5G, o P_2 no 4G, o P_3 no Wired...
        tipo_escolhido = tipos_redes[i % len(tipos_redes)] 
        links.append({'origem': agente_central_id, 'destino': pid, 'tipo': tipo_escolhido})
        print(f"   🔌 {agente_central_id} conectado ao {pid} via {tipo_escolhido}")

    # 3. GERA O ARQUIVO QUE O OMNeT++ ESTÁ ESPERANDO
    print("⚙️ Gerando DynamicNetwork.ned para o OMNeT++...")
    gerar_topologia_ned(todos_agentes_omnet, links)

    # 4. Inicia os simuladores
    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim')

    monitor = coletor_sim.Monitor()
    
    # 5. Criando a Entidade CENTRAL
    agente_central_pade = pade_sim.PadeAgent(agent_id='AgenteCentral')
    # O OMNeT++ já instanciou os nós via NED. O Mosaik agora só "amarra" eles à simulação.
    node_central_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid=agente_central_id)
    
    world.connect(agente_central_pade, node_central_omnet, ('val_out', 'val_in'))
    world.connect(node_central_omnet, agente_central_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
    world.connect(node_central_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

    # 6. Criando as Entidades PERIFÉRICAS
    for i in range(1, NUM_PERIFERICOS + 1):
        pid = f'agent_p_{i}'
        
        agente_p_pade = pade_sim.PadeAgent(agent_id=f'AgenteP_{i}')
        node_p_omnet = omnet_sim.AgentNode(node_type='AgentNode', eid=pid)
        
        # Conecta o PADE ao OMNeT clone dele
        world.connect(agente_p_pade, node_p_omnet, ('val_out', 'val_in'))
        world.connect(node_p_omnet, agente_p_pade, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': ''})
        
        # Conecta o OMNeT clone ao Monitor
        world.connect(node_p_omnet, monitor, 'status', 'packets_sent', 'packets_received', 'packets_dropped', 'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)