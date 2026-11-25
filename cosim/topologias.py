"""
cosim.topologias — Montagem das redes de cada topologia.

Cada função devolve uma `Rede` (nós com posição, enlaces com o canal NED e
metadados para o config.json), sem efeitos colaterais. É a única definição
das topologias: o scenario.py (Mosaik) gera o DynamicNetwork.ned a partir dela
e os agentes PADE derivam seus vizinhos dos mesmos enlaces (`vizinhos`).

Reprodutibilidade: com o mesmo `rng`/semente, as funções devolvem exatamente
a mesma rede (listas em ordem determinística; nunca se itera um set).
"""

import itertools
import math
import random
from dataclasses import dataclass, field

from cosim.catalogo import canal_celular

__all__ = [
    'Rede', 'calcular_malha_parcial', 'montar_anel', 'montar_arvore', 'montar_ieee13',
    'montar_estrela', 'montar_hibrida', 'montar_malha', 'omnet_para_pade',
    'pade_para_omnet', 'ponto_no_disco', 'vizinhos', 'vizinhos_anel',
]


@dataclass
class Rede:
    nos: list                                   # [{'id', 'x', 'y', 'tipo', 'camada'}]
    links: list                                 # [{'origem', 'destino', 'tipo'}]
    config: dict = field(default_factory=dict)  # metadados extras para o config.json


def _link(origem, destino, tipo):
    return {'origem': origem, 'destino': destino, 'tipo': tipo}


# ══════════════════════════════════════════════════════════════
# NOMES DOS AGENTES (estrela / malha)
# ══════════════════════════════════════════════════════════════
# No OMNeT++ os nós são agent_central / agent_p_<i>; no PADE, AgenteCentral /
# AgenteP_<i>. As demais topologias usam o mesmo nome nos dois lados.
# (O AgentNode.cc faz o mesmo mapeamento em mapPadeToOmnet.)

def pade_para_omnet(nome_pade):
    if nome_pade == 'AgenteCentral':
        return 'agent_central'
    if nome_pade.startswith('AgenteP_'):
        return 'agent_p_' + nome_pade[len('AgenteP_'):]
    return nome_pade


def omnet_para_pade(eid):
    if eid == 'agent_central':
        return 'AgenteCentral'
    if eid.startswith('agent_p_'):
        return 'AgenteP_' + eid[len('agent_p_'):]
    return eid


# ══════════════════════════════════════════════════════════════
# ESTRELA E MALHA
# ══════════════════════════════════════════════════════════════

def _central_e_perifericos(num_perifericos, rng):
    """Central no centro do grid de 1000 × 1000 m; periféricos em posições aleatórias."""
    nos = [{'id': 'agent_central', 'x': 500.0, 'y': 500.0,
            'tipo': 'Central', 'camada': 'controle'}]
    for i in range(1, num_perifericos + 1):
        nos.append({
            'id':   f'agent_p_{i}',
            'x':    round(rng.uniform(0, 1000), 2),
            'y':    round(rng.uniform(0, 1000), 2),
            'tipo': 'Periferico', 'camada': 'periferico',
        })
    return nos


def montar_estrela(num_perifericos, tipos_rede, rng=random):
    """1 central + `num_perifericos` periféricos (total = N + 1); um enlace por
    periférico, com a tecnologia escolhida ciclicamente de `tipos_rede`."""
    nos = _central_e_perifericos(num_perifericos, rng)
    central = nos[0]['id']
    links = [_link(central, no['id'], tipos_rede[i % len(tipos_rede)])
             for i, no in enumerate(nos[1:])]
    return Rede(nos, links)


def montar_malha(total_agentes, tipos_rede, rng=random):
    """Malha completa com `total_agentes` nós (1 master + N-1 peers, mínimo 2):
    todo par (i, j), i < j, recebe um enlace — N(N-1)/2 enlaces."""
    nos = _central_e_perifericos(max(1, total_agentes - 1), rng)
    links = []
    for k, (a, b) in enumerate(itertools.combinations(nos, 2)):
        links.append(_link(a['id'], b['id'], tipos_rede[k % len(tipos_rede)]))
    return Rede(nos, links)


# ══════════════════════════════════════════════════════════════
# ANEL
# ══════════════════════════════════════════════════════════════

def montar_anel(total_agentes, tipos_rede):
    """agente_1..agente_N em círculo; cada um ligado ao próximo, fechando o ciclo."""
    centro_x, centro_y, raio = 500.0, 500.0, 350.0
    nos = []
    for i in range(total_agentes):
        angulo = 2 * math.pi * i / total_agentes
        nos.append({
            'id':     f'agente_{i + 1}',
            'x':      round(centro_x + raio * math.cos(angulo), 2),
            'y':      round(centro_y + raio * math.sin(angulo), 2),
            'tipo':   'Anel',
            'camada': 'anel',
        })

    links = []
    n = len(nos)
    if n >= 2:
        for i in range(n):
            # Com 2 agentes, o "ciclo" duplicaria o mesmo canal físico.
            if n == 2 and i == 1:
                break
            links.append(_link(nos[i]['id'], nos[(i + 1) % n]['id'],
                               tipos_rede[i % len(tipos_rede)]))
    return Rede(nos, links)


