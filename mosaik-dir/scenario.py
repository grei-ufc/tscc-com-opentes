#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scenario.py — Orquestrador único de cenário Mosaik.

Substitui star.py. Lê TOPOLOGY, NUM_PERIFERICOS e TIPOS_REDE do ambiente
(injetadas pelo menu.py via docker-compose.yml) e monta, num único lugar,
QUALQUER uma das três topologias suportadas:

    estrela — 1 central  <-->  N periféricos          (pade_star.py)
    malha   — 1 central  <-->  N periféricos, full mesh (pade_star.py)
    anel    — N+1 agentes conectados em ciclo fechado   (pade_anel.py)

As três são escaláveis pela MESMA variável NUM_PERIFERICOS:
    - estrela/malha: total de agentes = 1 (central) + NUM_PERIFERICOS
    - anel         : total de agentes =  NUM_PERIFERICOS + 1
                     (mantém a mesma contagem total de nós entre as
                     topologias, só muda o papel/nomenclatura dos agentes)

Nomenclatura:
    - estrela/malha → 'agent_central' / 'agent_p_1'..'agent_p_N' no OMNeT++
                       e 'AgenteCentral' / 'AgenteP_1'..'AgenteP_N' no PADE
                       (é o que pade_star.py espera).
    - anel          → 'agente_1'..'agente_M' tanto no OMNeT++ quanto no
                       PADE (é o que pade_anel.py espera — CONFIG_REDE
                       usa exatamente esses nomes).
"""

import math
import mosaik
import os
import random
import json

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE
# ══════════════════════════════════════════════════════════════

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))
# 'estrela' é o padrão caso a variável não esteja definida
TOPOLOGY        = os.environ.get('TOPOLOGY', 'estrela').lower()
# TIPOS_REDE chega como string separada por vírgula vinda do menu.py
# ou do docker-compose.yml; dividimos aqui para obter uma lista Python.
# (IoT foi descontinuado -> usar Link_2G no lugar)
_tipos_raw = os.environ.get('TIPOS_REDE', 'Link_Wired,Link_5G,Link_4G,Link_2G,Link_Wireless')
TIPOS_REDE = [t.strip() for t in _tipos_raw.split(',')]

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
    Escreve o arquivo DynamicNetwork.ned a partir de listas genéricas.

    Parâmetros
    ----------
    agentes_info : list[dict]
        Cada item tem 'id', 'x', 'y', 'tipo'.
    links : list[dict]
        Cada item tem 'origem', 'destino', 'tipo' (nome do canal NED).
    arquivo_saida : str
        Caminho completo do arquivo .ned a ser escrito.

    Esta função é totalmente agnóstica à topologia — só descreve
    o que as listas mandam, então serve para estrela, malha e anel.
    """
    with open(arquivo_saida, 'w') as f:
        # Abertura da rede
        f.write("network DynamicNetwork\n{\n")
        f.write("    submodules:\n")

        # MosaikBridge sempre presente (servidor ZMQ do lado C++)
        f.write("        mosaikBridge: MosaikBridge;\n\n")

        # Um AgentNode por agente, com coordenadas geográficas injetadas
        for ag in agentes_info:
            f.write(f"        {ag['id']}: AgentNode {{\n")
            f.write(f"            xPos = {ag['x']};\n")
            f.write(f"            yPos = {ag['y']};\n")
            f.write("        }\n")

        # Conexões — a sintaxe 'port++' expande o vetor automaticamente
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
    """
    Cria a lista de enlaces para a topologia estrela:
        central ↔ periférico_1
        central ↔ periférico_2
        ...
        central ↔ periférico_N

    O tipo de enlace (Link_5G, Link_4G, ...) é escolhido ciclicamente
    da lista TIPOS_REDE, garantindo distribuição balanceada entre
    as tecnologias disponíveis.

    Parâmetros
    ----------
    agentes_info : list[dict]
        agentes_info[0] é sempre o nó central.

    Retorna
    -------
    list[dict]  — lista de enlaces no formato esperado por gerar_topologia_ned.
    """
    central_id = agentes_info[0]['id']   # 'agent_central'
    links = []

    # enumerate começa em 0 para o índice do tipo de rede;
    # usamos agentes_info[1:] para pular o central.
    for i, ag in enumerate(agentes_info[1:]):
        tipo = TIPOS_REDE[i % len(TIPOS_REDE)]
        links.append({
            'origem':  central_id,
            'destino': ag['id'],
            'tipo':    tipo,
        })
    return links


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DE LINKS — MALHA (full mesh)
# ══════════════════════════════════════════════════════════════

