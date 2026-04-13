# Branch development - TSCC
Um ambiente de co-simulação que conecta o gerenciador de cenários **Mosaik** (Python) ao simulador de eventos discretos **OMNeT++** (C++), a comunicação é construída sobre sockets **ZeroMQ (ZMQ)** e em lock-step entre os contêineres Docker.

### Estrutura

```
tscc-com-opentes/
├── docker-compose.yml              # Orquestra os dois contêineres
│
├── mosaik-dir/                     # Lado Python / Mosaik
│   ├── Dockerfile                  # Imagem Python com ZMQ e Mosaik
│   ├── main.py                     # Orquestrador principal: topologia, conexões, world.run()
│   ├── omnet_wrapper.py            # Adaptador Mosaik Simulator — cliente ZMQ para o OMNeT++
│   ├── controller.py               # Agente TrafficGen: injeta data_in; adapta taxa via feedback
│   ├── collector.py                # Agente Monitor: grava telemetria em results.csv
│   ├── plot_results.py             # Gera grafico_trafego.png a partir do results.csv
│   └── results.csv                 # Saída: telemetria em série temporal (gerado em execução)
│
└── omnet-dir/                      # Lado C++ / OMNeT++
    ├── Dockerfile                  # Imagem OMNeT++ com ZMQ e nlohmann/json
    ├── Makefile                    # Regras de build (gerado pelo opp_makemake)
    ├── omnetpp.ini                 # Configuração da simulação: rede, scheduler, limite de tempo
    ├── Network.ned                 # Contêiner de rede de alto nível (nós adicionados dinamicamente)
    ├── NetworkNode.ned             # Definição do nó: gates, parâmetros @mutable
    ├── MosaikBridge.cc             # Servidor ZMQ REP: protocolo CREATE / CONNECT / STEP
    ├── NetworkNode.cc              # Lógica do nó: geração de pacotes, tratamento de @mutable
    └── sim_exec                    # Binário compilado (gerado no build)
```

---

## Pré-requisitos

| Ferramenta | Versão | Observação |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) | ≥ 24.x | Obrigatório |
| [Docker Compose](https://docs.docker.com/compose/) | ≥ 2.x (plugin `compose` v2) | Obrigatório |
| Git | qualquer | Opcional — para clonar o repositório |

Nenhuma instalação local de Python ou C++ é necessária; tudo executa dentro do Docker.

---

## Instalação e Uso
### Windows
### 1.Instalação de Pré-requisitos
```bash
winget install Git.Git
winget install Docker.DockerDesktop
```
Antes de clonar o repositório, abra o software Docker Desktop e deixe com a janela habilitada, pois senão o Docker não conseguirá se conectar à sua API.

### Linux
```bash
sudo apt-get install git
sudo apt-get install docker
sudo apt-get install compose
```

### 2. Clonar o repositório

```bash
git clone https://github.com/grei-ufc/tscc-com-opentes.git
cd tscc-com-opentes
```

### 3. Construir e iniciar os contêineres

```bash
docker-compose up --build
```

A sequência de inicialização é:
1. `omnet_sim` compila e inicia a simulação OMNeT++, aguardando conexões ZMQ na porta `5555`.
2. `mosaik_master` (que depende do `omnet_sim`) instala os pacotes Python e executa `main.py`.

### 4. Verificar a saída

Após a simulação terminar (10 passos por padrão), dois arquivos são gerados:

- `results.csv`
- `grafico_trafego.png`

Para executar novamente sem recompilar o C++:

```bash
docker-compose up
```

Para parar e remover os contêineres:

```bash
docker-compose down
```

---
