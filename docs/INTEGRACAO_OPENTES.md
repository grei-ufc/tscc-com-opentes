# Contrato de Integração — TSCC (`tscc-com-opentes`) no OpenTES

Este documento descreve a interface exposta pela branch `integration-tscc` do repositório `tscc-com-opentes` para acoplamento como submódulo (`teams/tscc-com-opentes/`) na co-simulação do mercado transativo sobre a rede elétrica **IEEE 13 barras** (`co-simulation-opentes`).

Neste escopo, o time **TSCC** fornece o simulador de rede de comunicação (**OMNeT++**), os perfis físicos de enlace (`Profiles.ned`), a definição determinística da topologia IEEE 13 (`cosim/`), o adaptador Mosaik ↔ OMNeT++ (`omnet_wrapper.py`) e o **modo de consulta por mensagem** que o mercado usa. A definição dos agentes do mercado fica com os times integradores.

---

## 1. Componentes Expostos para Integração

| Componente | Caminho no repositório | Papel na integração |
|---|---|---|
| Topologia IEEE 13 | `cosim/topologias.py` (`montar_ieee13`) | Os 18 nós com coordenadas reais (embutidas ou lidas do `nodes_xy.csv`), em estrela ou em malha, com a subestação por cabo ou por rádio |
| Modelo de rádio da tese | `cosim/radio.py` | Friis em 915 MHz, Pister-Hack, tabela de PER (Prando et al.) e enlace por limiar: o PER de cada enlace dos canais da tese e a malha |
| Geração da rede | `cosim/ned.py` e `cosim/ieee13.py` | Escreve o `DynamicNetwork.ned` (com o `mosaikBridge` ou com o `servidorConsulta`) e o levantamento dos enlaces |
| Catálogo de canais | `cosim/catalogo.py` e `cosim/canais.py` | Rótulos, cores e leitura automática dos parâmetros de `Profiles.ned` |
| Perfis físicos NED | `omnet-dir/Profiles.ned` | Os canais do repositório, incluindo `Link_6TiSCH` e `Link_WiSUN`, e os da tese, `Link_6TiSCH_TSCH` e `Link_WiSUN_FAN` |
| Núcleo de rede C++ | `omnet-dir/AgentNode.cc`, `AgentNode.ned`, `AgentPacket.msg` | Filas finitas (5 pacotes/porta), atraso espacial, jitter, PER e roteamento multi-salto |
| Extensões do OpenTES | `omnet-dir/ExtensaoOpenTES.h` | MAC dos canais da tese, roteamento por ETX e nomes de agentes lidos de arquivo |
| Ponte ZeroMQ (Mosaik) | `omnet-dir/MosaikBridge.cc`, `MosaikBridge.ned` | Servidor ZeroMQ `REP` síncrono por passo (`mosaik_step`), porta configurável via `OMNET_PORT` |
| Consulta por mensagem | `omnet-dir/ServidorConsulta.cc`, `ServidorConsulta.ned`, `consulta.ini` | Servidor ZeroMQ `REP` por mensagem: cada envio de um agente atravessa os AgentNodes da topologia |
| Adaptador Python | `mosaik-dir/omnet_wrapper.py` | Simulador Mosaik API 3.0 (`OmnetAdapter`) que conversa com `MosaikBridge` via ZeroMQ |
| Container OMNeT++ | `omnet-dir/Dockerfile` | Imagem autônoma com OMNeT++ 6.0 e `libzmq` |

---

## 2. Topologia IEEE 13 Barras (`cosim.topologias.montar_ieee13`)

`montar_ieee13(tipos_rede=None, posicoes=None, topologia='estrela', subestacao='cabo', enlaces=None, radio=None, semente=0, cells=None, central='0')` retorna um objeto `Rede(nos, links, config)` sem efeitos colaterais. Chamada só com `tipos_rede`, é a rede original deste repositório.

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

Com `posicoes='.../nodes_xy.csv'`, os nós vêm do caso: o nome `611` vira `agent_611`, `DSO` vira `agent_dso`, e assim por diante.

### 2.2 Opções

