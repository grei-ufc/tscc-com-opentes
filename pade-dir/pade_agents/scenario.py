#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scenario.py — Orquestrador de cenário Mosaik.

Substitui star.py. Lê TOPOLOGY, NUM_PERIFERICOS e TIPOS_REDE do ambiente
e monta a topologia correspondente (estrela ou malha) antes de iniciar
o loop de co-simulação.
"""

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
_tipos_raw = os.environ.get('TIPOS_REDE', 'Link_Wired,Link_5G,Link_4G,Link_IoT')
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

    Esta função é idêntica à que existia em star.py; ela já era
    totalmente agnóstica à topologia — só descreve o que as listas mandam.
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
# MONTAGEM DO CENÁRIO MOSAIK
# ══════════════════════════════════════════════════════════════

def create_scenario(world):
    print(f"\nTopologia : {TOPOLOGY.upper()}")
    print(f"   Periféricos: {NUM_PERIFERICOS}")
    print(f"   Redes      : {', '.join(TIPOS_REDE)}\n")

    # ── IDs dos agentes ──────────────────────────────────────
    agente_central_id = 'agent_central'
    perifericos_ids   = [f'agent_p_{i}' for i in range(1, NUM_PERIFERICOS + 1)]

    # ── Geolocalização ───────────────────────────────────────
    # O nó central é fixado no centro do grid (500, 500).
    # Periféricos recebem posições aleatórias dentro de um
    # grid de 1000 × 1000 metros.
    agentes_info = []
    agentes_info.append({
        'id':   agente_central_id,
        'x':    500.0,
        'y':    500.0,
        'tipo': 'Central',
    })
    for pid in perifericos_ids:
        agentes_info.append({
            'id':   pid,
            'x':    round(random.uniform(0, 1000), 2),
            'y':    round(random.uniform(0, 1000), 2),
            'tipo': 'Periferico',
        })

    # ── Persiste posições para o dashboard ──────────────────
    # plot_results_star.py lê este arquivo para desenhar o mapa espacial.
    with open('/omnet-dir/posicoes.json', 'w') as f:
        json.dump(agentes_info, f, indent=4)

    # ── Persiste configuração para o script de plotagem ─────
    # Permite que plot_results_star.py saiba qual topologia foi usada
    # e ajuste a visualização das arestas do mapa de acordo.
    with open('/omnet-dir/config.json', 'w') as f:
        json.dump({
            'topologia':       TOPOLOGY,
            'num_perifericos': NUM_PERIFERICOS,
            'tipos_rede':      TIPOS_REDE,
        }, f, indent=4)

    # ── Gera os links de acordo com a topologia ──────────────
    if TOPOLOGY == 'malha':
        links = gerar_links_malha(agentes_info)
    else:                                           # 'estrela' ou qualquer outro valor
        links = gerar_links_estrela(agentes_info)

    total = len(links)
    print(f"   ↳ {total} enlaces gerados para topologia '{TOPOLOGY}'.")

    # ── Escreve o DynamicNetwork.ned ─────────────────────────
    gerar_topologia_ned(agentes_info, links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    # ── Inicia os três simuladores ───────────────────────────
    omnet_sim   = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    pade_sim    = world.start('PadeSim')
    monitor     = coletor_sim.Monitor()

    # ── Entidade: nó central ─────────────────────────────────
    agente_central_pade = pade_sim.PadeAgent(agent_id='AgenteCentral')
    node_central_omnet  = omnet_sim.AgentNode(
        node_type='AgentNode', eid=agente_central_id
    )

    # Central → OMNeT++ (envia)
    world.connect(agente_central_pade, node_central_omnet,
                  ('val_out', 'val_in'))
    # OMNeT++ → Central (recebe, com defasagem para quebrar ciclo)
    world.connect(node_central_omnet, agente_central_pade,
                  ('val_out', 'val_in'),
                  time_shifted=True, initial_data={'val_out': ''})
    # OMNeT++ → Monitor (telemetria do nó central)
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


# ══════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=20)