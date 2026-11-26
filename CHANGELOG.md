# Histórico de mudanças

Mudanças relevantes do projeto, da mais recente para a mais antiga.

## [Não lançado]

### Adicionado (integração com o mercado do OpenTES, 26/11/2026)
- **Modo de consulta por mensagem** (`ServidorConsulta.cc`, `consulta.ini`): cada envio de um agente vira uma consulta ZeroMQ e atravessa os AgentNodes da topologia. Mesmo contrato do servidor de rotas do `co-simulation-opentes`. O modo Mosaik não muda.
- **Canais do modelo da tese** `Link_6TiSCH_TSCH` (TSCH: slotframe, cells, fragmentação, retentativas) e `Link_WiSUN_FAN` (CSMA/CA), com o PER de cada enlace calculado por `cosim/radio.py` (Friis, Pister-Hack, tabela de PER, limiar). Os canais existentes continuam como estavam.
- `montar_ieee13`: posições lidas do `nodes_xy.csv`, topologia em malha, subestação por cabo ou por rádio, repetição de um `tisch_links.csv` e cells/taxa por enlace. Sem as opções, é a rede de antes.
- `cosim/ned.py` (escrita única do `DynamicNetwork.ned`, usada pelo `scenario.py`) e `cosim/ieee13.py` (rede do modo de consulta).
- AgentNode (`ExtensaoOpenTES.h`, incluído só quando presente): roteamento por ETX (`roteamento`), propagação nos meios não guiados configurável (`propagacao_radio_s_m`, padrão inalterado) e nomes de agentes por arquivo (`arquivo_nomes`).
- Testes de consistência do modelo de rádio, das opções da IEEE 13 e do NED gerado, e teste E2E da topologia `ieee13`.

### Restaurado
- O menu do terminal da `main` (`40d0ed8`): árvore e híbrida no terminal, dimensionamento, fan-out, rede celular, semente, tecnologia por agente e limpeza de resíduos, agora com a malha e as descrições lidas do `Profiles.ned`.
- A topologia `ieee13` executável da `iee13-barras`: `pade_ieee13.py`, `ieee13_plot.py`, despacho no compose e entrada no catálogo.

### Corrigido (integração com o OpenTES)
- Mensagem para destino sem rota, no modo Mosaik, passa a ser contada em `packets_dropped` em vez de sumir sem registro.

### Adicionado
- **Fonte única de verdade (fase 3):** pacote `cosim/`, instalado no `.venv` pelo `uv sync` e montado nos containers `pade` e `mosaik_master` (`/opt/cosim` + `PYTHONPATH`).
  - `cosim.topologias` monta cada rede uma única vez. O `scenario.py` gera o `DynamicNetwork.ned` a partir dela, e os agentes PADE tiram seus vizinhos dos mesmos enlaces. Acaba a cópia da geometria da híbrida no PADE, que precisava ser "idêntica ao scenario.py" à mão e calculava a malha RF com posições não arredondadas.
  - `cosim.catalogo` reúne topologias (rótulo, descrição, scripts PADE e de plotagem) e tecnologias (rótulo e cor), usados pelos menus, pelo `scenario.py`, pelos plots e pelos testes.
  - `cosim.canais` lê o `Profiles.ned`; os menus geram a descrição de cada tecnologia a partir dele.
