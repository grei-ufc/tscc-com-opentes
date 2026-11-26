#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_consistencia.py — Testes rápidos (< 1 s) de consistência entre as partes
do projeto que precisam concordar: catálogo × Profiles.ned × docker-compose.yml,
e a montagem das topologias (cosim.topologias) usada pelo Mosaik e pelo PADE.
"""

import os
import random
import re

import pytest

from cosim import canais, radio
from cosim.catalogo import (COR_POR_ROTULO, TECNOLOGIAS, TIPOS_REDE_PADRAO, TOPOLOGIAS,
                            canal_celular)
from cosim.topologias import (montar_anel, montar_arvore, montar_estrela, montar_hibrida, montar_ieee13,
                              montar_malha, omnet_para_pade, pade_para_omnet, vizinhos,
                              vizinhos_anel)
from cosim.ned import escrever_ned
from cosim.topologias import IEEE13_NOS

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _ler(*partes):
    with open(os.path.join(ROOT_DIR, *partes), encoding='utf-8') as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
# CATÁLOGO × Profiles.ned × docker-compose.yml
# ══════════════════════════════════════════════════════════════

def test_catalogo_cobre_exatamente_os_canais_do_profiles_ned():
    perfis = canais.ler_perfis(os.path.join(ROOT_DIR, 'omnet-dir', 'Profiles.ned'))
    assert set(perfis) == set(TECNOLOGIAS), (
        "Todo canal de Profiles.ned precisa de rótulo e cor em cosim/catalogo.py (e vice-versa)")


def test_perfis_sao_validos_e_descritos():
    for perfil in canais.ler_perfis(os.path.join(ROOT_DIR, 'omnet-dir', 'Profiles.ned')).values():
        assert perfil.bps > 0
        assert 0.0 <= perfil.per < 1.0
        assert canais.taxa_legivel(perfil) in canais.descrever(perfil)


def test_mesmo_rotulo_mesma_cor():
    for t in TECNOLOGIAS.values():
        assert COR_POR_ROTULO[t.rotulo] == t.cor, f"{t.ned}: cor diferente das outras '{t.rotulo}'"


def test_canal_celular():
    assert canal_celular('2g') == 'Celular2G'
    assert canal_celular('5G') == 'Celular5G'
    assert canal_celular('xyz') == 'Celular4G'


def test_tipos_rede_padrao_iguais_no_compose():
    padroes = re.findall(r'TIPOS_REDE=\$\{TIPOS_REDE:-([^}]*)\}', _ler('docker-compose.yml'))
    assert padroes, "TIPOS_REDE não encontrado no docker-compose.yml"
    assert set(padroes) == {','.join(TIPOS_REDE_PADRAO)}


def test_scripts_do_catalogo_existem_e_sao_despachados():
    compose = _ler('docker-compose.yml')
    for t in TOPOLOGIAS.values():
        assert os.path.exists(os.path.join(ROOT_DIR, 'pade-dir', 'pade_agents', t.script_pade))
        assert os.path.exists(os.path.join(ROOT_DIR, 'mosaik-dir', t.script_plot))
        if t.id != 'estrela':   # estrela é o "else" do despacho
            assert f'"$$TOPOLOGY" = "{t.id}"' in compose, f"{t.id} fora do despacho do compose"
        assert t.script_pade in compose


def test_cosim_montado_nos_containers():
    compose = _ler('docker-compose.yml')
    assert compose.count('./cosim:/opt/cosim/cosim:ro') == 2
    assert compose.count('PYTHONPATH=/opt/cosim') == 2


# ══════════════════════════════════════════════════════════════
# TOPOLOGIAS
# ══════════════════════════════════════════════════════════════

TIPOS = ['Link_Wired', 'Link_5G', 'Link_4G']


def _conexa(rede):
    adj = vizinhos(rede)
    inicio = rede.nos[0]['id']
    vistos, fila = {inicio}, [inicio]
    while fila:
        for nb in adj[fila.pop()]:
            if nb not in vistos:
                vistos.add(nb)
                fila.append(nb)
    return len(vistos) == len(rede.nos)


def _ids_unicos(rede):
    ids = [n['id'] for n in rede.nos]
    return len(ids) == len(set(ids))


@pytest.mark.parametrize('n', [1, 5, 20])
def test_estrela(n):
    rede = montar_estrela(n, TIPOS, random.Random(1))
    assert len(rede.nos) == n + 1 and len(rede.links) == n
    assert all(lk['origem'] == 'agent_central' for lk in rede.links)
    assert [lk['tipo'] for lk in rede.links] == [TIPOS[i % 3] for i in range(n)]
    assert _ids_unicos(rede) and _conexa(rede)


@pytest.mark.parametrize('n', [2, 5, 9])
def test_malha(n):
    rede = montar_malha(n, TIPOS, random.Random(1))
    assert len(rede.nos) == n and len(rede.links) == n * (n - 1) // 2
    assert _ids_unicos(rede) and _conexa(rede)


@pytest.mark.parametrize('n', [2, 3, 5, 8])
def test_anel_e_vizinhanca_do_pade(n):
    rede = montar_anel(n, TIPOS)
    assert len(rede.nos) == n and len(rede.links) == (1 if n == 2 else n)
    assert _conexa(rede)
    # pade_anel.py usa vizinhos_anel; precisam ser exatamente os enlaces do NED
    adj = vizinhos(rede)
    assert {k: set(v) for k, v in vizinhos_anel(n).items()} == {k: set(v) for k, v in adj.items()}


@pytest.mark.parametrize('fanout', ['2,2,2', '3,2,4', '1,1,1,1'])
def test_arvore(fanout):
    rede = montar_arvore(fanout, '5g')
    total, nivel = 1, 1
    for f in map(int, fanout.split(',')):
        nivel *= f
        total += nivel
    assert len(rede.nos) == total and len(rede.links) == total - 1
    assert _ids_unicos(rede) and _conexa(rede)
    assert {lk['tipo'] for lk in rede.links} <= {'Fibra', 'Celular5G', 'PLC'}
    assert rede.config == {'arvore_fanout': fanout, 'celular_arvore': '5g'}


@pytest.mark.parametrize('subs,cons,meds,semente', [(3, 1, 3, 42), (3, 3, 5, 42), (2, 2, 4, 7), (5, 4, 10, 1)])
def test_hibrida(subs, cons, meds, semente):
    rede = montar_hibrida(subs, cons, meds, '3g', semente)
    assert len(rede.nos) == 1 + subs + subs * cons + subs * cons * meds
    assert _ids_unicos(rede) and _conexa(rede)
    fibras = sum(lk['tipo'] == 'Fibra' for lk in rede.links)
    assert fibras == (subs if subs >= 3 else 1) + min(2, subs)
    assert sum(lk['tipo'] == 'Celular3G' for lk in rede.links) == subs * cons
    # sem enlaces duplicados (em qualquer sentido)
    pares = [frozenset((lk['origem'], lk['destino'])) for lk in rede.links]
    assert len(pares) == len(set(pares))


def test_topologias_sao_reprodutiveis():
    assert montar_hibrida(4, 3, 8, '4g', 7) == montar_hibrida(4, 3, 8, '4g', 7)
    assert montar_estrela(10, TIPOS, random.Random(3)) == montar_estrela(10, TIPOS, random.Random(3))
    assert montar_malha(6, TIPOS, random.Random(3)) == montar_malha(6, TIPOS, random.Random(3))


def test_vizinhanca_e_simetrica_e_igual_aos_enlaces():
    rede = montar_hibrida(3, 3, 5, '4g', 42)
    adj = vizinhos(rede)
    for a, viz in adj.items():
        for b in viz:
            assert a in adj[b]
    assert sum(len(v) for v in adj.values()) == 2 * len(rede.links)


def test_nomes_pade_omnet():
    for eid in ('agent_central', 'agent_p_1', 'agent_p_12', 'agente_3', 'raiz', 'med0_1_2'):
        assert pade_para_omnet(omnet_para_pade(eid)) == eid
    assert omnet_para_pade('agent_p_7') == 'AgenteP_7'
    assert pade_para_omnet('AgenteCentral') == 'agent_central'

def test_ieee13():
    rede = montar_ieee13(['Link_6TiSCH', 'Link_WiSUN'])
    assert len(rede.nos) == 18
    assert len(rede.links) == 17
    assert rede.config['topologia'] == 'ieee13'
    assert rede.config['num_perifericos'] == 17

    # Enlaces locais na subestação devem usar Link_Wired
    enlaces_subestacao = {lk['destino']: lk['tipo'] for lk in rede.links[:2]}
    assert enlaces_subestacao == {'agent_dso': 'Link_Wired', 'agent_market': 'Link_Wired'}

    # Demais 15 barras ciclam entre Link_6TiSCH e Link_WiSUN de forma determinística
    assert rede == montar_ieee13(['Link_6TiSCH', 'Link_WiSUN'])

# ══════════════════════════════════════════════════════════════
# IEEE 13 NO MERCADO DO OPENTES (modelo de rádio da tese e consulta por mensagem)
# ══════════════════════════════════════════════════════════════

def _posicoes_ieee13(tmp_path):
    """nodes_xy.csv com as coordenadas embutidas, nos nomes do caso do OpenTES."""
    nomes = {'agent_0': '0', 'agent_dso': 'DSO', 'agent_market': 'Market'}
    linhas = ['node,x_m,y_m'] + [
        f"{nomes.get(n['id'], n['id'][6:])},{n['x']},{n['y']}" for n in IEEE13_NOS]
    caminho = tmp_path / 'nodes_xy.csv'
    caminho.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    return str(caminho)


def test_modelo_de_radio_da_tese():
    assert radio.per_do_rssi(-106.37, -106.37) == 1.0      # na sensibilidade: ainda perde tudo
    assert radio.per_do_rssi(-105.0, -106.37) == 0.8       # 1 dB acima: segundo passo da tabela
    assert radio.per_do_rssi(-110.0, -106.37) == 1.0       # abaixo da sensibilidade
    assert radio.per_do_rssi(-90.0, -106.37) == 0.0        # 7 dB ou mais acima
    assert radio.Radio(taxa_bps=150000).sensibilidade > radio.Radio().sensibilidade


def test_ieee13_do_arquivo_de_posicoes(tmp_path):
    rede = montar_ieee13(['Link_6TiSCH', 'Link_WiSUN'], posicoes=_posicoes_ieee13(tmp_path))
    assert [(n['id'], n['x'], n['y']) for n in rede.nos] == \
           [(n['id'], n['x'], n['y']) for n in IEEE13_NOS]
    assert rede.links == montar_ieee13(['Link_6TiSCH', 'Link_WiSUN']).links


def test_ieee13_canais_da_tese_e_opcoes(tmp_path):
    pos = _posicoes_ieee13(tmp_path)
    estrela = montar_ieee13(['Link_6TiSCH_TSCH'], posicoes=pos, subestacao='radio')
    assert len(estrela.links) == 17
    assert all(lk['tipo'] == 'Link_6TiSCH_TSCH' for lk in estrela.links)
    # Enlace imposto pela estrela nunca nasce morto: o PER é condicionado ao limiar.
    assert all(float(lk['params']['per_enlace']) < 0.5 for lk in estrela.links)

    malha = montar_ieee13(['Link_6TiSCH_TSCH'], posicoes=pos, topologia='malha', subestacao='cabo')
    cabo = [lk for lk in malha.links if lk['tipo'] == 'Link_Wired']
    assert len(cabo) == 3, "Concentrador, DSO e Market interligados por cabo"
    assert len(malha.links) > 17, "Na malha os enlaces saem do limiar de PER, com rotas multissalto"
    assert malha == montar_ieee13(['Link_6TiSCH_TSCH'], posicoes=pos, topologia='malha', subestacao='cabo')

    wisun = montar_ieee13(['Link_WiSUN_FAN'], posicoes=pos, topologia='malha',
                          radio=radio.Radio(taxa_bps=300000))
    assert all(lk['params']['taxa_bps'] == '300000' for lk in wisun.links if 'params' in lk)
    assert len(wisun.links) < len(malha.links), "Taxa maior, sensibilidade pior, menos enlaces"


def test_ned_com_parametros_e_ponte(tmp_path):
    rede = montar_ieee13(['Link_6TiSCH_TSCH'], posicoes=_posicoes_ieee13(tmp_path), cells=4)
    ned = tmp_path / 'DynamicNetwork.ned'
    escrever_ned(rede.nos, rede.links, str(ned), ponte='ServidorConsulta')
    texto = ned.read_text(encoding='utf-8')
    assert 'servidorConsulta: ServidorConsulta;' in texto and 'mosaikBridge' not in texto
    assert texto.count('<--> Link_6TiSCH_TSCH { per_enlace = ') == 15
    assert 'cells = 4;' in texto
    assert texto.count('.port++ <-->') == len(rede.links)
