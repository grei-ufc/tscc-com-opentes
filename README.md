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
- [Dashboards gerados](#dashboards-gerados)
- [Validação e testes automatizados](#validação-e-testes-automatizados)
- [Gerenciamento de dependências (uv)](#gerenciamento-de-dependências-uv)
- [Histórico de mudanças](#histórico-de-mudanças)

---

## Arquitetura

A co-simulação é composta por três containers que rodam simultaneamente. `omnet_sim` e `mosaik_master` compartilham o namespace de rede do container `pade` (`network_mode: "service:pade"`) e se comunicam por `127.0.0.1`, o que dispensa DNS entre containers e funciona também no Docker-in-Docker do GitHub Codespaces:

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

O framework PADE não está neste repositório: `pade-dir/` contém só o container e os agentes desta co-simulação. O PADE é instalado do PyPI (`pade-agents`), publicado a partir de [grei-ufc/pade](https://github.com/grei-ufc/pade).

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
3. O OMNeT++ roteia cada mensagem até o destinatário (multi-salto quando necessário) e simula latência, atraso de propagação espacial, jitter, perda por PER/BER e buffer overflow em cada salto
4. O resultado retorna em `val_in` para o agente PADE no próximo passo (`time_shifted=True`)

O padrão **REQ/REP bloqueante** do ZeroMQ garante que Mosaik e OMNeT++ nunca avançam em passos diferentes — o sincronismo é garantido **por construção** e auditado passo a passo via `mosaik_step`.

---

## Topologias suportadas

| Topologia | Script PADE | Script de plotagem | Agentes | Comportamento PADE |
|---|---|---|---|---|
| `estrela` | `pade_star.py` | `plot_results_star.py` | 1 central + N periféricos | Central faz poll em todos; periféricos respondem ao central |
| `malha` | `pade_malha.py` | `plot_results_malha.py` | N agentes peers | Todos enviam para todos a cada passo (full mesh) |
| `anel` | `pade_anel.py` | `plot_results_anel.py` | N agentes peers | Cada agente envia para os dois vizinhos adjacentes |
| `arvore` | `pade_arvore.py` | `plot_results_arvore.py` | raiz → subestações → concentradores → medidores | Medidores enviam telemetria à raiz por vários saltos; a raiz faz poll a cada 5 passos; nós intermediários trocam heartbeat |
| `hibrida` | `pade_hibrida.py` | `plot_results_hibrida.py` | CCO → subestações → concentradores → medidores | Igual à árvore, com o CCO no lugar da raiz |

O `mosaik-dir/scenario.py` monta todas as topologias e, ao final da co-simulação, chama o script de plotagem correspondente.

**Contagem de agentes:**
- `estrela`: `NUM_PERIFERICOS` define os periféricos; total = `NUM_PERIFERICOS + 1`
- `malha` e `anel`: `NUM_PERIFERICOS` define o **total** de agentes (`N` peers)
- `arvore`: `ARVORE_FANOUT` define os filhos por nível; com `3,2,4`, total = 1 + 3 + 6 + 24 = 34
- `hibrida`: 1 CCO + `SUBESTACOES` + `SUBESTACOES × CONCENTRADORES` + `SUBESTACOES × CONCENTRADORES × MEDIDORES_CLUSTER`

**Enlaces no OMNeT++:**
- Estrela: $N$ enlaces
- Anel: $N$ enlaces (ciclo fechado bidirecional)
- Malha: $N(N-1)/2$ enlaces (quadrático — atenção ao desempenho com $N$ grande)
- Árvore: um enlace por nó filho; Fibra (raiz→subestação), celular (subestação→concentrador) e PLC (concentrador→medidor)
- Híbrida: anel de Fibra entre subestações + CCO ligado a 2 subestações, celular até os concentradores e malha parcial RFMesh (k vizinhos + garantia de conectividade) em cada cluster de medidores

---

## Tecnologias de rede

Definidas em `omnet-dir/Profiles.ned` (fonte única: o emulador dos testes lê os mesmos valores):

| Nome | Identificador NED | Banda | Delay | PER | Uso |
|---|---|---|---|---|---|
| Cabeada | `Link_Wired` | 1 Gbps | 1 ms fixo | 0% | estrela, malha, anel |
| 5G | `Link_5G` | 500 Mbps | truncnormal(5ms, 1ms) | 0,001% | estrela, malha, anel |
| Wireless | `Link_Wireless` | 300 Mbps | truncnormal(2ms, 0,5ms) | 0,1% | estrela, malha, anel |
| 4G | `Link_4G` | 50 Mbps | truncnormal(35ms, 8ms) | 0,5% | estrela, malha, anel |
| 2G | `Link_2G` | 250 kbps | exponential(200ms) | 15% | estrela, malha, anel |
| Fibra | `Fibra` | 1 Gbps | 0,05 ms | 0% | árvore, híbrida |
| Celular 2G | `Celular2G` | 100 kbps | 500 ms | 2% | árvore, híbrida |
| Celular 3G | `Celular3G` | 2 Mbps | 150 ms | 1% | árvore, híbrida |
| Celular 4G | `Celular4G` | 50 Mbps | 50 ms | 0,5% | árvore, híbrida |
| Celular 5G | `Celular5G` | 200 Mbps | 10 ms | 0,1% | árvore, híbrida |
| RF Mesh | `RFMesh` | 150 kbps | 20 ms | 3% | híbrida |
| PLC | `PLC` | 100 kbps | 30 ms | 2% | árvore |

Em estrela, malha e anel, os tipos de enlace são atribuídos ciclicamente aos enlaces gerados (ou individualmente por agente no menu web) e persistidos em `omnet-dir/links.json`.

### Física de rede simulada (`AgentNode.cc`)

- **Roteamento multi-salto**: tabela estática de próximo salto por caminho mínimo em nº de saltos (BFS); nós intermediários encaminham os pacotes e contabilizam `packets_forwarded`
- **Buffer overflow**: fila limitada a 5 pacotes por porta; excedente é descartado e contabilizado em `packets_dropped`
- **PER nativo do canal (`pkt->hasBitError()`)**: taxa de erro de pacote parametrizada em `Profiles.ned`, avaliada em cada salto
- **BER espacial e escalonado por payload**: chance base de 1,5% a cada 100 m, `finalDropChance = min(0.99, base × max(1.0, tamanho/15000))`; não se aplica a meio guiado (Fibra/Cabeada)
- **Atraso por distância e jitter dinâmico**: propagação de `dist × 0.00005` s (meio guiado: ~5 ns/m) somada ao delay base do canal, com jitter estocástico por pacote
- **RNG configurável**: `std::mt19937` inicializado via `RANDOM_SEED` (reprodutibilidade científica) ou `std::random_device` (entropia de hardware)

---

## Estrutura de diretórios

```
tscc-com-opentes/
├── menu-streamlit.py              # Interface web (Streamlit) — ponto de entrada recomendado
├── menu.py                        # Interface interativa de linha de comando (CLI)
├── docker-compose.yml             # Orquestração dos três containers
├── pyproject.toml                 # Dependências Python (host e containers), gerenciadas pelo uv
├── uv.lock                        # Versões exatas resolvidas pelo uv (não editar à mão)
├── .python-version                # Python 3.12, o mesmo das imagens Docker
├── CHANGELOG.md                   # Histórico de mudanças
├── CONTRIBUTING.md                # Fluxo de branches, dependências e testes
├── assets/                        # Logotipo GREI e ícones SVG usados na interface
│
├── pade-dir/                      # Container PADE (o framework vem do PyPI)
│   ├── Dockerfile
│   ├── requirements.txt           # Exportado do uv.lock (grupo "pade"); não editar à mão
│   └── pade_agents/
│       ├── pade_bridge.py         # Base comum: MosaikSim, tradução ACL↔JSON, AgenteCosim
│       ├── pade_hierarquico.py    # Agente das topologias em camadas (árvore e híbrida)
│       ├── pade_star.py           # Agentes da topologia estrela
│       ├── pade_malha.py          # Agentes da topologia malha (full mesh)
│       ├── pade_anel.py           # Agentes da topologia anel
│       ├── pade_arvore.py         # Agentes da árvore radial IEC 61850
│       ├── pade_hibrida.py        # Agentes da topologia híbrida
│       └── logs/                  # CSVs do data_logger do PADE (gerado)
│
├── omnet-dir/
│   ├── Dockerfile
│   ├── AgentNode.cc               # Módulo C++: física de rede e roteamento
│   ├── AgentNode.ned              # Definição NED do nó
│   ├── MosaikBridge.cc            # Ponte ZeroMQ entre OMNeT++ e Mosaik
│   ├── MosaikBridge.ned           # Declaração NED da ponte
│   ├── AgentPacket.msg            # Pacote trocado entre os nós
│   ├── Profiles.ned               # Perfis de canal (12 tecnologias)
│   ├── omnetpp.ini                # Configuração da simulação
│   ├── DynamicNetwork.ned         # Gerado pelo scenario.py a cada rodada (fora do git)
│   └── posicoes.json, links.json, config.json   # Gerados a cada rodada (fora do git)
│
├── mosaik-dir/
│   ├── Dockerfile
│   ├── requirements.txt           # Exportado do uv.lock (grupo "mosaik"); não editar à mão
│   ├── scenario.py                # Orquestrador: monta qualquer topologia e chama a plotagem
│   ├── collector.py               # Coleta métricas de cada nó em results.csv
│   ├── omnet_wrapper.py           # Adaptador Mosaik ↔ OMNeT++
│   ├── plot_results_*.py          # Dashboards matplotlib (um ponto de entrada por topologia)
│   ├── plot_camadas.py            # Dashboards de árvore e híbrida (implementação comum)
│   ├── plot_comum.py              # Utilitários compartilhados pelos plots
│   └── results.csv, grafico_*     # Saídas de cada rodada (fora do git)
│
├── tests/
│   ├── test_validation_suite.py   # Física C++ + co-simulação E2E nas 5 topologias
│   └── omnet_zmq_emulator.py      # Substituto do OMNeT++ para rodar os testes sem Docker
│
├── examples/legacy/               # Scripts antigos, só como referência (não mantidos)
└── artigo-overleaf/               # Fonte LaTeX do artigo
```

---

## Pré-requisitos

- **Docker** ≥ 24 e **Docker Compose** ≥ 2.20
- **[uv](https://docs.astral.sh/uv/)** para gerenciar o Python e as dependências do host. Não é preciso instalar o Python à parte: o uv baixa o **Python 3.12** indicado em `.python-version`, o mesmo das imagens Docker (o `pade-agents` 3.0 exige Python ≥ 3.12)

Instalação do uv:

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Depois de clonar o repositório, crie o ambiente virtual (`.venv/`) com as versões travadas em `uv.lock`:

```bash
uv sync            # interface + dependências de teste (PADE, Mosaik, pytest)
uv sync --no-dev   # apenas a interface (streamlit, plotly)
```

---

## Como executar

### Via interface web (recomendado)

```bash
git clone https://github.com/grei-ufc/tscc-com-opentes.git
cd tscc-com-opentes
uv sync
uv run streamlit run menu-streamlit.py
```

> `uv run` usa o `.venv/` do projeto sem precisar ativá-lo. Com o ambiente ativado (`source .venv/bin/activate` no Linux/macOS, `.venv\Scripts\activate` no Windows), os comandos antigos continuam valendo: `streamlit run menu-streamlit.py`, `python3 menu.py` e `pytest`.

Acesse `http://localhost:8501`, configure a topologia (estrela, anel, árvore ou híbrida), o número de agentes e os tipos de enlace, e clique em **Iniciar simulação**. Os gráficos aparecem na aba **Resultados** ao término.

### Via terminal (CLI)

```bash
uv run python menu.py
```

O menu interativo em terminal permite escolher a topologia (`1=Estrela`, `2=Malha`, `3=Anel`), a quantidade de agentes e as tecnologias de enlace (`1..5`), exibindo o resumo antes de disparar `docker compose up --build`. Para encerrar os containers:

```bash
uv run python menu.py --parar
```

### Direto pelo Docker Compose

Todas as topologias, inclusive árvore e híbrida, podem ser disparadas pelas variáveis de ambiente:

```bash
TOPOLOGY=arvore ARVORE_FANOUT=3,2,4 docker compose up --build --abort-on-container-exit --exit-code-from mosaik_master
```

---

## Variáveis de ambiente

Injetadas via `docker-compose.yml` a partir das escolhas feitas no menu:

| Variável | Valores válidos | Padrão | Descrição |
|---|---|---|---|
| `TOPOLOGY` | `estrela`, `malha`, `anel`, `arvore`, `hibrida` | `estrela` | Topologia da rede |
| `NUM_PERIFERICOS` | 1 – 500 | `3` | Periféricos (estrela) ou total de agentes (malha/anel) |
| `TIPOS_REDE` | Lista separada por vírgula | `Link_Wired,Link_5G,Link_Wireless,Link_4G,Link_2G` | Tecnologias de enlace de estrela, malha e anel |
| `RANDOM_SEED` | Inteiro opcional | vazio (hardware RNG) | Semente determinística para reprodutibilidade em Python e C++ |
| `SIM_STEPS` | Inteiro ≥ 2 | `20` | Quantidade de passos discretos da co-simulação no Mosaik |
| `ARVORE_FANOUT` | Inteiros separados por vírgula | `3,2,4` | Árvore: filhos por nível |
| `CELULAR_ARVORE` | `2g`, `3g`, `4g`, `5g` | `4g` | Árvore: canal do nível subestação → concentrador |
| `SUBESTACOES` | Inteiro | `3` | Híbrida: subestações no anel de fibra |
| `CONCENTRADORES` | Inteiro | `3` | Híbrida: concentradores por subestação |
| `MEDIDORES_CLUSTER` | Inteiro | `5` | Híbrida: medidores por concentrador |
| `CELULAR_HIBRIDA` | `2g`, `3g`, `4g`, `5g` | `4g` | Híbrida: canal subestação → concentrador |
| `SEMENTE_HIBRIDA` | Inteiro | `42` | Híbrida: semente das posições (PADE e Mosaik usam a mesma) |

---

## Dashboards gerados

Os scripts de plotagem usam `links.json`, `posicoes.json` e `config.json` e salvam os painéis em `mosaik-dir/`, em **SVG** (estrela, anel, árvore e híbrida) ou PNG (malha, ainda não padronizada):

| Arquivo | Conteúdo |
|---|---|
| `grafico_trafego_Geral.svg` | Visão consolidada de todas as tecnologias ativas |
| `grafico_trafego_<Tecnologia>.svg` | Latência, payload, jitter, PDR, tabela e mapa de cada tecnologia |
| `grafico_trafego_Anel.svg` | Visão por agente roteador P2P (anel) |
| `grafico_trafego_Arvore.svg` | Visão por camada: raiz, subestação, concentrador e medidor (árvore) |
| `grafico_trafego_Hibrida.svg` | Visão por camada: CCO, subestação, concentrador e medidor (híbrida) |
| `grafico_*_<painel>_<topologia>.svg` | Painéis individuais da visão geral, para uso em artigos |

---

## Validação e testes automatizados

A suíte compila e testa a física C++ (`AgentNode.cc`, incluindo roteamento multi-salto e meio guiado), confere o sincronismo do `MosaikBridge.cc` e roda a co-simulação fim a fim nas 5 topologias, validando contagens de agentes e enlaces, entrega de mensagens, encaminhamento e geração dos dashboards:

```bash
uv sync    # instala PADE, Mosaik, pytest e ziglang (compilador C++ do teste) no .venv/
uv run pytest -v tests/test_validation_suite.py
```

Os testes E2E não precisam de Docker: rodam PADE, Mosaik e os dashboards no host, com `tests/omnet_zmq_emulator.py` fazendo o papel do OMNeT++ (mesmo roteamento e mesma física do `AgentNode.cc`, com os canais lidos do `Profiles.ned`).

---

## Gerenciamento de dependências (uv)

O `pyproject.toml` é a fonte única das dependências Python, e o `uv.lock` guarda as versões exatas resolvidas, incluindo as transitivas. Os containers instalam essas mesmas versões, então host e Docker rodam exatamente o mesmo ambiente.

| Grupo | Onde é usado | Conteúdo |
|---|---|---|
| `dependencies` | host: `menu-streamlit.py`, `menu.py` | streamlit, plotly |
| `pade` | container `pade` (exportado para `pade-dir/requirements.txt`) | pade-agents, twisted, autobahn, pyzmq, mosaik-api-v3, ipython |
| `mosaik` | container `mosaik_master` (exportado para `mosaik-dir/requirements.txt`) | mosaik, mosaik-api-v3, mosaik-csv, pyzmq, pandas, matplotlib, plotly, numpy |
| `dev` | testes no host (instalado por padrão no `uv sync`) | pytest, ziglang, mais os grupos `pade` e `mosaik` |

Para adicionar, remover ou atualizar um pacote:

```bash
uv add streamlit-aggrid                 # dependência da interface
uv add --group mosaik scipy             # dependência do container Mosaik
uv remove --group pade <pacote>         # remove do container PADE
uv lock --upgrade-package pandas        # atualiza só um pacote no uv.lock
```

Sempre que os grupos `pade` ou `mosaik` mudarem, regenere os arquivos que os Dockerfiles instalam e reconstrua as imagens (`docker compose build`):

```bash
uv export --frozen --only-group pade   --no-hashes -o pade-dir/requirements.txt
uv export --frozen --only-group mosaik --no-hashes -o mosaik-dir/requirements.txt
```

Faça commit de `pyproject.toml`, `uv.lock` e dos dois `requirements.txt` juntos. A pasta `.venv/` não vai para o git.

---

## Histórico de mudanças

Veja [CHANGELOG.md](CHANGELOG.md). Para contribuir, veja [CONTRIBUTING.md](CONTRIBUTING.md).
