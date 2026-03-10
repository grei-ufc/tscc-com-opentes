# Dynamic Mosaik-OMNeT++ Co-Simulation Environment

A robust, dynamic co-simulation framework connecting Python's Mosaik scenario manager with the C++ OMNeT++ discrete event network simulator. This environment enables advanced simulations where Python controls the high-level scenario and injects real-time parameters into a detailed, dynamic network model simulated by C++.

The communication is built on ZeroMQ sockets, ensuring synchronized, lock-step execution across Docker containers.

## Architecture Diagram

The diagram below illustrates the dynamic interaction between the Python (Mosaik) and C++ (OMNeT++) worlds. It visualizes the flow of command execution (CREATE, CONNECT, STEP), parameter injection (`15.0`), internal OMNeT++ network events, and real-time telemetry collection into a CSV file.

![Architecture Diagram](https://your-repository-url-path/image_0.png)
*(Note: Replace this placeholder link with the actual path to your image in your repository)*

### Key Architecture Features:

1.  **Hybrid Environment:** C++ manages the specialized network logic (latencies, packets) while Python manages the dynamic scenario and logic agents.
2.  **Dynamic Network Construction:** Nodes (`NetworkNode`) and channels (`cIdealChannel`) are instantiated and connected *at runtime* via ZMQ commands from Python, without needing pre-defined `.ned` network structures.
3.  **Real-Time Parameter Injection:** The framework uses OMNeT++ `@mutable` parameter annotations to inject Python values (e.g., `15.0`) directly into C++ objects during the simulation loop.
4.  **Lock-Step Synchronization:** A custom ZMQ bridge (`MosaikBridge.cc`) ensures that the OMNeT++ simulation time advances only when commanded by Mosaik, keeping both worlds perfectly in sync.

## Prerequisites

* [Docker](https://www.docker.com/) and Docker Compose
* (Optional, for direct editing) Git and CMake

## Directory Structure

* `docker-compose.yml`: Orchestrates the containers.
* `mosaik-dir/`: Python Mosaik Master Cluster.
    * `Dockerfile`: Builds the Python image with ZMQ.
    * `main.py`: The main Mosaik scenario definition (orchestrator).
    * `omnet_wrapper.py`: The Python ZMQ client adapter for Mosaik.
    * `controller.py`: The `TrafficGenerator` agent, injecting data.
    * `collector.py`: The `DataCollector` agent, writing to CSV.
* `omnet-dir/`: C++ OMNeT++ Simulation Cluster.
    * `Dockerfile`: Builds the OMNeT++ image with dynamic C++17 compilation.
    * `Network.ned`: A largely empty network container for dynamic creation.
    * `NetworkNode.ned`: Definition of the dynamic node, including gates and `@mutable` parameters.
    * `MosaikBridge.cc` / `.h`: The C++ ZMQ Server, handling all dynamic creation and stepping.
    * `NetworkNode.cc` / `.h`: The C++ logic for handling mutable parameters and generating packets.
    * `omnetpp.ini`: Basic OMNeT++ configuration.

## Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/your-repository-name.git](https://github.com/yourusername/your-repository-name.git)
    cd your-repository-name
    ```

2.  **Build and run the containers:**
    ```bash
    docker-compose up --build
    ```
    *The `--build` flag is required only when C++ code has changed.*

3.  **Check the output:**
    A file named `results.csv` will be generated in the `mosaik-dir/` directory, containing the data flow results collected in real-time.

## System Workflow Example

1.  **Mosaik (Python)** sends a `CREATE` command.
2.  **OMNeT++ (C++)** dynamically instantiates `node_0`.
3.  **Mosaik (Python)** sends a `STEP` command with data (e.g., `15.0`).
4.  **OMNeT++ (C++)** sets `node_0.@mutable data_in = 15.0` and advances time 1 second.
5.  **OMNeT++ (C++)** internal logic detects the data change, generates a packet (`Pacote_Mosaik-1`), and sends it to `node_1`. It updates its `@mutable data_out = 1.0`.
6.  **OMNeT++ (C++)** sends the `STEP` response with telemetry.
7.  **Mosaik (Python)** receives `data_out = 1.0` and writes it to `results.csv`.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please feel free to open a pull request.
