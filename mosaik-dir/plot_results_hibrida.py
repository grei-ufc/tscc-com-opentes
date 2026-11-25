#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_hibrida.py — Dashboards da topologia Híbrida.

A implementação é compartilhada com a topologia árvore em plot_camadas.py.
Arquivos gerados:
  - grafico_trafego_Hibrida.svg        (visão por camada: CCO / Subestação / Concentrador / Medidor)
  - grafico_trafego_Geral.svg        (visão global por tecnologia de enlace)
  - grafico_trafego_{Tecnologia}.svg (visão individual por tecnologia de enlace)
"""

from plot_camadas import HIBRIDA, gerar_graficos as _gerar_graficos


def gerar_graficos():
    _gerar_graficos(HIBRIDA)


if __name__ == '__main__':
    gerar_graficos()
