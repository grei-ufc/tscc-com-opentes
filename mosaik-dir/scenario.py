#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scenario.py — Orquestrador único de cenário Mosaik.

Suporta cinco topologias, selecionadas via TOPOLOGY:

    estrela  — 1 central  <-->  N periféricos          (pade_star.py)
    malha    — full mesh entre central + N periféricos  (pade_star.py)
    anel     — N agentes em ciclo fechado               (pade_anel.py)
    arvore   — árvore radial IEC 61850 com fan-out      (pade_arvore.py)
    hibrida  — hierarquia CCO→subs(fibra)→cons(celular)→meds(RF mesh)
                                                        (pade_hibrida.py)

Variáveis de ambiente
---------------------
Comuns:
    TOPOLOGY          estrela | malha | anel | arvore | hibrida
    NUM_PERIFERICOS   (estrela/malha/anel) número de periféricos
    TIPOS_REDE        lista separada por vírgula de nomes de canal

Árvore (TOPOLOGY=arvore):
    ARVORE_FANOUT     ex.: "3,2,4"  (filhos por nível)
    CELULAR_ARVORE    2g | 3g | 4g | 5g  (canal do nível concentrador)

Híbrida (TOPOLOGY=hibrida):
    SUBESTACOES       int  (padrão 3)
    CONCENTRADORES    int  (padrão 3)  por subestação
    MEDIDORES_CLUSTER int  (padrão 5)  por concentrador
    CELULAR_HIBRIDA   2g | 3g | 4g | 5g
    SEMENTE_HIBRIDA   int  (padrão 42)
