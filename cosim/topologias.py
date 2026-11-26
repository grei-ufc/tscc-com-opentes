"""
cosim.topologias — Montagem das redes de cada topologia.

Cada função devolve uma `Rede` (nós com posição, enlaces com o canal NED e
metadados para o config.json), sem efeitos colaterais. É a única definição
das topologias: o scenario.py (Mosaik) gera o DynamicNetwork.ned a partir dela
e os agentes PADE derivam seus vizinhos dos mesmos enlaces (`vizinhos`).

Reprodutibilidade: com o mesmo `rng`/semente, as funções devolvem exatamente
a mesma rede (listas em ordem determinística; nunca se itera um set).
"""

import csv
import itertools
import math
import random
from dataclasses import dataclass, field

from cosim import radio as _radio
from cosim.catalogo import CANAIS_TESE, canal_celular

__all__ = [
    'Rede', 'calcular_malha_parcial', 'ler_posicoes', 'montar_anel', 'montar_arvore', 'montar_ieee13',
    'montar_estrela', 'montar_hibrida', 'montar_malha', 'omnet_para_pade',
    'pade_para_omnet', 'ponto_no_disco', 'vizinhos', 'vizinhos_anel',
]


@dataclass
class Rede:
    nos: list                                   # [{'id', 'x', 'y', 'tipo', 'camada'}]
    links: list                                 # [{'origem', 'destino', 'tipo'}]
    config: dict = field(default_factory=dict)  # metadados extras para o config.json
    # Levantamento de rádio dos pares de nós (formato tisch_links.csv), quando a
    # topologia usa o modelo da tese; não entra na comparação nem no config.json.
    levantamento: list = field(default_factory=list, compare=False, repr=False)


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


def ler_posicoes(caminho, central='0'):
    """Nós a partir do `nodes_xy.csv` do caso (colunas node, x_m, y_m).

    O nó se chama agent_<nome em minúsculas>: "611" -> agent_611, "DSO" ->
    agent_dso. O `central` (o concentrador da subestação), o DSO e o Market
    formam a camada de controle.
    """
    nos = []
    with open(caminho, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            nome = r['node'].strip()
            controle = nome == central or nome.lower() in ('dso', 'market')
            nos.append({'id': 'agent_' + nome.lower(), 'x': float(r['x_m']), 'y': float(r['y_m']),
                        'tipo': 'Central' if nome == central else 'Periferico',
                        'camada': 'controle' if controle else 'periferico', 'nome': nome})
    return nos


def _nome_no(no):
    if no.get('nome'):
        return no['nome']
    return no['id'][len('agent_'):] if no['id'].startswith('agent_') else no['id']


def _params_canal(tipo, per, radio, cells):
    """Parâmetros NED do enlace nos canais da tese (o PER sai do modelo de rádio)."""
    if tipo not in CANAIS_TESE:
        return None
    params = {'per_enlace': f'{per:g}'}
    if tipo == 'Link_6TiSCH_TSCH' and cells:
        params['cells'] = str(int(cells))
    if tipo == 'Link_WiSUN_FAN':
        params['taxa_bps'] = f'{radio.taxa_bps:g}'
    return params


def montar_ieee13(tipos_rede=None, posicoes=None, topologia='estrela', subestacao='cabo',
                  enlaces=None, radio=None, semente=0, cells=None, central='0'):
    """Rede elétrica IEEE 13 barras (18 nós: Concentrador, DSO, Market e 15 barras).

    Sem argumentos além de `tipos_rede`, é a rede original deste repositório:
    estrela centrada no Concentrador (agent_0), DSO e Market ligados a ele por
    Link_Wired e as 15 barras pelos canais de `tipos_rede` (padrão: Link_6TiSCH).

    Opções para o mercado do OpenTES (todas mantêm os canais do repositório
    disponíveis, inclusive misturados):
      posicoes   : `nodes_xy.csv` do caso, no lugar das coordenadas embutidas.
      topologia  : 'estrela' (padrão) ou 'malha', em que os enlaces são os pares
                   com PER abaixo do limiar no modelo de rádio da tese
                   (cosim/radio.py), com roteamento multissalto.
      subestacao : 'cabo' (padrão; Concentrador, DSO e Market por Link_Wired) ou
                   'radio' (eles também usam o rádio, como na tese).
      enlaces    : `tisch_links.csv` de uma execução da tese, para repetir a
                   mesma topologia de rádio e os mesmos PER; sem ele, o
                   levantamento é sorteado com a `semente`.
      radio      : cosim.radio.Radio (frequência, potência, taxa do Wi-SUN...).
      cells      : cells por slotframe do Link_6TiSCH_TSCH.
    """
    if topologia not in ('estrela', 'malha'):
        raise ValueError(f"topologia IEEE 13 desconhecida: {topologia!r} (estrela ou malha)")
    if subestacao not in ('cabo', 'radio'):
        raise ValueError(f"subestacao desconhecida: {subestacao!r} (cabo ou radio)")
    canais = list(tipos_rede) if tipos_rede else ['Link_6TiSCH']
    radio = radio or _radio.Radio()
    nos = ler_posicoes(posicoes, central) if posicoes else [dict(n) for n in IEEE13_NOS]
    hub = 'agent_' + central.lower()
    controle = {n['id'] for n in nos if n['camada'] == 'controle'}
    barras = [n for n in nos if n['camada'] == 'periferico']

    # Estrela: os pares são impostos pela topologia. Malha: saem do rádio.
    estrela = [(hub, c) for c in sorted(controle - {hub}, key=[n['id'] for n in nos].index)]
    estrela += [(hub, b['id']) for b in barras]
    usa_radio = topologia == 'malha' or any(c in CANAIS_TESE for c in canais)
    per = {}
    pares = estrela
    levantamento = []
    if usa_radio:
        if enlaces:
            levantamento = _radio.ler_enlaces(enlaces, [{**n, 'nome': _nome_no(n)} for n in nos])
        else:
            levantamento = _radio.levantar_enlaces(
                [{**n, 'nome': _nome_no(n)} for n in nos], radio, random.Random(semente),
                impostos=estrela if topologia == 'estrela' else None)
        per = {frozenset((r['id_i'], r['id_j'])): r['per'] for r in levantamento}
        if topologia == 'malha':
            pares = [(r['id_i'], r['id_j']) for r in levantamento if r['adjacent']]

    links, k = [], 0
    for a, b in pares:
        if subestacao == 'cabo' and a in controle and b in controle:
            links.append(_link(a, b, 'Link_Wired'))
            continue
        if topologia == 'estrela' and b in controle:
            tipo = canais[0]          # subestação por rádio, na estrela
        else:
            tipo = canais[k % len(canais)]
            k += 1
        link = _link(a, b, tipo)
        params = _params_canal(tipo, per.get(frozenset((a, b)), 0.0), radio, cells)
        if params:
            link['params'] = params
        links.append(link)

    config = {
        'topologia': 'ieee13',
        'num_perifericos': len(nos) - 1,
        'tipos_rede': canais,
    }
    if (posicoes, topologia, subestacao, enlaces) != (None, 'estrela', 'cabo', None):
        config.update({'estrutura_ieee13': topologia, 'subestacao': subestacao})
    return Rede(nos=nos, links=links, config=config, levantamento=levantamento)


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
