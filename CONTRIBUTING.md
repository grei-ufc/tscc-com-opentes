# Como contribuir

## Branches

- A `main` recebe só merges vindos da `development`, por pull request.
- Trabalhe numa branch criada a partir da `development` atualizada e abra o pull request para a `development`.
- **Antes de editar, atualize sua branch** (`git pull` ou `git merge origin/development`). Não substitua arquivos inteiros por cópias locais antigas: isso desfaz, sem aviso, correções que outras pessoas já integraram.

## Ambiente

```bash
uv sync                                   # cria o .venv/ com as versões do uv.lock
uv run pre-commit install                 # ativa as verificações a cada commit (uma vez por clone)
uv run streamlit run menu-streamlit.py    # interface web
uv run pytest -v                          # suítes de teste
```

Rode a suíte antes de abrir o pull request. Ela não precisa de Docker: um emulador faz o papel do OMNeT++.

## Verificações automáticas

- **pre-commit** (`.pre-commit-config.yaml`), a cada commit: lint com ruff (erros de sintaxe e pyflakes), `uv.lock` em dia com o `pyproject.toml`, `requirements.txt` dos containers em dia com o `uv.lock` (o hook os regenera; basta adicioná-los ao commit), YAML/TOML válidos e nenhum arquivo acima de 1 MB.
- **CI** (`.github/workflows/testes.yml`), a cada push na `main`/`development` e em todo pull request: as mesmas verificações, os testes de consistência e, em seguida, a suíte E2E completa.

## Nova topologia

Não copie um script existente; reaproveite as bases comuns:

1. **Rede:** escreva `montar_<topologia>()` em `cosim/topologias.py`, devolvendo uma `Rede` (nós, enlaces e metadados). Use ordem determinística (listas ordenadas, nunca iterar um `set`), para que a mesma semente reproduza a mesma rodada. Registre a topologia em `TOPOLOGIAS` (`cosim/catalogo.py`); um canal novo vai no `Profiles.ned` e em `TECNOLOGIAS`.
2. **Mosaik:** chame a função em `montar_rede()` do `mosaik-dir/scenario.py`. NED, artefatos e conexões do Mosaik já são genéricos.
3. **PADE:** crie `pade-dir/pade_agents/pade_<topologia>.py` com uma subclasse de `AgenteCosim` (`pade_bridge.py`), definindo `ONTOLOGIAS`, `agir()` e `react()`, e inicie com `iniciar(agentes)`. Tire os vizinhos da mesma rede (`cosim.topologias.vizinhos`). Se for uma hierarquia raiz → subestação → concentrador → medidor, use `AgenteHierarquico` e `config_rede` (`pade_hierarquico.py`).
4. **Plotagem:** use `plot_comum.py`; para topologias em camadas, basta um `TopologiaEmCamadas` em `plot_camadas.py`.
5. **Despacho e testes:** inclua a topologia no despacho do `docker-compose.yml`, adicione um teste E2E em `tests/test_validation_suite.py` e casos de contagem em `tests/test_consistencia.py`. O teste de consistência acusa se o catálogo e o compose ficarem divergentes.

## Dependências

Use `uv add` / `uv remove` (com `--group pade` ou `--group mosaik` para os containers) em vez de editar versões à mão. Depois de mudar um grupo dos containers, regenere os `requirements.txt` conforme a seção "Gerenciamento de dependências" do README e faça commit de `pyproject.toml`, `uv.lock` e dos `requirements.txt` juntos.

## O que não vai para o git

Saídas de cada rodada (`results.csv`, `grafico_*`, `DynamicNetwork.ned`, `posicoes.json`, `links.json`, `config.json`, `pade_agents/logs/`) e o `.venv/` estão no `.gitignore`. Figuras para artigos devem ser copiadas para a pasta do artigo.

## Mensagens de commit

Prefira mensagens curtas e descritivas, no padrão já usado no histórico: `fix(docker): ...`, `feat: ...`, `docs: ...`.
