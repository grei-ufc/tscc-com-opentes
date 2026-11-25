#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results_arvore.py — Dashboards da topologia em Árvore.

A implementação é compartilhada com a topologia híbrida em plot_camadas.py.
Arquivos gerados:
  - grafico_trafego_Arvore.svg        (visão por camada: Raiz / Subestação / Concentrador / Medidor)
  - grafico_trafego_Geral.svg        (visão global por tecnologia de enlace)
  - grafico_trafego_{Tecnologia}.svg (visão individual por tecnologia de enlace)
"""

from plot_camadas import ARVORE, gerar_graficos as _gerar_graficos


def gerar_graficos():
    _gerar_graficos(ARVORE)


if __name__ == '__main__':
    gerar_graficos()
