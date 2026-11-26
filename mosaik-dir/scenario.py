#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scenario.py — Orquestrador único de cenário Mosaik.

Suporta cinco topologias, selecionadas via TOPOLOGY:

    estrela  — 1 central  <-->  N periféricos          (pade_star.py)
    malha    — N agentes peers em full mesh             (pade_malha.py)
    anel     — N agentes em ciclo fechado               (pade_anel.py)
    arvore   — árvore radial IEC 61850 com fan-out      (pade_arvore.py)
    hibrida  — hierarquia CCO→subs(fibra)→cons(celular)→meds(RF mesh)
                                                        (pade_hibrida.py)
    ieee13   — 18 agentes do alimentador IEEE 13 (OpenTES) (pade_ieee13.py)

A rede de cada topologia (nós, posições, enlaces) é montada por
cosim.topologias — a mesma definição que os agentes PADE usam para achar
seus vizinhos. Aqui ficam só a integração com o Mosaik, a escrita dos
artefatos da rodada e a chamada do script de plotagem.

Variáveis de ambiente
---------------------
Comuns:
    TOPOLOGY          estrela | malha | anel | arvore | hibrida | ieee13
    NUM_PERIFERICOS   estrela: nº de periféricos (total = N + 1)
                      malha/anel: nº TOTAL de agentes (N)
    TIPOS_REDE        lista separada por vírgula de nomes de canal
    SIM_STEPS         passos da co-simulação (padrão 20)
    RANDOM_SEED       semente para reprodutibilidade (vazio = aleatório)
    PADE_HOST         host do PADE (padrão 127.0.0.1)
    PADE_PORT         porta do PADE (padrão 5678)
    OMNET_DIR         pasta do modelo OMNeT++ (padrão /omnet-dir no container,
                      ../omnet-dir fora dele)
    OUTPUT_DIR        pasta das saídas da rodada: results.csv, gráficos e uma
                      cópia de DynamicNetwork.ned, posicoes/links/config.json
                      (padrão: a pasta atual, como sempre foi)

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

import importlib
import json
import os
import random
import shutil
import socket
import time

import mosaik

from cosim import topologias
from cosim.catalogo import TIPOS_REDE_PADRAO, TOPOLOGIAS
from cosim.ned import escrever_ned

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE
# ══════════════════════════════════════════════════════════════

TOPOLOGY         = os.environ.get('TOPOLOGY', 'estrela').lower()
NUM_PERIFERICOS  = int(os.environ.get('NUM_PERIFERICOS', 3))
_tipos_raw       = os.environ.get('TIPOS_REDE', ','.join(TIPOS_REDE_PADRAO))
TIPOS_REDE       = [t.strip() for t in _tipos_raw.split(',') if t.strip()]

SIM_STEPS   = int(os.environ.get('SIM_STEPS', 20))
RANDOM_SEED = os.environ.get('RANDOM_SEED', '').strip()
if RANDOM_SEED:
    random.seed(int(RANDOM_SEED))

PADE_HOST = os.environ.get('PADE_HOST', '127.0.0.1')
PADE_PORT = int(os.environ.get('PADE_PORT', 5678))

# Dentro do container o modelo OMNeT++ é montado em /omnet-dir; fora dele
# (testes locais) usa a pasta irmã ../omnet-dir.
_DEFAULT_OMNET_DIR = (
    '/omnet-dir'
    if os.path.isdir('/omnet-dir')
    else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'omnet-dir'))
)
OMNET_DIR = os.path.abspath(os.environ.get('OMNET_DIR', _DEFAULT_OMNET_DIR))

# Absoluto desde já: o ponto de entrada muda a pasta atual para OUTPUT_DIR.
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '').strip()
OUTPUT_DIR = os.path.abspath(OUTPUT_DIR) if OUTPUT_DIR else ''

# Árvore
ARVORE_FANOUT  = os.environ.get('ARVORE_FANOUT', '3,2,4')
CELULAR_ARVORE = os.environ.get('CELULAR_ARVORE', '4g').lower()

