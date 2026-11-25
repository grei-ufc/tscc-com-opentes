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

A rede vem de cosim.topologias.montar_arvore, a mesma que o scenario.py usa
para gerar o DynamicNetwork.ned. O comportamento dos agentes (telemetria
multi-salto, poll e heartbeat) é o mesmo da topologia híbrida e está em
pade_hierarquico.py.

ENV VARS
--------
ARVORE_FANOUT   ex.: "3,2,4"  (padrão) — filhos por nível
CELULAR_ARVORE  2g | 3g | 4g | 5g  (padrão 4g)
"""

import os

from cosim.topologias import montar_arvore
from pade_hierarquico import AgenteHierarquico, config_rede, iniciar_rede

ARVORE_FANOUT = os.environ.get('ARVORE_FANOUT', '3,2,4')
CELULAR_ARVORE = os.environ.get('CELULAR_ARVORE', '4g').lower()


class AgenteArvoreFIPA(AgenteHierarquico):
    RAIZ = 'raiz'
    ROTULO_RAIZ = 'RAIZ'
    ONT_LOCAL = 'arvore_restrita'         # heartbeat vizinho-a-vizinho (interior)
    ONT_TELEMETRIA = 'arvore_telemetria'  # leituras e polls multi-salto
    CONFIG_REDE = config_rede(montar_arvore(ARVORE_FANOUT, CELULAR_ARVORE))


if __name__ == '__main__':
    iniciar_rede(AgenteArvoreFIPA)
