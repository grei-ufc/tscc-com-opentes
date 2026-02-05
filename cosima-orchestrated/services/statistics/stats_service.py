import argparse
import os
import mosaik_api

from cosima_core.simulators.statistics_simulator import StatisticsSimulator


def start(sim, port: int):
    try:
        mosaik_api.start_simulation(sim, port=port)
    except TypeError:
        mosaik_api.start_simulation(sim, ('0.0.0.0', port))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("MOSAIK_PORT", "5570")))
    args = parser.parse_args()
    start(StatisticsSimulator(), args.port)


if __name__ == "__main__":
    main()