def gerar_links_malha(agentes_info):
    """
    Cria a lista de enlaces para a topologia malha completa (full mesh):
    todo par de agentes (i, j) com i < j recebe um enlace bidirecional.

    Por quê só o triângulo superior (i < j)?
    No OMNeT++, a sintaxe:
        A.port++ <--> Canal <--> B.port++
    já declara comunicação bidirecional. Se também criássemos
        B.port++ <--> Canal <--> A.port++
    teríamos um enlace duplicado e erro de compilação do NED.

    Para N+1 nós (1 central + N periféricos), o total de enlaces é:
        (N+1) * N / 2
    Exemplo: N=4 → 10 enlaces; N=10 → 55 enlaces.

    O tipo de canal é escolhido ciclicamente de TIPOS_REDE,
    assim cada tecnologia recebe aproximadamente o mesmo número de enlaces.

    Parâmetros
    ----------
    agentes_info : list[dict]  — todos os agentes (central + periféricos).

    Retorna
    -------
    list[dict]  — lista de enlaces no formato esperado por gerar_topologia_ned.
    """
    links = []
    n = len(agentes_info)
    contador = 0  # índice global para ciclar TIPOS_REDE

    for i in range(n):
        for j in range(i + 1, n):       # triângulo superior → sem duplicatas
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
    """
    Cria a lista de enlaces para a topologia anel: cada agente conecta-se
    apenas ao próximo, fechando o ciclo no final:
        agente_1 -> agente_2 -> agente_3 -> ... -> agente_M -> agente_1

    Isso reproduz, de forma escalável, a mesma ideia da topologia fixa de
    4 agentes que existia em mosaik_anel.py — só que agora para M
    agentes quaisquer (M = NUM_PERIFERICOS + 1), o que é exatamente o
    formato de vizinhança (CONFIG_REDE) que pade_anel.py monta em tempo
    de execução a partir de NUM_PERIFERICOS.

    O tipo de canal é escolhido ciclicamente de TIPOS_REDE.

    Parâmetros
    ----------
    agentes_info : list[dict]  — todos os agentes do anel (agente_1..agente_M).

    Retorna
    -------
    list[dict]  — lista de enlaces no formato esperado por gerar_topologia_ned.
    """
    links = []
    n = len(agentes_info)

    if n < 2:
        return links

    for i in range(n):
        # Com apenas 2 agentes, o "ciclo" seria um único enlace duplicado
        # (A->B e B->A seriam o mesmo canal físico) — evitamos o duplicado.
        if n == 2 and i == 1:
            break

        origem  = agentes_info[i]['id']
        destino = agentes_info[(i + 1) % n]['id']
        tipo    = TIPOS_REDE[i % len(TIPOS_REDE)]
        links.append({
            'origem':  origem,
            'destino': destino,
            'tipo':    tipo,
        })

    return links


# ══════════════════════════════════════════════════════════════
# MONTAGEM DO CENÁRIO MOSAIK
# ══════════════════════════════════════════════════════════════

def create_scenario(world):
    print(f"\nTopologia : {TOPOLOGY.upper()}")
    print(f"   Periféricos: {NUM_PERIFERICOS}")
    print(f"   Redes      : {', '.join(TIPOS_REDE)}\n")

    omnet_sim   = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim    = world.start('PadeSim')
    monitor     = coletor_sim.Monitor()

    if TOPOLOGY == 'anel':
        _montar_anel(world, omnet_sim, pade_sim, monitor)
    else:
        # 'estrela', 'malha' ou qualquer outro valor cai aqui
        _montar_central_periferico(world, omnet_sim, pade_sim, monitor)


