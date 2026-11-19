#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
omnet_zmq_emulator.py — Emulador ZMQ (REP) de eventos discretos compatível com
MosaikBridge.cc + AgentNode.cc + Profiles.ned, para validação fim a fim sem
Docker e sem OMNeT++.

Lê DynamicNetwork.ned (gerado pelo scenario.py) e Profiles.ned (fonte única
dos parâmetros de canal) e reproduz a física de AgentNode.cc:
  - Endereçamento pelos `receivers` da mensagem FIPA-ACL (mapPadeToOmnet)
  - Roteamento estático por caminho mínimo em nº de saltos (BFS, empate pela
    menor porta) e encaminhamento multi-salto (`packets_forwarded`)
  - Atraso base do canal (amostrado uma vez por canal, como parâmetro NED não
    volátil) + propagação espacial: 5 ns/m em meio guiado (Fibra/Wired) e
    0,00005 s/m nos demais; ruído de jitter U(0, 25%) quando base > 1,5 ms
  - Tempo de transmissão (bytes * 8 / datarate) e fila finita de 5 pacotes por
    porta (buffer overflow)
  - Perda POR SALTO: PER do canal + atenuação espacial (1,5% a cada 100 m,
    exceto meio guiado) escalonada pelo payload
  - Protocolo ZMQ REQ/REP do MosaikBridge.cc (incluindo mosaik_step)

