# Relatório de alterações — refatoração do repositório

| | |
|---|---|
| **Branch** | `refactor/organizacao-repositorio` |
| **Base** | `origin/development` em `7737a55` (26/10/2026) |
| **Período** | 19/11/2026 |
| **Commits** | 10 (`d96ee23` … `3dc5fe8`) |
| **Diferença total para a base** | 74 arquivos alterados, +4.962 / −8.412 linhas |
| **Situação** | commits locais; a branch ainda não foi enviada ao GitHub nem tem pull request |

Este relatório trata **só das alterações feitas nesta refatoração**. O histórico anterior aparece apenas onde é necessário para explicar o ponto de partida. O relatório tem quatro partes:
- **o que foi alterado**, commit a commit (seção 3);
- **as decisões tomadas**, com as alternativas consideradas e o motivo de cada escolha (seção 4);
- **uma discussão** dos riscos, compromissos e lições (seção 5);
- **os pontos em aberto**, organizados para o grupo decidir depois (seção 9).

---

## Sumário

1. [Resumo](#1-resumo)
2. [Ponto de partida](#2-ponto-de-partida)
3. [Alterações, commit a commit](#3-alterações-commit-a-commit)
4. [Decisões tomadas](#4-decisões-tomadas)
5. [Discussão](#5-discussão)
6. [Como as alterações foram verificadas](#6-como-as-alterações-foram-verificadas)
7. [Números: antes e depois](#7-números-antes-e-depois)
8. [O que muda para quem usa o projeto](#8-o-que-muda-para-quem-usa-o-projeto)
9. [Pontos em aberto](#9-pontos-em-aberto)
10. [Como revisar e integrar](#10-como-revisar-e-integrar)
11. [Apêndice A: os 10 commits](#apêndice-a-os-10-commits)
12. [Apêndice B: arquivos criados, movidos e removidos](#apêndice-b-arquivos-criados-movidos-e-removidos)

---

## 1. Resumo

A refatoração reorganizou o repositório tomando como referência pandas, scikit-learn, `grei-ufc/tsre-der-opentes` e `PauloRadatz/py_dss_interface`. A forma de usar continua a mesma: `docker compose`, os dois menus e as variáveis de ambiente.

**Principais resultados**

- **Dependências gerenciadas pelo uv.** O `pyproject.toml` e o `uv.lock` definem as versões para o host e para os containers.
- **A suíte de testes voltou a passar.** Na `development`, os 4 testes falhavam. Agora são **33 de 33**, com testes E2E novos para árvore e híbrida.
- **Regressões corrigidas.** Commits de 23/10 tinham desfeito correções de 22/10: semente, número de passos, rede compartilhada do Docker, semântica da malha e outras.
- **Quatro bugs encontrados e corrigidos:**
  1. a híbrida **não era reprodutível** com a mesma semente;
  2. o **OMNeT++ abortava** na híbrida; só apareceu ao rodar no Docker;
  3. o menu Streamlit **descrevia o Wireless com valores diferentes** dos simulados;
  4. o `Makefile` versionado sujava o `git status` a cada rodada no Docker.
- **Duplicação removida.** Os scripts PADE caíram de 1.396 para 294 linhas, com as bases comuns em módulos próprios. Os plots de árvore e híbrida viraram uma implementação só. A geometria da híbrida, copiada entre o container Mosaik e o PADE, ficou num único lugar: o pacote `cosim/`.
- **Repositório limpo.** As saídas da simulação saíram do git, os legados foram separados e a documentação foi atualizada.
- **Qualidade automatizada.** CI no GitHub Actions e pre-commit.
- **Comportamento preservado.** Nas refatorações, as saídas das 5 topologias com semente fixa ficaram **idênticas**: 74 de 74 arquivos.
- **Validado no Docker.** Todas as topologias rodaram até o fim nos containers reais, inclusive pelo `menu.py`.

**O que fica para o grupo decidir**, com detalhes na [seção 9](#9-pontos-em-aberto):
- como integrar a branch `iee13-barras`;
- a comunicação com quem trabalha na `development`;
- os valores corretos do Wireless;
- o registro no AMS do PADE;
- a malha no Streamlit;
- os autores do `CITATION.cff`;
- o `.zip` do artigo;
- empacotar a ponte OMNeT++ ↔ Mosaik;
- outros oito itens técnicos de menor prioridade.

---

## 2. Ponto de partida

### 2.1 Diagnóstico da organização

A análise inicial, comparando com os projetos de referência, apontou estes problemas:

| Problema | Exemplo encontrado |
|---|---|
| Saídas da simulação versionadas no git | `results.csv`, 11 PNGs, `DynamicNetwork.ned`, `posicoes.json`, `links.json`, `config.json` e `logs/*.csv` eram reescritos a cada rodada e pelos testes |
| Código legado misturado ao ativo | `first.py`, `star.py`, `mosaik_anel.py`, `plot_results.py`, `pade_sim.py` (ainda o `CMD` do Dockerfile do PADE) e `agent_example_1_mosaik_updated.py` |
| Duplicação de código | tradutores ACL↔JSON em 6 scripts; `_path` e `_exportar_paineis_separados` iguais em vários plots; catálogo de tecnologias copiado nos menus, plots e emulador; geração de enlaces repetida no `scenario.py`, no menu Streamlit e nos plots |
| Dependências do host não declaradas | o README pedia só `pip install streamlit plotly`, mas os testes precisam de PADE, Mosaik, pandas, matplotlib e de um compilador C++ (`ziglang`) |
| Arquivos sem uso na raiz | `githubicone.png` e `icone-linkedin.png` |
| Sem CI, CHANGELOG, CONTRIBUTING | o histórico de correções ficava no README |
| Nome enganoso | `omnet-dir/Network.ned` continha a declaração indispensável de `MosaikBridge` e uma rede `CoSimulationNetwork` que ninguém usava |

### 2.2 Situação da `development`: 0 de 4 testes passando

A `origin/development` tinha **23 commits a mais que a `main`** (22–26/10/2026): topologias árvore e híbrida, roteamento multi-salto no `AgentNode.cc`, 12 tipos de canal, gráficos em SVG, uma aba nova no Streamlit e o artigo em `artigo-overleaf/`. Rodada com o ambiente do uv, a suíte falhava inteira, por dois motivos.

1. **Regressão de merge.** Os commits `12801a9` e `277ab38` (23/10) substituíram o `docker-compose.yml` e o `scenario.py` por versões anteriores às correções `b78f298`, `de491a7` e `298aedf` (20–22/10). O padrão de cada commit trocar um arquivo inteiro sugere upload de uma cópia local antiga. Com isso, se perdeu:

   | Perdido | Consequência |
   |---|---|
   | leitura de `RANDOM_SEED` | rodadas não reprodutíveis; o README continuava documentando a variável |
   | leitura de `SIM_STEPS` | passos fixos em `world.run(until=20)` |
   | `PADE_HOST`, `PADE_PORT`, `OMNET_DIR` | `pade:5678` e `/omnet-dir` fixos; o cenário só rodava dentro do Docker |
   | `network_mode: "service:pade"` e `PYTHONUNBUFFERED` | volta da rede `sim_net`; a correção para o Docker-in-Docker do GitHub Codespaces deixou de valer |
   | semântica da malha | a malha voltou a usar `pade_star.py`, com N+1 agentes e só o central enviando; o `menu.py` prometia outra coisa |
   | espera pela porta do PADE e escrita atômica do NED | possíveis condições de corrida na inicialização |

   Além disso, o compose passou a rodar `pip install pandas matplotlib plotly kaleido` **sem versão** a cada subida do `mosaik_master`. O `kaleido` não era usado.

2. **Mock C++ desatualizado.** O `AgentNode.cc` novo usa APIs do OMNeT++ (`cComponentType`, `getComponentType()`, `getArrivalGate()`, `cGate::getIndex()`) que o `omnetpp.h` simulado do teste não tinha. O código estava certo; o teste é que não compilava.

O que foi preservado da `development`: a física do `AgentNode.cc`, o sincronismo do `MosaikBridge.cc`, o `omnet_wrapper.py` (com handshake e retry) e os plots de estrela e anel mantiveram as correções de outubro.

---

## 3. Alterações, commit a commit

### 3.1 `d96ee23` — build(deps): gerencia as dependências Python com uv

**Motivo.** Não havia arquivo de dependências para o host. As imagens instalavam pandas, numpy, matplotlib, plotly e pade-agents sem versão.

**O que mudou**

- `pyproject.toml` com um grupo por contexto:

  | Grupo | Onde é usado | Conteúdo |
  |---|---|---|
  | `dependencies` | host: menus | streamlit, plotly |
  | `pade` | container `pade` | mosaik-api-v3 3.0.14, twisted 24.7.0, autobahn 23.6.2, pyzmq 27.1.0, pade-agents 3.0, ipython 8.26.0 |
  | `mosaik` | container `mosaik_master` | mosaik 3.6.0, mosaik-api-v3, mosaik-csv 2.0.1, pyzmq, pandas, matplotlib, plotly, numpy |
  | `dev` | testes no host (padrão do `uv sync`) | pytest, ziglang e os grupos `pade` e `mosaik` |

- `uv.lock` com as versões exatas de 88 pacotes e `.python-version` fixando o **Python 3.12**. O `pade-agents` 3.0 exige Python ≥ 3.12; o README dizia ≥ 3.10.
- `pade-dir/requirements.txt` e `mosaik-dir/requirements.txt` exportados do lock. Os Dockerfiles passaram a fazer `pip install -r requirements.txt`.
- **Dependência oculta encontrada:** o teste C++ compila com `python -m ziglang c++` e precisava do `ziglang`, que não estava declarado.

**Verificação.** O lock resolveu sem conflitos. O Streamlit 1.67 resolvido aceita o `use_container_width` usado no menu. No Docker, as imagens foram construídas a partir dos `requirements.txt`.

### 3.2 `d4cfbf0` — fix(cosim): restaura correções perdidas na development e volta a suíte ao verde (fase 0)

**O que mudou**

- `mosaik-dir/scenario.py`: voltaram `RANDOM_SEED`, `SIM_STEPS`, `PADE_HOST`, `PADE_PORT` e `OMNET_DIR`, a resolução IPv4, a espera pela porta do PADE e a escrita atômica do NED. Os padrões reproduzem o comportamento do Docker. A malha voltou a usar `pade_malha.py` e `plot_results_malha.py`, com N agentes no total.
- `docker-compose.yml`: voltaram `network_mode: "service:pade"`, `PADE_HOST`/`OMNET_HOST=127.0.0.1`, `RANDOM_SEED`, `SIM_STEPS` e `PYTHONUNBUFFERED`; o despacho da malha voltou para o `pade_malha.py`; saiu o `pip install` feito a cada subida.
- `pade_arvore.py` e `pade_hibrida.py`: passaram a ler `PADE_PORT`/`AMS_PORT` e ganharam o substituto de `fcntl`, sem o qual não rodavam no Windows. O substituto precisa ficar **depois** dos imports do PADE; se o Twisted o encontrar ao ser importado, entra no caminho POSIX e quebra.
- **Mock C++:** ganhou as 4 APIs novas e casos de meio guiado (Fibra) e de roteamento multi-salto.
- **Emulador ZMQ:** reescrito para seguir o `AgentNode.cc`. Antes, mandava cada mensagem para todos os vizinhos e conhecia 5 canais. Agora:
  - endereça pelos `receivers`;
  - roteia por BFS de próximo salto, desempatando pela menor porta;
  - calcula a perda a cada salto (PER e atenuação espacial);
  - trata o meio guiado;
  - modela fila finita de 5 por porta e o tempo de transmissão;
  - conta `packets_forwarded`;
  - lê os **12 canais do `Profiles.ned`**.
- **Testes E2E:** generalizados para as 5 topologias, com testes novos de **árvore** (2,2,2: 15 nós) e **híbrida** (3/1/3: 16 nós), aceitando os gráficos em SVG.

**Verificação.** Suíte 6 de 6. Compose validado com `docker compose config`.

### 3.3 `73f6df1` — chore(repo): organiza o repositório e atualiza a documentação (fase 1)

**O que mudou**

- **Saídas fora do git:** `results.csv`, gráficos, `DynamicNetwork.ned`, `posicoes.json`, `links.json`, `config.json` e `pade_agents/logs/` foram para o `.gitignore`. Os PNGs de rodadas antigas foram apagados, entre eles `grafico_trafego_IoT.png`, de uma tecnologia descontinuada.
- **Pastas novas:** as imagens da interface foram para `assets/`; os scripts legados, com `git mv`, para `examples/legacy/`, com um README.
- **`omnet-dir/Network.ned` → `MosaikBridge.ned`:** ficou só a declaração usada.
- **Removidos:** `githubicone.png`, `icone-linkedin.png` e `agent_example_1_mosaik_updated.py` (o original vem no `pade-agents`; o PADE 3.0 do PyPI é idêntico ao `master` do `grei-ufc/pade`).
- **`CMD` do Dockerfile do PADE:** passou de `pade_sim.py` para `pade_star.py`.
- **Documentação:** README reescrito para a `development`; **CHANGELOG.md** e **CONTRIBUTING.md** novos. O CONTRIBUTING traz a regra de atualizar a branch antes de editar, em vez de substituir arquivos por cópias antigas.

**Verificação.** Suíte 6 de 6. Streamlit carregando os ícones de `assets/`. Rodar os testes não suja mais o `git status`.

### 3.4 `da7fe54` — fix(hibrida): torna a topologia híbrida reprodutível com a mesma semente

**Causa.** `_calcular_malha_parcial`, duplicada no `scenario.py` e no `pade_hibrida.py`, devolvia um `set` de arestas, e a ordem de iteração de um `set` de strings muda a cada processo do Python. Com a mesma semente, os enlaces RF mesh saíam em outra ordem, o que mudava as portas no OMNeT++, o desempate das rotas e os resultados.

**O que mudou.** A função passou a devolver as arestas **ordenadas**, nas duas cópias.

**Verificação.** Duas rodadas seguidas geraram arquivos idênticos (15 de 15). As outras topologias não mudaram.

### 3.5 `54a3faa` — refactor: remove a duplicação entre os scripts PADE e de plotagem (fase 2)

**O que mudou**

- **`pade_bridge.py`** reúne o que estava copiado nos 5 scripts PADE: o substituto de `fcntl`, as portas, o modelo `PadeAgent`, o `MosaikSim`, a tradução ACL↔JSON e o agente base `AgenteCosim`.
- **`pade_hierarquico.py`** reúne o agente de árvore e híbrida, que eram o mesmo código com nomes trocados.
- **`plot_camadas.py`** unifica os dashboards de árvore e híbrida (605 linhas cada, só 34 diferentes). Foi gerado por substituições exatas, para manter o corpo idêntico. `plot_results_arvore.py` e `plot_results_hibrida.py` viraram pontos de entrada de poucas linhas.
- **`plot_comum.py`** reúne `caminho_omnet` (idêntico nos 5 plots), `exportar_paineis_separados` (idêntico em 4) e o dicionário de rótulos.

**Verificação.** Saídas idênticas às de antes, nas 5 topologias (74 de 74). Suíte 6 de 6.

### 3.6 `00afa50` — refactor(cosim): fonte única para topologias, catálogo e perfis de canal (fase 3)

**O que mudou.** Um pacote novo, **`cosim/`**, que só usa a biblioteca padrão:

| Módulo | Conteúdo | Usado por |
|---|---|---|
| `cosim/topologias.py` | `montar_estrela/malha/anel/arvore/hibrida`, que devolvem uma `Rede` (nós, posições, enlaces, metadados); `vizinhos()`, `vizinhos_anel()` e o mapeamento de nomes PADE↔OMNeT++ | `scenario.py` e agentes PADE |
| `cosim/catalogo.py` | topologias (rótulo, descrição, scripts, mínimo de agentes) e tecnologias (rótulo e cor) | menus, `scenario.py`, plots e testes |
| `cosim/canais.py` | leitura do `Profiles.ned` e descrições legíveis | menus e emulador |

Com isso:
- O `scenario.py` caiu de 580 para 315 linhas.
- O PADE tira os vizinhos dos mesmos enlaces que vão para o NED.
- Os menus descrevem as tecnologias a partir do `Profiles.ned`. O Wireless aparece agora como **300 Mbps · ~2 ms · 0,1%**, em vez dos "100 Mbps · ~15 ms · 3%" que o Streamlit mostrava.
- As cores do preview do Streamlit seguem as dos dashboards.
- O projeto virou pacote instalável, com o `cosim` dentro. No compose, `./cosim` é montado em `/opt/cosim`, com `PYTHONPATH`, nos containers `pade` e `mosaik_master`.
- **`tests/test_consistencia.py`**, novo: 27 verificações em menos de 1 s.

**Verificação.** Saídas idênticas (74 de 74). Suíte 33 de 33. Streamlit e `menu.py` verificados.

### 3.7 `5e6c4b8` — feat(saida): OUTPUT_DIR opcional para as saídas de cada rodada (fase 4, escopo reduzido)

**O que mudou.** Com `OUTPUT_DIR`, o `scenario.py` grava os resultados, os gráficos e uma cópia da rede numa pasta própria da rodada. Sem a variável, nada muda. Os testes E2E passaram a usar uma pasta temporária do pytest.

**Verificação.** Saídas idênticas (74 de 74). Suíte 33 de 33.

### 3.8 `9c6d830` — ci: GitHub Actions, pre-commit e lint mínimo com ruff (fase 5)

**O que mudou**

- **`.github/workflows/testes.yml`**, com dois jobs:
  1. *verificações*: `uv lock --check`; `requirements.txt` em dia com o lock; `uv sync --frozen`; ruff; `docker compose config -q`; testes de consistência;
  2. *E2E*: a suíte completa, sem Docker.

  Ações fixadas: `actions/checkout@v7` e `astral-sh/setup-uv@v10.3.3`.
- **`.pre-commit-config.yaml`**: os hooks básicos do `pre-commit-hooks` v6.0.0, incluindo o bloqueio de arquivos acima de 1 MB, e hooks locais para ruff, lock e `requirements.txt`.
- **ruff e pre-commit** no grupo `dev`, com lint restrito a `E9` e `F`.
- **Avisos antigos:** os 10 que já existiam foram corrigidos, sem mudar comportamento: f-strings sem placeholder e imports sem uso nos menus.

**Verificação.** Todos os hooks e os passos do workflow passam localmente. O workflow só roda no GitHub depois do push.

### 3.9 `45fd083` — fix(omnet): OMNeT++ abortava na topologia híbrida ao reagendar endTx

**Sintoma** (no Docker):

```
<!> Error: scheduleAt(): Message (omnetpp::cMessage)endTx_1 is currently scheduled,
use cancelEvent() before rescheduling -- in module (AgentNode) DynamicNetwork.sub0, at t=5.00011656s
```

**Causa.** Com encaminhamento multi-salto, um pacote podia chegar no instante exato em que a transmissão anterior terminava, antes de o `endTx` pendente ser processado. Com o canal já livre e a fila vazia, o `transmitPacket` transmitia de novo e reagendava o `endTx` ainda agendado. No caminho de injeção, o erro era engolido pelo `catch (...)` de `processInjectedData`; no de encaminhamento, não.

**O que mudou.** A porta só é considerada livre sem `endTx` pendente; senão, o pacote entra na fila e o próprio `endTx` o transmite, no mesmo instante. O mock C++ passou a recusar reagendamento, como o OMNeT++, e ganhou o caso de teste 7.

**Verificação.** O teste falha com o código antigo e passa com o novo. Todas as rodadas no Docker da [seção 6.3](#63-execução-real-no-docker) terminaram sem erro.

### 3.10 `3dc5fe8` — chore(omnet): tira do git o Makefile regenerado a cada subida do container

**O que mudou.** O `opp_makemake -f` do container sobrescrevia o `Makefile` versionado a cada subida (mesmo conteúdo, outros finais de linha), e o `git status` ficava sujo. O arquivo saiu do índice e foi para o `.gitignore`.

**Verificação.** Depois de uma rodada no Docker, o `git status` fica limpo.

---

## 4. Decisões tomadas

Cada decisão traz o contexto, as alternativas consideradas, a escolha e o porquê, e o custo ou o caminho para reverter. A tabela resume; os detalhes vêm em seguida.

| ID | Decisão | Onde | Reversível? |
|---|---|---|---|
| D1 | Partir da `development`, não da `main` | toda a branch | — |
| D2 | Restaurar as correções perdidas na `development` | `d4cfbf0` | sim, mas reintroduz os bugs |
| D3 | Voltar à rede compartilhada `service:pade` | `d4cfbf0` | sim |
| D4 | Malha com N agentes no total e todos enviando | `d4cfbf0` | sim |
| D5 | uv como fonte das versões; containers com pip e `requirements.txt` exportados | `d96ee23` | sim |
| D6 | Fixar o Python em 3.12 | `d96ee23` | sim |
| D7 | Saídas geradas fora do git | `73f6df1` | sim |
| D8 | Legados em `examples/legacy/`, não apagados | `73f6df1` | sim |
| D9 | Não renomear pastas nem pontos de entrada | toda a branch | — |
| D10 | Refatorações sem mudar nenhuma saída, provado por comparação | `54a3faa`, `00afa50`, `5e6c4b8` | — |
| D11 | Preservar diferenças de comportamento que parecem acidentais | `54a3faa` | ver pontos em aberto |
| D12 | Emulador fiel ao `AgentNode.cc`, com canais do `Profiles.ned` | `d4cfbf0` | sim |
| D13 | Pacote `cosim/` instalável no host e montado nos containers | `00afa50` | sim |
| D14 | `Profiles.ned` como fonte das descrições dos canais | `00afa50` | sim |
| D15 | Cores dos dashboards como cores oficiais | `00afa50` | sim |
| D16 | `OUTPUT_DIR` opcional, com escopo reduzido | `5e6c4b8` | sim |
| D17 | Lint mínimo (só erros reais) e hooks locais | `9c6d830` | sim |
| D18 | CI sem Docker | `9c6d830` | sim |
| D19 | Corrigir o `endTx` tratando o evento pendente como porta ocupada | `45fd083` | sim |
| D20 | Tirar o `Makefile` do git; manter `AgentPacket_m.*` | `3dc5fe8` | sim |
| D21 | Commits temáticos, sem push e sem *upstream* | toda a branch | — |

### 4.1 Base e escopo

**D1 — Partir da `development`, não da `main`.**
- **Contexto:** a análise começou na `main`, mas a `development` tinha 23 commits a mais com funcionalidades novas.
- **Alternativas:** refatorar na `main` e deixar a `development` se adaptar depois; ou esperar a `development` estabilizar.
- **Escolha e motivo:** a `development`. Refatorar a `main` criaria conflitos em praticamente todos os arquivos tocados pelas duas linhas de trabalho.
- **Custo:** esta branch altera arquivos em edição ativa na `development`, o que exige coordenação ([P2](#p2--coordenação-com-quem-trabalha-na-development)).

**D2 — Restaurar as correções perdidas, em vez de aceitar a `development` como estava.**
- **Contexto:** a suíte estava 0 de 4, e funcionalidades documentadas no README (`RANDOM_SEED`, `SIM_STEPS`) não funcionavam.
- **Alternativas:** aceitar a versão de 23/10 e só atualizar o README; ou reverter os commits de 23/10.
- **Escolha e motivo:** reaplicar as correções **sobre** o código novo, preservando as topologias árvore e híbrida. Reverter apagaria trabalho legítimo, e aceitar manteria rodadas não reprodutíveis, ruim para trabalho científico.
- **Cuidado:** os valores padrão foram escolhidos para que, dentro do Docker, o comportamento fosse igual ao da `development`.

**D9 — Não renomear pastas nem pontos de entrada.**
- **Alternativas consideradas:** `mosaik-dir/` → `mosaik/` e equivalentes; layout `src/` completo, como no pandas; renomear `menu-streamlit.py`.
- **Escolha e motivo:** nada disso. O pedido era não mudar a forma de usar, e as renomeações quebrariam compose, testes, menus, documentação e hábitos do grupo. Além disso, pastas chamadas `mosaik/` ou `pade/` na raiz podem confundir os imports dos pacotes pip de mesmo nome.

### 4.2 Docker e ambiente

**D3 — Voltar à rede compartilhada (`network_mode: "service:pade"`).**
- **Contexto:** os commits de 23/10 voltaram para a rede bridge `sim_net`, com DNS entre containers.
- **Alternativas:** manter a `sim_net`.
- **Escolha e motivo:** restaurar. Era a correção explícita de 22/10 para o Docker-in-Docker do GitHub Codespaces, onde o DNS entre containers falha. Foi validada no Docker local com todas as topologias.
- **Custo:** os três serviços compartilham as mesmas portas, então a 5555 do OMNeT++ e as do PADE (5678 em diante) não podem colidir. Os serviços também não podem ser escalados separadamente. Para reverter, basta trocar o `network_mode` por `networks: [sim_net]` e os hosts por `omnet_sim`/`pade`.

**D5 — uv como fonte das versões; containers com pip e `requirements.txt` exportados.**
- **Alternativas:** usar o uv dentro das imagens (`uv sync` no Dockerfile); ou manter listas soltas de `pip install`.
- **Escolha e motivo:** exportar o lock para `requirements.txt` e manter o pip nos Dockerfiles. Usar o uv nas imagens exigiria mudar o diretório de build do compose para a raiz, para elas enxergarem o `pyproject.toml`, e mexeria mais na infraestrutura.
- **Custo:** um passo de exportação. Está automatizado no pre-commit e verificado no CI, e não é preciso lembrar dele.

**D6 — Fixar o Python em 3.12 (`==3.12.*`).**
- **Motivo:** o `pade-agents` 3.0 exige Python ≥ 3.12, e as imagens usam o 3.12.11; o host fica igual aos containers. O uv baixa a versão certa sozinho.
- **Custo:** para mudar de versão, é preciso atualizar o `pyproject.toml`, o `.python-version` e as imagens juntos.

**D13 — `cosim/` instalável no host e montado nos containers.**
- **Alternativas:** copiar o `cosim` para dentro de cada imagem; montá-lo dentro de `/app`; ou usar `PYTHONPATH` também no host.
- **Escolha e motivo:**
  - **no host**, o projeto virou pacote (hatchling) e o `uv sync` instala o `cosim` em modo editável, sem variáveis extras;
  - **nos containers**, um volume em `/opt/cosim` com `PYTHONPATH`. Não dá para copiar para as imagens, porque o build de cada uma só enxerga a própria subpasta. E montar dentro de `/app` criaria pastas vazias no host.
- **Custo:** um `docker run` direto, sem o compose, não encontra o `cosim`.

### 4.3 Organização do repositório

**D7 — Saídas geradas fora do git.**
- **Alternativas:** mantê-las versionadas, como registro dos resultados.
- **Escolha e motivo:** tirar. Elas eram reescritas a cada rodada e pelos testes, sujavam o `git status` e já estavam desatualizadas (PNG da tecnologia IoT, descontinuada). Os projetos de referência fazem o mesmo; o tsre-der-opentes usa uma pasta `output/` fora do git.
- **Custo:** figuras para artigos precisam ser copiadas para a pasta do artigo, e, ao atualizar um clone, o git apaga as cópias locais ([seção 8.3](#83-atenção-ao-atualizar-um-clone-existente)).

**D8 — Legados em `examples/legacy/`, não apagados.**
- **Alternativas:** apagar de vez, já que o histórico do git os preserva.
- **Escolha e motivo:** mover, com `git mv`, para o grupo ainda poder consultá-los facilmente. A exceção foi `agent_example_1_mosaik_updated.py`, apagado porque o original vem no pacote `pade-agents`.
- **Custo:** se ninguém mais os usa, podem ser apagados depois ([P13](#p13--apagar-os-legados)).

**D20 — Tirar o `Makefile` do git; manter `AgentPacket_m.*`.**
- **Motivo:** o `Makefile` é sempre recriado pelo `opp_makemake -f` antes de compilar, então versioná-lo só gerava ruído. Os arquivos `AgentPacket_m.cc/.h` também são gerados (pelo `opp_msgtool`), mas foram mantidos, por cautela, até haver uma verificação específica ([P11](#p11--arquivos-gerados-agentpacket_m)).

### 4.4 Refatoração e preservação do comportamento

**D10 — Nenhuma saída pode mudar nas refatorações.**
- **Alternativas:** confiar só nos testes E2E, que conferem propriedades gerais (contagens, presença de arquivos).
- **Escolha e motivo:** comparar as saídas antes e depois, arquivo por arquivo, com semente fixa ([seção 6.2](#62-comparação-das-saídas-antes-e-depois)). Os E2E não pegariam, por exemplo, uma mudança na ordem das mensagens que alterasse latências.
- **Efeito colateral:** foi essa comparação que revelou o bug de reprodutibilidade da híbrida (D10 → `da7fe54`).

**D11 — Preservar diferenças de comportamento que parecem acidentais.**
- **Casos:**
  - árvore e híbrida mantêm a inscrição no AMS do PADE, e as outras três a desligam;
  - a ordem dos rótulos usada como fallback de cores no anel e na malha;
  - os plotters de estrela, anel e malha continuam separados.
- **Escolha e motivo:** numa refatoração, unificar essas diferenças mudaria o comportamento sem uma decisão do grupo. Cada caso ficou explícito no código (por exemplo, o atributo `LIMPAR_COMPORTAMENTOS_SISTEMA`) e listado como ponto em aberto.

**D12 — Emulador fiel ao `AgentNode.cc`.**
- **Alternativas:** só atualizar a lista de canais do emulador antigo, que mandava cada mensagem para todos os vizinhos.
- **Escolha e motivo:** reescrever o núcleo para seguir o C++ (receivers, BFS, perda por salto, meio guiado, fila) e ler os canais do `Profiles.ned`. Sem isso, os testes de árvore e híbrida não testariam o roteamento.
- **Limite aceito:** continua uma aproximação. Resolve os eventos dentro do passo e não modela o `endTx`, e isso deixou passar o bug que só o Docker revelou ([P8](#p8--fidelidade-do-emulador)).

**D19 — Corrigir o `endTx` tratando o evento pendente como porta ocupada.**
- **Alternativas:** cancelar o `endTx` pendente (`cancelEvent`) e reagendá-lo.
- **Escolha e motivo:** tratar a porta como ocupada. O pacote entra na fila e sai no mesmo instante, pelo próprio `endTx`, então o tempo de envio não muda e a lógica da fila não é tocada. Cancelar e reagendar alteraria a ordem dos eventos.

### 4.5 Dados e interface

**D4 — Malha com N agentes no total, todos enviando para todos.**
- **Contexto:** na `development`, a malha usava o comportamento da estrela, com N+1 agentes.
- **Escolha e motivo:** voltar à semântica da `main`, documentada no README, no `menu.py` e na tabela de correções de 22/10. O `pade_malha.py` e o `plot_results_malha.py` existiam e estavam sem uso.

**D14 — `Profiles.ned` como fonte das descrições dos canais.**
- **Contexto:** o Streamlit descrevia o Wireless com valores diferentes dos simulados.
- **Alternativas:** corrigir só o texto do Wireless; ou mudar o `Profiles.ned` para bater com o texto.
- **Escolha e motivo:** gerar as descrições do arquivo que o OMNeT++ de fato usa. Assim a interface não pode mais divergir da simulação.
- **Pendência:** qual dos dois valores do Wireless é o pretendido ([P3](#p3--valores-do-wireless)).

**D15 — Cores dos dashboards como cores oficiais.**
- **Contexto:** o preview do Streamlit e os dashboards usavam cores diferentes para os mesmos canais de árvore e híbrida.
- **Escolha e motivo:** adotar as dos dashboards, que já aparecem nas figuras do artigo. Mudar as dos dashboards alteraria as figuras publicadas.

**D16 — `OUTPUT_DIR` opcional, com escopo reduzido.**
- **Alternativas:** a proposta completa, com `output/` por padrão, uma subpasta por rodada e integração com o Streamlit.
- **Escolha e motivo:** só a parte que não muda o padrão e que pode ser verificada sem a interface. A versão completa depende da aba Resultados do Streamlit e de testes com Docker ([P9](#p9--pastas-de-saída-por-rodada)).

### 4.6 Qualidade

**D17 — Lint mínimo e hooks locais.**
- **Alternativas:** adotar um conjunto completo de regras de estilo e formatação.
- **Escolha e motivo:** só erros reais (`E9`, `F`). Um formatador ou regras de estilo gerariam um diff enorme no código de outras pessoas e conflitos com a `development`. Os hooks são locais, para usar o ruff e o uv do lock, nas mesmas versões do CI.

**D18 — CI sem Docker.**
- **Alternativas:** construir as imagens e rodar uma co-simulação no CI.
- **Escolha e motivo:** a imagem do OMNeT++ tem 2,37 GB, e baixá-la e construí-la a cada execução do CI leva vários minutos; o emulador cobre o fluxo em ~5 min, sem Docker.
- **Custo:** bugs como o do `endTx` não são pegos pelo CI ([P7](#p7--teste-com-docker-no-ci)).

**D21 — Commits temáticos, sem push e sem *upstream*.**
- **Motivo:** cada commit é autocontido e revisável isoladamente. A branch não acompanha a `development` para que um `git push` acidental não altere a branch compartilhada. O envio fica a critério de quem mantém o repositório.

---

## 5. Discussão

### 5.1 A causa da regressão é de processo, não de código

As regressões da `development` não vieram de um erro de programação, mas de **substituir arquivos inteiros por cópias locais** feitas a partir de uma versão antiga. Corrigir o código resolve o caso, mas não impede que se repita. Por isso a refatoração também mexeu no processo:
- a regra explícita no CONTRIBUTING;
- o CI, que rodaria a suíte no pull request e acusaria a regressão antes do merge;
- os testes de consistência, que acusam quando catálogo, `Profiles.ned` e compose divergem.

Nenhuma dessas medidas funciona se o pull request não for revisado com o CI verde. É uma prática do grupo, não uma garantia técnica.

### 5.2 Refatorar com prova de equivalência

As fases 2, 3 e 4 mudaram muito código (mais de 4 mil linhas entre adições e remoções) sem mudar nenhuma saída. Isso foi possível porque, **antes** de refatorar, foi montada uma referência determinística de todas as saídas de cada topologia. O custo foi pequeno (5 minutos por rodada) diante do risco evitado, e o processo ainda revelou um bug real (a híbrida não reprodutível). Fica como recomendação para mudanças futuras que não deveriam alterar resultados.

### 5.3 O emulador é útil, mas não substitui o OMNeT++

O emulador permite rodar a suíte inteira em ~5 min, sem Docker, inclusive no CI. A rodada no Docker real, porém, encontrou um bug que o emulador nunca encontraria (o `endTx`), porque ele não modela aquele detalhe do OMNeT++. As duas camadas são complementares:
- o emulador, para o dia a dia e o CI;
- rodadas periódicas no Docker real, antes de releases e de gerar resultados para artigos.

Uma forma de tornar o Docker viável no CI é publicar a imagem do OMNeT++ pronta ([P7](#p7--teste-com-docker-no-ci)).

### 5.4 Abstração: menos código, mais conceitos

A duplicação caiu bastante (PADE de 1.396 para 294 linhas por topologia, mais 447 de base comum), mas quem chega ao projeto agora precisa conhecer mais conceitos: `AgenteCosim`, `AgenteHierarquico`, `Rede`, catálogo, `TopologiaEmCamadas`. O CONTRIBUTING tem o roteiro de "nova topologia", mas vale apresentar a nova estrutura ao grupo antes de seguir desenvolvendo.

### 5.5 Pontos frágeis que ficaram

- **Rede compartilhada (D3):** todos os serviços usam as mesmas portas; um conflito aparece como erro de bind no container.
- **`cosim` por volume (D13):** depende do compose; quem usar `docker run` direto precisa montar o volume.
- **Lista de atributos do protocolo:** `val_in`, `val_out`, `packets_*` etc. continuam repetidos em cinco lugares (`AgentNode.ned`, `MosaikBridge.cc`, `META` do wrapper, `scenario.py` e `collector.py`). Mudar um sem mudar os outros quebra a troca de dados. É o próximo alvo natural de unificação ([P10](#p10--empacotar-a-ponte-omnet--mosaik)).
- **`use_container_width`:** o menu Streamlit usa esse parâmetro, marcado como obsoleto. O lock fixa uma versão que o aceita; atualizar o Streamlit no futuro pode exigir trocá-lo.

### 5.6 Relação com o trabalho em andamento

Esta branch toca arquivos que estão em evolução em outras frentes: a `development` e a `iee13-barras`, de 18/11. Quanto mais tempo ela ficar sem integração, maior o custo de juntar as linhas de trabalho. A recomendação é decidir rápido [P1](#p1--integrar-a-branch-iee13-barras) e [P2](#p2--coordenação-com-quem-trabalha-na-development).

---

## 6. Como as alterações foram verificadas

### 6.1 Suítes de teste

| Momento | Resultado |
|---|---|
| `development` original | **0/4** |
| depois da fase 0 (`d4cfbf0`) | 6/6 (1 teste C++ com 6 casos + 5 E2E) |
| depois da fase 3 (`00afa50`) em diante | **33/33** (27 de consistência + 1 C++ + 5 E2E) |
| depois de `45fd083` | 33/33 (o teste C++ passa a ter 7 casos) |

### 6.2 Comparação das saídas, antes e depois

- **Referência:** cada topologia rodou com `RANDOM_SEED=42` e 20 passos (estrela 20, malha 5, anel 5, árvore 2,2,2, híbrida 3/1/3), e todos os arquivos produzidos foram guardados.
- **Determinismo dos SVGs:** `SOURCE_DATE_EPOCH=0` e `svg.hashsalt` fixo.
- **Critério:** o `results.csv` comparado pelo conteúdo (linhas ordenadas, porque a ordem segue o hash aleatório do Python); os demais arquivos, byte a byte.
- **Conferência da comparação:** antes de usar a referência, ela foi gerada duas vezes, para confirmar que era determinística. Foi isso que revelou a híbrida não reprodutível.

| Comparação | Resultado |
|---|---|
| antes × depois da fase 2 | 74/74 iguais |
| antes × depois da fase 3 | 74/74 iguais |
| antes × depois da fase 4 | 74/74 iguais |

### 6.3 Execução real no Docker

- **Imagens:** `omnet_sim` com 2,37 GB, `pade` com 901 MB e `mosaik_master` com 648 MB.
- **Todas as rodadas** usaram `docker compose up --force-recreate --abort-on-container-exit --exit-code-from mosaik_master`, com `RANDOM_SEED=42` e 20 passos.

| Rodada | Nós | Resultado | Enviados | Recebidos | Encaminhados | Descartados |
|---|---:|---|---:|---:|---:|---:|
| estrela, 3 periféricos | 4 | código 0 | 108 | 102 | 0 | 6 |
| estrela, 20 periféricos | 21 | código 0 | 708 | 655 | 0 | 53 |
| malha, 5 | 5 | código 0 | 380 | 347 | 0 | 33 |
| anel, 5 | 5 | código 0 | 190 | 172 | 0 | 18 |
| árvore 2,2,2 | 15 | código 0 | 537 | 497 | 357 | 40 |
| árvore 3,2,4 (padrão) | 34 | código 0 | 1.315 | 1.208 | 1.036 | 107 |
| híbrida 3/1/3, antes de `45fd083` | 16 | **abortou em t ≈ 5 s** | — | — | — | — |
| híbrida 3/1/3 | 16 | código 0 | 602 | 573 | 555 | 29 |
| híbrida 3/3/5 (padrão) | 58 | código 0 | 1.932 | 1.673 | 2.511 | 259 |

Também foram verificados:
- **Rede compartilhada:** o Mosaik achou o PADE e o OMNeT++ em `127.0.0.1`.
- **Compilação:** o OMNeT++ compilou com o `MosaikBridge.ned`.
- **Caminho pelo menu:** `menu.py` → `docker compose up --build` → "Co-simulação concluída com sucesso".
- **`git status` limpo** depois de uma rodada.
- **Fim de rodada normal:** o OMNeT++ sai com "Interrupted system call" e o PADE com código 137, porque o compose derruba os containers quando o Mosaik termina.

### 6.4 Outras verificações

- **Streamlit:** `AppTest` renderizou as 4 topologias da interface sem exceção.
- **`menu.py`:** percorrido até o resumo.
- **Modo local sem Docker:** emulador, PADE e `scenario.py` como processos separados geraram todos os arquivos esperados.
- **Ferramentas:** `docker compose config -q`, `uv lock --check` e pre-commit em todos os arquivos passam.

### 6.5 O que não foi verificado

- Uma simulação disparada **pela interface Streamlit**, clicando em "Iniciar simulação". O comando do compose é o mesmo testado pelo `menu.py`.
- O workflow rodando no GitHub; ele só roda depois do push.
- A execução com OMNeT++ instalado nativamente, fora do Docker.

---

## 7. Números: antes e depois

| Grupo de arquivos | `development` | agora |
|---|---:|---:|
| Scripts PADE das 5 topologias | 1.396 linhas | 294 |
| Bases PADE (`pade_bridge.py`, `pade_hierarquico.py`) | — | 447 |
| Plots (5 `plot_results_*.py`) | 2.610 | 1.333 |
| Bases dos plots (`plot_comum.py`, `plot_camadas.py`) | — | 637 |
| `mosaik-dir/scenario.py` | 580 | 315 |
| Pacote `cosim/` | — | 539 |
| Testes (suítes + emulador) | 973 | 1.330 |
| `omnet-dir/AgentNode.cc` | 333 | 340 |
| Arquivos versionados | 72 | 68 |
| Saídas geradas versionadas | 20 | 0 |
| Testes passando | 0/4 | 33/33 |

---

## 8. O que muda para quem usa o projeto

### 8.1 Comandos

- **Primeira vez:** `uv sync`. Depois, rode os comandos com `uv run`, por exemplo `uv run streamlit run menu-streamlit.py` ou `uv run python menu.py`. Com o `.venv` ativado, os comandos antigos continuam funcionando.
- **Testes:** `uv run pytest -v` (as duas suítes, ~5 min) ou `uv run pytest -v tests/test_consistencia.py` (menos de 1 s).
- **Docker:** os mesmos comandos. Na primeira vez depois do merge, rode `docker compose build`, porque os Dockerfiles mudaram.
- **Quem contribui:** `uv run pre-commit install`, uma vez por clone.

### 8.2 Comportamento diferente da `development`

| Antes, na `development` | Agora |
|---|---|
| `RANDOM_SEED` ignorado: rodadas não reprodutíveis | respeitado no Python e no C++ |
| `SIM_STEPS` ignorado (sempre 20) | respeitado |
| malha com N+1 agentes e só o central enviando | N agentes, todos enviando para todos |
| híbrida diferente a cada execução com a mesma semente | reprodutível |
| híbrida podia abortar no OMNeT++ | corrigido |
| `mosaik_master` instalava pacotes da internet a cada subida | sobe mais rápido e não depende de internet |
| Streamlit: Wireless "100 Mbps · ~15 ms · 3%" | "300 Mbps · ~2 ms (σ 0,5 ms) · 0,1%", o que o `Profiles.ned` simula |

As descrições das topologias foram unificadas entre os dois menus, e as cores dos canais de árvore e híbrida no preview do Streamlit seguem as dos dashboards.

### 8.3 Atenção ao atualizar um clone existente

- **Saídas e `Makefile`:** depois do merge, o git **remove** do diretório de trabalho as saídas que deixaram de ser versionadas (`results.csv`, gráficos em `mosaik-dir/`, JSONs e NED em `omnet-dir/`, `logs/`) e o `omnet-dir/Makefile`. Todos são recriados na próxima rodada. **Copie antes qualquer gráfico que queira guardar.**
- **Arquivos movidos:** os scripts legados estão em `examples/legacy/`, e as imagens da interface, em `assets/`.

### 8.4 Para quem desenvolve

- **Nova topologia:** a rede vai em `cosim/topologias.py` e no catálogo; o `scenario.py` só chama a função nova; o PADE usa `AgenteCosim` e tira os vizinhos da mesma rede; os plots usam `plot_comum.py`, ou `plot_camadas.py` para topologias em camadas. Cada topologia nova ganha um teste E2E e casos de consistência. O roteiro completo está no CONTRIBUTING.
- **Canal novo:** vai no `Profiles.ned` e em `cosim/catalogo.py`. O teste de consistência acusa se um dos dois faltar.

---

## 9. Pontos em aberto

Os pontos estão ordenados por prioridade. Cada um traz a situação atual, as opções, uma recomendação e o que falta para decidir.

| ID | Tema | Tipo | Prioridade |
|---|---|---|---|
| P1 | Integrar a branch `iee13-barras` | integração | **alta** |
| P2 | Coordenação com quem trabalha na `development` | processo | **alta** |
| P3 | Valores do Wireless | dados da simulação | **alta** |
| P4 | Inscrição no AMS do PADE | comportamento | média |
| P5 | Malha no Streamlit | interface | média |
| P6 | `CITATION.cff` e o `.zip` do artigo | governança | média |
| P7 | Teste com Docker no CI | qualidade | média |
| P8 | Fidelidade do emulador | qualidade | baixa |
| P9 | Pastas de saída por rodada | funcionalidade | baixa |
| P10 | Empacotar a ponte OMNeT++ ↔ Mosaik | arquitetura | estratégica |
| P11 | Arquivos gerados `AgentPacket_m.*` | organização | baixa |
| P12 | Padronizar e unificar os plots de estrela, anel e malha | código | baixa |
| P13 | Apagar os legados | organização | baixa |
| P14 | Despacho de scripts no compose | código | baixa |
| P15 | Regras de lint e formatação | qualidade | baixa |
| P16 | Testar a interface Streamlit de ponta a ponta | verificação | média |

### P1 — Integrar a branch `iee13-barras`

- **Situação:** o commit `61829e2` (18/11/2026) traz a topologia IEEE 13 barras do co-simulation-opentes (18 agentes: concentrador, DSO, mercado e 15 barras; `pade_ieee13.py`, `ieee13_plot.py`) e os canais `Link_6TiSCH` e `Link_WiSUN`. A branch parte de `298aedf` (22/10), anterior à `development` e a esta refatoração.
- **Conflitos esperados:** no `scenario.py` (agora baseado no `cosim`), no `docker-compose.yml` e no `Profiles.ned`. Os canais novos também precisam entrar em `cosim/catalogo.py`, senão o teste de consistência falha. E o commit versiona saídas outra vez (`results.csv`, PNGs, JSONs, `logs/events.csv`).
- **Opções:**
  1. um merge direto da `iee13-barras`, resolvendo os conflitos;
  2. reaplicar a IEEE 13 sobre a estrutura nova: `montar_ieee13` em `cosim/topologias.py`, agentes derivados de `AgenteCosim`, plot com `plot_comum.py` e um teste E2E;
  3. adiar.
- **Recomendação:** a opção 2, depois do merge desta branch. Dá menos conflito do que parece, porque a lógica nova se concentra em funções de montagem e agentes, e o resultado já fica testado.
- **Para decidir:** quem cuida da IEEE 13 e a ordem dos merges.

### P2 — Coordenação com quem trabalha na `development`

- **Situação:** esta branch altera arquivos modificados recentemente na `development`: `scenario.py`, `docker-compose.yml`, `AgentNode.cc`, `pade_arvore.py`, `pade_hibrida.py`, plots e `menu-streamlit.py`.
- **Opções:**
  1. congelar a `development` até o merge;
  2. fazer o merge rápido e todos atualizarem as branches depois;
  3. revisão conjunta do pull request.
- **Recomendação:** a opção 3, com o pull request aberto o quanto antes e as seções 2.2, 4 e 8 deste relatório como guia.
- **Para decidir:** uma data para revisão e merge.

### P3 — Valores do Wireless

- **Situação:** os menus agora seguem o `Profiles.ned`: 300 Mbps, delay ~2 ms (σ 0,5 ms), PER 0,1%. Antes, o Streamlit mostrava 100 Mbps, ~15 ms e 3%.
- **Opções:**
  1. manter o `Profiles.ned` como está;
  2. alterar o `Profiles.ned` para os valores que o Streamlit mostrava.
- **Recomendação:** confirmar com quem definiu os perfis e com o texto do artigo. Na opção 2, os resultados com Wireless mudam, e as figuras precisariam ser refeitas.
- **Para decidir:** qual dos dois valores representa a tecnologia pretendida.

### P4 — Inscrição no AMS do PADE

- **Situação:** árvore e híbrida mantêm os comportamentos de sistema do PADE (conexão e inscrição `IDENT` no AMS); estrela, malha e anel os desligam. Isso afeta só o plano de controle do PADE, não as mensagens que passam pelo OMNeT++.
- **Opções:** desligar nas cinco, padronizando como na estrela; ou manter.
- **Recomendação:** desligar nas cinco, mudando `LIMPAR_COMPORTAMENTOS_SISTEMA` em `pade_hierarquico.py` e confirmando com a comparação de saídas. Antes, convém perguntar se a árvore ou a híbrida usam o AMS de propósito.
- **Para decidir:** se há uso intencional do AMS.

### P5 — Malha no Streamlit

- **Situação:** o menu Streamlit da `development` oferece estrela, anel, árvore e híbrida, sem malha; o `menu.py` e o backend continuam com ela.
- **Opções:** recolocar a malha no Streamlit; ou retirá-la também do `menu.py` e do backend.
- **Recomendação:** recolocar. É pouco trabalho (o catálogo já tem a malha) e os dois menus ficam coerentes.
- **Para decidir:** se a retirada no Streamlit foi intencional.

### P6 — `CITATION.cff` e o `.zip` do artigo

- **`CITATION.cff`:** não foi criado, por falta da lista de autores e da forma de citação. Pandas e scikit-learn têm um; é importante para um projeto acadêmico.
- **`artigo-overleaf/`:** guarda um `.zip` de 1,4 MB e figuras dentro do repositório de código. O pre-commit agora bloqueia arquivos acima de 1 MB.
- **Opções para o artigo:** um repositório próprio, que o Overleaf sincroniza via git; manter só a fonte LaTeX e as figuras, sem o `.zip`; ou manter como está.
- **Recomendação:** um repositório próprio para o artigo.
- **Para decidir:** os autores e a decisão sobre o artigo, a cargo de quem mantém `artigo-overleaf/`.

### P7 — Teste com Docker no CI

- **Situação:** o CI roda com o emulador (D18), então bugs que só aparecem no OMNeT++ real não são pegos.
- **Opções:**
  1. publicar a imagem do OMNeT++ (OMNeT++ 6.0, ZMQ e a ponte) no GitHub Container Registry e rodar uma rodada curta no CI;
  2. rodar o Docker manualmente antes de releases;
  3. um job semanal que constrói tudo.
- **Recomendação:** começar pela 2, documentada como passo de release, e partir para a 1 junto com P10.
- **Para decidir:** quanto tempo de CI é aceitável.

### P8 — Fidelidade do emulador

- **Situação:** o emulador resolve todos os eventos dentro do passo, não modela o `endTx` e usa outro gerador aleatório, então os números não batem com os do OMNeT++.
- **Opções:** modelar mais detalhes; ou aceitar como teste de integração e não de resultados.
- **Recomendação:** aceitar e deixar claro que resultados para artigos vêm do Docker. Modelar o `endTx` é possível, mas só vale a pena se o emulador passar a ser usado para estudos.

### P9 — Pastas de saída por rodada

- **Situação:** o `OUTPUT_DIR` existe (D16), mas a aba Resultados do Streamlit lê `mosaik-dir/` e o compose não expõe a variável.
- **Opções:** uma pasta `output/<data>_<topologia>/` por rodada, com o Streamlit listando as rodadas anteriores; ou manter como está.
- **Recomendação:** implementar junto com uma revisão da aba Resultados. Isso permite comparar rodadas e guardar a configuração com os resultados. Exige testes da interface com Docker.

### P10 — Empacotar a ponte OMNeT++ ↔ Mosaik

- **Situação:** o núcleo reutilizável é o adaptador Python (`omnet_wrapper.py`), a ponte C++/NED (`MosaikBridge`, `AgentNode`, `AgentPacket.msg`, `Profiles.ned`), o protocolo JSON (`create`/`connect`/`step`) e os extras (`pade_bridge.py`, `cosim/`, o emulador). Ainda há acoplamentos com esta aplicação:
  - a porta 5555 fixa no `MosaikBridge.cc`;
  - o mapeamento `AgenteCentral`/`AgenteP_` e o formato FIPA-ACL no `AgentNode.cc`;
  - as constantes da física no código;
  - a lista de atributos repetida em cinco lugares.
- **Opções:**
  1. **etapa 1:** um *workspace* do uv neste repositório, com `packages/mosaik-omnetpp/` em layout `src`, os desacoplamentos acima e uma especificação do protocolo;
  2. **etapa 2:** um repositório próprio (`grei-ufc/mosaik-omnetpp`), pacote no PyPI e imagem no GitHub Container Registry, com este repositório virando o estudo de caso;
  3. **git submodules:** não recomendados para o Python (uma dependência do uv é melhor) e só justificáveis para o C++ se alguém precisar compilar a ponte dentro de outro projeto OMNeT++.
- **Antes de publicar:** posicionar o trabalho em relação ao **cosima**, da OFFIS, que também integra OMNeT++ (com INET) ao Mosaik. As diferenças deste projeto são o nó leve sem INET, o sincronismo REQ/REP auditado por `mosaik_step`, a integração com o PADE, o foco em Docker e o emulador.
- **Para decidir:** se o grupo quer publicar a ponte (e em que prazo), se vai se diferenciar do cosima ou contribuir com ele, e quem mantém. Os nomes `mosaik-omnetpp` e `omnetpp-mosaik` estavam livres no PyPI em 19/11/2026.

### P11 — Arquivos gerados `AgentPacket_m.*`

- **Situação:** são gerados a partir do `AgentPacket.msg` durante o `make`, mas continuam versionados (D20).
- **Recomendação:** tirar do git depois de confirmar, com uma rodada no Docker, que o `make` os regenera num clone limpo.

### P12 — Padronizar e unificar os plots de estrela, anel e malha

- **Situação:** os três têm estrutura parecida, mas paletas e painéis diferentes; a malha ainda gera PNG.
- **Opções:** unificar num plotter genérico, como foi feito com `plot_camadas.py`; ou só converter a malha para SVG.
- **Recomendação:** converter a malha para SVG primeiro, como as outras. Unificar os três muda as figuras, então só vale se o grupo aceitar refazer as do artigo.

### P13 — Apagar os legados

- **Situação:** os arquivos em `examples/legacy/` não são mantidos nem testados (D8).
- **Recomendação:** apagar depois de confirmar que ninguém os usa como referência; o histórico do git os preserva.

### P14 — Despacho de scripts no compose

- **Situação:** a escolha do script PADE por topologia é um `if/elif` em shell no compose. Um teste garante que bate com o catálogo.
- **Opção:** um ponto de entrada Python que lê o catálogo (por exemplo, `python -m cosim.despacho pade`), eliminando a lista do compose.
- **Recomendação:** fazer junto com P1, já que a IEEE 13 vai exigir mais um ramo no `if/elif`.

### P15 — Regras de lint e formatação

- **Situação:** só erros reais (D17).
- **Opções:** adotar `ruff format` e regras de estilo; ou manter como está.
- **Recomendação:** se o grupo quiser, aplicar a formatação num único commit dedicado, logo depois dos merges pendentes, para não gerar conflitos.

### P16 — Testar a interface Streamlit de ponta a ponta

- **Situação:** a interface foi testada até a renderização, mas não com uma simulação disparada por ela.
- **Recomendação:** uma pessoa do grupo roda uma simulação de cada topologia pela interface e confere a aba Resultados. São uns 5 minutos com as imagens já construídas.

---

## 10. Como revisar e integrar

**Ordem sugerida de revisão.** A dos commits, porque cada um é autocontido:

1. `d96ee23` (uv)
2. `d4cfbf0` (regressões; o mais importante para quem trabalha na `development`)
3. `73f6df1` (organização)
4. `da7fe54` e `45fd083` (correções de simulação)
5. `54a3faa` e `00afa50` (refatorações, com o comportamento verificado)
6. `5e6c4b8`, `9c6d830` e `3dc5fe8`

**Reproduzir as verificações**

```bash
uv sync
uv run pytest -v                         # 33 testes, ~5 min
uv run pre-commit run --all-files        # lint, lock, requirements, yaml/toml
docker compose build
TOPOLOGY=hibrida RANDOM_SEED=42 docker compose up --abort-on-container-exit --exit-code-from mosaik_master
```

**Integração sugerida**

1. Decidir P2 e abrir o pull request de `refactor/organizacao-repositorio` para a `development`. O push dispara o CI.
2. Depois do merge, cada pessoa roda `uv sync`, `uv run pre-commit install` e `docker compose build`.
3. Tratar P1 (IEEE 13) e P3 (Wireless) em seguida.

---

## Apêndice A: os 10 commits

| # | Commit | Título | Arquivos | Linhas |
|---:|---|---|---:|---|
| 1 | `d96ee23` | build(deps): gerencia as dependências Python com uv | 7 | +1.592 / −22 |
| 2 | `d4cfbf0` | fix(cosim): restaura correções perdidas na development e volta a suíte ao verde | 6 | +709 / −394 |
| 3 | `73f6df1` | chore(repo): organiza o repositório e atualiza a documentação | 40 | +286 / −4.838 |
| 4 | `da7fe54` | fix(hibrida): torna a topologia híbrida reprodutível com a mesma semente | 2 | +8 / −3 |
| 5 | `54a3faa` | refactor: remove a duplicação entre os scripts PADE e de plotagem | 17 | +1.256 / −2.399 |
| 6 | `00afa50` | refactor(cosim): fonte única para topologias, catálogo e perfis de canal | 22 | +929 / −778 |
| 7 | `5e6c4b8` | feat(saida): OUTPUT_DIR opcional para as saídas de cada rodada | 4 | +49 / −28 |
| 8 | `9c6d830` | ci: GitHub Actions, pre-commit e lint mínimo com ruff | 9 | +279 / −11 |
| 9 | `45fd083` | fix(omnet): OMNeT++ abortava na topologia híbrida ao reagendar endTx | 3 | +50 / −1 |
| 10 | `3dc5fe8` | chore(omnet): tira do git o Makefile regenerado a cada subida do container | 2 | +2 / −136 |

O `uv.lock` responde pela maior parte das linhas adicionadas no commit 1 (1.352). As remoções do commit 3 são, em grande parte, saídas geradas que deixaram de ser versionadas.

---

## Apêndice B: arquivos criados, movidos e removidos

**Criados**

| Arquivo | Commit | Conteúdo |
|---|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | `d96ee23` | dependências e versão do Python |
| `pade-dir/requirements.txt`, `mosaik-dir/requirements.txt` | `d96ee23` | dependências dos containers, exportadas do lock |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `examples/legacy/README.md` | `73f6df1` | documentação |
| `omnet-dir/MosaikBridge.ned` | `73f6df1` | declaração do módulo da ponte (antes em `Network.ned`) |
| `pade-dir/pade_agents/pade_bridge.py`, `pade_hierarquico.py` | `54a3faa` | bases comuns dos agentes PADE |
| `mosaik-dir/plot_comum.py`, `plot_camadas.py` | `54a3faa` | bases comuns dos plots |
| `cosim/__init__.py`, `topologias.py`, `catalogo.py`, `canais.py` | `00afa50` | fonte única de topologias, catálogo e perfis de canal |
| `tests/test_consistencia.py` | `00afa50` | testes rápidos de consistência |
| `.github/workflows/testes.yml`, `.pre-commit-config.yaml` | `9c6d830` | CI e pre-commit |
| `docs/RELATORIO_DE_ALTERACOES.md` | este relatório | — |

**Movidos (com histórico preservado)**

| De | Para |
|---|---|
| `LOGO.png`, `server-svgrepo-com.svg`, `laptop-minimalistic-svgrepo-com.svg`, `router-bottom-1112-svgrepo-com.svg` | `assets/` |
| `mosaik-dir/first.py`, `star.py`, `mosaik_anel.py`, `plot_results.py` | `examples/legacy/mosaik/` |
| `pade-dir/pade_agents/pade_sim.py` | `examples/legacy/pade/` |
| `omnet-dir/Network.ned` | `omnet-dir/MosaikBridge.ned` (só a declaração usada) |

**Removidos do repositório**

| Arquivo | Motivo |
|---|---|
| `githubicone.png`, `icone-linkedin.png` | sem uso |
| `pade-dir/pade_agents/agent_example_1_mosaik_updated.py` | o original vem no pacote `pade-agents` |
| `mosaik-dir/grafico_malha.png`, `grafico_trafego.png`, `grafico_trafego_IoT.png` | saídas antigas, de tecnologia ou nome descontinuados |
| `mosaik-dir/grafico_trafego_{2G,4G,5G,Anel,Cabeada,Geral,Wireless}.png`, `mosaik-dir/results.csv` | saídas geradas; agora no `.gitignore` |
| `omnet-dir/DynamicNetwork.ned`, `posicoes.json`, `links.json`, `config.json` | gerados a cada rodada pelo `scenario.py`; agora no `.gitignore` |
| `pade-dir/pade_agents/logs/*.csv` | gerados pelo `data_logger` do PADE; agora no `.gitignore` |
| `omnet-dir/Makefile` | regenerado pelo `opp_makemake -f` a cada subida do container; agora no `.gitignore` |

**Principais arquivos alterados:** `docker-compose.yml`, `mosaik-dir/scenario.py`, `mosaik-dir/Dockerfile`, `pade-dir/Dockerfile`, os 5 `pade_<topologia>.py`, os 5 `plot_results_*.py`, `omnet-dir/AgentNode.cc`, `menu.py`, `menu-streamlit.py`, `tests/test_validation_suite.py`, `tests/omnet_zmq_emulator.py`, `README.md` e `.gitignore`.
