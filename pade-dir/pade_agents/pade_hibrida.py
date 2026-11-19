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

O comportamento dos agentes (telemetria multi-salto, poll e heartbeat) é o
mesmo da topologia árvore e está em pade_hierarquico.py.

IMPORTANTE: usa random.Random(SEMENTE_HIBRIDA) com a mesma sequência de
chamadas que scenario.py/_montar_hibrida() para reproduzir as posições e
os vizinhos RF mesh exatos.

ENV VARS
--------
SUBESTACOES        int  (padrão 3)
CONCENTRADORES     int  (padrão 3)  — por subestação
MEDIDORES_CLUSTER  int  (padrão 5)  — por concentrador
CELULAR_HIBRIDA    str  '2g'|'3g'|'4g'|'5g'  (padrão '4g')
SEMENTE_HIBRIDA    int  (padrão 42)
"""

import math
import os
import random
from itertools import combinations

from pade_bridge import PORTA_BASE
from pade_hierarquico import AgenteHierarquico, iniciar_rede

SUBESTACOES         = int(os.environ.get('SUBESTACOES',        3))
CONCENTRADORES      = int(os.environ.get('CONCENTRADORES',     3))
MEDIDORES_CLUSTER   = int(os.environ.get('MEDIDORES_CLUSTER',  5))
CELULAR_HIBRIDA     = os.environ.get('CELULAR_HIBRIDA', '4g').lower()
SEMENTE_HIBRIDA     = int(os.environ.get('SEMENTE_HIBRIDA',    42))


# ── Helpers de geometria / malha (DEVE ser idêntico ao scenario.py) ───────────

def _ponto_no_disco(rng, cx, cy, r):
    ang = rng.uniform(0, 2 * math.pi)
    rad = r * math.sqrt(rng.random())
    return cx + rad * math.cos(ang), cy + rad * math.sin(ang)


def _calcular_malha_parcial(ids, pos, k_neigh=4, raio=60.0):
    arestas: set = set()
    for i in ids:
        candidatos = sorted(
            (j for j in ids if j != i),
            key=lambda j: math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]),
        )
        for j in candidatos[:k_neigh]:
            d = math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1])
            if raio is None or d <= raio:
                arestas.add(tuple(sorted((i, j))))

    pai = {i: i for i in ids}

    def find(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for a, b in arestas:
        pai[find(a)] = find(b)

    pares = sorted(
        combinations(ids, 2),
        key=lambda p: math.hypot(pos[p[0]][0] - pos[p[1]][0],
                                 pos[p[0]][1] - pos[p[1]][1]),
    )
    for a, b in pares:
        if find(a) != find(b):
            pai[find(a)] = find(b)
            arestas.add(tuple(sorted((a, b))))

    # Ordenado, como no scenario.py: iterar o set dependeria do hash aleatório do Python.
    return sorted(arestas)


# ── Construção da configuração de rede ────────────────────────────────────────

def _gerar_config_hibrida():
    """
    Reconstrói CONFIG_REDE espelhando exatamente scenario.py/_montar_hibrida().
    Usa a mesma semente aleatória para obter posições idênticas e, portanto,
    os mesmos vizinhos RF mesh.
    """
    rng = random.Random(SEMENTE_HIBRIDA)
    config: dict = {}
    porta_counter = [PORTA_BASE]

    def prox_porta():
        p = porta_counter[0]
        porta_counter[0] += 1
        return p

    config['cco'] = {'port': prox_porta(), 'vizinhos': []}

    subs = []
    pos_subs = {}
    for i in range(SUBESTACOES):
        ang = 2 * math.pi * i / SUBESTACOES
        sid = f'sub{i}'
        sx  = 2500 * math.cos(ang)
        sy  = 2500 * math.sin(ang)
        config[sid] = {'port': prox_porta(), 'vizinhos': []}
        subs.append(sid)
        pos_subs[sid] = (sx, sy)

    n = len(subs)
    if n >= 3:
        for i in range(n):
            a, b = subs[i], subs[(i + 1) % n]
            if b not in config[a]['vizinhos']:
                config[a]['vizinhos'].append(b)
            if a not in config[b]['vizinhos']:
                config[b]['vizinhos'].append(a)
    elif n == 2:
        config[subs[0]]['vizinhos'].append(subs[1])
        config[subs[1]]['vizinhos'].append(subs[0])

    for s in subs[:2]:
        if s not in config['cco']['vizinhos']:
            config['cco']['vizinhos'].append(s)
        if 'cco' not in config[s]['vizinhos']:
            config[s]['vizinhos'].append('cco')

    for i, sid in enumerate(subs):
        sx, sy = pos_subs[sid]
        for j in range(CONCENTRADORES):
            cid = f'con{i}_{j}'
            cx, cy = _ponto_no_disco(rng, sx, sy, 700)
            config[cid] = {'port': prox_porta(), 'vizinhos': [sid]}
            config[sid]['vizinhos'].append(cid)

            cluster = [cid]
            cluster_pos = {cid: (cx, cy)}
            for k in range(MEDIDORES_CLUSTER):
                mid = f'med{i}_{j}_{k}'
                mx, my = _ponto_no_disco(rng, cx, cy, 150.0)
                config[mid] = {'port': prox_porta(), 'vizinhos': []}
                cluster.append(mid)
                cluster_pos[mid] = (mx, my)

            for a, b in _calcular_malha_parcial(cluster, cluster_pos, k_neigh=4, raio=60.0):
                if b not in config[a]['vizinhos']:
                    config[a]['vizinhos'].append(b)
                if a not in config[b]['vizinhos']:
                    config[b]['vizinhos'].append(a)

    return config


class AgenteHibridaFIPA(AgenteHierarquico):
    RAIZ = 'cco'
    ROTULO_RAIZ = 'CCO'
    ONT_LOCAL = 'hibrida_restrita'        # heartbeat vizinho-a-vizinho (interior)
    ONT_TELEMETRIA = 'hibrida_telemetria'  # leituras e polls multi-salto
    CONFIG_REDE = _gerar_config_hibrida()


if __name__ == '__main__':
    iniciar_rede(AgenteHibridaFIPA)
