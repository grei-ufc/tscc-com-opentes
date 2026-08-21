#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu.py — Configurador interativo da co-simulação PADE + OMNeT++ + Mosaik.

Pergunta ao usuário a topologia, o número de agentes e os tipos de enlace,
exibe um resumo e dispara o docker-compose com as variáveis de ambiente certas.
"""

import subprocess
import os
import sys

# ══════════════════════════════════════════════════════════════
# MAPEAMENTOS DE OPÇÕES
# ══════════════════════════════════════════════════════════════

# Chave → (valor interno,  descrição exibida)
TOPOLOGIAS = {
    '1': ('estrela', 'Estrela — 1 central + N periféricos (cada um conectado só ao central)'),
    '2': ('malha',   'Malha   — todos os agentes conectados entre si (full mesh)'),
}

# Chave → (nome NED,      nome legível,  descrição técnica)
REDES = {
    '1': ('Link_Wired', 'Cabeada', '1 Gbps  | delay fixo 1ms    |  0%    de perda'),
    '2': ('Link_5G',    '5G',      '500Mbps | delay ~5ms (σ=1ms) |  0.001% de perda'),
    '3': ('Link_4G',    '4G',      '50 Mbps | delay ~35ms(σ=8ms) |  0.5%  de perda'),
    '4': ('Link_IoT',   'IoT',     '250kbps | delay exp(200ms)   | 15%    de perda'),
}


# ══════════════════════════════════════════════════════════════
# FUNÇÕES DE INTERFACE
# ══════════════════════════════════════════════════════════════

def cabecalho():
    """Exibe o banner inicial do menu."""
    print()
    print("╔" + "═"*54 + "╗")
    print("║   CO-SIMULAÇÃO  ·  PADE + OMNeT++ + Mosaik + Docker   ║")
    print("║   GREI-UFC  ·  Configurador de Cenário Interativo      ║")
    print("╚" + "═"*54 + "╝")
    print()


def pedir_topologia():
    """
    Apresenta as opções de topologia e retorna o valor interno escolhido
    (ex.: 'estrela' ou 'malha').
    """
    print("┌─ 1. TOPOLOGIA DE REDE ──────────────────────────────────┐")
    for chave, (_, descricao) in TOPOLOGIAS.items():
        print(f"│  [{chave}] {descricao:<51}│")
    print("└─────────────────────────────────────────────────────────┘")

    while True:
        escolha = input("   Opção [1/2]: ").strip()
        if escolha in TOPOLOGIAS:
            nome, _ = TOPOLOGIAS[escolha]
            print(f"Topologia selecionada: {nome.upper()}\n")
            return nome
        print("   ⚠  Opção inválida. Digite 1 ou 2.")


def pedir_num_agentes():
    """
    Pede o número de agentes periféricos e retorna um inteiro validado.
    Aceita entre 1 e 50 periféricos.
    """
    print("┌─ 2. NÚMERO DE AGENTES PERIFÉRICOS ──────────────────────┐")
    print("│  Mínimo: 1   |   Máximo recomendado: 20 (suporta até 50)│")
    print("└─────────────────────────────────────────────────────────┘")

    while True:
        try:
            num = int(input("Quantidade de periféricos: ").strip())
            if 1 <= num <= 50:
                print(f"{num} periférico(s) configurado(s).\n")
                return num
            print("Digite um valor entre 1 e 50.")
        except ValueError:
            print("Valor inválido. Digite um número entre 1 e 50.")


def pedir_tipos_rede():
    """
    Apresenta as opções de tecnologia de enlace.
    O usuário digita os números separados por vírgula ou pressiona ENTER
    para selecionar todas as quatro opções.

    Retorna:
        tipos  — lista de nomes NED  (ex.: ['Link_5G', 'Link_4G'])
        nomes  — lista de nomes legíveis (ex.: ['5G', '4G'])
        chaves — lista das chaves escolhidas, para o resumo
    """
    print("┌─ 3. TIPOS DE ENLACE ────────────────────────────────────┐")
    for chave, (_, nome, desc) in REDES.items():
        print(f"│  [{chave}] {nome:<8}  {desc:<41}│")
    print("│                                                         │")
    print("│  Digite os números separados por vírgula (ex: 1,3).    │")
    print("│  Pressione ENTER para usar os quatro tipos.             │")
    print("└─────────────────────────────────────────────────────────┘")

    while True:
        entrada = input("Redes [1-4]: ").strip()

        if entrada == '':
            # ENTER → seleciona todas
            chaves = list(REDES.keys())
        else:
            chaves = [c.strip() for c in entrada.split(',')]
            if not all(c in REDES for c in chaves) or len(chaves) == 0:
                print("Opção inválida. Use números de 1 a 4 separados por vírgula.")
                continue

        tipos = [REDES[c][0] for c in chaves]
        nomes = [REDES[c][1] for c in chaves]
        print(f" Redes selecionadas: {', '.join(nomes)}\n")
        return tipos, nomes


def exibir_resumo(topologia, num, nomes_rede):
    """Imprime um painel de resumo antes de confirmar."""
    redes_str = ', '.join(nomes_rede)
    print("┌─ RESUMO DA CONFIGURAÇÃO ────────────────────────────────┐")
    print(f"│  Topologia  : {topologia.upper():<42}│")
    print(f"│  Periféricos: {num:<42}│")
    print(f"│  Redes      : {redes_str:<42}│")
    print("└─────────────────────────────────────────────────────────┘")


def confirmar():
    """Aguarda confirmação do usuário. Retorna True para 's', False para 'n'."""
    while True:
        resp = input("\n   Confirmar e iniciar a simulação? [s/n]: ").strip().lower()
        if resp == 's':
            return True
        if resp == 'n':
            return False
        print("   ⚠  Digite 's' para confirmar ou 'n' para cancelar.")


# ══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main():
    cabecalho()

    topologia       = pedir_topologia()
    num_perifericos = pedir_num_agentes()
    tipos_rede, nomes_rede = pedir_tipos_rede()

    exibir_resumo(topologia, num_perifericos, nomes_rede)

    if not confirmar():
        print("\n   Simulação cancelada.\n")
        sys.exit(0)

    # ── Prepara as variáveis de ambiente ──────────────────────
    # os.environ.copy() garante que PATH, HOME etc. continuem disponíveis
    # para o docker-compose. Adicionamos (ou sobrescrevemos) apenas as
    # três variáveis que definem o cenário.
    env = os.environ.copy()
    env['TOPOLOGY']        = topologia
    env['NUM_PERIFERICOS'] = str(num_perifericos)
    env['TIPOS_REDE']      = ','.join(tipos_rede)

    # ── Descobre o diretório raiz do projeto ─────────────────
    # __file__ = .../tscc-com-opentes-main/menu.py
    # Queremos o diretório que contém o docker-compose.yml.
    raiz = os.path.dirname(os.path.abspath(__file__))

    print(f"\n Iniciando co-simulação "
          f"({topologia} | {num_perifericos} agentes)...\n")

    # ── Dispara o docker-compose ──────────────────────────────
    resultado = subprocess.run(
        ['docker', 'compose', 'up', '--build'],
        env=env,
        cwd=raiz,          # garante que o compose encontre o arquivo correto
    )

    # ── Verifica se houve erro ────────────────────────────────
    if resultado.returncode != 0:
        print("\n docker-compose encerrou com erro.")
        sys.exit(resultado.returncode)

    print("\nCo-simulação concluída.")


if __name__ == '__main__':
    main()