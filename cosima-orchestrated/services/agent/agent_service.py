import os
import inspect
import mosaik_api

from cosima_core.simulators.tutorial.simple_agent_simulator import SimpleAgent


def start_server(sim, host: str, port: int):
    fn = mosaik_api.start_simulation
    params = inspect.signature(fn).parameters

    if 'port' in params:
        return fn(sim, port=port)
    if 'address' in params:
        return fn(sim, address=(host, port))
    if 'addr' in params:
        return fn(sim, addr=(host, port))

    # fallback: algumas versões usam 'host' e 'port'
    if 'host' in params and 'port' in params:
        return fn(sim, host=host, port=port)

    raise RuntimeError(f"mosaik_api.start_simulation signature not supported: {inspect.signature(fn)}")


if __name__ == "__main__":
    host = os.getenv("MOSAIK_HOST", "0.0.0.0")
    port = int(os.getenv("MOSAIK_PORT", "5550"))
    start_server(SimpleAgent(), host, port)
