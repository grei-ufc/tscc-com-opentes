
# TSCC Co-Simulação PADE + OMNeT++ + mosaik

# Co-Simulação PADE + OMNeT++ + Mosaik

**Grupo de Redes Elétricas Inteligentes (GREI) — Universidade Federal do Ceará (UFC)**

Plataforma de co-simulação que integra três ferramentas de diferentes domínios em containers Docker: **PADE** (camada cognitiva de agentes), **OMNeT++** (simulação de rede de comunicação) e **Mosaik** (orquestrador). A comunicação entre camadas usa **ZeroMQ REQ/REP**.

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
- [Débitos técnicos e acoplamentos implícitos](#débitos-técnicos-e-acoplamentos-implícitos)

---

## Arquitetura

A co-simulação é composta por três containers que rodam simultaneamente e se comunicam via rede Docker interna (`sim_net`):

```
┌─────────────────────────────────────────────────────────────┐
│  menu_streamlit.py  ──── env vars ────  docker compose up   │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┼───────────────────────┐
        │                      │                       │
  ┌─────▼──────┐       ┌───────▼──────┐       ┌───────▼───────┐
  │    pade    │       │  omnet_sim   │       │ mosaik_master │
  │            │       │              │       │               │
  │ PADE       │◄─────►│ OMNeT++      │◄─────►│ Mosaik 3.6    │
  │ Twisted    │  ZMQ  │ C++ eventos  │  ZMQ  │ scenario.py   │
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

1. Cada agente PADE serializa mensagens FIPA-ACL em JSON e escreve em `val_out`
2. O Mosaik entrega `val_out` ao nó correspondente no OMNeT++ via `MosaikBridge.cc`
3. O OMNeT++ simula latência, jitter, perda e buffer overflow do canal físico
4. O resultado retorna em `val_in` para o agente PADE no próximo passo (`time_shifted=True`)

O padrão **REQ/REP bloqueante** do ZeroMQ garante que Mosaik e OMNeT++ nunca avançam em passos diferentes — o sincronismo é garantido **por construção**, não por detecção posterior.

---

## Topologias suportadas

| Topologia | Script PADE | Script Mosaik | Agentes | Comportamento PADE |
|---|---|---|---|---|
| `estrela` | `pade_star.py` | `scenario.py` | 1 central + N periféricos | Central faz broadcast; periféricos respondem só ao central |
| `malha` | `pade_malha.py` | `scenario.py` | N agentes peers | Todos enviam para todos a cada passo (full mesh) |
| `anel` | `pade_anel.py` | `scenario.py` | N agentes peers | Cada agente envia só para os dois vizinhos adjacentes |

**Contagem de agentes:**
- `estrela`: `NUM_PERIFERICOS` define os periféricos; total = `NUM_PERIFERICOS + 1`
- `malha` e `anel`: `NUM_PERIFERICOS` define o **total** de agentes (sem +1 — todos são peers)

**Contagem de enlaces no OMNeT++:**
- Estrela: N enlaces (linear)
- Anel: N enlaces (linear, ciclo fechado)
- Malha: N×(N-1)/2 enlaces (quadrático — atenção ao desempenho com N grande)

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

Os tipos de enlace são atribuídos **ciclicamente** aos enlaces gerados, garantindo distribuição equilibrada entre as tecnologias selecionadas.

### Física de rede simulada (`AgentNode.cc`)

O módulo C++ implementa quatro efeitos realistas:

- **Buffer overflow**: fila limitada a 5 pacotes por porta; excedente é descartado e contabilizado em `packets_dropped`
- **BER escalonado por payload**: `finalDropChance = min(0.99, baseDropChance × max(1.0, tamanho/15000))` — pacotes maiores têm mais chance de corrupção
- **Atraso por distância**: `propagationDelay = dist × 0.00005` somado ao delay base do canal
- **Hardware RNG**: `std::random_device → std::mt19937` para resultados não-determinísticos

---

## Estrutura de diretórios

```
tscc-com-opentes/
├── menu_streamlit.py              # Interface web (Streamlit) — ponto de entrada recomendado
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
└── mosaik-dir/
    ├── Dockerfile
    ├── scenario.py                # Orquestrador: monta qualquer topologia
    ├── collector.py               # Coleta métricas de cada nó
    ├── omnet_wrapper.py           # Adaptador Mosaik ↔ OMNeT++
    ├── plot_results_star.py       # Dashboard matplotlib para estrela e anel
    ├── plot_results_malha.py      # Dashboard matplotlib para malha
    └── results.csv                # Dados brutos coletados (gerado)
```

---

## Pré-requisitos

- **Docker** ≥ 24 e **Docker Compose** ≥ 2.20
- **Python** ≥ 3.10 (apenas para rodar a interface Streamlit no host)
- `streamlit`, `plotly` instalados no host: `pip install streamlit plotly`

---

## Como executar

### Via interface web (recomendado)

```bash
git clone <url-do-repositório>
cd tscc-com-opentes
git switch development # atualmente estamos trabalhando com a development, pós testes faremos o pull request e mergimos as branchs 
streamlit run menu-streamlit.py
```

Acesse `http://localhost:8501`, configure topologia, número de agentes e tipos de enlace, e clique em **Iniciar simulação**. Os gráficos aparecem automaticamente na interface ao término.

### Via terminal (CLI)

 a prencher ainda 

---

## Variáveis de ambiente

Injetadas via `docker-compose.yml` a partir das escolhas feitas no menu:

| Variável | Valores válidos | Padrão | Descrição |
|---|---|---|---|
| `TOPOLOGY` | `estrela`, `malha`, `anel` | `estrela` | Topologia da rede |
| `NUM_PERIFERICOS` | 1 – 500 | `3` | Periféricos (estrela) ou total de agentes (malha/anel) |
| `TIPOS_REDE` | Lista separada por vírgula | todos os 5 tipos | Tecnologias de enlace disponíveis na simulação |

---

## Interface web (Streamlit)

`menu_streamlit.py` oferece:

- **Seleção de topologia** com descrição contextual
- **Campo de agentes** com semântica correta por topologia (estrela: periféricos; malha/anel: total de peers)
- **Multiselect de tecnologias** com cores consistentes entre a interface e os dashboards
- **Ícones SVG** dos agentes (servidor, PC, roteador) coloridos na identidade visual do GREI
- **Preview interativo** da topologia em Plotly — arestas coloridas por tecnologia, atualizado em tempo real a cada alteração
- **Nota de bidirecionalidade** para anel (cada enlace físico transporta dados nos dois sentidos)
- **Terminal embutido** com streaming do log do `docker compose` durante a simulação
- **Dashboards automáticos** exibidos na interface ao fim da simulação; limpos ao iniciar nova rodada

---

## Dashboards gerados

### Estrela e Anel — `plot_results_star.py`

Gera um PNG por visão em `mosaik-dir/`:

| Arquivo | Conteúdo |
|---|---|
| `grafico_trafego_Geral.png` | Visão consolidada de todas as tecnologias |
| `grafico_trafego_Cabeada.png` | Latência, jitter, PDR e payload da rede Cabeada |
| `grafico_trafego_5G.png` | Idem para 5G |
| `grafico_trafego_Wireless.png` | Idem para Wireless |
| `grafico_trafego_4G.png` | Idem para 4G |
| `grafico_trafego_2G.png` | Idem para 2G |

### Malha — `plot_results_malha.py`

Gera `mosaik-dir/grafico_malha.png` com quatro painéis:

1. **Mapa da rede** — nós posicionados geograficamente, arestas coloridas por tecnologia
2. **PDR por tecnologia** — barras horizontais com taxa de entrega de cada tipo de enlace
3. **Latência por tecnologia** — barras verticais com média por tipo de enlace
4. **PDR global** — barra empilhada: entregues / descartados / restantes

> Se `links.json` não existir (versão anterior do `scenario.py`), o script reconstrói os enlaces automaticamente a partir de `posicoes.json` e `config.json`.

---

## Débitos técnicos e acoplamentos implícitos

| Acoplamento | Onde | Risco |
|---|---|---|
| `classificar_rede()` em `plot_results_star.py` reimplementa a lógica cíclica de `scenario.py` | Ambos os arquivos | Mudança na ordem de TIPOS_REDE quebra a classificação sem erro explícito |
| `+1.0` hardcoded em `MosaikBridge.cc` deve bater com `time+1` em `omnet_wrapper.py` | C++ e Python | Dessincronismo silencioso se um lado mudar |
| `TOTAL_AGENTES` deve ser consistente entre `scenario.py` e os scripts PADE | 4 arquivos | Topologia NED diferente da topologia PADE |
| `mosaik_step` retornado pelo C++ é sempre `None` | `MosaikBridge.cc` | Auditoria formal de sincronismo pendente |
