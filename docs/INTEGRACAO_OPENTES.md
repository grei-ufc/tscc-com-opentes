# Contrato de Integração — TSCC (`tscc-com-opentes`) no OpenTES

Este documento descreve a interface exposta pela branch `integration-tscc` do repositório `tscc-com-opentes` para acoplamento como submódulo (`teams/tscc-com-opentes/`) na co-simulação do mercado transativo sobre a rede elétrica **IEEE 13 barras** (`co-simulation-opentes`).

Neste escopo, o time **TSCC** fornece o simulador de rede de comunicação (**OMNeT++**), os perfis físicos de enlace (`Profiles.ned`), a definição determinística da topologia IEEE 13 (`cosim/`) e o adaptador Mosaik ↔ OMNeT++ (`omnet_wrapper.py`). A definição dos agentes PADE e do cenário Mosaik fica sob responsabilidade dos times integradores.

---

## 1. Componentes Expostos para Integração

| Componente | Caminho no repositório | Papel na integração |
|---|---|---|
| Topologia IEEE 13 | `cosim/topologias.py` (`montar_ieee13`) | Fornece os 18 nós com coordenadas reais (`nodes_xy.csv`) e os 17 enlaces determinísticos |
| Catálogo de canais | `cosim/catalogo.py` e `cosim/canais.py` | Rótulos, cores e leitura automática dos parâmetros de `Profiles.ned` |
| Perfis físicos NED | `omnet-dir/Profiles.ned` | Definição dos canais no OMNeT++, incluindo `Link_6TiSCH` e `Link_WiSUN` |
| Núcleo de rede C++ | `omnet-dir/AgentNode.cc`, `AgentNode.ned`, `AgentPacket.msg` | Física de filas finitas (5 pacotes/porta), atraso espacial, jitter, PER e roteamento multi-salto |
| Ponte ZeroMQ C++ | `omnet-dir/MosaikBridge.cc`, `MosaikBridge.ned` | Servidor ZeroMQ `REP` síncrono por passo (`mosaik_step`), com porta configurável via `OMNET_PORT` |
| Adaptador Python | `mosaik-dir/omnet_wrapper.py` | Simulador Mosaik API 3.0 (`OmnetAdapter`) que conversa com `MosaikBridge` via ZeroMQ |
| Container OMNeT++ | `omnet-dir/Dockerfile` | Imagem autônoma com OMNeT++ 6.0 e `libzmq` |

---

## 2. Topologia IEEE 13 Barras (`cosim.topologias.montar_ieee13`)

A função `montar_ieee13(tipos_rede=None)` retorna um objeto `Rede(nos, links, config)` sem efeitos colaterais, pronto para gerar o arquivo `DynamicNetwork.ned` e os metadados (`posicoes.json`, `links.json`, `config.json`).

### 2.1 Nós da Rede (18 agentes)

| ID do Nó (OMNeT++ / PADE) | Coordenada X (m) | Coordenada Y (m) | Camada | Papel no Mercado Transativo |
|---|---:|---:|---|---|
| `agent_0` | 0.00 | 0.00 | `controle` | Concentrador / Agregador (Subestação) |
| `agent_dso` | 0.00 | 0.00 | `controle` | Operador do Sistema de Distribuição (DSO) |
| `agent_market` | 0.00 | 0.00 | `controle` | Coordenador do Mercado (Decomposição Dual) |
| `agent_611` | -182.88 | -1221.20 | `periferico` | Barra 611 |
| `agent_632` | 0.00 | -611.60 | `periferico` | Barra 632 |
| `agent_633` | 152.40 | -611.60 | `periferico` | Barra 633 |
| `agent_634` | 153.40 | -611.60 | `periferico` | Barra 634 |
| `agent_645` | -152.40 | -611.60 | `periferico` | Barra 645 |
| `agent_646` | -243.84 | -611.60 | `periferico` | Barra 646 |
| `agent_650` | 0.00 | -1.00 | `periferico` | Barra 650 |
| `agent_652` | -91.44 | -1465.04 | `periferico` | Barra 652 |
| `agent_660` | 0.00 | -2.00 | `periferico` | Barra 660 |
| `agent_670` | 0.00 | -814.90 | `periferico` | Barra 670 |
| `agent_671` | 0.00 | -1221.20 | `periferico` | Barra 671 |
| `agent_675` | 153.40 | -1221.20 | `periferico` | Barra 675 |
| `agent_680` | 0.00 | -1526.00 | `periferico` | Barra 680 |
| `agent_684` | -91.44 | -1221.20 | `periferico` | Barra 684 |
| `agent_692` | 1.00 | -1221.20 | `periferico` | Barra 692 |

* **Enlaces locais na subestação:** `agent_0 <-> agent_dso` e `agent_0 <-> agent_market` usam `Link_Wired`.
* **Enlaces das 15 barras:** `agent_0 <-> agent_<barra>` ciclam os canais informados em `tipos_rede` (padrão: `['Link_6TiSCH']`).

### 2.2 Exemplo de uso no cenário Mosaik

```python
from cosim.topologias import montar_ieee13, vizinhos

rede = montar_ieee13(tipos_rede=['Link_6TiSCH'])
# rede.nos   -> lista com os 18 dicts {'id', 'x', 'y', 'tipo', 'camada'}
# rede.links -> lista com os 17 dicts {'origem', 'destino', 'tipo'}
# mapa_vizinhos = vizinhos(rede)