- **CI** com GitHub Actions (`.github/workflows/testes.yml`): `uv.lock` e `requirements.txt` em dia, lint, `docker-compose.yml` válido, testes de consistência e suíte E2E, a cada push na `main`/`development` e em pull requests.
- **pre-commit** (`.pre-commit-config.yaml`) com as mesmas verificações. Ruff e pre-commit entram no grupo `dev`; o lint cobre só erros reais (`E9`, `F`).
- `OUTPUT_DIR` (opcional) no `scenario.py`: grava `results.csv`, gráficos e uma cópia da rede numa pasta própria da rodada. Sem a variável, nada muda. Os testes E2E passam a usar uma pasta temporária e não escrevem mais em `mosaik-dir/`.
- `tests/test_consistencia.py`: 27 verificações em menos de 1 s (catálogo × `Profiles.ned` × compose, contagens, conectividade e reprodutibilidade das topologias, vizinhança do PADE × enlaces).
- Gerenciamento de dependências com **uv**: `pyproject.toml`, `uv.lock` e `.python-version` (Python 3.12, o mesmo das imagens). Os containers instalam as versões travadas via `pade-dir/requirements.txt` e `mosaik-dir/requirements.txt`, exportados do lock.
- Testes E2E das topologias **árvore** e **híbrida**, com verificação de encaminhamento multi-salto (`packets_forwarded`).
- Testes C++ de **roteamento multi-salto** e de **meio guiado** (Fibra) no `AgentNode.cc`.
- `CONTRIBUTING.md`, este `CHANGELOG.md` e `examples/legacy/README.md`.

### Corrigido
- Regressões introduzidas na `development` em 23/10/2026 (`12801a9`, `277ab38`), que reescreveram o `scenario.py` e o `docker-compose.yml` a partir de uma versão anterior às correções de 22/10:
  - `RANDOM_SEED` e `SIM_STEPS` voltaram a ser respeitados (a semente era ignorada e os passos estavam fixos em 20).
  - `PADE_HOST`, `PADE_PORT` e `OMNET_DIR` voltaram ao `scenario.py`, que tinha `pade:5678` e `/omnet-dir` fixos e não rodava fora do Docker.
  - `network_mode: "service:pade"` voltou ao compose (correção para o GitHub Codespaces), junto com `PYTHONUNBUFFERED`.
  - A topologia `malha` voltou a usar `pade_malha.py` e `plot_results_malha.py`, com `NUM_PERIFERICOS` como total de agentes, como documentado no `menu.py`.
  - Voltaram a espera pela porta do PADE antes do `world.start('PadeSim')` e a escrita atômica do `DynamicNetwork.ned`.
- `pade_arvore.py` e `pade_hibrida.py` passaram a ler `PADE_PORT`/`AMS_PORT` e ganharam o shim de `fcntl`, sem o qual não rodavam no Windows.
- O mock C++ dos testes ganhou as APIs do OMNeT++ usadas pelo novo `AgentNode.cc` (`cComponentType`, `getArrivalGate()`, `cGate::getIndex()`).
- O emulador ZMQ dos testes passou a reproduzir o `AgentNode.cc` atual: endereçamento por `receivers`, roteamento BFS, perda por salto, meio guiado e os 12 canais lidos do `Profiles.ned`.
- **OMNeT++ abortava na topologia híbrida** (`scheduleAt(): Message endTx_N is currently scheduled`). Com encaminhamento multi-salto, um pacote podia chegar no instante em que a transmissão anterior terminava, antes de o `endTx` pendente ser processado. Com o canal já livre e a fila vazia, o `AgentNode::transmitPacket` transmitia de novo e reagendava o `endTx`. Agora a porta só é considerada livre sem `endTx` pendente; senão, o pacote entra na fila e sai no mesmo instante. Teste C++ novo (o mock passou a recusar reagendamento, como o OMNeT++). Verificado no Docker: estrela (3 e 20), malha, anel, árvore (2,2,2 e 3,2,4) e híbrida (3/1/3 e 3/3/5) terminam sem erro.
- O menu Streamlit descrevia o Wireless como "100 Mbps · ~15 ms · 3% perda", mas o `Profiles.ned` simula 300 Mbps, ~2 ms e 0,1%. As descrições dos dois menus agora são geradas do `Profiles.ned`.
- A topologia **híbrida** não era reprodutível com a mesma semente: os enlaces RF mesh vinham de um `set`, cuja ordem muda a cada processo (hash aleatório do Python), alterando portas e rotas. Agora saem ordenados.

