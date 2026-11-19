# Como contribuir

## Branches

- A `main` recebe só merges vindos da `development`, por pull request.
- Trabalhe numa branch criada a partir da `development` atualizada e abra o pull request para a `development`.
- **Antes de editar, atualize sua branch** (`git pull` ou `git merge origin/development`). Não substitua arquivos inteiros por cópias locais antigas: isso desfaz, sem aviso, correções que outras pessoas já integraram.

## Ambiente

```bash
uv sync                                   # cria o .venv/ com as versões do uv.lock
uv run streamlit run menu-streamlit.py    # interface web
uv run pytest -v tests/                   # suíte de validação
```

Rode a suíte antes de abrir o pull request. Ela não precisa de Docker: um emulador faz o papel do OMNeT++. Ao criar uma topologia, adicione um teste E2E para ela em `tests/test_validation_suite.py`.

## Dependências

Use `uv add` / `uv remove` (com `--group pade` ou `--group mosaik` para os containers) em vez de editar versões à mão. Depois de mudar um grupo dos containers, regenere os `requirements.txt` conforme a seção "Gerenciamento de dependências" do README e faça commit de `pyproject.toml`, `uv.lock` e dos `requirements.txt` juntos.

## O que não vai para o git

Saídas de cada rodada (`results.csv`, `grafico_*`, `DynamicNetwork.ned`, `posicoes.json`, `links.json`, `config.json`, `pade_agents/logs/`) e o `.venv/` estão no `.gitignore`. Figuras para artigos devem ser copiadas para a pasta do artigo.

## Mensagens de commit

Prefira mensagens curtas e descritivas, no padrão já usado no histórico: `fix(docker): ...`, `feat: ...`, `docs: ...`.
