#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_hibrida.py — Agentes PADE para topologia Híbrida em camadas (IEC 61850 + AMI).

Hierarquia
----------
  cco           (Centro de Controle Operacional)
    └─ sub{i}   (Subestação — anel de fibra + estrelas celulares)
         └─ con{i}_{j}  (Concentrador / DCU — backhaul celular)
              └─ med{i}_{j}_{k} (Medidor inteligente — RF mesh parcial)

A rede (posições e vizinhos RF mesh) vem de cosim.topologias.montar_hibrida
com a mesma semente que o scenario.py usa, então os vizinhos de cada agente
são exatamente os enlaces do DynamicNetwork.ned. O comportamento dos agentes
(telemetria multi-salto, poll e heartbeat) é o mesmo da topologia árvore e
está em pade_hierarquico.py.

ENV VARS
--------
SUBESTACOES        int  (padrão 3)
CONCENTRADORES     int  (padrão 3)  — por subestação
MEDIDORES_CLUSTER  int  (padrão 5)  — por concentrador
CELULAR_HIBRIDA    str  '2g'|'3g'|'4g'|'5g'  (padrão '4g')
SEMENTE_HIBRIDA    int  (padrão 42)
"""

import os

from cosim.topologias import montar_hibrida
from pade_hierarquico import AgenteHierarquico, config_rede, iniciar_rede

SUBESTACOES       = int(os.environ.get('SUBESTACOES', 3))
CONCENTRADORES    = int(os.environ.get('CONCENTRADORES', 3))
MEDIDORES_CLUSTER = int(os.environ.get('MEDIDORES_CLUSTER', 5))
CELULAR_HIBRIDA   = os.environ.get('CELULAR_HIBRIDA', '4g').lower()
SEMENTE_HIBRIDA   = int(os.environ.get('SEMENTE_HIBRIDA', 42))


class AgenteHibridaFIPA(AgenteHierarquico):
    RAIZ = 'cco'
    ROTULO_RAIZ = 'CCO'
    ONT_LOCAL = 'hibrida_restrita'         # heartbeat vizinho-a-vizinho (interior)
    ONT_TELEMETRIA = 'hibrida_telemetria'  # leituras e polls multi-salto
    CONFIG_REDE = config_rede(montar_hibrida(SUBESTACOES, CONCENTRADORES, MEDIDORES_CLUSTER,
                                             CELULAR_HIBRIDA, SEMENTE_HIBRIDA))


if __name__ == '__main__':
    iniciar_rede(AgenteHibridaFIPA)
