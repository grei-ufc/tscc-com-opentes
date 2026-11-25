# Scripts legados

Versões anteriores da co-simulação, guardadas só como referência. **Não são mantidas
nem testadas**, e não rodam a partir desta pasta: esperam estar em `mosaik-dir/` ou
`pade-dir/pade_agents/` e usam caminhos e hosts fixos do Docker (`/omnet-dir`, `pade:5678`).

| Arquivo | O que era | Substituído por |
|---|---|---|
| `mosaik/first.py` | cenário ponto a ponto com 2 agentes em 5G | `mosaik-dir/scenario.py` |
| `mosaik/star.py` | cenário só da topologia estrela | `mosaik-dir/scenario.py` (`TOPOLOGY=estrela`) |
| `mosaik/mosaik_anel.py` | cenário só da topologia anel | `mosaik-dir/scenario.py` (`TOPOLOGY=anel`) |
| `mosaik/plot_results.py` | dashboard do cenário ponto a ponto | `mosaik-dir/plot_results_*.py` |
| `pade/pade_sim.py` | agentes PADE do cenário ponto a ponto | `pade-dir/pade_agents/pade_*.py` |

O exemplo oficial de integração PADE + Mosaik, no qual o projeto se baseou, vem
dentro do próprio pacote `pade-agents`, em `pade/tests/mosaik_example/`
(repositório [grei-ufc/pade](https://github.com/grei-ufc/pade)).
