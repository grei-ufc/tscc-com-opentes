# Co-Simulação PADE + OMNeT++ + Mosaik

**Grupo de Redes Elétricas Inteligentes (GREI) — Universidade Federal do Ceará (UFC)**

Plataforma de co-simulação que integra três ferramentas de diferentes domínios em containers Docker: **PADE** (camada cognitiva de agentes FIPA-ACL), **OMNeT++** (simulação de rede de comunicação por eventos discretos em C++) e **Mosaik** (orquestrador de co-simulação). A comunicação entre Mosaik e OMNeT++ usa **ZeroMQ REQ/REP**.

---

## Sumário

- [Arquitetura](#arquitetura)
- [Topologias suportadas](#topologias-suportadas)
- [Tecnologias de rede](#tecnologias-de-rede)
- [Estrutura de diretórios](#estrutura-de-diretórios)
- [Pré-requisitos](#pré-requisitos)
- [Como executar](#como-executar)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Interface web (Streamlit)](#interface-web-streamlit)
- [Dashboards gerados](#dashboards-gerados)
- [Validação e testes automatizados](#validação-e-testes-automatizados)
- [Débitos técnicos resolvidos](#débitos-técnicos-resolvidos)

---

## Arquitetura

A co-simulação é composta por três containers que rodam simultaneamente e se comunicam via rede Docker interna (`sim_net`):

```
┌─────────────────────────────────────────────────────────────┐
│  menu-streamlit.py / menu.py ── env vars ── docker compose  │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┼───────────────────────┐
        │                      │                       │
  ┌─────▼──────┐       ┌───────▼──────┐       ┌───────▼───────┐
  │    pade    │       │  omnet_sim   │       │ mosaik_master │
  │            │       │              │       │               │
  │ PADE       │◄─────►│ OMNeT++ 6.0  │◄─────►│ Mosaik 3.6    │
  │ Twisted    │  TCP  │ C++ eventos  │  ZMQ  │ scenario.py   │
  │ FIPA-ACL   │       │ discretos    │       │ lock-step     │
  │ porta 5678 │       │ porta 5555   │       │               │
  └────────────┘       └──────────────┘       └───────────────┘
```

### Fluxo de dados por passo de simulação

```
PADE (agentes)          Mosaik (orquestrador)         OMNeT++ (física)
    │                         │                             │
    │── val_out (JSON ACL) ──►│── step(inputs) ────────────►│
    │                         │                             │── simula canal ──
    │◄── val_in (JSON ACL) ───│◄── get_data(outputs) ───────│
    │                         │                             │
```

1. Cada agente PADE serializa mensagens FIPA-ACL em JSON e escreve de forma síncrona em `val_out`
2. O Mosaik entrega `val_out` ao nó correspondente no OMNeT++ via `MosaikBridge.cc`
3. O OMNeT++ simula latência, atraso de propagação espacial, jitter, perda por PER/BER e buffer overflow do canal físico
4. O resultado retorna em `val_in` para o agente PADE no próximo passo (`time_shifted=True`)

O padrão **REQ/REP bloqueante** do ZeroMQ garante que Mosaik e OMNeT++ nunca avançam em passos diferentes — o sincronismo é garantido **por construção** e auditado passo a passo via `mosaik_step`.

---

## Topologias suportadas

| Topologia | Script PADE | Script Mosaik | Script de Plotagem | Agentes | Comportamento PADE |
|---|---|---|---|---|---|
| `estrela` | `pade_star.py` | `scenario.py` | `plot_results_star.py` | 1 central + N periféricos | Central faz broadcast; periféricos respondem ao central |
| `malha` | `pade_malha.py` | `scenario.py` | `plot_results_malha.py` | N agentes peers | Todos enviam para todos a cada passo (full mesh) |
| `anel` | `pade_anel.py` | `scenario.py` | `plot_results_anel.py` | N agentes peers | Cada agente envia para os dois vizinhos adjacentes |

**Contagem de agentes:**
- `estrela`: `NUM_PERIFERICOS` define os periféricos; total = `NUM_PERIFERICOS + 1`
- `malha` e `anel`: `NUM_PERIFERICOS` define o **total** de agentes (`N` peers)

**Contagem de enlaces no OMNeT++:**
- Estrela: $N$ enlaces (linear)
- Anel: $N$ enlaces (linear, ciclo fechado bidirecional)
- Malha: $N(N-1)/2$ enlaces (quadrático — atenção ao desempenho com $N$ grande)

---

## Tecnologias de rede

Definidas em `omnet-dir/Profiles.ned` e selecionáveis pelo usuário:

| Nome | Identificador NED | Banda | Delay | PER |
|---|---|---|---|---|
| Cabeada | `Link_Wired` | 1 Gbps | 1 ms fixo | 0% |
| 5G | `Link_5G` | 500 Mbps | truncnormal(5ms, 1ms) | 0,001% |
| Wireless | `Link_Wireless` | 300 Mbps | truncnormal(2ms, 0,5ms) | 0,1% |
| 4G | `Link_4G` | 50 Mbps | truncnormal(35ms, 8ms) | 0,5% |
| 2G | `Link_2G` | 250 kbps | exponential(200ms) | 15% |

Os tipos de enlace são atribuídos ciclicamente aos enlaces gerados (ou individualmente por agente no menu web para Estrela e Anel) e persistidos em `omnet-dir/links.json`.

### Física de rede simulada (`AgentNode.cc`)

O módulo C++ implementa cinco efeitos físicos realistas:

- **Buffer overflow**: fila limitada a 5 pacotes por porta; excedente é descartado e contabilizado em `packets_dropped`
- **PER nativo do canal (`pkt->hasBitError()`)**: avalia a taxa de erro de pacote parametrizada em `Profiles.ned`
- **BER espacial e escalonado por payload**: `finalDropChance = min(0.99, baseDropChance × max(1.0, tamanho/15000))`
- **Atraso por distância e Jitter dinâmico**: `propagationDelay = dist × 0.00005` somado ao delay base do canal (`cDatarateChannel`/`cDelayChannel`), com variação estocástica de jitter por pacote
- **RNG configurável**: `std::mt19937` inicializado via `RANDOM_SEED` (reprodutibilidade científica) ou `std::random_device` (entropia de hardware)

---

## Estrutura de diretórios

```
tscc-com-opentes/
├── menu-streamlit.py              # Interface web (Streamlit) — ponto de entrada recomendado
├── menu.py                        # Interface interativa de linha de comando (CLI)
├── docker-compose.yml             # Orquestração dos três containers
├── server-svgrepo-com.svg         # Ícone servidor (usado na interface)
├── laptop-minimalistic-svgrepo-com.svg  # Ícone PC periférico
├── router-bottom-1112-svgrepo-com.svg   # Ícone roteador
├── LOGO.png                       # Logotipo GREI
│
├── pade-dir/
│   ├── Dockerfile
│   └── pade_agents/
│       ├── pade_star.py           # Agentes para topologia estrela
│       ├── pade_malha.py          # Agentes para topologia malha (full mesh)
│       └── pade_anel.py           # Agentes para topologia anel
│
├── omnet-dir/
│   ├── Dockerfile
│   ├── AgentNode.cc               # Módulo C++: física de rede realista
│   ├── AgentNode.ned              # Definição NED do nó
│   ├── MosaikBridge.cc            # Ponte ZeroMQ entre OMNeT++ e Mosaik
│   ├── Profiles.ned               # Perfis de canal (5 tecnologias)
│   ├── omnetpp.ini                # Configuração da simulação
│   ├── DynamicNetwork.ned         # Gerado dinamicamente pelo scenario.py
│   ├── posicoes.json              # Coordenadas geográficas dos nós (gerado)
│   ├── config.json                # Metadados da execução (gerado)
│   └── links.json                 # Mapeamento enlace→tecnologia (gerado)
│
├── mosaik-dir/
│   ├── Dockerfile
│   ├── scenario.py                # Orquestrador: monta qualquer topologia
│   ├── collector.py               # Coleta métricas de cada nó em results.csv
│   ├── omnet_wrapper.py           # Adaptador Mosaik ↔ OMNeT++
│   ├── plot_results_star.py       # Dashboard matplotlib para estrela
│   ├── plot_results_malha.py      # Dashboard matplotlib para malha
│   ├── plot_results_anel.py       # Dashboard matplotlib para anel
│   └── results.csv                # Dados brutos coletados (gerado)
│
└── tests/
    └── test_validation_suite.py   # Suíte de testes automatizados (C++ e co-simulação E2E)
```

---

## Pré-requisitos

- **Docker** ≥ 24 e **Docker Compose** ≥ 2.20
- **Python** ≥ 3.10 (para rodar a interface Streamlit/CLI ou os testes locais)
- `streamlit`, `plotly` instalados no host: `pip install streamlit plotly`

---

## Como executar

### Via interface web (recomendado)

```bash
git clone https://github.com/grei-ufc/tscc-com-opentes.git
cd tscc-com-opentes
streamlit run menu-streamlit.py
```

Acesse `http://localhost:8501`, configure topologia, número de agentes e tipos de enlace, e clique em **Iniciar simulação**. Os gráficos aparecem automaticamente na aba **Resultados** ao término.

### Via terminal (CLI)

```bash
python3 menu.py
```

O menu interativo em terminal permite escolher a topologia (`1=Estrela`, `2=Malha`, `3=Anel`), quantidade de agentes e tecnologias de enlace (`1..5`), exibindo o resumo antes de disparar `docker compose up --build`. Para encerrar os containers:

```bash
python3 menu.py --parar
```

---

## Variáveis de ambiente

Injetadas via `docker-compose.yml` a partir das escolhas feitas no menu:

| Variável | Valores válidos | Padrão | Descrição |
|---|---|---|---|
| `TOPOLOGY` | `estrela`, `malha`, `anel` | `estrela` | Topologia da rede |
| `NUM_PERIFERICOS` | 1 – 500 | `3` | Periféricos (estrela) ou total de agentes (malha/anel) |
| `TIPOS_REDE` | Lista separada por vírgula | todos os 5 tipos | Tecnologias de enlace disponíveis na simulação |
| `RANDOM_SEED` | Inteiro opcional | vazio (hardware RNG) | Semente determinística para reprodutibilidade em Python e C++ |
| `SIM_STEPS` | Inteiro ≥ 2 | `20` | Quantidade de passos discretos da co-simulação no Mosaik |

---

## Dashboards gerados

Todos os scripts de plotagem (`plot_results_star.py`, `plot_results_malha.py`, `plot_results_anel.py`) utilizam `links.json`, `posicoes.json` e `config.json` para gerar painéis executivos de 6 visões em `mosaik-dir/`:

| Arquivo | Conteúdo |
|---|---|
| `grafico_trafego_Geral.png` | Visão consolidada de todas as tecnologias ativas |
| `grafico_trafego_Cabeada.png` | Latência, payload, jitter, PDR, tabela e mapa da rede Cabeada |
| `grafico_trafego_5G.png` | Idem para 5G |
| `grafico_trafego_Wireless.png` | Idem para Wireless |
| `grafico_trafego_4G.png` | Idem para 4G |
| `grafico_trafego_2G.png` | Idem para 2G |
| `grafico_trafego_Anel.png` | Visão dedicada por Agente Roteador P2P para a topologia em Anel |

---

## Validação e testes automatizados

Para executar a suíte de validação automatizada (compilação e teste da física C++ `AgentNode.cc`/`MosaikBridge.cc` + co-simulação integrada fim a fim para `estrela`, `malha` e `anel` + validação dos dashboards):

```bash
pytest -v tests/test_validation_suite.py
```

---

## Débitos técnicos resolvidos

| Item | Solução implementada |
|---|---|
| Classificação de enlace nos dashboards | `scenario.py` persiste `omnet-dir/links.json` e todos os scripts (`star`, `malha`, `anel`) consultam o mapa real de enlaces |
| Alinhamento de `time_resolution` e `mosaik_step` | `MosaikBridge.cc` lê `time` e `time_resolution` do JSON de `step` e retorna `"mosaik_step": currentMosaikStep` no ACK ZMQ |
| Semântica unificada de `NUM_PERIFERICOS` | Unificada entre `menu.py`, `menu-streamlit.py`, `scenario.py` e scripts PADE (`N+1` na estrela; `N` total na malha e no anel) |
| Física de canal `cDatarateChannel` e `PER` | `AgentNode.cc` manipula `cDatarateChannel`/`cDelayChannel` via `par("delay")` e verifica `pkt->hasBitError()` além do BER espacial |
| Sincronismo de envio em memória no PADE | Removidos timers `call_later` assíncronos de parede em `pade_star.py` e `pade_malha.py` em favor de escrita síncrona em `val_out` no passo `t` |
