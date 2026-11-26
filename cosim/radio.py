"""
cosim.radio: Modelo de propagação da rede LPWA da tese (Melo, 2022, seção 6.1.5).

Usado pelos canais `Link_6TiSCH_TSCH` e `Link_WiSUN_FAN` (Profiles.ned) e pela
topologia em malha da IEEE 13 barras. É o modelo do servidor 6TiSCH do
co-simulation-opentes (`comm-opentes/Tisch.cc`):

  - RSSI pelo modelo de Friis em 915 MHz, menos uma uniforme de 0 a 40 dB
    (Pister-Hack), sorteada UMA vez por enlace: variação de longo prazo do
    ambiente, não desvanecimento por pacote;
  - PER pela curva de Prando et al. (2019), em passos de 1 dB acima da
    sensibilidade de -106,37 dBm;
  - enlace viável quando o PER fica abaixo de 0,5;
  - no Wi-SUN, a sensibilidade piora 10 log10(R / 50 kbps), o que encurta o alcance.

Também lê e grava o levantamento de enlaces no formato `tisch_links.csv`
(i,j,name_i,name_j,distance_m,rssi_dbm,per,adjacent), o que permite repetir
exatamente a topologia de rádio de uma execução do servidor da tese.
"""

import csv
import math
import random
from dataclasses import dataclass

__all__ = ['PER_TABELA', 'Radio', 'gravar_enlaces', 'ler_enlaces', 'levantar_enlaces',
           'per_do_rssi', 'rssi_espaco_livre']

# PER de um quadro de 127 B em função do RSSI acima da sensibilidade, em dB.
PER_TABELA = (1.0, 0.8, 0.4, 0.15, 0.03, 0.006, 0.0015, 0.0)
LUZ = 299792458.0


@dataclass(frozen=True)
class Radio:
    frequencia_hz: float = 915e6
    potencia_dbm: float = 0.0
    ganho_tx_db: float = 0.0
    ganho_rx_db: float = 0.0
    pister_hack_db: float = 40.0
    sensibilidade_dbm: float = -106.37
    limiar_per: float = 0.5
    taxa_bps: float = 50000.0   # a sensibilidade sobe com a taxa (Wi-SUN)

    @property
    def sensibilidade(self):
        return self.sensibilidade_dbm + 10.0 * math.log10(self.taxa_bps / 50000.0)


def rssi_espaco_livre(d, radio):
    """Potência recebida pelo modelo de Friis, em dBm."""
    fspl = 20.0 * math.log10(LUZ / (4.0 * math.pi * d * radio.frequencia_hz))
    return radio.potencia_dbm + radio.ganho_tx_db + radio.ganho_rx_db + fspl


def per_do_rssi(rssi, sensibilidade):
    passo = math.floor(rssi - sensibilidade)
    if passo < 0:
        return 1.0
    if passo >= len(PER_TABELA):
        return 0.0
    return PER_TABELA[passo]


def levantar_enlaces(nos, radio=Radio(), rng=None, impostos=None):
    """Levantamento de todos os pares de nós, como o `buildLinks` da tese.

    nos      : lista de dicts com 'id', 'x', 'y' (e 'nome', opcional).
    impostos : pares (id, id) que existem por decisão da topologia (por exemplo,
               a estrela). O sorteio deles é condicionado a PER abaixo do limiar,
               que é a distribuição implicada por o enlace existir; sem isso um
               enlace imposto poderia receber PER 1,0 e virar rota morta.
    Devolve uma lista de dicts no formato do `tisch_links.csv`.
    """
    rng = rng or random.Random(0)
    impostos = {frozenset(p) for p in (impostos or ())}
    linhas = []
    for i, a in enumerate(nos):
        for j in range(i + 1, len(nos)):
            b = nos[j]
            d = math.hypot(a['x'] - b['x'], a['y'] - b['y'])
            imposto = frozenset((a['id'], b['id'])) in impostos
            if d < 1e-9:
                # Mesma coordenada (a subestação): enlace perfeito.
                rssi, per = 0.0, 0.0
            else:
                pr = rssi_espaco_livre(d, radio)
                for _ in range(200):
                    rssi = pr - rng.uniform(0.0, radio.pister_hack_db)
                    per = per_do_rssi(rssi, radio.sensibilidade)
                    if not imposto or per < radio.limiar_per:
                        break
                else:
                    # Distância grande demais para o modelo admitir o enlace: fica
                    # com o melhor PER possível, como na tese.
                    per = PER_TABELA[-2]
            linhas.append({
                'i': i, 'j': j, 'name_i': a.get('nome', a['id']), 'name_j': b.get('nome', b['id']),
                'id_i': a['id'], 'id_j': b['id'], 'distance_m': d, 'rssi_dbm': rssi, 'per': per,
                'adjacent': int(imposto or per < radio.limiar_per),
            })
    return linhas


def ler_enlaces(caminho, nos):
    """Lê um `tisch_links.csv`, associando name_i/name_j aos ids dos nós."""
    por_nome = {str(n.get('nome', n['id'])).lower(): n['id'] for n in nos}
    linhas = []
    with open(caminho, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ni, nj = r['name_i'].lower(), r['name_j'].lower()
            if ni not in por_nome or nj not in por_nome:
                continue
            linhas.append({
                'i': int(r['i']), 'j': int(r['j']), 'name_i': r['name_i'], 'name_j': r['name_j'],
                'id_i': por_nome[ni], 'id_j': por_nome[nj],
                'distance_m': float(r['distance_m']), 'rssi_dbm': float(r['rssi_dbm']),
                'per': float(r['per']), 'adjacent': int(r['adjacent']),
            })
    return linhas


def gravar_enlaces(linhas, caminho):
    campos = ['i', 'j', 'name_i', 'name_j', 'distance_m', 'rssi_dbm', 'per', 'adjacent']
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        w.writeheader()
        for r in linhas:
            w.writerow({**r, 'distance_m': f"{r['distance_m']:g}", 'rssi_dbm': f"{r['rssi_dbm']:g}",
                        'per': f"{r['per']:g}"})
