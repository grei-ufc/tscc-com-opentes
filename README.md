
# TSCC Co-Simulação PADE + OMNeT++ + mosaik

Esse repositório contém uma plataforma de co-simulação baseada em containers, unindo três subsistemas:

- **PADE**: agentes FIPA em Python que produzem e processam eventos.
- **mosaik**: orquestração e sincronização entre simuladores.
- **OMNeT++**: simulação de rede usando topologias geradas dinamicamente.

O objetivo é suportar experimentos distribuídos em lock-step, com comunicação estruturada entre agentes, orquestrador e simulação de rede.

## Visão geral da arquitetura

```
[PADE agents] <--> [mosaik_master] <--> [OMNeT++ sim] 
       |                          |             ^
       v                          v             |
  Telemetria / Controle      Topologia NED      |  Dados de rede
                               gerados          |  enviados para
                                                 +-- [Coletor] --> CSV
```

- `pade` gera tráfego e responde a eventos de rede.
- `mosaik_master` cria a topologia `DynamicNetwork.ned`, alcança o OMNeT++ e conecta os simuladores.
- `omnet_sim` compila e executa a simulação OMNeT++.
- `mosaik-dir/collector.py` salva métricas em `results.csv`.

## Estrutura do repositório

- `docker-compose.yml` - orquestra os serviços e volumes.
- `mosaik-dir/` - scripts mosaik, coleta e plotagem de resultados.
- `pade-dir/` - Dockerfile e agentes PADE.
- `omnet-dir/` - código OMNeT++, configuração e executável.

## Pré-requisitos

- Docker
- Docker Compose V2

> Não é necessário instalar OMNeT++ ou ferramentas Python localmente: tudo roda em containers.

## Execução rápida

1. Clone o repositório:

```bash
git clone https://github.com/grei-ufc/tscc-com-opentes.git
cd tscc-com-opentes
```

2. Inicie os containers:

```bash
docker compose up --build
```

3. Aguarde a simulação.
4. Verifique os resultados em `mosaik-dir/results.csv`.

## Exemplos de execução

### Iniciar em modo interativo

```bash
docker compose up --build
```

### Iniciar em modo detached

```bash
docker compose up -d --build
```

### Parar e remover containers

```bash
docker compose down
```

### Ver logs em tempo real

```bash
docker compose logs -f pade
```

```bash
docker compose logs -f omnet_sim
```

```bash
docker compose logs -f mosaik_master
```

### Ajustar o número de agentes

Edite `docker-compose.yml` e altere `NUM_PERIFERICOS` em `pade` e `mosaik_master`, depois reinicie:

```bash
docker compose down

docker compose up --build
```

### Ver resultados gerados

```bash
ls -l mosaik-dir/
cat mosaik-dir/results.csv | head
```

## Como funciona a execução

1. `omnet_sim` inicia e compila o código OMNeT++ em `omnet-dir/`.
2. `pade` inicia os agentes PADE e expõe a porta `5678` para comunicação.
3. `mosaik_master` inicia o script `mosaik-dir/star.py`.
4. O `star.py` gera uma topologia estrela em `omnet-dir/DynamicNetwork.ned` com um nó central e `NUM_PERIFERICOS` periféricos.
5. O `omnet_sim` detecta o arquivo `DynamicNetwork.ned`, executa `sim_exec` e passa dados para o mosaik.
6. O coletor grava métricas em `mosaik-dir/results.csv`.
7. `mosaik-dir/plot_results_star.py` gera gráficos a partir de `results.csv`.

## Serviços do Docker Compose

### pade
- build: `./pade-dir`
- expõe: `5678:5678`
- volume: `./pade-dir/pade_agents:/app`
- comando: `python3 pade_star.py`
- variável: `NUM_PERIFERICOS` controla quantos agentes periféricos são criados.

### omnet_sim
- build: `./omnet-dir`
- volume: `./omnet-dir:/root/models`
- executa:
  - ambiente OMNeT++
  - `opp_makemake -f --deep -o sim_exec -lzmq`
  - `make`
  - aguarda `DynamicNetwork.ned`
  - roda `./sim_exec -u Cmdenv -c General`

### mosaik_master
- build: `./mosaik-dir`
- depende de `omnet_sim` e `pade`
- volumes:
  - `./mosaik-dir:/app`
  - `./omnet-dir:/omnet-dir`
