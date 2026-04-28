
# 🚀 TSCC: Co-Simulação PADE + OMNeT++ + Mosaik

![Docker](https://img.shields.io/badge/Docker-%E2%89%A5%2024.x-blue)
![Compose](https://img.shields.io/badge/Docker%20Compose-V2-blue)
![Status](https://img.shields.io/badge/status-active-success)

Ambiente avançado de **co-simulação distribuída** que integra:

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

O sistema implementa uma integração cíclica com **Física de Rede Dinâmica**:

### 🔄 Fluxo da Simulação

1. **PADE → Mosaik**  
   Agentes enviam mensagens **FIPA-ACL (JSON)** ao Mosaik

2. **Mosaik → OMNeT++**  
   Mensagens são injetadas na rede simulada

3. **Processamento de Rede (C++)**  
```

Latência = Atraso de Propagação + (Tamanho em bits / Largura de Banda)

````

4. **Entrega sincronizada**  
Mensagens são liberadas no tempo correto (**lock-step**)

---

## 📂 Estrutura do Projeto

```text
tscc-com-opentes/
├── docker-compose.yml
│
├── mosaik-dir/
│   ├── first.py
│   ├── collector.py
│   └── plot_results.py
│
├── pade-dir/
│   ├── Dockerfile
│   └── agent_example.py
│
└── omnet-dir/
 ├── Dockerfile
 ├── MosaikBridge.cc
 └── NetworkNode.cc
````

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

---

### 🔄 Inicialização automática

| Serviço         | Função                                     |
| --------------- | ------------------------------------------ |
| `omnet_sim`     | Compila e inicia servidor ZMQ (porta 5555) |
| `pade`          | Inicializa agentes (porta 5678)            |
| `mosaik_master` | Orquestra e executa a simulação            |

---

## 📊 Resultados

Após a execução (`Simulation finished successfully`):

### 📄 Arquivos gerados

* **`results.csv`**
  Métricas por passo de simulação:

  * Latência
  * Tamanho de pacote

* **`grafico_trafego.png`**

### 📈 Visualizações

* 📦 **Tamanho do Pacote**
  Comportamento ping-pong (ex: 113 ↔ 101 bytes)

* ⏱️ **Latência**
  Demonstra impacto do tamanho do pacote no atraso

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

* Arquitetura baseada em **co-simulação sincronizada**
* Comunicação desacoplada via **ZeroMQ**
* Totalmente reprodutível via Docker

---

## 📄 Licença


