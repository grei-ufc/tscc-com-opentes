import mosaik
import scenario_config as scfg
import cosima_core.util.general_config as cfg

SIMULATION_END = scfg.SIMULATION_END
NETWORK = scfg.NETWORK
NUM_CLIENTS = scfg.NUMBER_OF_AGENTS

CONTENT_PATH = cfg.ROOT_PATH / 'simulators' / 'tic_toc_example' / 'content.csv'

SIM_CONFIG = {
    'Agent0': {'connect': 'agent0:5550'},
    'Agent1': {'connect': 'agent1:5551'},
    'Agent2': {'connect': 'agent2:5552'},
    'Agent3': {'connect': 'agent3:5553'},

    'CommunicationSimulator': {'connect': 'commsim:5560'},
    'StatisticsSimulator': {'connect': 'stats:5570'},
}

world = mosaik.World(SIM_CONFIG, time_resolution=0.001, cache=False)

client_attribute_mapping = {
    f'client{i}': f'message_with_delay_for_client{i}'
    for i in range(NUM_CLIENTS)
}

agents = []
for i in range(NUM_CLIENTS):
    agent = world.start(
        f'Agent{i}',
        content_path=CONTENT_PATH,
        client_name=f'client{i}',
        neighbor=None
    ).SimpleAgentModel()
    agents.append(agent)

comm_sim = world.start(
    'CommunicationSimulator',
    step_size=1,
    port=4242,  # cfg.PORT confirmado por você
    client_attribute_mapping=client_attribute_mapping
).CommunicationModel()

stat_sim = world.start(
    'StatisticsSimulator',
    network=NETWORK,
    save_plots=True
).Statistics()

for i, agent in enumerate(agents):
    world.connect(agent, comm_sim, 'message', weak=True)
    world.connect(comm_sim, agent, client_attribute_mapping[f'client{i}'])

    # se seu stats não expõe 'message', comente esta linha
    world.connect(agent, stat_sim, 'message', time_shifted=True, initial_data={'message': None})

for agent in agents:
    world.set_initial_event(agent.sid, time=0)

world.run(until=SIMULATION_END)