def vizinhos_anel(total_agentes):
    """{agente_i: [próximo, anterior]} — ordem usada pelos agentes PADE do anel."""
    resultado = {}
    for i in range(1, total_agentes + 1):
        proximo = f'agente_{i % total_agentes + 1}'
        anterior = f'agente_{(i - 2) % total_agentes + 1}'
        resultado[f'agente_{i}'] = [proximo, anterior] if proximo != anterior else [proximo]
    return resultado


# ══════════════════════════════════════════════════════════════
# ÁRVORE RADIAL (IEC 61850 / AMI)
# ══════════════════════════════════════════════════════════════

def montar_arvore(fanout='3,2,4', celular='4g'):
    """Árvore fan-out por nível: raiz → subestações → concentradores → medidores.

    Canais por nível: Fibra (raiz→sub), celular `celular` (sub→con) e PLC
    (con→medidor e níveis abaixo). `fanout` = filhos por nível, ex.: "3,2,4".
    """
    fan = [int(v) for v in fanout.split(',')]
    canais_nivel = ['Fibra', canal_celular(celular), 'PLC']
    prefixos = ['sub', 'con', 'med']
    camadas = ['subestacao', 'concentrador', 'medidor']

    nos = [{'id': 'raiz', 'x': 500.0, 'y': 150.0, 'tipo': 'Raiz', 'camada': 'controle'}]
    links = []
    nivel_atual = ['raiz']
    for d, f in enumerate(fan):
        idx = min(d, 2)
        pares = []   # (pai, filho)
        for pai in nivel_atual:
            for _ in range(f):
                pares.append((pai, f'{prefixos[idx]}{d + 1}_{len(pares)}'))

        y_pos = 150.0 + (d + 1) * 280.0
        for p, (pai, nid) in enumerate(pares):
            nos.append({
                'id':     nid,
                'x':      round((p + 0.5) * (1000.0 / len(pares)), 2),
                'y':      round(y_pos, 2),
                'tipo':   camadas[idx].capitalize(),
                'camada': camadas[idx],
            })
            links.append(_link(pai, nid, canais_nivel[idx]))
        nivel_atual = [nid for _, nid in pares]

    return Rede(nos, links, {'arvore_fanout': fanout, 'celular_arvore': celular})

# ══════════════════════════════════════════════════════════════
# IEEE 13 BARRAS (OpenTES — coordenadas reais de nodes_xy.csv)
# ══════════════════════════════════════════════════════════════

