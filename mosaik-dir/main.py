import mosaik
import os

# Configuração: apontamos para o nosso OMNeT++ e conectamos ao servidor nativo do PADE
SIM_CONFIG = {
    'OmnetSim': {
        'python': 'omnet_wrapper:OmnetAdapter'
    },
    'ColetorSim': { 
        'python': 'collector:Coletor' 
    },
    'PadeSim': {
        # Remova o "_container", deixe apenas "pade"
        'connect': 'pade:5678' 
    }
}
def main():
    world = mosaik.World(SIM_CONFIG)

    # 1. Inicia/Conecta os Simuladores
    omnet_sim = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim = world.start('PadeSim') # Conecta ao PADE nativo

    # 2. Instancia os Modelos (As entidades)
    # ATENÇÃO: Verifique no 'mosaik_example' qual o nome exato do modelo e atributo 
    # que o PADE expõe (geralmente é 'Agent', 'msg_out' e 'msg_in')
    agente_a = pade_sim.Agent(agent_id='AgenteA')
    agente_b = pade_sim.Agent(agent_id='AgenteB')
    
    rede_omnet = omnet_sim.NetworkNode(node_id='RedePrincipal')
    monitor = coletor_sim.Monitor()

    # 3. A INTERCEPTAÇÃO (O seu objetivo!)
    # Em vez de Agente A -> Agente B direto, fazemos:
    
    # A) PADE envia para a Rede
    world.connect(agente_a, rede_omnet, 'val_out', 'val_in')
    
    # B) Rede calcula o delay e envia de volta ao PADE
    world.connect(rede_omnet, agente_b, 'val_out', 'val_in')

    # Monitoria do OMNeT++
    world.connect(rede_omnet, monitor, 'status', 'packets_sent', 'last_latency')

    # 4. Roda a co-simulação
    world.run(until=10)

if __name__ == '__main__':
    main()