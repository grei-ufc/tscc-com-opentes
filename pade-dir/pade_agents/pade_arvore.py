#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_arvore.py — Agentes PADE para topologia Árvore Radial (IEC 61850 / AMI).

Hierarquia
----------
  raiz  (subestação raiz / RTU)
    └─ sub{d}_{i}  (subestação de nível d)
         └─ con{d}_{i}  (concentrador / DCU)
              └─ med{d}_{i}  (medidor / smart-meter)

O comportamento dos agentes (telemetria multi-salto, poll e heartbeat) é o
mesmo da topologia híbrida e está em pade_hierarquico.py.

ENV VARS
--------
ARVORE_FANOUT   ex.: "3,2,4"  (padrão) — filhos por nível
"""

import os

from pade_bridge import PORTA_BASE
from pade_hierarquico import AgenteHierarquico, iniciar_rede

ARVORE_FANOUT = os.environ.get('ARVORE_FANOUT', '3,2,4')


# ── Construção da configuração de rede ────────────────────────────────────────

def _gerar_config_arvore(fanout_str: str) -> dict:
    """
    Calcula CONFIG_REDE = {nome: {port, vizinhos}} para toda a árvore.
    Idêntico ao estado anterior; apenas exposto aqui para referência.
    """
    fan = [int(v) for v in fanout_str.split(',')]
    prefixos = ['sub', 'con', 'med']
    config = {}
    porta_counter = [PORTA_BASE]

    def prox_porta():
        p = porta_counter[0]
        porta_counter[0] += 1
        return p

    config['raiz'] = {'port': prox_porta(), 'vizinhos': []}
    nivel_atual = ['raiz']

    for d, f in enumerate(fan):
        idx = min(d, 2)
        nivel_proximo = []
        for pai_nome in nivel_atual:
            for _ in range(f):
                nid = f"{prefixos[idx]}{d + 1}_{len(nivel_proximo)}"
                config[nid] = {'port': prox_porta(), 'vizinhos': [pai_nome]}
                config[pai_nome]['vizinhos'].append(nid)
                nivel_proximo.append(nid)
        nivel_atual = nivel_proximo

    return config


class AgenteArvoreFIPA(AgenteHierarquico):
    RAIZ = 'raiz'
    ROTULO_RAIZ = 'RAIZ'
    ONT_LOCAL = 'arvore_restrita'       # heartbeat vizinho-a-vizinho (interior)
    ONT_TELEMETRIA = 'arvore_telemetria'  # leituras e polls multi-salto
    CONFIG_REDE = _gerar_config_arvore(ARVORE_FANOUT)


if __name__ == '__main__':
    iniciar_rede(AgenteArvoreFIPA)
