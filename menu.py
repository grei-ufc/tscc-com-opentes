#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu.py — Configurador CLI da co-simulação PADE + OMNeT++ + Mosaik.

Alternativa terminal ao menu_streamlit.py: mesma lógica, mesmas variáveis
de ambiente (TOPOLOGY, NUM_PERIFERICOS, TIPOS_REDE), sem dependência de
navegador ou Streamlit.

Como rodar:
    python3 menu.py

Semântica de NUM_PERIFERICOS (igual ao menu_streamlit.py):
  - estrela : número de PERIFÉRICOS  → total = N + 1 (+ 1 central)
  - malha   : número TOTAL de agentes peers
  - anel    : número TOTAL de agentes peers
"""

import os
import subprocess
import sys

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE OPÇÕES
# ══════════════════════════════════════════════════════════════

TOPOLOGIAS = {
    "1": {
        "id":   "estrela",
        "nome": "Estrela",
        "desc": "1 agente central + N periféricos (hub-and-spoke).",
        "min":  1,
    },
    "2": {
        "id":   "malha",
        "nome": "Malha",
        "desc": "N agentes, todos conectados entre si (full mesh).",
        "min":  2,
    },
    "3": {
        "id":   "anel",
        "nome": "Anel",
        "desc": "N agentes em ciclo fechado, cada um fala só com vizinhos. COMUNICAÇÃO BIDIRECIONAL.",
        "min":  3,
    },
}

REDES = {
    "1": ("Link_Wired",    "Cabeada",  "1 Gbps   | delay fixo 1 ms      |  0 %    perda"),
    "2": ("Link_5G",       "5G",       "500 Mbps | delay ~5 ms (σ=1ms)  |  0,001% perda"),
    "3": ("Link_Wireless", "Wireless", "300 Mbps | delay ~2 ms (σ=0,5)  |  0,1%   perda"),
    "4": ("Link_4G",       "4G",       "50 Mbps  | delay ~35ms (σ=8ms)  |  0,5%   perda"),
    "5": ("Link_2G",       "2G",       "250 kbps | delay exp(200ms)      | 15 %    perda"),
}

RAIZ = os.path.dirname(os.path.abspath(__file__))


def linha(char="─", n=58):
    return char * n


def cabecalho():
    print()
    print(f"╔{linha('═')}                              ╗")
    print(f"║  Co-Simulação PADE + OMNeT++ + Mosaik    ║")
    print(f"║  GREI-UFC · Configurador de Cenário (CLI)║")
    print(f"╚{linha('═')}                              ╝")
    print()


def titulo(texto):
    print(f"\n┌─ {texto} {linha('─', max(0, 52 - len(texto)))}┐")


def rodape_bloco():
    print(f"└{linha()}┘")


def ok(msg):
    print(f"{msg}")


def aviso(msg):
    print(f"{msg}")


def entrada(prompt):
    try:
        return input(f"{prompt} ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Interrompido pelo usuário.")
        sys.exit(0)


def pedir_topologia():
    titulo("1. TOPOLOGIA DE REDE")
    for k, v in TOPOLOGIAS.items():
        print(f"  [{k}]{v['nome']:<10}{v['desc']}")
    rodape_bloco()

    while True:
        resp = entrada("Escolha [1/2/3]:")
        if resp in TOPOLOGIAS:
            top = TOPOLOGIAS[resp]
            ok(f"{top['nome'].upper()} selecionada.")
            return top
        aviso("Digite 1, 2 ou 3.")


def pedir_num_agentes(topologia):
    min_val = topologia["min"]

    if topologia["id"] == "estrela":
        subtitulo = "2. NÚMERO DE AGENTES PERIFÉRICOS"
        nota      = f"  Mínimo: {min_val}  |  Máximo: 500  (total = N + 1 com o central)"
        rotulo    = "Periféricos"
    else:
        subtitulo = "2. NÚMERO TOTAL DE AGENTES"
        nota      = f"  Mínimo: {min_val}  |  Máximo: 500  (todos são peers — sem central)"
        rotulo    = "Total de agentes"

    titulo(subtitulo)
    print(nota)
    rodape_bloco()

    while True:
        resp = entrada(f"{rotulo} [≥{min_val}]:")
        try:
            n = int(resp)
            if n < min_val:
                aviso(f"Mínimo para {topologia['nome']} é {min_val}.")
            elif n > 500:
                aviso("Máximo suportado é 500.")
            else:
                if topologia["id"] == "estrela":
                    ok(f"{n} periférico(s) → {n+1} agentes no total.")
                else:
                    ok(f"{n} agentes no total.")
                return n
        except ValueError:
            aviso("Digite um número inteiro.")


def pedir_tipos_rede():
    titulo("3. TECNOLOGIAS DE ENLACE")
    for k, (_, nome, desc) in REDES.items():
        print(f"  [{k}]{nome:<10}{desc}")
    print()
    print("  Separe por vírgula para múltiplas. ENTER = todas as cinco.")
    rodape_bloco()

    while True:
        resp = entrada("Tecnologias [1-5]:")
        if resp == "":
            chaves = list(REDES.keys())
        else:
            chaves = [c.strip() for c in resp.split(",")]
            invalidas = [c for c in chaves if c not in REDES]
            if invalidas:
                aviso(f"Opção(ões) inválida(s): {', '.join(invalidas)}. Use 1 a 5.")
                continue
            if not chaves:
                aviso("Selecione ao menos uma tecnologia.")
                continue

        tipos = [REDES[c][0] for c in chaves]
        nomes = [REDES[c][1] for c in chaves]
        ok(f"{', '.join(nomes)}")
        return tipos, nomes


def exibir_resumo(topologia, num, nomes_rede):
    titulo("RESUMO DA CONFIGURAÇÃO")
    if topologia["id"] == "estrela":
        detalhe = f"1 central + {num} periféricos = {num+1} agentes"
    else:
        detalhe = f"{num} agentes peers"

    print(f"  {'Topologia':<15}:{topologia['nome']}")
    print(f"  {'Agentes':<15}:{detalhe}")
    print(f"  {'Redes':<15}:{', '.join(nomes_rede)}")
    rodape_bloco()


def confirmar():
    while True:
        resp = entrada("Iniciar simulação? [s/n]:").lower()
        if resp in ("s", "sim", "y", "yes"):
            return True
        if resp in ("n", "nao", "não", "no"):
            return False
        aviso("Digite 's' para sim ou 'n' para não.")

# EXECUÇÃO DO DOCKER COMPOSE

def rodar(topologia_id, num_agentes, tipos_rede):
    env = os.environ.copy()
    env["TOPOLOGY"]        = topologia_id
    env["NUM_PERIFERICOS"] = str(num_agentes)
    env["TIPOS_REDE"]      = ",".join(tipos_rede)

    print(f"\nIniciando docker compose...\n")

    resultado = subprocess.run(
        [
            "docker", "compose", "up", "--build",
            "--abort-on-container-exit",
            "--exit-code-from", "mosaik_master",
        ],
        cwd=RAIZ,
        env=env,
    )

    print()
    if resultado.returncode == 0:
        print(f"Co-simulação concluída com sucesso.")
        print(f"  Os gráficos foram salvos em mosaik-dir/")
    else:
        print(f"XXX docker compose encerrou com código {resultado.returncode}.")

    return resultado.returncode


def parar():
    print(f"\nDerrubando containers...")
    subprocess.run(["docker", "compose", "down"], cwd=RAIZ)
    print(f"Containers parados.")

def main():
    cabecalho()

    # Verifica se o usuário só quer parar os containers
    if len(sys.argv) > 1 and sys.argv[1] in ("--parar", "--down", "-d"):
        parar()
        return

    topologia         = pedir_topologia()
    num_agentes       = pedir_num_agentes(topologia)
    tipos_rede, nomes = pedir_tipos_rede()

    exibir_resumo(topologia, num_agentes, nomes)

    if not confirmar():
        print(f"\n  Cancelado.\n")
        sys.exit(0)

    codigo = rodar(topologia["id"], num_agentes, tipos_rede)
    sys.exit(codigo)


if __name__ == "__main__":
    main()