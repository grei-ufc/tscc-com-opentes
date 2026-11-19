"""
cosim.canais — Perfis de canal lidos de omnet-dir/Profiles.ned.

O Profiles.ned é a fonte única dos parâmetros físicos (banda, atraso, PER):
o OMNeT++ simula com ele, o emulador dos testes o lê e os menus descrevem as
tecnologias a partir dele. Assim, o que a interface mostra é o que é simulado.
"""

import os
import re

__all__ = ['Perfil', 'descrever', 'ler_perfis', 'localizar_profiles']

_TEMPO = {'s': 1.0, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9}
_TAXA = {'bps': 1.0, 'kbps': 1e3, 'Mbps': 1e6, 'Gbps': 1e9}


class Perfil:
    """Parâmetros de um canal `ned.DatarateChannel`."""

    def __init__(self, nome, delay, datarate, per):
        self.nome = nome
        self.delay = delay          # expressão NED, ex.: 'truncnormal(5ms, 1ms)'
        self.datarate = datarate    # texto NED, ex.: '500Mbps'
        self.per = per              # probabilidade de erro de pacote (0..1)

    @property
    def bps(self):
        return taxa_bps(self.datarate)

    def __repr__(self):
        return f'Perfil({self.nome!r}, delay={self.delay!r}, datarate={self.datarate!r}, per={self.per})'


def tempo_s(txt):
    """'5ms' -> 0.005."""
    m = re.fullmatch(r'\s*([0-9.]+)\s*(s|ms|us|ns)?\s*', txt)
    if not m:
        raise ValueError(f'Tempo NED não reconhecido: {txt!r}')
    return float(m.group(1)) * _TEMPO[m.group(2) or 's']


def taxa_bps(txt):
    """'250kbps' -> 250000.0."""
    m = re.fullmatch(r'\s*([0-9.]+)\s*(bps|kbps|Mbps|Gbps)\s*', txt)
    if not m:
        raise ValueError(f'Datarate NED não reconhecido: {txt!r}')
    return float(m.group(1)) * _TAXA[m.group(2)]


def localizar_profiles():
    """Caminho do Profiles.ned: $OMNET_DIR, /omnet-dir (container) ou ../omnet-dir."""
    candidatos = []
    if os.environ.get('OMNET_DIR'):
        candidatos.append(os.path.join(os.environ['OMNET_DIR'], 'Profiles.ned'))
    candidatos += [
        '/omnet-dir/Profiles.ned',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'omnet-dir', 'Profiles.ned'),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f'Profiles.ned não encontrado em: {candidatos}')


def ler_perfis(caminho=None):
    """{nome_do_canal: Perfil} para cada `channel X extends ned.DatarateChannel`."""
    with open(caminho or localizar_profiles(), 'r', encoding='utf-8') as f:
        conteudo = re.sub(r'//[^\n]*', '', f.read())
    perfis = {}
    for m in re.finditer(r'channel\s+(\w+)\s+extends\s+ned\.DatarateChannel\s*\{(.*?)\}',
                         conteudo, re.DOTALL):
        corpo = m.group(2)
        delay = re.search(r'\bdelay\s*=\s*([^;]+);', corpo)
        taxa = re.search(r'\bdatarate\s*=\s*([^;]+);', corpo)
        per = re.search(r'\bper\s*=\s*([^;]+);', corpo)
        perfis[m.group(1)] = Perfil(
            m.group(1),
            delay.group(1).strip() if delay else '0s',
            taxa.group(1).strip() if taxa else '1Gbps',
            float(per.group(1)) if per else 0.0,
        )
    return perfis


def _num(txt):
    return txt.strip().replace('.', ',')


def _tempo_legivel(txt):
    m = re.fullmatch(r'\s*([0-9.]+)\s*(s|ms|us|ns)?\s*', txt)
    return f'{_num(m.group(1))} {m.group(2) or "s"}' if m else txt.strip()


def _delay_legivel(expr):
    m = re.fullmatch(r'\s*truncnormal\(([^,]+),([^)]+)\)\s*', expr)
    if m:
        return f'~{_tempo_legivel(m.group(1))} (σ {_tempo_legivel(m.group(2))})'
    m = re.fullmatch(r'\s*exponential\(([^)]+)\)\s*', expr)
    if m:
        return f'exp({_tempo_legivel(m.group(1))})'
    return _tempo_legivel(expr)


def _taxa_legivel(txt):
    m = re.fullmatch(r'\s*([0-9.]+)\s*(bps|kbps|Mbps|Gbps)\s*', txt)
    return f'{_num(m.group(1))} {m.group(2)}' if m else txt.strip()


def descrever(perfil):
    """Descrição curta para os menus, ex.: '500 Mbps · delay ~5 ms (σ 1 ms) · 0,001% perda'."""
    perda = _num(f'{perfil.per * 100:g}')
    return f'{_taxa_legivel(perfil.datarate)} · delay {_delay_legivel(perfil.delay)} · {perda}% perda'


def taxa_legivel(perfil):
    """'1 Gbps', '150 kbps'."""
    return _taxa_legivel(perfil.datarate)