Todas mantêm os canais do repositório disponíveis, inclusive misturados.

| Opção | Valores | O que faz |
|---|---|---|
| `topologia` | `estrela` (padrão), `malha` | Na malha, os enlaces são os pares com PER abaixo de 0,5 no modelo de rádio da tese, e as mensagens atravessam vários saltos |
| `subestacao` | `cabo` (padrão), `radio` | Concentrador, DSO e Market ligados por `Link_Wired`, ou pelo rádio, como na tese |
| `enlaces` | caminho de um `tisch_links.csv` | Repete exatamente a topologia de rádio e os PER de uma execução do servidor da tese; sem ele, o levantamento é sorteado com a `semente` |
| `radio` | `cosim.radio.Radio(...)` | Frequência, potência, ganhos e taxa do Wi-SUN (a sensibilidade sobe 10 log10(R / 50 kbps)) |
| `cells` | inteiro | Cells por slotframe do `Link_6TiSCH_TSCH` |

### 2.3 Exemplo de uso no cenário Mosaik

```python
from cosim.topologias import montar_ieee13, vizinhos

rede = montar_ieee13(tipos_rede=['Link_6TiSCH'])
# rede.nos   -> lista com os 18 dicts {'id', 'x', 'y', 'tipo', 'camada'}
# rede.links -> lista com os 17 dicts {'origem', 'destino', 'tipo'}
# mapa_vizinhos = vizinhos(rede)
```

A topologia também roda dentro deste repositório: `TOPOLOGY=ieee13` (menus, `scenario.py` e `pade_ieee13.py`).

---

## 3. Canais do modelo da tese

`Link_6TiSCH_TSCH` e `Link_WiSUN_FAN` reproduzem a rede LPWA de Melo (2022, seção 6.1.5), a mesma do servidor 6TiSCH do `co-simulation-opentes` (`comm-opentes/Tisch.cc`). Neles, o atraso e a perda de cada salto vêm do MAC do rádio, calculados no AgentNode:

- **TSCH:** um quadro de 127 B por cell, `cells` cells por slotframe de 4,04 s, fragmentação da mensagem em quadros e até 3 retentativas por quadro. Perder um fragmento perde a mensagem.
- **Wi-SUN FAN:** CSMA/CA não sincronizado, quadro de até 1280 B, recuo, tempo no ar, reversão, ACK e LIFS. A taxa (50, 150 ou 300 kbps) entra pelo parâmetro `taxa_bps` do enlace.

O PER de cada enlace (`per_enlace`) é calculado na montagem da topologia por `cosim/radio.py`. Os canais do repositório (`Link_6TiSCH`, `Link_WiSUN`, `RFMesh`, `PLC`, `Link_4G`...) continuam com o modelo próprio do AgentNode.

---

## 4. Modo de consulta por mensagem

No mercado transativo, a negociação inteira acontece dentro de **um** passo de 15 min do Mosaik, com o relógio da co-simulação parado. Por isso, além do `MosaikBridge`, há um modo em que cada envio de um agente vira uma consulta ZeroMQ, e a mensagem atravessa os nós, as filas e os canais da topologia.

```bash
python -m cosim.ieee13 --posicoes nodes_xy.csv --canal Link_6TiSCH_TSCH \
    --topologia malha --subestacao radio --ned omnet-dir/DynamicNetwork.ned
cd omnet-dir && ./sim_exec -u Cmdenv -f consulta.ini
```

| Pedido | Resposta |
|---|---|
| `{"action": "route", "src": "611", "dst": "0", "bytes": 656}` | `{"status": "ok", "dropped": false, "delay": 24.19, "hops": 2, "frames": 6}` |
| `{"action": "info"}` | nós, enlaces, PER médio, saltos médios e pares sem rota |
| `{"action": "stop"}` | encerra a simulação |

Os nomes aceitos são o do módulo (`agent_611`) ou o do caso (`611`, `DSO`). Um nome sem nó é entregue sem atraso, com aviso no log e `"unknown": true` na resposta. O contrato é o mesmo do servidor de rotas do `co-simulation-opentes`, então os agentes do mercado usam a rede do TSCC sem alteração.

