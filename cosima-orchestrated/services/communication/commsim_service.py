import argparse
import os
import mosaik_api

from cosima_core.simulators.communication_simulator import CommunicationSimulator
from cosima_core.util.util_functions import check_omnet_connection
import cosima_core.util.general_config as cfg


def start(sim, port: int):
    try:
        mosaik_api.start_simulation(sim, port=port)
    except TypeError:
        mosaik_api.start_simulation(sim, ('0.0.0.0', port))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("MOSAIK_PORT", "5560")))
    args = parser.parse_args()

    # garante que o OMNeT++ está acessível (host remoto via env)
    check_omnet_connection(cfg.PORT)

    start(CommunicationSimulator(), args.port)


if __name__ == "__main__":
    main()
