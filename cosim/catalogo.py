"""
cosim.catalogo — Topologias e tecnologias de enlace da co-simulação.

Os parâmetros físicos de cada canal (banda, atraso, PER) NÃO ficam aqui: a
fonte é omnet-dir/Profiles.ned, lida por cosim.canais. Aqui ficam o rótulo e a
cor de cada canal e os metadados de cada topologia.
"""

from dataclasses import dataclass

__all__ = [
    'CELULAR', 'COR_POR_ROTULO', 'NED_PARA_ROTULO', 'TECNOLOGIAS', 'TIPOS_REDE_PADRAO',
    'TOPOLOGIAS', 'Tecnologia', 'Topologia', 'canal_celular', 'rotulo',
]


@dataclass(frozen=True)
class Tecnologia:
    ned: str      # nome do canal em Profiles.ned
    rotulo: str   # nome exibido nos menus e gráficos
    cor: str      # cor nos dashboards e no preview (mesma tecnologia = mesma cor)


_TECNOLOGIAS = [
    # Estrela, malha e anel (escolhidas pelo usuário em TIPOS_REDE)
    Tecnologia('Link_Wired',    'Cabeada',  '#1f77b4'),
    Tecnologia('Link_5G',       '5G',       '#2ca02c'),
    Tecnologia('Link_Wireless', 'Wireless', '#17becf'),
    Tecnologia('Link_4G',       '4G',       '#ff7f0e'),
    Tecnologia('Link_2G',       '2G',       '#9467bd'),
    # Árvore e híbrida (definidas pela própria topologia)
    Tecnologia('Fibra',         'Fibra',    '#08306b'),
    Tecnologia('Celular5G',     '5G',       '#2ca02c'),
    Tecnologia('Celular4G',     '4G',       '#ff7f0e'),
    Tecnologia('Celular3G',     '3G',       '#bcbd22'),
    Tecnologia('Celular2G',     '2G',       '#9467bd'),
    Tecnologia('RFMesh',        'RF Mesh',  '#d62728'),
    Tecnologia('PLC',           'PLC',      '#8c564b'),
    # LPWA / Smart Grid (IEEE 13 barras — OpenTES)
    Tecnologia('Link_6TiSCH',   '6TiSCH',   '#e377c2'),
    Tecnologia('Link_WiSUN',    'Wi-SUN',   '#7f7f7f'),
]
TECNOLOGIAS = {t.ned: t for t in _TECNOLOGIAS}

# Tecnologias de estrela/malha/anel, na ordem padrão de TIPOS_REDE
TIPOS_REDE_PADRAO = ['Link_Wired', 'Link_5G', 'Link_Wireless', 'Link_4G', 'Link_2G']

NED_PARA_ROTULO = {t.ned: t.rotulo for t in _TECNOLOGIAS}
COR_POR_ROTULO = {t.rotulo: t.cor for t in _TECNOLOGIAS}

# Código da geração celular (CELULAR_ARVORE / CELULAR_HIBRIDA) -> canal NED
CELULAR = {'2g': 'Celular2G', '3g': 'Celular3G', '4g': 'Celular4G', '5g': 'Celular5G'}


def canal_celular(codigo):
    """'4g' -> 'Celular4G'. Código desconhecido cai em Celular4G."""
    return CELULAR.get(str(codigo).lower(), 'Celular4G')


def rotulo(ned):
    return NED_PARA_ROTULO.get(ned, ned)


@dataclass(frozen=True)
class Topologia:
    id: str            # valor de TOPOLOGY
    rotulo: str
    descricao: str
    script_pade: str   # em pade-dir/pade_agents/
    script_plot: str   # em mosaik-dir/
    min_agentes: int = 1


_TOPOLOGIAS = [
    Topologia('estrela', 'Estrela',
              '1 agente central conectado a N periféricos (hub-and-spoke).',
              'pade_star.py', 'plot_results_star.py', 1),
    Topologia('malha', 'Malha',
              'N agentes, todos conectados entre si (full mesh).',
              'pade_malha.py', 'plot_results_malha.py', 2),
    Topologia('anel', 'Anel',
              'N agentes em ciclo fechado; cada um fala com os dois vizinhos (bidirecional).',
              'pade_anel.py', 'plot_results_anel.py', 3),
    Topologia('arvore', 'Árvore',
              'Árvore radial IEC 61850: raiz → subestações → concentradores → medidores.',
              'pade_arvore.py', 'plot_results_arvore.py'),
    Topologia('hibrida', 'Híbrida',
              'Backbone fibra (anel) + estrela celular + malha RF mesh por cluster.',
              'pade_hibrida.py', 'plot_results_hibrida.py'),
]
TOPOLOGIAS = {t.id: t for t in _TOPOLOGIAS}
