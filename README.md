
# 🚀 TSCC: Co-Simulação PADE + OMNeT++ + Mosaik

![Docker](https://img.shields.io/badge/Docker-%E2%89%A5%2024.x-blue)
![Compose](https://img.shields.io/badge/Docker%20Compose-V2-blue)
![Status](https://img.shields.io/badge/status-active-success)

Ambiente de **co-simulação distribuída** que integra:

- 🤖 **PADE (Python)** → Agentes inteligentes
- 🌐 **OMNeT++ (C++)** → Simulação de rede
- 🔄 **Mosaik** → Orquestração e sincronização

A comunicação é realizada via **ZeroMQ (ZMQ)** com sincronização em **lock-step**, garantindo consistência temporal entre os simuladores.

---

## 📑 Sumário

- [🧠 Arquitetura](#-arquitetura)
- [📂 Estrutura do Projeto](#-estrutura-do-projeto)
- [🛠️ Pré-requisitos](#️-pré-requisitos)
- [⚙️ Instalação](#️-instalação)
- [🚀 Execução](#-execução)
- [📊 Resultados](#-resultados)
- [🧰 Comandos Úteis](#-comandos-úteis)

---

## 🧠 Arquitetura

O sistema executa uma co-simulação sincronizada entre:

1. **PADE**: agentes Python que produzem e consomem eventos.
2. **Mosaik**: orquestra a simulação e injeção de rede.
3. **OMNeT++**: simula a topologia de rede e o comportamento de pacotes.

### 🔄 Fluxo da Simulação

1. **PADE → Mosaik**
   - Agentes enviam mensagens e eventos para o orquestrador.
2. **Mosaik → OMNeT++**
   - A rede dinâmica é gerada/injetada em `omnet-dir`.
3. **OMNeT++**
   - Compila/simula `sim_exec` e processa a entrega de pacotes.
4. **Resultado**
   - `mosaik_master` coleta dados, gera `results.csv` e plota o tráfego.

---

## 📂 Estrutura do Projeto

```text
tscc-com-opentes/
├── docker-compose.yml
├── mosaik-dir/
│   ├── collector.py
│   ├── first.py
│   ├── omnet_wrapper.py
│   ├── plot_results.py
│   ├── plot_results_star.py
│   ├── results.csv
│   ├── star.py
│   └── grafico_trafego.png
├── pade-dir/
│   ├── Dockerfile
│   └── pade_agents/
│       ├── agent_a.py
│       ├── agent_example_1_mosaik_updated.py
│       ├── pade_sim.py
│       └── pade_star.py
└── omnet-dir/
    ├── Dockerfile
    ├── AgentNode.cc
    ├── AgentNode.ned
    ├── AgentPacket.msg
    ├── AgentPacket_m.cc
    ├── AgentPacket_m.h
    ├── DynamicNetwork.ned
    ├── Makefile
    ├── MosaikBridge.cc
    ├── Network.ned
    ├── Profiles.ned
    ├── omnetpp.ini
    ├── sim_exec
    └── out/
```

---

## 🛠️ Pré-requisitos

| Ferramenta     | Versão | Obrigatório |
| -------------- | ------ | ----------- |
| Docker         | ≥ 24.x | ✅           |
| Docker Compose | V2     | ✅           |
| Git            | -      | ❌           |

> 💡 Todo o ambiente é containerizado — não é necessário instalar Python, C++ ou OMNeT++ localmente.

---

## ⚙️ Instalação

### 🪟 Windows

```powershell
winget install Git.Git
winget install Docker.DockerDesktop
```

> ⚠️ Certifique-se de que o Docker Desktop está em execução.

---

### 🐧 Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install git docker.io docker-compose-plugin
```

**(Opcional) Rodar sem sudo:**

```bash
sudo usermod -aG docker $USER
```

---

## 🚀 Execução

### 1. Clonar repositório

```bash
git clone https://github.com/grei-ufc/tscc-com-opentes.git
cd tscc-com-opentes
```

### 2. Subir o ambiente

```bash
docker compose up --build
```

### 3. Como funciona

- `pade`
  - Executa `python3 pade_star.py` dentro do container.
  - Expõe a porta `5678`.
  - Usa a variável `NUM_PERIFERICOS=50` para controlar escala.
- `omnet_sim`
  - Compila o modelo OMNeT++ com `opp_makemake` e `make`.
  - Aguarda até que `DynamicNetwork.ned` seja gerado em `omnet-dir`.
  - Executa `./sim_exec -u Cmdenv -c General`.
- `mosaik_master`
  - Instala `pandas` e `matplotlib` em runtime.
  - Executa `star.py` e `plot_results_star.py`.
  - Mapeia `omnet-dir` para permitir a geração de `DynamicNetwork.ned`.

---

## 📊 Resultados

Após a execução, os principais artefatos gerados são:

- `mosaik-dir/results.csv`
- `mosaik-dir/grafico_trafego.png`

### Métricas típicas

- Latência
- Tamanho de pacote

### Observação

O `mosaik_master` também gera gráficos de tráfego e processa os resultados após a simulação.

---

## 🧰 Comandos Úteis

### ▶️ Executar novamente

```bash
docker compose up
```

### 🛑 Parar e limpar

```bash
docker compose down
```

---

## 📌 Observações

- `NUM_PERIFERICOS=50` pode ser ajustado no `docker-compose.yml` para variar a escala.
- `omnet_sim` depende de `DynamicNetwork.ned` para iniciar a simulação de rede.
- O serviço `mosaik_master` usa o volume `./omnet-dir:/omnet-dir` para injetar arquivos de rede.