IEEE13_NOS = [
    {'id': 'agent_0',      'x':    0.00, 'y':     0.00, 'tipo': 'Central',    'camada': 'controle'},
    {'id': 'agent_dso',    'x':    0.00, 'y':     0.00, 'tipo': 'Periferico', 'camada': 'controle'},
    {'id': 'agent_market', 'x':    0.00, 'y':     0.00, 'tipo': 'Periferico', 'camada': 'controle'},
    {'id': 'agent_611',    'x': -182.88, 'y': -1221.20, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_632',    'x':    0.00, 'y':  -611.60, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_633',    'x':  152.40, 'y':  -611.60, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_634',    'x':  153.40, 'y':  -611.60, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_645',    'x': -152.40, 'y':  -611.60, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_646',    'x': -243.84, 'y':  -611.60, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_650',    'x':    0.00, 'y':    -1.00, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_652',    'x':  -91.44, 'y': -1465.04, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_660',    'x':    0.00, 'y':    -2.00, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_670',    'x':    0.00, 'y':  -814.90, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_671',    'x':    0.00, 'y': -1221.20, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_675',    'x':  153.40, 'y': -1221.20, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_680',    'x':    0.00, 'y': -1526.00, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_684',    'x':  -91.44, 'y': -1221.20, 'tipo': 'Periferico', 'camada': 'periferico'},
    {'id': 'agent_692',    'x':    1.00, 'y': -1221.20, 'tipo': 'Periferico', 'camada': 'periferico'},
]


def montar_ieee13(tipos_rede=None):
    """Rede elétrica IEEE 13 barras (18 nós: Concentrador, DSO, Market e 15 barras).

    DSO e Market conectam-se ao Concentrador (agent_0) por Link_Wired; as 15 barras
    usam os canais de `tipos_rede` (padrão: Link_6TiSCH).
    """
    canais = list(tipos_rede) if tipos_rede else ['Link_6TiSCH']
    nos = [dict(n) for n in IEEE13_NOS]
    links = [
        _link('agent_0', 'agent_dso', 'Link_Wired'),
        _link('agent_0', 'agent_market', 'Link_Wired'),
    ]
    barras = [n for n in nos if n['camada'] == 'periferico']
    for i, barra in enumerate(barras):
        links.append(_link('agent_0', barra['id'], canais[i % len(canais)]))

    return Rede(
        nos=nos,
        links=links,
        config={
            'topologia': 'ieee13',
            'num_perifericos': len(nos) - 1,
            'tipos_rede': canais,
        },
    )


# ══════════════════════════════════════════════════════════════
# HÍBRIDA (CCO → anel de fibra → estrela celular → RF mesh)
# ══════════════════════════════════════════════════════════════

def ponto_no_disco(rng, cx, cy, r):
    """Ponto aleatório uniformemente distribuído num disco de raio r."""
    ang = rng.uniform(0, 2 * math.pi)
    rad = r * math.sqrt(rng.random())
    return cx + rad * math.cos(ang), cy + rad * math.sin(ang)


def calcular_malha_parcial(ids, pos, k_neigh=4, raio=60.0):
    """
    Malha parcial: cada nó liga-se aos k vizinhos mais próximos dentro de `raio`;
    depois, arestas mínimas (estilo Kruskal) garantem a conectividade.

    Retorna lista ORDENADA de tuplas (a, b) com a < b. A ordem define a ordem dos
    enlaces no DynamicNetwork.ned (portas e desempate das rotas).
    """
    arestas = set()
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

    todos_pares = sorted(
        itertools.combinations(ids, 2),
        key=lambda p: math.hypot(pos[p[0]][0] - pos[p[1]][0], pos[p[0]][1] - pos[p[1]][1]),
    )
    for a, b in todos_pares:
        if find(a) != find(b):
            pai[find(a)] = find(b)
            arestas.add(tuple(sorted((a, b))))

    return sorted(arestas)


def montar_hibrida(subestacoes=3, concentradores=3, medidores_cluster=5,
                   celular='4g', semente=42):
    """
    Hierarquia em camadas:
      cco ──(Fibra)──► anel de subestações (CCO ligado às 2 primeiras)
      sub{i} ──(celular)──► concentradores (estrela, num disco de 700 m)
      con{i}_{j} ──(RFMesh)──► cluster de medidores (disco de 150 m, malha parcial)

    As posições vêm de random.Random(semente).
    """
    rng = random.Random(semente)
    canal = canal_celular(celular)

    nos = [{'id': 'cco', 'x': 0.0, 'y': 0.0, 'tipo': 'CCO', 'camada': 'controle'}]
    links = []
    vistos = set()

    def add_link(a, b, tipo):
        chave = frozenset((a, b))
        if chave not in vistos:
            vistos.add(chave)
            links.append(_link(a, b, tipo))

    subs = []
    for i in range(subestacoes):
        ang = 2 * math.pi * i / subestacoes
        sid = f'sub{i}'
        nos.append({'id': sid, 'x': round(2500 * math.cos(ang), 2),
                    'y': round(2500 * math.sin(ang), 2),
                    'tipo': 'Subestacao', 'camada': 'subestacao'})
        subs.append(sid)

    n = len(subs)
    if n >= 3:
        for i in range(n):
            add_link(subs[i], subs[(i + 1) % n], 'Fibra')
    elif n == 2:
        add_link(subs[0], subs[1], 'Fibra')

    # CCO ligado às 2 primeiras subestações (redundância IEC 61850)
    for s in subs[:2]:
        add_link('cco', s, 'Fibra')

    pos = {no['id']: (no['x'], no['y']) for no in nos}
    for i, sid in enumerate(subs):
        sx, sy = pos[sid]
        for j in range(concentradores):
            cid = f'con{i}_{j}'
            cx, cy = ponto_no_disco(rng, sx, sy, 700)
            cx, cy = round(cx, 2), round(cy, 2)
            nos.append({'id': cid, 'x': cx, 'y': cy,
                        'tipo': 'Concentrador', 'camada': 'concentrador'})
            add_link(sid, cid, canal)

            cluster = [cid]
            cluster_pos = {cid: (cx, cy)}
            for k in range(medidores_cluster):
                mid = f'med{i}_{j}_{k}'
                mx, my = ponto_no_disco(rng, cx, cy, 150.0)
                mx, my = round(mx, 2), round(my, 2)
                nos.append({'id': mid, 'x': mx, 'y': my,
                            'tipo': 'Medidor', 'camada': 'medidor'})
                cluster.append(mid)
                cluster_pos[mid] = (mx, my)

            for a, b in calcular_malha_parcial(cluster, cluster_pos, k_neigh=4, raio=60.0):
                add_link(a, b, 'RFMesh')

    return Rede(nos, links, {
        'subestacoes':       subestacoes,
        'concentradores':    concentradores,
        'medidores_cluster': medidores_cluster,
        'celular_hibrida':   celular,
        'semente_hibrida':   semente,
    })


# ══════════════════════════════════════════════════════════════
# VIZINHANÇA
# ══════════════════════════════════════════════════════════════

def vizinhos(rede):
    """{nó: [vizinhos diretos]} na ordem dos nós e dos enlaces da rede."""
    adj = {no['id']: [] for no in rede.nos}
    for lk in rede.links:
        o, d = lk['origem'], lk['destino']
        if d not in adj[o]:
            adj[o].append(d)
        if o not in adj[d]:
            adj[d].append(o)
    return adj