# Híbrida
SUBESTACOES        = int(os.environ.get('SUBESTACOES',        3))
CONCENTRADORES     = int(os.environ.get('CONCENTRADORES',     3))
MEDIDORES_CLUSTER  = int(os.environ.get('MEDIDORES_CLUSTER',  5))
CELULAR_HIBRIDA    = os.environ.get('CELULAR_HIBRIDA', '4g').lower()
SEMENTE_HIBRIDA    = int(os.environ.get('SEMENTE_HIBRIDA',    42))

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DOS SIMULADORES MOSAIK
# ══════════════════════════════════════════════════════════════

def _resolver_ipv4(host):
    """
    Resolve o hostname explicitamente para IPv4. Evita que o glibc no Docker
    (ex.: GitHub Codespaces) tente IPv6 primeiro e trave ~30 s na conexão.
    """
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except OSError as e:
        print(f"[MOSAIK] ⚠ Falha ao resolver IPv4 de '{host}': {e}; mantendo original.", flush=True)
    return host


PADE_HOST_IPV4 = _resolver_ipv4(PADE_HOST)

sim_config = {
    'OmnetSim':   {'python': 'omnet_wrapper:OmnetAdapter'},
    'ColetorSim': {'python': 'collector:Coletor'},
    'PadeSim':    {'connect': f'{PADE_HOST_IPV4}:{PADE_PORT}'},
}


def _aguardar_pade_pronto(timeout=30.0):
    """Espera a porta TCP do PADE aceitar conexões antes do world.start('PadeSim')."""
    print(f"[MOSAIK] Aguardando PADE em {PADE_HOST_IPV4}:{PADE_PORT}...", flush=True)
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            with socket.create_connection((PADE_HOST_IPV4, PADE_PORT), timeout=0.5):
                print("[MOSAIK] ✓ PADE pronto.", flush=True)
                return True
        except OSError:
            time.sleep(0.3)
    print(f"[MOSAIK] ⚠ Timeout ({timeout}s) aguardando PADE; tentando conectar mesmo assim.", flush=True)
    return False


def _caminho_omnet(nome):
    return os.path.join(OMNET_DIR, nome)


# ══════════════════════════════════════════════════════════════
# MONTAGEM DA REDE
# ══════════════════════════════════════════════════════════════

def montar_rede():
    """Rede da topologia selecionada (definição única em cosim.topologias)."""
    if TOPOLOGY == 'anel':
        print(f"   Agentes: {NUM_PERIFERICOS}   Redes: {', '.join(TIPOS_REDE)}\n")
        return topologias.montar_anel(NUM_PERIFERICOS, TIPOS_REDE)
    if TOPOLOGY == 'arvore':
        print(f"   Fan-out: {ARVORE_FANOUT}   Celular: {CELULAR_ARVORE}\n")
        return topologias.montar_arvore(ARVORE_FANOUT, CELULAR_ARVORE)
    if TOPOLOGY == 'hibrida':
        print(f"   Subs: {SUBESTACOES}  Cons/sub: {CONCENTRADORES}  "
              f"Meds/con: {MEDIDORES_CLUSTER}  Celular: {CELULAR_HIBRIDA}  "
              f"Semente: {SEMENTE_HIBRIDA}\n")
        return topologias.montar_hibrida(SUBESTACOES, CONCENTRADORES, MEDIDORES_CLUSTER,
                                         CELULAR_HIBRIDA, SEMENTE_HIBRIDA)
    print(f"   N: {NUM_PERIFERICOS}\n   Redes: {', '.join(TIPOS_REDE)}\n")
    if TOPOLOGY == 'malha':
        # Posições aleatórias do módulo random, semeado por RANDOM_SEED.
        return topologias.montar_malha(NUM_PERIFERICOS, TIPOS_REDE, random)
    if TOPOLOGY == 'ieee13':
        # Concentrador, DSO e Market na subestação e as 15 barras ciclando TIPOS_REDE.
        return topologias.montar_ieee13(TIPOS_REDE)
    # 'estrela' ou qualquer outro valor
    return topologias.montar_estrela(NUM_PERIFERICOS, TIPOS_REDE, random)


# ══════════════════════════════════════════════════════════════
# GERAÇÃO DO ARQUIVO NED  (agnóstica à topologia)
# ══════════════════════════════════════════════════════════════