- comando:
  - instala `pandas` e `matplotlib`
  - roda `python star.py`
  - roda `python plot_results_star.py`

## Componentes-chave

### `mosaik-dir/star.py`
- monta um cenário em estrela com um nó central e `NUM_PERIFERICOS` periféricos.
- gera `omnet-dir/DynamicNetwork.ned` com posições e tipos de links (`Link_5G`, `Link_4G`, `Link_Wired`, `Link_IoT`).
- inicia os simuladores `OmnetSim`, `ColetorSim` e `PadeSim`.
- conecta agentes OMNeT++ ao PADE e ao coletor.
- executa `world.run(until=20)`.

### `mosaik-dir/collector.py`
- simula um coletor mosaik que escreve todas as mensagens recebidas em `results.csv`.
- atributos gravados: tempo, origem, atributo e valor.
- flush automático para persistência em tempo real.

### `mosaik-dir/plot_results_star.py`
- lê `results.csv` com pandas.
- extrai métricas de latência, jitter, throughput e entregas.
- gera painéis de análise por tipo de link e topologia.
- detecta `posicoes.json` para apresentar mapa espacial dos nós.

### `pade-dir/pade_agents/pade_star.py`
- cria um agente central (`AgenteCentral`) e vários agentes periféricos (`AgenteP_i`).
- o agente central envia `telemetria_rede` para todos os periféricos.
- periféricos respondem com mensagem de status.
- mensagens de simulação são convertidas para JSON e transmitidas via mosaik.
- o PADE trata mensagens de controle internamente e não envia tráfego de sistema para OMNeT++.

### `omnet-dir/omnetpp.ini`
- usa `network = DynamicNetwork`.
- scheduler sequencial padrão.
- sim-time-limit configurado em `1000s`.
- parâmetro coringa `**.agent_id = ""` para evitar falhas de validação quando o NED é gerado dinamicamente.

## Arquivos importantes

- `docker-compose.yml`
- `omnet-dir/DynamicNetwork.ned`
- `omnet-dir/omnetpp.ini`
- `omnet-dir/Makefile`
- `omnet-dir/sim_exec`
- `mosaik-dir/star.py`
- `mosaik-dir/collector.py`
- `mosaik-dir/plot_results_star.py`
- `pade-dir/Dockerfile`
- `pade-dir/pade_agents/pade_star.py`
- `pade-dir/pade_agents/pade_sim.py`
- `omnet-dir/AgentNode.cc`, `omnet-dir/AgentNode.ned`, `omnet-dir/MosaikBridge.cc` - adaptadores e wrappers OMNeT++.

## Saída e análise

- `mosaik-dir/results.csv`: CSV principal com métricas de simulação.
- `mosaik-dir/posicoes.json`: posições dos nós usadas pelo plot.
- O script de plot tenta gerar painéis de performance por rede e por tipo de link.

## Personalização

### Ajustar escala

Altere `NUM_PERIFERICOS` em `docker-compose.yml` para aumentar ou reduzir o número de agentes.

### Topologia

O script `mosaik-dir/star.py` gera um cenário em estrela:
- `agent_central`
- `agent_p_1` a `agent_p_N`

Para criar outra topologia, edite `create_scenario(world)`.

### Parâmetros OMNeT++

Edite `omnet-dir/omnetpp.ini` para alterar tempo de simulação, scheduler ou parâmetros globais.

## Comandos úteis

- `docker compose up --build`
- `docker compose up -d --build`
- `docker compose down`
- `docker compose logs -f pade`
- `docker compose logs -f omnet_sim`
- `docker compose logs -f mosaik_master`

## Troubleshooting

- Se `omnet_sim` falhar antes de encontrar `DynamicNetwork.ned`, o serviço compila OMNeT++ mas aguarda o arquivo.
- Se `mosaik_master` falhar por falta de `pandas`/`matplotlib`, a imagem instala dependências no comando de inicialização.
- Caso `results.csv` esteja vazio, verifique se `mosaik_master` criou o cenário e se `omnet_sim` iniciou a simulação.
- Problemas de permissão podem ocorrer ao montar `./omnet-dir` e `./mosaik-dir` como volumes.

## Próximos passos

- adicionar cenários variados (malha, anéis, clusters).
- refinar coleta de métricas para cada fluxo de pacote.
- incluir suporte a simulações maiores e comparação de tecnologias de link.
- criar uma interface de análise baseada em dashboards.

