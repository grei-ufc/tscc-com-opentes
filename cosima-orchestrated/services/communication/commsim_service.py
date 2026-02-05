import os
import inspect
import mosaik_api

import cosima_core.util.general_config as cfg
from cosima_core.util.util_functions import check_omnet_connection
from cosima_core.simulators.communication_simulator import CommunicationSimulator


def start_server(sim, host: str, port: int):
    fn = mosaik_api.start_simulation
    params = inspect.signature(fn).parameters

    if 'port' in params:
        return fn(sim, port=port)
    if 'address' in params:
        return fn(sim, address=(host, port))
    if 'addr' in params:
        return fn(sim, addr=(host, port))
    if 'host' in params and 'port' in params:
        return fn(sim, host=host, port=port)

    raise RuntimeError(f"mosaik_api.start_simulation signature not supported: {inspect.signature(fn)}")


if __name__ == "__main__":
    # garante OMNeT++ acessível via OMNET_HOST/OMNET_PORT
    check_omnet_connection(cfg.PORT)

    host = os.getenv("MOSAIK_HOST", "0.0.0.0")
    port = int(os.getenv("MOSAIK_PORT", "5560"))
    start_server(CommunicationSimulator(), host, port)