O `consulta.ini` usa roteamento por ETX da mensagem (`**.roteamento = "etx"`) e propagação de 3,336 ns/m nos meios não guiados. O modo Mosaik (`omnetpp.ini`) não muda.

### 4.1 Conferência com o servidor da tese

As 2.978 mensagens reais de um dia de mercado, enviadas aos dois servidores com a mesma topologia de rádio:

| Canal | Servidor | Perdas | Atraso mediano | Mensagens ≥ 20 kB (mediana) | Saltos médios |
|---|---|---:|---:|---:|---:|
| 6TiSCH | `Tisch.cc` | 0 | 4,21 s | 388,5 s | 1,461 |
| 6TiSCH | TSCC, `Link_6TiSCH_TSCH` | 0 | 4,20 s | 388,1 s | 1,461 |
| Wi-SUN FAN 50 kbps | `Tisch.cc` | 0 | 0,433 s | 4,37 s | 1,461 |
| Wi-SUN FAN 50 kbps | TSCC, `Link_WiSUN_FAN` | 0 | 0,433 s | 4,37 s | 1,461 |

---

## 5. Nomes dos agentes no modo Mosaik

O `mapPadeToOmnet` do AgentNode traduz `AgenteCentral` e `AgenteP_<i>`. Com as extensões, também aceita a tabela do parâmetro `arquivo_nomes` (CSV `nome,nó`), o próprio nome do nó e a regra `nome -> agent_<nome em minúsculas>`. Uma mensagem para um destino sem rota passa a ser contada em `packets_dropped`.

---

## 6. O que este repositório tem além do que o mercado usa

Comparado com a rede do `co-simulation-opentes` (`comm-opentes`, só rádio 6TiSCH e Wi-SUN FAN como servidor de rotas), o TSCC oferece:

| Recurso | Onde | Situação no `co-simulation-opentes` |
|---|---|---|
| Co-simulação passo a passo PADE + Mosaik + OMNeT++, com agentes próprios por topologia | `mosaik-dir/scenario.py`, `pade-dir/pade_agents/` | não existe: o mercado usa só a consulta por mensagem |
| Seis topologias: estrela, malha, anel, árvore (IEC 61850: fibra, celular, PLC), híbrida (anel de fibra, celular, malha RF) e IEEE 13 | `cosim/topologias.py` | só a IEEE 13 em malha de rádio |
| Quatorze canais do repositório (cabo, 5G, Wireless, 4G, 2G, fibra, celular 2G a 5G, RF Mesh, PLC, 6TiSCH, Wi-SUN) e os dois da tese | `omnet-dir/Profiles.ned` | só os dois MACs da tese |
| Fila finita de 5 pacotes por porta, com descarte contado | `AgentNode.cc` | sem disputa entre mensagens |
| Meio guiado (fibra e cabo) sem atenuação espacial | `AgentNode.cc` | só cabo entre agentes na mesma coordenada (`colocated_wired`) |
| Interface Streamlit e menu de terminal, com tecnologia por agente | `menu-streamlit.py`, `menu.py` | console `opentes` com as redes da integração |
| Painéis por tecnologia e por camada, em SVG/PNG | `mosaik-dir/plot_*.py`, `ieee13_plot.py` | figuras do mercado (`market_opentes.figuras`) |
| Emulador ZeroMQ do OMNeT++, testes de consistência e E2E, CI | `tests/`, `.github/workflows/` | sem testes da rede |
| `uv.lock`, `RANDOM_SEED` único e `OUTPUT_DIR` por rodada | raiz, `scenario.py` | semente fixa do OMNeT++ |
| Artigo do TSCC | `artigo-overleaf/` | não se aplica |

Na integração, todos os canais e as duas topologias da IEEE 13 ficam disponíveis para o mercado pelo modo de consulta (`COMM=tscc`, `TSCC_CANAL`, `TSCC_TOPOLOGIA`, `TSCC_SUBESTACAO` no `run.sh` e no console `opentes`). As topologias genéricas e a co-simulação passo a passo continuam neste repositório, para os estudos de comunicação do TSCC.