### Alterado
- **Fim da duplicação de código (fase 2)**, sem mudar nenhuma saída: com semente fixa, `results.csv`, gráficos e arquivos de rede das 5 topologias são idênticos antes e depois.
  - `pade_bridge.py` concentra o que estava copiado nos 5 scripts PADE (shim de `fcntl`, configuração por ambiente, `MosaikSim`, tradução ACL↔JSON e o agente base `AgenteCosim`); cada `pade_<topologia>.py` define só o comportamento dos agentes.
  - `pade_hierarquico.py` reúne o agente de árvore e híbrida, que eram o mesmo código com nomes trocados.
  - `plot_camadas.py` reúne os dashboards de árvore e híbrida (~97% iguais); `plot_results_arvore.py` e `plot_results_hibrida.py` viraram pontos de entrada de poucas linhas.
  - `plot_comum.py` concentra `caminho_omnet`, `exportar_paineis_separados` e `NED_PARA_LABEL`, antes repetidos nos plots.
- Saídas geradas a cada rodada (`results.csv`, `grafico_*`, `DynamicNetwork.ned`, `posicoes.json`, `links.json`, `config.json`, `logs/` do PADE) saíram do git.
- Imagens da interface foram para `assets/`; scripts legados foram para `examples/legacy/`.
- `omnet-dir/Network.ned` virou `MosaikBridge.ned`, só com a declaração do módulo (a rede `CoSimulationNetwork` não era usada).
- O `mosaik_master` não roda mais `pip install pandas matplotlib plotly kaleido` a cada inicialização: as dependências vêm da imagem (o `kaleido` não era usado).
- O `CMD` padrão do container PADE aponta para `pade_star.py` (antes, `pade_sim.py`, legado).
- README atualizado para as 5 topologias, os 12 canais, o roteamento e os gráficos em SVG.

### Removido
- `githubicone.png` e `icone-linkedin.png` (a interface usa SVGs embutidos).
- `pade-dir/pade_agents/agent_example_1_mosaik_updated.py`: o exemplo original já vem no pacote `pade-agents`.
- PNGs de rodadas antigas, incluindo `grafico_trafego_IoT.png` (tecnologia descontinuada).

## development, 22–26/10/2026

- Topologias **árvore** (IEC 61850, fan-out por nível) e **híbrida** (CCO, anel de fibra, celular e RF mesh), com scripts PADE e de plotagem próprios.
- Roteamento multi-salto por BFS e contador `packets_forwarded` no `AgentNode.cc`/`MosaikBridge.cc`.
- 7 novos canais em `Profiles.ned` (Fibra, Celular 2G–5G, RF Mesh, PLC); Fibra e Cabeada como meio guiado.
- Gráficos em SVG e aba com os painéis individuais da visão geral no Streamlit.
- Handshake com retry no `omnet_wrapper.py`.
- Protótipo do artigo em `artigo-overleaf/`.

## Correções de 22/10/2026 (débitos técnicos resolvidos)

| Item | Solução implementada |
|---|---|
| Classificação de enlace nos dashboards | `scenario.py` persiste `omnet-dir/links.json` e os scripts de plotagem consultam o mapa real de enlaces |
| Alinhamento de `time_resolution` e `mosaik_step` | `MosaikBridge.cc` lê `time` e `time_resolution` do JSON de `step` e retorna `"mosaik_step": currentMosaikStep` no ACK ZMQ |
| Semântica unificada de `NUM_PERIFERICOS` | Unificada entre `menu.py`, `menu-streamlit.py`, `scenario.py` e scripts PADE (`N+1` na estrela; `N` total na malha e no anel) |
| Física de canal `cDatarateChannel` e `PER` | `AgentNode.cc` manipula `cDatarateChannel`/`cDelayChannel` via `par("delay")` e verifica `pkt->hasBitError()` além do BER espacial |
| Sincronismo de envio em memória no PADE | Removidos timers `call_later` assíncronos de parede em `pade_star.py` e `pade_malha.py` em favor de escrita síncrona em `val_out` no passo `t` |
| Rede entre containers no Codespaces | `omnet_sim` e `mosaik_master` usam o namespace de rede do `pade` (`network_mode: "service:pade"`) e se falam por `127.0.0.1` |
