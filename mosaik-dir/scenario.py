#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scenario.py — Orquestrador único de cenário Mosaik.

Substitui star.py. Lê TOPOLOGY, NUM_PERIFERICOS e TIPOS_REDE do ambiente
(injetadas pelo menu.py / menu-streamlit.py via docker-compose.yml) e monta,
num único lugar, QUALQUER uma das três topologias suportadas:

    estrela — 1 central  <-->  N periféricos          (pade_star.py)
    malha   — N agentes peers conectados em full mesh (pade_malha.py)
    anel    — N agentes peers em ciclo fechado        (pade_anel.py)

Semântica de NUM_PERIFERICOS (unificada com menu.py, menu-streamlit.py e PADE):
    - estrela : número de periféricos N  → total de agentes = 1 (central) + N
    - malha   : número TOTAL de agentes N → total de agentes = N (1 master + N-1 peers)
    - anel    : número TOTAL de agentes N → total de agentes = N (agente_1..agente_N)

Nomenclatura:
    - estrela/malha → 'agent_central' / 'agent_p_1'..'agent_p_K' no OMNeT++
                       e 'AgenteCentral' / 'AgenteP_1'..'AgenteP_K' no PADE.
    - anel          → 'agente_1'..'agente_N' tanto no OMNeT++ quanto no PADE.
"""

import json
import math
import os
import random
import socket
import time
import mosaik

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
TIPOS_REDE = [t.strip() for t in _tipos_raw.split(',') if t.strip()]

RANDOM_SEED = os.environ.get('RANDOM_SEED')
if RANDOM_SEED is not None and str(RANDOM_SEED).strip() != '':
    random.seed(int(RANDOM_SEED))

SIM_STEPS = int(os.environ.get('SIM_STEPS', 20))
PADE_HOST = os.environ.get('PADE_HOST', 'pade')
PADE_PORT = int(os.environ.get('PADE_PORT', 5678))

_DEFAULT_OMNET_DIR = (
    '/omnet-dir'
    if os.path.isdir('/omnet-dir')
    else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'omnet-dir'))
)
OMNET_DIR = os.environ.get('OMNET_DIR', _DEFAULT_OMNET_DIR)

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DOS SIMULADORES MOSAIK
# ══════════════════════════════════════════════════════════════

sim_config = {
    'OmnetSim':   {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim':    {'connect': f'{PADE_HOST}:{PADE_PORT}'},
}


def _aguardar_pade_pronto(host=PADE_HOST, port=PADE_PORT, timeout=30.0):
    """Aguarda a porta TCP do PADE estar pronta antes do world.start('PadeSim')."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    print(f"[MOSAIK] ⚠ Timeout aguardando PADE em {host}:{port}; tentando conectar...")
    return False


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DO ARQUIVO NED  (agnóstica à topologia)
# ══════════════════════════════════════════════════════════════

def gerar_topologia_ned(agentes_info, links, arquivo_saida=None):
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
    if arquivo_saida is None:
        arquivo_saida = os.path.join(OMNET_DIR, "DynamicNetwork.ned")

    os.makedirs(os.path.dirname(os.path.abspath(arquivo_saida)), exist_ok=True)
    arquivo_tmp = arquivo_saida + ".tmp"

    with open(arquivo_tmp, 'w', encoding='utf-8') as f:
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

    os.replace(arquivo_tmp, arquivo_saida)


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

    Para N nós (total = NUM_PERIFERICOS), o total de enlaces é:
        N * (N - 1) / 2
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
        agente_1 -> agente_2 -> agente_3 -> ... -> agente_N -> agente_1
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
    print(f"   Parâmetro N: {NUM_PERIFERICOS}")
    print(f"   Redes      : {', '.join(TIPOS_REDE)}\n")

    if TOPOLOGY == 'anel':
        _montar_anel(world)
    else:
        # 'estrela', 'malha' ou qualquer outro valor cai aqui
        _montar_central_periferico(world)


def _iniciar_simuladores(world):
    """Inicia OmnetSim, ColetorSim e PadeSim após gerar DynamicNetwork.ned."""
    omnet_sim   = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    _aguardar_pade_pronto(PADE_HOST, PADE_PORT)
    pade_sim    = world.start('PadeSim')
    monitor     = coletor_sim.Monitor()
    return omnet_sim, pade_sim, monitor


def _montar_central_periferico(world):
    """Monta estrela OU malha:
      - estrela: 1 central + NUM_PERIFERICOS periféricos (total = N + 1)
      - malha  : 1 master  + (NUM_PERIFERICOS - 1) peers (total = N)
    """
    num_peers_extras = (
        max(1, NUM_PERIFERICOS - 1)
        if TOPOLOGY == 'malha'
        else NUM_PERIFERICOS
    )

    # ── IDs dos agentes ──────────────────────────────────────
    agente_central_id = 'agent_central'
    perifericos_ids   = [f'agent_p_{i}' for i in range(1, num_peers_extras + 1)]

    # ── Geolocalização ───────────────────────────────────────
    # O nó central é fixado no centro do grid (500, 500).
    # Periféricos/peers recebem posições aleatórias dentro de um
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

    # ── Gera os links de acordo com a topologia ──────────────
    if TOPOLOGY == 'malha':
        links = gerar_links_malha(agentes_info)
    else:                                           # 'estrela' ou fallback
        links = gerar_links_estrela(agentes_info)

    _persistir_mapa_e_config(agentes_info, links)
    print(f"   ↳ {len(agentes_info)} agentes e {len(links)} enlaces gerados para topologia '{TOPOLOGY}'.")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    omnet_sim, pade_sim, monitor = _iniciar_simuladores(world)

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

    # ── Entidades: nós periféricos / peers ───────────────────
    for i in range(1, num_peers_extras + 1):
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


def _montar_anel(world):
    """Monta a topologia anel — N = NUM_PERIFERICOS agentes, todos com
    o mesmo papel, nomeados agente_1..agente_N (nomenclatura exigida por
    pade_anel.py, cujo CONFIG_REDE é construído dinamicamente a partir da
    mesma variável NUM_PERIFERICOS)."""

    total_agentes = max(2, NUM_PERIFERICOS)
    ids = [f'agente_{i}' for i in range(1, total_agentes + 1)]

    # ── Geolocalização: distribui os agentes num círculo ─────
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

    links = gerar_links_anel(agentes_info)
    _persistir_mapa_e_config(agentes_info, links)
    print(f"   ↳ {len(links)} enlaces gerados para topologia 'anel' "
          f"({total_agentes} agentes).")
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    omnet_sim, pade_sim, monitor = _iniciar_simuladores(world)

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


def _persistir_mapa_e_config(agentes_info, links):
    """Persiste posições, enlaces e a config da rodada
    (topologia/N/redes), comum às três topologias."""
    os.makedirs(OMNET_DIR, exist_ok=True)
    with open(os.path.join(OMNET_DIR, 'posicoes.json'), 'w', encoding='utf-8') as f:
        json.dump(agentes_info, f, indent=4)

    with open(os.path.join(OMNET_DIR, 'links.json'), 'w', encoding='utf-8') as f:
        json.dump(links, f, indent=4)

    with open(os.path.join(OMNET_DIR, 'config.json'), 'w', encoding='utf-8') as f:
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
    world.run(until=SIM_STEPS)
