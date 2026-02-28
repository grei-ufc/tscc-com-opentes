"""
COSIMA server simulation script
Receives scenario from Mosaik, simulates em OMNeT++, returns metrics.
"""

import socket
import json
from pathlib import Path
from time import sleep
import mosaik
from cosima_core.util.util_functions import start_omnet, check_omnet_connection, stop_omnet, log
import cosima_core.util.general_config as cfg

HOST = '0.0.0.0'
PORT = cfg.PORT  # porta que COSIMA vai ouvir do Mosaik

def run_simulation(scenario):
    """Executa a simulação do exemplo 01 baseado no cenário recebido"""
    SIMULATION_END = scenario.get('simulation_end', 2000)
    NUM_AGENTS = scenario.get('num_agents', 2)
    MESSAGE_SIZE = scenario.get('message_size', 512)
    
    # Escolher rede e conteúdo
    NETWORK = 'SimpleNetworkTCP'
    CONTENT_PATH = cfg.ROOT_PATH / 'simulators' / 'tic_toc_example' / 'content.csv'

    # --- Configuração mosaik ---
    SIM_CONFIG = {
        'SimpleAgent': {
            'python': 'cosima_core.simulators.tutorial.simple_agent_simulator:SimpleAgent',
        },
        'CommunicationSimulator': {
            'python': 'cosima_core.simulators.communication_simulator:CommunicationSimulator',
        },
        'StatisticsSimulator': {
            'python': 'cosima_core.simulators.statistics_simulator:StatisticsSimulator',
        }
    }

    # --- Start OMNeT++ ---
    omnet_process = start_omnet('cmd', NETWORK)
    check_omnet_connection(cfg.PORT)

    world = mosaik.World(SIM_CONFIG, time_resolution=0.001, cache=False)

    client_mapping = {f'client{i}': f'message_with_delay_for_client{i}' for i in range(NUM_AGENTS)}

    # --- Criar agentes ---
    agents = []
    for i in range(NUM_AGENTS):
        neighbor = f'client{(i+1)%NUM_AGENTS}'
        agent = world.start('SimpleAgent',
                            content_path=CONTENT_PATH,
                            client_name=f'client{i}',
                            neighbor=neighbor).SimpleAgentModel()
        agents.append(agent)

    # --- Communication Simulator ---
    comm_sim = world.start('CommunicationSimulator',
                           step_size=1,
                           port=cfg.PORT,
                           client_attribute_mapping=client_mapping).CommunicationModel()

    # --- Statistics Simulator ---
    stat_sim = world.start('StatisticsSimulator', network=NETWORK, save_plots=False).Statistics()

    # --- Conexões ---
    for i, agent in enumerate(agents):
        client_name = f'client{i}'
        world.connect(agent, comm_sim, 'message', weak=True)
        world.connect(comm_sim, agent, client_mapping[client_name])
        world.connect(agent, stat_sim, 'message', time_shifted=True, initial_data={'message': None})
        world.connect(stat_sim, agent, 'stats')

    # --- Evento inicial ---
    world.set_initial_event(agents[0].sid, time=0)

    # --- Executar simulação ---
    log(f"Running simulation for {SIMULATION_END} steps")
    world.run(until=SIMULATION_END)
    log("Simulation finished")

    # --- Coletar métricas ---
    metrics = {f'client{i}_stats': stat_sim.get_stats(f'client{i}') for i in range(NUM_AGENTS)}

    stop_omnet(omnet_process)
    return metrics


def main():
    """Server COSIMA que recebe cenário do Mosaik e devolve métricas"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        log(f"COSIMA listening on port {PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                log(f"Connected by {addr}")
                data = conn.recv(1024)
                if not data:
                    continue
                scenario = json.loads(data.decode())
                log(f"Received scenario: {scenario}")

                try:
                    metrics = run_simulation(scenario)
                except Exception as e:
                    metrics = {'error': str(e)}

                # Enviar métricas de volta ao Mosaik
                conn.sendall(json.dumps(metrics).encode())
                log("Metrics sent back to Mosaik")


if __name__ == "__main__":
    main()