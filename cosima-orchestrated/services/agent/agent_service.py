import argparse
import os
import mosaik_api

from cosima_core.simulators.tutorial.simple_agent_simulator import SimpleAgent


def start(sim, port: int):
    # compatibilidade com versões diferentes do mosaik_api
    try:
        mosaik_api.start_simulation(sim, port=port)
    except TypeError:
        mosaik_api.start_simulation(sim, ('0.0.0.0', port))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("MOSAIK_PORT", "5550")))
    args = parser.parse_args()
    start(SimpleAgent(), args.port)


if __name__ == "__main__":
    main()
