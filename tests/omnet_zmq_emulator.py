#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
omnet_zmq_emulator.py — Emulador de eventos discretos ZMQ (REP) compatível
com MosaikBridge.cc + AgentNode.cc + Profiles.ned para validação fim a fim
e execução local sem necessidade de Docker.

Lê DynamicNetwork.ned, posicoes.json e links.json gerados pelo scenario.py
e reproduz fielmente a física de rede implementada em AgentNode.cc e
MosaikBridge.cc:
  - Perfis de canal de Profiles.ned (Link_Wired, Link_5G, Link_Wireless, Link_4G, Link_2G)
  - Atraso de propagação espacial (dist * 0.00005 s)
  - Ruído de jitter (±25% sobre baseDelay > 1.5 ms)
  - Limite de fila de transmissão (buffer overflow > 5 pacotes por porta)
  - Perda de pacote por PER nativo do canal (Profiles.ned) + BER espacial/payload
  - Protocolo ZMQ REQ/REP idêntico ao MosaikBridge.cc (incluindo mosaik_step)
"""

import json
import math
import os
import random
import re
import sys
import zmq


def _sample_truncnormal(rng, mean, std):
    for _ in range(50):
        val = rng.gauss(mean, std)
        if val >= 0.0001:
            return val
    return max(0.0001, mean)


def sample_channel_profile(rng, link_type):
    """Retorna (base_delay_s, per) de acordo com omnet-dir/Profiles.ned."""
    if link_type == 'Link_Wired':
        return 0.001, 0.0
    elif link_type == 'Link_5G':
        return _sample_truncnormal(rng, 0.005, 0.001), 0.00001
    elif link_type == 'Link_Wireless':
        return _sample_truncnormal(rng, 0.002, 0.0005), 0.001
    elif link_type == 'Link_4G':
        return _sample_truncnormal(rng, 0.035, 0.008), 0.005
    elif link_type == 'Link_2G':
        return rng.expovariate(1.0 / 0.200), 0.15
    return 0.001, 0.0


def parse_dynamic_network_ned(ned_path):
    """Extrai nós (xPos, yPos) e conexões de DynamicNetwork.ned."""
    nodes = {}
    links = []
    if not os.path.exists(ned_path):
        return nodes, links

    with open(ned_path, 'r', encoding='utf-8') as f:
        content = f.read()

    node_pattern = re.compile(
        r'(\w+)\s*:\s*AgentNode\s*\{([^}]*)\}', re.MULTILINE | re.DOTALL
    )
    for match in node_pattern.finditer(content):
        nid = match.group(1)
        body = match.group(2)
        xm = re.search(r'xPos\s*=\s*([0-9.+-]+)', body)
        ym = re.search(r'yPos\s*=\s*([0-9.+-]+)', body)
        nodes[nid] = {
            'x': float(xm.group(1)) if xm else 500.0,
            'y': float(ym.group(1)) if ym else 500.0,
        }

    conn_pattern = re.compile(
        r'(\w+)\.port\+\+\s*<-->\s*(\w+)\s*<-->\s*(\w+)\.port\+\+\s*;'
    )
    for match in conn_pattern.finditer(content):
        links.append({
            'origem': match.group(1),
            'destino': match.group(3),
            'tipo': match.group(2),
        })

    return nodes, links


class AgentNodeSim:
    def __init__(self, eid, x=500.0, y=500.0):
        self.eid = eid
        self.x = x
        self.y = y
        self.gates = []  # list of (neighbor_eid, link_type)
        self.status = "idle"
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_dropped = 0
        self.last_delay_from = {}
        self.val_out_buffer = ""
        self.packet_sizes_buffer = ""
        self.latencies_buffer = ""
        self.jitters_buffer = ""

    def clear_step_buffers(self):
        self.val_out_buffer = ""
        self.packet_sizes_buffer = ""
        self.latencies_buffer = ""
        self.jitters_buffer = ""
        if self.status != "error_dropped":
            self.status = "idle"


class OmnetDiscreteSimulator:
    def __init__(self, omnet_dir, seed=None):
        self.omnet_dir = omnet_dir
        self.rng = random.Random(int(seed) if seed is not None and str(seed) != '' else 42)
        self.nodes = {}
        self.loaded_ned = False

    def _ensure_topology_loaded(self):
        ned_path = os.path.join(self.omnet_dir, 'DynamicNetwork.ned')
        ned_nodes, ned_links = parse_dynamic_network_ned(ned_path)
        for nid, coords in ned_nodes.items():
            if nid not in self.nodes:
                self.nodes[nid] = AgentNodeSim(nid, coords['x'], coords['y'])
            else:
                self.nodes[nid].x = coords['x']
                self.nodes[nid].y = coords['y']

        if ned_links and not self.loaded_ned:
            for node in self.nodes.values():
                node.gates.clear()
            for lk in ned_links:
                u, v, t = lk['origem'], lk['destino'], lk['tipo']
                if u in self.nodes and v in self.nodes:
                    self.nodes[u].gates.append((v, t))
                    self.nodes[v].gates.append((u, t))
            self.loaded_ned = True

    def handle_request(self, req):
        action = req.get('action', '')
        if action == 'create':
            self._ensure_topology_loaded()
            eid = req.get('eid', 'unknown')
            if eid not in self.nodes:
                self.nodes[eid] = AgentNodeSim(eid)
            return {'status': 'ok', 'eid': eid}

        elif action == 'connect':
            self._ensure_topology_loaded()
            src = req.get('src')
            dest = req.get('dest')
            if src in self.nodes and dest in self.nodes:
                self.nodes[src].gates.append((dest, 'Link_Wired'))
                self.nodes[dest].gates.append((src, 'Link_Wired'))
                return {'status': 'ok', 'msg': f'Connected {src} to {dest}'}
            return {'status': 'error', 'reason': 'Nodes not found'}

        elif action == 'step':
            self._ensure_topology_loaded()
            mosaik_step = int(req.get('time', 0))
            inputs = req.get('inputs', {})

            for node in self.nodes.values():
                node.clear_step_buffers()

            # 1. Processa envios (processMosaikInput de AgentNode.cc)
            in_flight_packets = []
            for eid, attrs in inputs.items():
                if eid not in self.nodes or 'val_in' not in attrs:
                    continue
                sender_node = self.nodes[eid]
                val_in_dict = attrs['val_in']
                consolidated = ""
                if isinstance(val_in_dict, dict):
                    for v in val_in_dict.values():
                        if isinstance(v, str) and v:
                            consolidated = (consolidated + "|||" + v) if consolidated else v
                elif isinstance(val_in_dict, str):
                    consolidated = val_in_dict

                if not consolidated:
                    continue

                raw_msgs = [m for m in consolidated.split("|||") if m]
                for gate_idx, (neighbor_eid, link_type) in enumerate(sender_node.gates):
                    dest_node = self.nodes.get(neighbor_eid)
                    if dest_node is None:
                        continue
                    dist = math.hypot(sender_node.x - dest_node.x, sender_node.y - dest_node.y)
                    prop_delay = dist * 0.00005

                    for msg_idx, single_msg in enumerate(raw_msgs):
                        # Buffer overflow: limite de 5 pacotes por porta
                        if msg_idx >= 5:
                            sender_node.packets_dropped += 1
                            sender_node.status = "overflow_drop"
                            continue

                        base_delay, channel_per = sample_channel_profile(self.rng, link_type)
                        jitter_noise = 0.0
                        if base_delay > 0.0015:
                            jitter_noise = self.rng.uniform(-0.25 * base_delay, 0.25 * base_delay)
                        total_delay = max(0.0001, base_delay + prop_delay + jitter_noise)

                        # Serialization delay (byteLength * 8 / datarate)
                        datarates = {
                            'Link_Wired': 1e9,
                            'Link_5G': 500e6,
                            'Link_Wireless': 300e6,
                            'Link_4G': 50e6,
                            'Link_2G': 250e3,
                        }
                        tx_delay = (len(single_msg.encode('utf-8')) * 8.0) / datarates.get(link_type, 1e9)
                        arrival_delay = total_delay + tx_delay

                        has_bit_error = (self.rng.random() < channel_per)
                        in_flight_packets.append({
                            'src': sender_node,
                            'dst': dest_node,
                            'payload': single_msg,
                            'byte_len': float(len(single_msg.encode('utf-8'))),
                            'delay': arrival_delay,
                            'has_bit_error': has_bit_error,
                            'link_type': link_type,
                        })
                        sender_node.packets_sent += 1
                        sender_node.status = "transmitting"

            # Ordena chegadas pelo menor atraso (ordem cronológica de eventos discretos)
            in_flight_packets.sort(key=lambda pkt: pkt['delay'])

            # 2. Processa recepções (handleMessage de AgentNode.cc)
            for pkt in in_flight_packets:
                src_node = pkt['src']
                dst_node = pkt['dst']

                # Checagem 1: PER nativo do canal (pkt->hasBitError())
                if pkt['has_bit_error']:
                    dst_node.packets_dropped += 1
                    dst_node.status = "error_dropped"
                    continue

                # Checagem 2: BER espacial e escalonado por payload (AgentNode.cc)
                dist = math.hypot(dst_node.x - src_node.x, dst_node.y - src_node.y)
                base_drop = 0.0
                if dist > 400.0 and pkt['link_type'] != 'Link_Wired':
                    base_drop = 0.12
                elif dist > 150.0 and pkt['link_type'] in ('Link_4G', 'Link_2G'):
                    base_drop = 0.03

                size_factor = max(1.0, pkt['byte_len'] / 15000.0)
                final_drop = min(0.99, base_drop * size_factor)

                if self.rng.random() < final_drop:
                    dst_node.packets_dropped += 1
                    dst_node.status = "error_dropped"
                    continue

                # Sucesso na recepção
                dst_node.packets_received += 1
                dst_node.status = "receiving"
                delay = pkt['delay']
                prev_delay = dst_node.last_delay_from.get(src_node.eid)
                jitter = abs(delay - prev_delay) if prev_delay is not None else 0.0
                dst_node.last_delay_from[src_node.eid] = delay

                dst_node.val_out_buffer = (
                    (dst_node.val_out_buffer + "|||" + pkt['payload'])
                    if dst_node.val_out_buffer else pkt['payload']
                )
                sz_s = f"{pkt['byte_len']:.6f}"
                lat_s = f"{delay:.6f}"
                jit_s = f"{jitter:.6f}"
                dst_node.packet_sizes_buffer = (
                    (dst_node.packet_sizes_buffer + "|||" + sz_s)
                    if dst_node.packet_sizes_buffer else sz_s
                )
                dst_node.latencies_buffer = (
                    (dst_node.latencies_buffer + "|||" + lat_s)
                    if dst_node.latencies_buffer else lat_s
                )
                dst_node.jitters_buffer = (
                    (dst_node.jitters_buffer + "|||" + jit_s)
                    if dst_node.jitters_buffer else jit_s
                )

            data_out = {}
            for eid, node in self.nodes.items():
                data_out[eid] = {
                    'status': node.status,
                    'packets_sent': node.packets_sent,
                    'packets_received': node.packets_received,
                    'packets_dropped': node.packets_dropped,
                    'val_out': node.val_out_buffer,
                    'packet_sizes_out': node.packet_sizes_buffer,
                    'latencies_out': node.latencies_buffer,
                    'jitters_out': node.jitters_buffer,
                }

            return {
                'status': 'ok',
                'mosaik_step': mosaik_step,
                'data': data_out,
            }

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
            resp = sim.handle_request(req)
            sock.send_json(resp)
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
