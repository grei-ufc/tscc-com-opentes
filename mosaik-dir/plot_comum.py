#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_comum.py — Utilitários compartilhados pelos scripts plot_results_*.py.
"""

import os

from matplotlib.transforms import Bbox

# Nome do canal no NED (Profiles.ned) -> rótulo exibido nos gráficos
NED_PARA_LABEL = {
    'Link_Wired':    'Cabeada',
    'Link_5G':       '5G',
    'Link_Wireless': 'Wireless',
    'Link_4G':       '4G',
    'Link_2G':       '2G',
    'Fibra':         'Fibra',
    'Celular5G':     '5G',
    'Celular4G':     '4G',
    'Celular3G':     '3G',
    'Celular2G':     '2G',
    'RFMesh':        'RF Mesh',
    'PLC':           'PLC',
}

# Tecnologias de estrela/malha/anel, na ordem padrão de TIPOS_REDE.
# Usada quando config.json não informa as tecnologias da rodada.
ROTULOS_PADRAO = ['Cabeada', '5G', 'Wireless', '4G', '2G']


def caminho_omnet(nome):
    """Localiza um artefato da rodada (posicoes.json, links.json, config.json):
    OMNET_DIR, /omnet-dir (container), ../omnet-dir (host) ou a pasta atual."""
    candidatos = []
    omnet_env = os.environ.get('OMNET_DIR')
    if omnet_env:
        candidatos.append(os.path.join(omnet_env, nome))
    candidatos.extend([
        f'/omnet-dir/{nome}',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'omnet-dir', nome),
        nome,
    ])
    for c in candidatos:
        if os.path.exists(c):
            return c
    return nome


def exportar_paineis_separados(fig, paineis, rotulo_topologia, sufixo_arquivo,
                               prefixo='grafico_trafego_Geral', pad_px=12):
    """Salva cada painel do dashboard como um SVG próprio (título, legenda e colorbar
    inclusos), para uso em artigos. O título ganha uma linha com o nome da topologia,
    para o gráfico fazer sentido isolado.

    paineis         lista de (sufixo, [axes que compõem o painel])
    rotulo_topologia  ex.: 'Topologia em Anel' (vai no título)
    sufixo_arquivo    ex.: 'Anel' -> grafico_trafego_Geral_<painel>_Anel.svg
    """
    inv = fig.dpi_scale_trans.inverted()
    for sufixo, axs in paineis:
        ax0 = axs[0]
        titulo_orig = ax0.get_title()
        ax0.set_title(f'{rotulo_topologia}\n{titulo_orig}', fontweight='bold',
                      fontsize=ax0.title.get_fontsize())
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bb = Bbox.union([a.get_tightbbox(renderer) for a in axs])
        bb = Bbox.from_extents(bb.x0 - pad_px, bb.y0 - pad_px, bb.x1 + pad_px, bb.y1 + pad_px)
        nome = f'{prefixo}_{sufixo}_{sufixo_arquivo}.svg'
        fig.savefig(nome, format='svg', bbox_inches=bb.transformed(inv))
        ax0.set_title(titulo_orig, fontweight='bold', fontsize=ax0.title.get_fontsize())
        print(f'Salvo: {nome}')