Simplificação: todos os eventos de um passo são resolvidos dentro do próprio
passo (o OMNeT++ real pode entregar pacotes muito lentos no passo seguinte).
"""

import heapq
import itertools
import json
import math
import os
import random
import re
import zmq


# ══════════════════════════════════════════════════════════════
# PERFIS DE CANAL (Profiles.ned)
# ══════════════════════════════════════════════════════════════

_UNIDADES_TEMPO = {'s': 1.0, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9}
_UNIDADES_TAXA = {'bps': 1.0, 'kbps': 1e3, 'Mbps': 1e6, 'Gbps': 1e9}


def _tempo(txt):
    m = re.fullmatch(r'\s*([0-9.]+)\s*(s|ms|us|ns)?\s*', txt)
    if not m:
        raise ValueError(f"Tempo NED não reconhecido: {txt!r}")
    return float(m.group(1)) * _UNIDADES_TEMPO[m.group(2) or 's']


def _taxa(txt):
    m = re.fullmatch(r'\s*([0-9.]+)\s*(bps|kbps|Mbps|Gbps)\s*', txt)
    if not m:
        raise ValueError(f"Datarate NED não reconhecido: {txt!r}")
    return float(m.group(1)) * _UNIDADES_TAXA[m.group(2)]


def _amostrar_delay(rng, expr):
    """Avalia as expressões de delay usadas em Profiles.ned."""
    expr = expr.strip()
    m = re.fullmatch(r'truncnormal\(([^,]+),([^)]+)\)', expr)
    if m:
        media, desvio = _tempo(m.group(1)), _tempo(m.group(2))
        for _ in range(100):
            v = rng.gauss(media, desvio)
            if v >= 0.0:
                return v
        return media
    m = re.fullmatch(r'exponential\(([^)]+)\)', expr)
    if m:
        return rng.expovariate(1.0 / _tempo(m.group(1)))
    return _tempo(expr)


def parse_profiles_ned(path):
    """Retorna {nome_canal: {'delay': expr, 'datarate': bps, 'per': float}}."""
    with open(path, 'r', encoding='utf-8') as f:
        conteudo = re.sub(r'//[^\n]*', '', f.read())
    perfis = {}
    for m in re.finditer(r'channel\s+(\w+)\s+extends\s+ned\.DatarateChannel\s*\{(.*?)\}',
                         conteudo, re.DOTALL):
        corpo = m.group(2)
        delay = re.search(r'\bdelay\s*=\s*([^;]+);', corpo)
        taxa = re.search(r'\bdatarate\s*=\s*([^;]+);', corpo)
        per = re.search(r'\bper\s*=\s*([^;]+);', corpo)
        perfis[m.group(1)] = {
            'delay': delay.group(1) if delay else '0s',
            'datarate': _taxa(taxa.group(1)) if taxa else 1e9,
            'per': float(per.group(1)) if per else 0.0,
        }
    return perfis


def _meio_guiado(tipo):
    # Mesmo critério de AgentNode::isGuidedMedium
    return 'Fibra' in tipo or 'Wired' in tipo


# ══════════════════════════════════════════════════════════════
# TOPOLOGIA (DynamicNetwork.ned)
# ══════════════════════════════════════════════════════════════

def parse_dynamic_network_ned(ned_path):
    """Extrai nós (xPos, yPos) e conexões, na ordem em que aparecem."""
    nodes, links = {}, []
    if not os.path.exists(ned_path):
        return nodes, links
    with open(ned_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for match in re.finditer(r'(\w+)\s*:\s*AgentNode\s*\{([^}]*)\}', content, re.DOTALL):
        body = match.group(2)
        xm = re.search(r'xPos\s*=\s*([0-9.eE+-]+)', body)
        ym = re.search(r'yPos\s*=\s*([0-9.eE+-]+)', body)
        nodes[match.group(1)] = {
            'x': float(xm.group(1)) if xm else 0.0,
            'y': float(ym.group(1)) if ym else 0.0,
        }

    for match in re.finditer(r'(\w+)\.port\+\+\s*<-->\s*(\w+)\s*<-->\s*(\w+)\.port\+\+\s*;', content):
        links.append({'origem': match.group(1), 'tipo': match.group(2), 'destino': match.group(3)})
    return nodes, links


def map_pade_to_omnet(pade_id):
    # Mesmo mapeamento de AgentNode::mapPadeToOmnet
    if pade_id == 'AgenteCentral':
        return 'agent_central'
    if pade_id.startswith('AgenteP_'):
        return 'agent_p_' + pade_id[len('AgenteP_'):]
    return pade_id


class Porta:
    """Uma porta de saída (port$o[i]) com seu canal e fila de transmissão."""

    def __init__(self, vizinho, tipo, base_delay, datarate, per):
        self.vizinho = vizinho
        self.tipo = tipo
        self.base_delay = base_delay
        self.datarate = datarate
        self.per = per
        self.ocupada_ate = 0.0
        self.fila = []


class AgentNodeSim:
    def __init__(self, eid, x=0.0, y=0.0):
        self.eid = eid
        self.x = x
        self.y = y
        self.portas = []          # índice = número da porta (ordem de port++)
        self.rota = {}            # destino -> índice da porta do próximo salto
        self.drop_espacial = {}   # vizinho -> chance base de perda por distância
        self.status = 'idle'
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_dropped = 0
        self.packets_forwarded = 0
        self.ultima_latencia = {}
        self.clear_step_buffers()

    def clear_step_buffers(self):
        self.val_out = []
        self.sizes = []
        self.latencies = []
        self.jitters = []


# ══════════════════════════════════════════════════════════════
# SIMULADOR
# ══════════════════════════════════════════════════════════════

class OmnetDiscreteSimulator:
    def __init__(self, omnet_dir, seed=None):
        self.omnet_dir = omnet_dir
        self.rng = random.Random(int(seed) if seed not in (None, '') else 42)
        self.nodes = {}
        self.topologia_carregada = False
        self.perfis = parse_profiles_ned(os.path.join(omnet_dir, 'Profiles.ned'))

    def _carregar_topologia(self):
        if self.topologia_carregada:
            return
        ned_nodes, ned_links = parse_dynamic_network_ned(
            os.path.join(self.omnet_dir, 'DynamicNetwork.ned'))
        if not ned_links:
            return
        for nid, c in ned_nodes.items():
            self.nodes[nid] = AgentNodeSim(nid, c['x'], c['y'])

        # Cada '<-->' cria um canal por sentido, cada um com seu delay amostrado.
        for lk in ned_links:
            u, v, tipo = lk['origem'], lk['destino'], lk['tipo']
            if u not in self.nodes or v not in self.nodes:
                continue
            perfil = self.perfis.get(tipo, {'delay': '1ms', 'datarate': 1e9, 'per': 0.0})
            for a, b in ((u, v), (v, u)):
                na, nb = self.nodes[a], self.nodes[b]
                dist = math.hypot(na.x - nb.x, na.y - nb.y)
                guiado = _meio_guiado(tipo)
                base = _amostrar_delay(self.rng, perfil['delay']) + dist * (5e-9 if guiado else 0.00005)
                na.portas.append(Porta(b, tipo, base, perfil['datarate'], perfil['per']))
                na.drop_espacial[b] = 0.0 if guiado else (dist / 100.0) * 0.015

        for node in self.nodes.values():
            self._construir_rotas(node)
        self.topologia_carregada = True

    def _construir_rotas(self, origem):
        """BFS em nº de saltos; guarda a 1ª porta do caminho (AgentNode::buildRoutingTable)."""
        primeira_porta = {origem.eid: -1}
        fila = [origem.eid]
        while fila:
            atual = fila.pop(0)
            for idx, porta in enumerate(self.nodes[atual].portas):
                if porta.vizinho in primeira_porta:
                    continue
                primeira_porta[porta.vizinho] = idx if atual == origem.eid else primeira_porta[atual]
                fila.append(porta.vizinho)
        origem.rota = {d: p for d, p in primeira_porta.items() if d != origem.eid}

    # ── eventos ─────────────────────────────────────────────────
    def _transmitir(self, agenda, agora, node, idx_porta, pkt):
        """AgentNode::transmitPacket: envia se o canal está livre, senão enfileira (máx. 5)."""
        porta = node.portas[idx_porta]
        if agora >= porta.ocupada_ate and not porta.fila:
            self._enviar(agenda, agora, node, porta, pkt)
        elif len(porta.fila) >= 5:
            node.packets_dropped += 1
            node.status = 'overflow_drop'
        else:
            porta.fila.append(pkt)

    def _enviar(self, agenda, agora, node, porta, pkt):
        ruido = self.rng.random() * porta.base_delay * 0.25 if porta.base_delay > 0.0015 else 0.0
        t_tx = pkt['bytes'] * 8.0 / porta.datarate
        porta.ocupada_ate = agora + t_tx
        chegada = agora + t_tx + max(0.0001, porta.base_delay + ruido)
        erro_bit = self.rng.random() < porta.per
        heapq.heappush(agenda, (chegada, next(self._seq), 'rx',
                                (porta.vizinho, node.eid, pkt, erro_bit)))
        heapq.heappush(agenda, (porta.ocupada_ate, next(self._seq), 'fim_tx', (node, porta)))

    def _receber(self, agenda, agora, eid, salto_anterior, pkt, erro_bit):
        """AgentNode::handleMessage para um pacote que chegou."""
        node = self.nodes[eid]
        fator = max(1.0, pkt['bytes'] / 15000.0)
        chance = min(0.99, node.drop_espacial.get(salto_anterior, 0.0) * fator)
        if erro_bit or self.rng.random() < chance:
            node.packets_dropped += 1
            node.status = 'error_dropped'
            return

        if pkt['dest'] != eid:
            idx = node.rota.get(pkt['dest'])
            if idx is None:
                node.packets_dropped += 1
                return
            node.packets_forwarded += 1
            self._transmitir(agenda, agora, node, idx, pkt)
            return

        latencia = agora - pkt['criado']
        anterior = node.ultima_latencia.get(pkt['src'], 0.0)
        jitter = abs(latencia - anterior) if anterior > 0 else 0.0
        node.ultima_latencia[pkt['src']] = latencia
        node.packets_received += 1
        node.status = 'receiving'
        node.val_out.append(pkt['payload'])
        node.sizes.append(f"{float(pkt['bytes']):.6f}")
        node.latencies.append(f"{latencia:.6f}")
        node.jitters.append(f"{jitter:.6f}")

    def _passo(self, inputs):
        for node in self.nodes.values():
            node.clear_step_buffers()
            if node.status != 'error_dropped':
                node.status = 'idle'
            for porta in node.portas:
                porta.ocupada_ate = 0.0
                porta.fila.clear()

        agenda = []
        self._seq = itertools.count()

        # Injeção (AgentNode::processInjectedData) no instante 0 do passo
        for eid, attrs in inputs.items():
            node = self.nodes.get(eid)
            if node is None or 'val_in' not in attrs:
                continue
            valores = attrs['val_in']
            valores = valores.values() if isinstance(valores, dict) else [valores]
            bruto = '|||'.join(v for v in valores if isinstance(v, str) and v)
            for msg in (m for m in bruto.split('|||') if m):
                try:
                    receivers = json.loads(msg).get('receivers', [])
                except (ValueError, AttributeError):
                    continue
                for rec in receivers:
                    dest = map_pade_to_omnet(str(rec).split('@')[0])
                    if not dest or dest == eid or dest not in node.rota:
                        continue
                    pkt = {'src': eid, 'dest': dest, 'payload': msg,
                           'bytes': len(msg.encode('utf-8')), 'criado': 0.0}
                    self._transmitir(agenda, 0.0, node, node.rota[dest], pkt)
                    node.packets_sent += 1
                    node.status = 'transmitting'

        while agenda:
            agora, _, tipo, dados = heapq.heappop(agenda)
            if tipo == 'rx':
                self._receber(agenda, agora, *dados)
            else:  # fim_tx: libera o canal e envia o próximo da fila
                node, porta = dados
                if porta.fila:
                    self._enviar(agenda, agora, node, porta, porta.fila.pop(0))

    def handle_request(self, req):
        action = req.get('action', '')
        if action == 'create':
            self._carregar_topologia()
            eid = req.get('eid', 'unknown')
            if eid not in self.nodes:
                self.nodes[eid] = AgentNodeSim(eid)
            return {'status': 'ok', 'eid': eid}

        if action == 'connect':
            # Também usado pelo omnet_wrapper como sonda de disponibilidade.
            src, dest = req.get('src'), req.get('dest')
            if src in self.nodes and dest in self.nodes:
                return {'status': 'ok', 'msg': f'Connected {src} to {dest}'}
            return {'status': 'error', 'reason': 'Nodes not found'}

        if action == 'step':
            self._carregar_topologia()
            mosaik_step = int(req.get('time', 0))
            self._passo(req.get('inputs', {}))
            data_out = {
                eid: {
                    'status': n.status,
                    'packets_sent': n.packets_sent,
                    'packets_received': n.packets_received,
                    'packets_dropped': n.packets_dropped,
                    'packets_forwarded': n.packets_forwarded,
                    'val_out': '|||'.join(n.val_out),
                    'packet_sizes_out': '|||'.join(n.sizes),
                    'latencies_out': '|||'.join(n.latencies),
                    'jitters_out': '|||'.join(n.jitters),
                }
                for eid, n in self.nodes.items()
            }
            return {'status': 'ok', 'mosaik_step': mosaik_step, 'data': data_out}

        return {'status': 'error', 'reason': f'Unknown action: {action}'}


def serve_forever(port, omnet_dir, seed=None, max_steps=None):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(f"tcp://127.0.0.1:{port}")
    sim = OmnetDiscreteSimulator(omnet_dir=omnet_dir, seed=seed)
    steps_done = 0
    try:
        while True:
            req = sock.recv_json()
            sock.send_json(sim.handle_request(req))
            if req.get('action') == 'step':
                steps_done += 1
                if max_steps is not None and steps_done >= max_steps:
                    break
    finally:
        sock.close(linger=0)
        ctx.term()


if __name__ == '__main__':
    port = int(os.environ.get('OMNET_PORT', 5555))
    omnet_dir = os.environ.get(
        'OMNET_DIR',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'omnet-dir'))
    )
    seed = os.environ.get('RANDOM_SEED', '42')
    max_steps = int(os.environ['SIM_STEPS']) if 'SIM_STEPS' in os.environ else None
    serve_forever(port=port, omnet_dir=omnet_dir, seed=seed, max_steps=max_steps)