"""

import itertools
import math
import mosaik
import os
import random
import json

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE
# ══════════════════════════════════════════════════════════════

TOPOLOGY         = os.environ.get('TOPOLOGY', 'estrela').lower()
NUM_PERIFERICOS  = int(os.environ.get('NUM_PERIFERICOS', 3))
_tipos_raw       = os.environ.get('TIPOS_REDE', 'Link_Wired,Link_5G,Link_4G,Link_2G,Link_Wireless')
TIPOS_REDE       = [t.strip() for t in _tipos_raw.split(',')]

# Árvore
ARVORE_FANOUT  = os.environ.get('ARVORE_FANOUT', '3,2,4')
CELULAR_ARVORE = os.environ.get('CELULAR_ARVORE', '4g').lower()

# Híbrida
SUBESTACOES        = int(os.environ.get('SUBESTACOES',        3))
CONCENTRADORES     = int(os.environ.get('CONCENTRADORES',     3))
MEDIDORES_CLUSTER  = int(os.environ.get('MEDIDORES_CLUSTER',  5))
CELULAR_HIBRIDA    = os.environ.get('CELULAR_HIBRIDA', '4g').lower()
SEMENTE_HIBRIDA    = int(os.environ.get('SEMENTE_HIBRIDA',    42))

# Mapeamento de código de operadora → nome do canal NED
CELULAR_MAP = {
    '2g': 'Celular2G',
    '3g': 'Celular3G',
    '4g': 'Celular4G',
    '5g': 'Celular5G',
}

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DOS SIMULADORES MOSAIK
# ══════════════════════════════════════════════════════════════

sim_config = {
    'OmnetSim':   {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim':    {'connect': 'pade:5678'},
}


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DO ARQUIVO NED  (agnóstica à topologia)
# ══════════════════════════════════════════════════════════════

def gerar_topologia_ned(agentes_info, links,
                        arquivo_saida="/omnet-dir/DynamicNetwork.ned"):
    """
    Escreve DynamicNetwork.ned a partir de listas genéricas.

    agentes_info : list[dict]  — cada item tem 'id', 'x', 'y', 'tipo'.
    links        : list[dict]  — cada item tem 'origem', 'destino', 'tipo'.
    """
    with open(arquivo_saida, 'w') as f:
        f.write("network DynamicNetwork\n{\n")
        f.write("    submodules:\n")
        f.write("        mosaikBridge: MosaikBridge;\n\n")

        for ag in agentes_info:
            f.write(f"        {ag['id']}: AgentNode {{\n")
            f.write(f"            xPos = {ag['x']};\n")
            f.write(f"            yPos = {ag['y']};\n")
            f.write("        }\n")

        f.write("\n    connections:\n")
        for link in links:
            f.write(
                f"        {link['origem']}.port++ <--> "
                f"{link['tipo']} <--> "
                f"{link['destino']}.port++;\n"
            )
        f.write("}\n")


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DE LINKS — ESTRELA
# ══════════════════════════════════════════════════════════════

def gerar_links_estrela(agentes_info):
    central_id = agentes_info[0]['id']
    links = []
    for i, ag in enumerate(agentes_info[1:]):
        tipo = TIPOS_REDE[i % len(TIPOS_REDE)]
        links.append({'origem': central_id, 'destino': ag['id'], 'tipo': tipo})
    return links


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DE LINKS — MALHA (full mesh)
# ══════════════════════════════════════════════════════════════

def gerar_links_malha(agentes_info):
    links = []
    n = len(agentes_info)
    contador = 0
    for i in range(n):
        for j in range(i + 1, n):
            tipo = TIPOS_REDE[contador % len(TIPOS_REDE)]
            links.append({
                'origem':  agentes_info[i]['id'],
                'destino': agentes_info[j]['id'],
                'tipo':    tipo,
            })
            contador += 1
    return links


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DE LINKS — ANEL (ciclo fechado)
# ══════════════════════════════════════════════════════════════

def gerar_links_anel(agentes_info):
    links = []
    n = len(agentes_info)
    if n < 2:
        return links
    for i in range(n):
        if n == 2 and i == 1:
            break
        origem  = agentes_info[i]['id']
        destino = agentes_info[(i + 1) % n]['id']
        tipo    = TIPOS_REDE[i % len(TIPOS_REDE)]
        links.append({'origem': origem, 'destino': destino, 'tipo': tipo})
    return links


# ══════════════════════════════════════════════════════════════
# HELPERS PARA TOPOLOGIAS ARVORE E HIBRIDA
# ══════════════════════════════════════════════════════════════

def _ponto_no_disco(rng, cx, cy, r):
    """Gera ponto aleatório uniformemente distribuído num disco de raio r."""
    ang = rng.uniform(0, 2 * math.pi)
    rad = r * math.sqrt(rng.random())
    return cx + rad * math.cos(ang), cy + rad * math.sin(ang)


def _calcular_malha_parcial(ids, pos, k_neigh=4, raio=60.0):
    """
    Malha parcial k-vizinhos + Kruskal para garantir conectividade.

    ids  : list de identificadores de nó
    pos  : dict  nó -> (x, y)
    Retorna set de tuplas (a, b) com a < b (sem duplicatas).
    """
    arestas: set = set()
    for i in ids:
        candidatos = sorted(
            (j for j in ids if j != i),
            key=lambda j: math.hypot(pos[i][0] - pos[j][0],
                                     pos[i][1] - pos[j][1]),
        )
        for j in candidatos[:k_neigh]:
            d = math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1])
            if raio is None or d <= raio:
                arestas.add(tuple(sorted((i, j))))

    # Garantia de conectividade (estilo Kruskal)
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
        key=lambda p: math.hypot(pos[p[0]][0] - pos[p[1]][0],
                                 pos[p[0]][1] - pos[p[1]][1]),
    )
    for a, b in todos_pares:
        if find(a) != find(b):
            pai[find(a)] = find(b)
            arestas.add(tuple(sorted((a, b))))

    return arestas


# ══════════════════════════════════════════════════════════════
# MONTAGEM DO CENÁRIO MOSAIK
# ══════════════════════════════════════════════════════════════

def create_scenario(world):
    print(f"\nTopologia : {TOPOLOGY.upper()}")

    omnet_sim   = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim    = world.start('PadeSim')
    monitor     = coletor_sim.Monitor()

    if TOPOLOGY == 'anel':
        _montar_anel(world, omnet_sim, pade_sim, monitor)
    elif TOPOLOGY == 'arvore':
        _montar_arvore(world, omnet_sim, pade_sim, monitor)
    elif TOPOLOGY == 'hibrida':
        _montar_hibrida(world, omnet_sim, pade_sim, monitor)
    else:
        # 'estrela', 'malha' ou qualquer fallback
        _montar_central_periferico(world, omnet_sim, pade_sim, monitor)


# ──────────────────────────────────────────────────────────────
# Topologias existentes (estrela / malha / anel)
# ──────────────────────────────────────────────────────────────

def _montar_central_periferico(world, omnet_sim, pade_sim, monitor):
    print(f"   Periféricos: {NUM_PERIFERICOS}\n   Redes: {', '.join(TIPOS_REDE)}\n")
    agente_central_id = 'agent_central'
    perifericos_ids   = [f'agent_p_{i}' for i in range(1, NUM_PERIFERICOS + 1)]

    agentes_info = [{
        'id': agente_central_id, 'x': 500.0, 'y': 500.0,
        'tipo': 'Central', 'camada': 'controle',
    }]
    for pid in perifericos_ids:
        agentes_info.append({
            'id': pid,
            'x':  round(random.uniform(0, 1000), 2),
            'y':  round(random.uniform(0, 1000), 2),
            'tipo': 'Periferico', 'camada': 'periferico',
        })

    if TOPOLOGY == 'malha':
        links = gerar_links_malha(agentes_info)
    else:
        links = gerar_links_estrela(agentes_info)

    _persistir_mapa_e_config(agentes_info, links=links)
    print(f"   ↳ {len(links)} enlaces gerados para topologia '{TOPOLOGY}'.")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    agente_central_pade = pade_sim.PadeAgent(agent_id='AgenteCentral')
    node_central_omnet  = omnet_sim.AgentNode(node_type='AgentNode', eid=agente_central_id)
    world.connect(agente_central_pade, node_central_omnet, ('val_out', 'val_in'))
    world.connect(node_central_omnet, agente_central_pade, ('val_out', 'val_in'),
                  time_shifted=True, initial_data={'val_out': ''})
    world.connect(node_central_omnet, monitor,
                  'status', 'packets_sent', 'packets_received', 'packets_dropped',
                  'packets_forwarded',
                  'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

    for i in range(1, NUM_PERIFERICOS + 1):
        pid           = f'agent_p_{i}'
        agente_p_pade = pade_sim.PadeAgent(agent_id=f'AgenteP_{i}')
        node_p_omnet  = omnet_sim.AgentNode(node_type='AgentNode', eid=pid)
        world.connect(agente_p_pade, node_p_omnet, ('val_out', 'val_in'))
        world.connect(node_p_omnet, agente_p_pade, ('val_out', 'val_in'),
                      time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_p_omnet, monitor,
                      'status', 'packets_sent', 'packets_received', 'packets_dropped',
                  'packets_forwarded',
                      'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')


def _montar_anel(world, omnet_sim, pade_sim, monitor):
    total_agentes = NUM_PERIFERICOS      # mesmo total do menu e do pade_anel.py
    ids = [f'agente_{i}' for i in range(1, total_agentes + 1)]
    print(f"   Agentes: {total_agentes}   Redes: {', '.join(TIPOS_REDE)}\n")

    centro_x, centro_y, raio = 500.0, 500.0, 350.0
    agentes_info = []
    for i, aid in enumerate(ids):
        angulo = 2 * math.pi * i / total_agentes
        agentes_info.append({
            'id':     aid,
            'x':      round(centro_x + raio * math.cos(angulo), 2),
            'y':      round(centro_y + raio * math.sin(angulo), 2),
            'tipo':   'Anel',
            'camada': 'anel',
        })

    links = gerar_links_anel(agentes_info)
    _persistir_mapa_e_config(agentes_info, links=links)
    print(f"   ↳ {len(links)} enlaces gerados para topologia 'anel' ({total_agentes} agentes).")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    for ag in agentes_info:
        aid         = ag['id']
        agente_pade = pade_sim.PadeAgent(agent_id=aid)
        node_omnet  = omnet_sim.AgentNode(node_type='AgentNode', eid=aid)
        world.connect(agente_pade, node_omnet, ('val_out', 'val_in'))
        world.connect(node_omnet, agente_pade, ('val_out', 'val_in'),
                      time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_omnet, monitor,
                      'status', 'packets_sent', 'packets_received', 'packets_dropped',
                  'packets_forwarded',
                      'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')


# ──────────────────────────────────────────────────────────────
# Topologia ÁRVORE RADIAL (IEC 61850 / AMI)
# ──────────────────────────────────────────────────────────────

def _montar_arvore(world, omnet_sim, pade_sim, monitor):
    """
    Árvore fan-out por nível: raiz → subs → cons → meds.

    Canais por nível:
      0 → 1  (raiz→sub)  : Fibra
      1 → 2  (sub→con)   : CELULAR_MAP[CELULAR_ARVORE]
      2+     (con→med+)  : PLC
    """
    fan          = [int(v) for v in ARVORE_FANOUT.split(',')]
    canal_celular = CELULAR_MAP.get(CELULAR_ARVORE, 'Celular4G')
    prefixos     = ['sub', 'con', 'med']
    camadas_nome = ['subestacao', 'concentrador', 'medidor']
    canais_nivel = ['Fibra', canal_celular, 'PLC']

    print(f"   Fan-out: {ARVORE_FANOUT}   Celular: {canal_celular}\n")

    # ── Constrói árvore (BFS) ─────────────────────────────────
    agentes_info = [{'id': 'raiz', 'x': 500.0, 'y': 150.0,
                     'tipo': 'Raiz', 'camada': 'controle'}]
    links        = []
    nivel_atual  = ['raiz']

    for d, f in enumerate(fan):
        idx = min(d, 2)
        nivel_proximo_pares = []   # lista de (pai_id, filho_id)

        for pai_id in nivel_atual:
            for _ in range(f):
                nid = f"{prefixos[idx]}{d + 1}_{len(nivel_proximo_pares)}"
                nivel_proximo_pares.append((pai_id, nid))

        n_nivel = len(nivel_proximo_pares)
        y_pos   = 150.0 + (d + 1) * 280.0
        for p, (pai_id, nid) in enumerate(nivel_proximo_pares):
            x_pos = round((p + 0.5) * (1000.0 / n_nivel), 2)
            canal = canais_nivel[idx] if idx < len(canais_nivel) else 'PLC'
            agentes_info.append({
                'id':     nid,
                'x':      x_pos,
                'y':      round(y_pos, 2),
                'tipo':   camadas_nome[idx].capitalize(),
                'camada': camadas_nome[idx],
            })
            links.append({'origem': pai_id, 'destino': nid, 'tipo': canal})

        nivel_atual = [nid for _, nid in nivel_proximo_pares]

    _persistir_mapa_e_config(agentes_info, links=links,
                             extra_config={'arvore_fanout': ARVORE_FANOUT,
                                           'celular_arvore': CELULAR_ARVORE})
    print(f"   ↳ {len(agentes_info)} nós, {len(links)} enlaces (árvore).")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    _conectar_agentes_mosaik(world, omnet_sim, pade_sim, monitor, agentes_info)


# ──────────────────────────────────────────────────────────────
# Topologia HÍBRIDA (CCO → anel fibra → estrela celular → RF mesh)
# ──────────────────────────────────────────────────────────────

def _montar_hibrida(world, omnet_sim, pade_sim, monitor):
    """
    Hierarquia em camadas:
      cco ──(Fibra)──► anel de subestações
      sub{i} ──(Celular)──► concentradores (estrela)
      con{i}_{j} ──(RFMesh)──► cluster de medidores (malha parcial)

    Usa random.Random(SEMENTE_HIBRIDA) para reproduzir as mesmas posições
    que pade_hibrida.py calcula independentemente.
    """
    rng      = random.Random(SEMENTE_HIBRIDA)
    celular  = CELULAR_MAP.get(CELULAR_HIBRIDA, 'Celular4G')
    print(f"   Subs: {SUBESTACOES}  Cons/sub: {CONCENTRADORES}  "
          f"Meds/con: {MEDIDORES_CLUSTER}  Celular: {celular}  "
          f"Semente: {SEMENTE_HIBRIDA}\n")

    agentes_info = [{'id': 'cco', 'x': 0.0, 'y': 0.0,
                     'tipo': 'CCO', 'camada': 'controle'}]
    links     = []
    vistos    = set()   # frozenset para deduplicar links

    def add_link(a, b, canal):
        chave = frozenset((a, b))
        if chave not in vistos:
            vistos.add(chave)
            links.append({'origem': a, 'destino': b, 'tipo': canal})

    # ── Anel de subestações (Fibra) ───────────────────────────
    subs = []
    for i in range(SUBESTACOES):
        ang = 2 * math.pi * i / SUBESTACOES
        sid = f'sub{i}'
        sx  = round(2500 * math.cos(ang), 2)
        sy  = round(2500 * math.sin(ang), 2)
        agentes_info.append({'id': sid, 'x': sx, 'y': sy,
                             'tipo': 'Subestacao', 'camada': 'subestacao'})
        subs.append(sid)

    n = len(subs)
    if n >= 3:
        for i in range(n):
            add_link(subs[i], subs[(i + 1) % n], 'Fibra')
    elif n == 2:
        add_link(subs[0], subs[1], 'Fibra')

    # CCO conectado às primeiras 2 subs (redundância IEC 61850)
    for s in subs[:2]:
        add_link('cco', s, 'Fibra')

    # ── Estrela celular + cluster RF mesh por subestação ──────
    pos_idx = {ag['id']: (ag['x'], ag['y']) for ag in agentes_info}

    for i, sid in enumerate(subs):
        sx, sy = pos_idx[sid]
        for j in range(CONCENTRADORES):
            cid    = f'con{i}_{j}'
            cx, cy = _ponto_no_disco(rng, sx, sy, 700)
            cx, cy = round(cx, 2), round(cy, 2)
            agentes_info.append({'id': cid, 'x': cx, 'y': cy,
                                 'tipo': 'Concentrador', 'camada': 'concentrador'})
            add_link(sid, cid, celular)

            # Cluster: concentrador + medidores
            cluster     = [cid]
            cluster_pos = {cid: (cx, cy)}
            for k in range(MEDIDORES_CLUSTER):
                mid    = f'med{i}_{j}_{k}'
                mx, my = _ponto_no_disco(rng, cx, cy, 150.0)
                mx, my = round(mx, 2), round(my, 2)
                agentes_info.append({'id': mid, 'x': mx, 'y': my,
                                     'tipo': 'Medidor', 'camada': 'medidor'})
                cluster.append(mid)
                cluster_pos[mid] = (mx, my)

            # Malha parcial RF dentro do cluster
            for a, b in _calcular_malha_parcial(cluster, cluster_pos,
                                                k_neigh=4, raio=60.0):
                add_link(a, b, 'RFMesh')

    _persistir_mapa_e_config(
        agentes_info, links=links,
        extra_config={
            'subestacoes':       SUBESTACOES,
            'concentradores':    CONCENTRADORES,
            'medidores_cluster': MEDIDORES_CLUSTER,
            'celular_hibrida':   CELULAR_HIBRIDA,
            'semente_hibrida':   SEMENTE_HIBRIDA,
        },
    )
    print(f"   ↳ {len(agentes_info)} nós, {len(links)} enlaces (híbrida).")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    _conectar_agentes_mosaik(world, omnet_sim, pade_sim, monitor, agentes_info)


# ──────────────────────────────────────────────────────────────
# Utilitário compartilhado: conecta todos os agentes ao Mosaik
# ──────────────────────────────────────────────────────────────

def _conectar_agentes_mosaik(world, omnet_sim, pade_sim, monitor, agentes_info):
    """Registra cada agente no Mosaik e cria as conexões padrão."""
    for ag in agentes_info:
        aid         = ag['id']
        agente_pade = pade_sim.PadeAgent(agent_id=aid)
        node_omnet  = omnet_sim.AgentNode(node_type='AgentNode', eid=aid)
        world.connect(agente_pade, node_omnet, ('val_out', 'val_in'))
        world.connect(node_omnet, agente_pade, ('val_out', 'val_in'),
                      time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_omnet, monitor,
                      'status', 'packets_sent', 'packets_received', 'packets_dropped',
                  'packets_forwarded',
                      'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')


# ══════════════════════════════════════════════════════════════
# PERSISTÊNCIA DE ARTEFATOS (posicoes.json, config.json, links.json)
# ══════════════════════════════════════════════════════════════

def _persistir_mapa_e_config(agentes_info, links=None, extra_config=None):
    """
    Salva os artefatos da rodada em /omnet-dir/ para uso pelos scripts
    de plotagem e pelo dashboard Streamlit.

    posicoes.json  — lista de nós com id, x, y, tipo, camada (quando disponível)
    config.json    — topologia, parâmetros e metadados extras
    links.json     — lista de enlaces da rodada atual (removido se não houver)
    """
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)

    config_data = {
        'topologia':       TOPOLOGY,
        'num_perifericos': NUM_PERIFERICOS,
        'tipos_rede':      TIPOS_REDE,
    }
    if extra_config:
        config_data.update(extra_config)
    with open('/omnet-dir/config.json', 'w') as f:
        json.dump(config_data, f, indent=4)

    # links.json SEMPRE reflete a rodada atual. Um arquivo velho (de outra topologia) fazia os
    # scripts de plotagem não casarem remetente/destino e gerar painéis por tecnologia vazios.
    if links is not None:
        with open('/omnet-dir/links.json', 'w') as f:
            json.dump(links, f, indent=2)
    elif os.path.exists('/omnet-dir/links.json'):
        os.remove('/omnet-dir/links.json')


# ══════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)

    # ── Despacha script de plotagem conforme a topologia ─────
    def _rodar_plot(modulo, *nomes):
        """Chama a 1ª função existente entre `nomes` (tolera nomes diferentes entre scripts)."""
        for nome in nomes:
            fn = getattr(modulo, nome, None)
            if callable(fn):
                return fn()
        raise AttributeError(f"{modulo.__name__} não define nenhuma de {nomes}")

    print("\nGerando gráficos da simulação...")
    if TOPOLOGY == 'anel':
        import plot_results_anel as plotter
        _rodar_plot(plotter, 'gerar_grafico_anel', 'gerar_graficos')
    elif TOPOLOGY == 'arvore':
        import plot_results_arvore as plotter
        _rodar_plot(plotter, 'gerar_grafico_arvore', 'gerar_graficos')
    elif TOPOLOGY == 'hibrida':
        import plot_results_hibrida as plotter
        _rodar_plot(plotter, 'gerar_grafico_hibrida', 'gerar_graficos')
    else:
        # 'estrela', 'malha' ou qualquer fallback
        import plot_results_star as plotter
        _rodar_plot(plotter, 'gerar_graficos')