def _montar_central_periferico(world, omnet_sim, pade_sim, monitor):
    """Monta estrela OU malha — ambas usam o mesmo conjunto de agentes
    (1 central + N periféricos, nomenclatura AgenteCentral/AgenteP_i),
    diferindo apenas na lista de enlaces gerada no OMNeT++."""

    # ── IDs dos agentes ──────────────────────────────────────
    agente_central_id = 'agent_central'
    perifericos_ids    = [f'agent_p_{i}' for i in range(1, NUM_PERIFERICOS + 1)]

    # ── Geolocalização ───────────────────────────────────────
    # O nó central é fixado no centro do grid (500, 500).
    # Periféricos recebem posições aleatórias dentro de um
    # grid de 1000 × 1000 metros.
    agentes_info = [{
        'id':   agente_central_id,
        'x':    500.0,
        'y':    500.0,
        'tipo': 'Central',
    }]
    for pid in perifericos_ids:
        agentes_info.append({
            'id':   pid,
            'x':    round(random.uniform(0, 1000), 2),
            'y':    round(random.uniform(0, 1000), 2),
            'tipo': 'Periferico',
        })

    _persistir_mapa_e_config(agentes_info)

    # ── Gera os links de acordo com a topologia ──────────────
    if TOPOLOGY == 'malha':
        links = gerar_links_malha(agentes_info)
    else:                                           # 'estrela' ou fallback
        links = gerar_links_estrela(agentes_info)

    print(f"   ↳ {len(links)} enlaces gerados para topologia '{TOPOLOGY}'.")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    # ── Entidade: nó central ─────────────────────────────────
    agente_central_pade = pade_sim.PadeAgent(agent_id='AgenteCentral')
    node_central_omnet  = omnet_sim.AgentNode(
        node_type='AgentNode', eid=agente_central_id
    )

    world.connect(agente_central_pade, node_central_omnet,
                  ('val_out', 'val_in'))
    world.connect(node_central_omnet, agente_central_pade,
                  ('val_out', 'val_in'),
                  time_shifted=True, initial_data={'val_out': ''})
    world.connect(node_central_omnet, monitor,
                  'status', 'packets_sent', 'packets_received', 'packets_dropped',
                  'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')

    # ── Entidades: nós periféricos ───────────────────────────
    for i in range(1, NUM_PERIFERICOS + 1):
        pid           = f'agent_p_{i}'
        agente_p_pade = pade_sim.PadeAgent(agent_id=f'AgenteP_{i}')
        node_p_omnet  = omnet_sim.AgentNode(node_type='AgentNode', eid=pid)

        world.connect(agente_p_pade, node_p_omnet,
                      ('val_out', 'val_in'))
        world.connect(node_p_omnet, agente_p_pade,
                      ('val_out', 'val_in'),
                      time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_p_omnet, monitor,
                      'status', 'packets_sent', 'packets_received', 'packets_dropped',
                      'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')


def _montar_anel(world, omnet_sim, pade_sim, monitor):
    """Monta a topologia anel — M = NUM_PERIFERICOS + 1 agentes, todos com
    o mesmo papel, nomeados agente_1..agente_M (nomenclatura exigida por
    pade_anel.py, cujo CONFIG_REDE é construído dinamicamente a partir da
    mesma variável NUM_PERIFERICOS)."""

    total_agentes = NUM_PERIFERICOS + 1
    ids = [f'agente_{i}' for i in range(1, total_agentes + 1)]

    # ── Geolocalização: distribui os agentes num círculo ─────
    # (mesma ideia visual do anel de 4 nós original, mas para M nós)
    centro_x, centro_y, raio = 500.0, 500.0, 350.0
    agentes_info = []
    for i, aid in enumerate(ids):
        angulo = 2 * math.pi * i / total_agentes
        agentes_info.append({
            'id':   aid,
            'x':    round(centro_x + raio * math.cos(angulo), 2),
            'y':    round(centro_y + raio * math.sin(angulo), 2),
            'tipo': 'Anel',
        })

    _persistir_mapa_e_config(agentes_info)

    links = gerar_links_anel(agentes_info)
    print(f"   ↳ {len(links)} enlaces gerados para topologia 'anel' "
          f"({total_agentes} agentes).")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    # ── Entidades: todos os agentes têm o mesmo papel ────────
    for ag in agentes_info:
        aid           = ag['id']                       # ex.: 'agente_1'
        agente_pade   = pade_sim.PadeAgent(agent_id=aid)
        node_omnet    = omnet_sim.AgentNode(node_type='AgentNode', eid=aid)

        world.connect(agente_pade, node_omnet,
                      ('val_out', 'val_in'))
        world.connect(node_omnet, agente_pade,
                      ('val_out', 'val_in'),
                      time_shifted=True, initial_data={'val_out': ''})
        world.connect(node_omnet, monitor,
                      'status', 'packets_sent', 'packets_received', 'packets_dropped',
                      'packet_sizes_out', 'latencies_out', 'jitters_out', 'val_out')


def _persistir_mapa_e_config(agentes_info):
    """Persiste posições (para o dashboard) e a config da rodada
    (topologia/N/redes), comum às três topologias."""
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)

    with open('/omnet-dir/config.json', 'w') as f:
        json.dump({
            'topologia':       TOPOLOGY,
            'num_perifericos': NUM_PERIFERICOS,
            'tipos_rede':      TIPOS_REDE,
        }, f, indent=4)


# ══════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)