def gerar_topologia_ned(agentes_info, links, arquivo_saida=None):
    """
    Escreve DynamicNetwork.ned a partir de listas genéricas.

    agentes_info : list[dict]  — cada item tem 'id', 'x', 'y', 'tipo'.
    links        : list[dict]  — cada item tem 'origem', 'destino', 'tipo' (e,
                   nos canais da tese, 'params').

    A escrita é atômica e fica em cosim.ned, a fonte única da geração do NED.
    """
    escrever_ned(agentes_info, links, arquivo_saida or _caminho_omnet('DynamicNetwork.ned'),
                 ponte='MosaikBridge')


# ══════════════════════════════════════════════════════════════
# MONTAGEM DO CENÁRIO MOSAIK
# ══════════════════════════════════════════════════════════════

def create_scenario(world):
    print(f"\nTopologia : {TOPOLOGY.upper()}")

    omnet_sim   = world.start('OmnetSim')
    coletor_sim = world.start('ColetorSim')
    _aguardar_pade_pronto()
    pade_sim    = world.start('PadeSim')
    monitor     = coletor_sim.Monitor()

    rede = montar_rede()
    _persistir_mapa_e_config(rede.nos, links=rede.links, extra_config=rede.config)
    print(f"   ↳ {len(rede.nos)} nós e {len(rede.links)} enlaces gerados para topologia '{TOPOLOGY}'.")
    gerar_topologia_ned(rede.nos, rede.links)
    print("   ↳ DynamicNetwork.ned gerado.\n")

    _conectar_agentes_mosaik(world, omnet_sim, pade_sim, monitor, rede.nos)


def _conectar_agentes_mosaik(world, omnet_sim, pade_sim, monitor, agentes_info):
    """Registra cada agente no Mosaik e cria as conexões padrão:
    PADE → OMNeT++ (val_out → val_in), OMNeT++ → PADE no passo seguinte
    (time_shifted) e OMNeT++ → coletor (métricas)."""
    for ag in agentes_info:
        eid         = ag['id']
        agente_pade = pade_sim.PadeAgent(agent_id=topologias.omnet_para_pade(eid))
        node_omnet  = omnet_sim.AgentNode(node_type='AgentNode', eid=eid)
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
    Salva os artefatos da rodada em OMNET_DIR para uso pelos scripts
    de plotagem e pelo dashboard Streamlit.

    posicoes.json  — lista de nós com id, x, y, tipo, camada (quando disponível)
    config.json    — topologia, parâmetros e metadados extras
    links.json     — lista de enlaces da rodada atual (removido se não houver)
    """
    os.makedirs(OMNET_DIR, exist_ok=True)
    with open(_caminho_omnet('posicoes.json'), 'w', encoding='utf-8') as f:
        json.dump(agentes_info, f, indent=4)

    config_data = {
        'topologia':       TOPOLOGY,
        'num_perifericos': NUM_PERIFERICOS,
        'tipos_rede':      TIPOS_REDE,
    }
    if extra_config:
        config_data.update(extra_config)
    with open(_caminho_omnet('config.json'), 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

    # links.json SEMPRE reflete a rodada atual. Um arquivo velho (de outra topologia) fazia os
    # scripts de plotagem não casarem remetente/destino e gerar painéis por tecnologia vazios.
    caminho_links = _caminho_omnet('links.json')
    if links is not None:
        with open(caminho_links, 'w', encoding='utf-8') as f:
            json.dump(links, f, indent=2)
    elif os.path.exists(caminho_links):
        os.remove(caminho_links)


# ══════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if OUTPUT_DIR:
        # O coletor (results.csv) e os plots (grafico_*) gravam na pasta atual.
        # Os imports não são afetados: a pasta deste script já está no sys.path.
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.chdir(OUTPUT_DIR)
        print(f"[MOSAIK] Saídas da rodada em {OUTPUT_DIR}", flush=True)

    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=SIM_STEPS)

    # Plotagem da topologia (script definido no catálogo; estrela é o padrão)
    print("\nGerando gráficos da simulação...")
    script = TOPOLOGIAS.get(TOPOLOGY, TOPOLOGIAS['estrela']).script_plot
    importlib.import_module(script.removesuffix('.py')).gerar_graficos()

    if OUTPUT_DIR:
        # Registro completo da rodada: a rede e a configuração junto dos resultados
        for nome in ('DynamicNetwork.ned', 'posicoes.json', 'links.json', 'config.json'):
            if os.path.exists(_caminho_omnet(nome)):
                shutil.copy2(_caminho_omnet(nome), os.path.join(OUTPUT_DIR, nome))
