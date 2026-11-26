#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu.py — Configurador CLI da co-simulação PADE + OMNeT++ + Mosaik.

Alternativa terminal ao menu-streamlit.py: mesmas topologias, mesmos parâmetros
e as mesmas variáveis de ambiente, sem dependência de navegador ou Streamlit.

Como rodar:
    python3 menu.py            # configura e inicia a simulação
    python3 menu.py --parar    # derruba os containers (docker compose down)

Topologias (catálogo em cosim/catalogo.py):
  - estrela  : 1 agente central conectado a N periféricos
  - malha    : N agentes, todos conectados entre si
  - anel     : N agentes em ciclo fechado (bidirecional)
  - arvore   : árvore radial IEC 61850 com fan-out configurável
  - hibrida  : hierarquia CCO → fibra → celular → RF mesh
  - ieee13   : alimentador IEEE 13 barras do OpenTES (18 agentes)

Variáveis de ambiente enviadas ao docker compose:
  Todas      : TOPOLOGY, NUM_PERIFERICOS, TIPOS_REDE
  Árvore     : ARVORE_FANOUT, CELULAR_ARVORE
  Híbrida    : SUBESTACOES, CONCENTRADORES, MEDIDORES_CLUSTER,
               CELULAR_HIBRIDA, SEMENTE_HIBRIDA

Semântica de NUM_PERIFERICOS:
  - estrela            : número de PERIFÉRICOS (total = N + 1 com o central)
  - malha / anel       : número TOTAL de agentes
  - árvore / híbrida   : total de nós - 1 (tudo menos a raiz / CCO)
  - ieee13             : 17 (fixo: DSO, Market e 15 barras em torno do concentrador)
"""

import os
import subprocess
import sys

from cosim.canais import descrever, ler_perfis
from cosim.catalogo import CELULAR, TECNOLOGIAS, TIPOS_REDE_PADRAO
from cosim.catalogo import TOPOLOGIAS as CATALOGO_TOPOLOGIAS
from cosim.topologias import IEEE13_NOS

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE OPÇÕES  (catálogo compartilhado em cosim/)
# ══════════════════════════════════════════════════════════════

TOPOLOGIAS = {
    str(i): {"id": t.id, "nome": t.rotulo, "desc": t.descricao, "min": t.min_agentes}
    for i, t in enumerate((CATALOGO_TOPOLOGIAS[k] for k in
                           ("estrela", "malha", "anel", "arvore", "hibrida", "ieee13")), 1)
}

# Tecnologias escolhidas pelo usuário: as cinco de estrela/malha/anel e as duas
# LPWA da IEEE 13. Descrição gerada a partir do Profiles.ned.
_PERFIS = ler_perfis()
_ESCOLHIVEIS = TIPOS_REDE_PADRAO + ["Link_6TiSCH", "Link_WiSUN"]
REDES = {
    str(i): (ned, TECNOLOGIAS[ned].rotulo, descrever(_PERFIS[ned]))
    for i, ned in enumerate(_ESCOLHIVEIS, 1)
}

CELULAR_OPTIONS = list(CELULAR)

MAX_AGENTES_VISIVEIS = 20   # igual ao menu-streamlit.py
MAX_AGENTES = 500

RAIZ = os.path.dirname(os.path.abspath(__file__))
MOSAIK_DIR = os.path.join(RAIZ, "mosaik-dir")
BARRAS_IEEE13 = [n["id"].removeprefix("agent_") for n in IEEE13_NOS if n["camada"] == "periferico"]


def linha(char="─", n=60):
    return char * n


def cabecalho():
    largura = 46
    print()
    print("╔" + "═" * largura + "╗")
    print("║" + "Co-Simulação PADE + OMNeT++ + Mosaik".center(largura) + "║")
    print("║" + "GREI-UFC · Configurador de Cenário (CLI)".center(largura) + "║")
    print("╚" + "═" * largura + "╝")
    print()


def titulo(texto):
    print(f"\n┌─ {texto} {linha('─', max(0, 56 - len(texto)))}┐")


def rodape_bloco():
    print(f"└{linha()}┘")


def ok(msg):
    print(f"  {msg}")


def aviso(msg):
    print(f"  {msg}")


def entrada(prompt):
    try:
        return input(f"{prompt} ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Interrompido pelo usuário.")
        sys.exit(0)


def pedir_inteiro(prompt, minimo, maximo, padrao=None):
    """Lê um inteiro em [minimo, maximo]. ENTER usa o padrão, se houver."""
    sufixo = f" [{minimo}-{maximo}" + (f", padrão {padrao}]" if padrao is not None else "]")
    while True:
        resp = entrada(f"{prompt}{sufixo}:")
        if resp == "" and padrao is not None:
            return padrao
        try:
            n = int(resp)
        except ValueError:
            aviso("Digite um número inteiro.")
            continue
        if n < minimo:
            aviso(f"O mínimo é {minimo}.")
        elif n > maximo:
            aviso(f"O máximo é {maximo}.")
        else:
            return n


def pedir_topologia():
    titulo("1. TOPOLOGIA DE REDE")
    for k, v in TOPOLOGIAS.items():
        print(f"  [{k}] {v['nome']:<15} {v['desc']}")
    rodape_bloco()

    while True:
        resp = entrada(f"Escolha [1-{len(TOPOLOGIAS)}]:")
        if resp in TOPOLOGIAS:
            top = TOPOLOGIAS[resp]
            ok(f"{top['nome'].upper()} selecionada.")
            return top
        aviso(f"Digite um número de 1 a {len(TOPOLOGIAS)}.")


def pedir_celular(rotulo):
    print(f"  Tecnologia celular ({rotulo}): " + " / ".join(c.upper() for c in CELULAR_OPTIONS))
    while True:
        resp = entrada("Celular [padrão 4g]:").lower()
        if resp == "":
            return "4g"
        if resp in CELULAR_OPTIONS:
            return resp
        aviso("Opção inválida. Use 2g, 3g, 4g ou 5g.")


def pedir_fanout():
    print("  Fan-out por nível = número de filhos por nó em cada nível, separados por vírgula.")
    print("  Exemplo: 3,2,4 → 3 subestações, 2 concentradores por sub, 4 medidores por conc.")
    while True:
        resp = entrada("Fan-out [padrão 3,2,4]:").replace(" ", "")
        if resp == "":
            resp = "3,2,4"
        try:
            fan_list = [int(v) for v in resp.split(",")]
            if not fan_list or any(f <= 0 for f in fan_list):
                raise ValueError
        except ValueError:
            aviso("Fan-out inválido. Use inteiros positivos separados por vírgula (ex.: 3,2,4).")
            continue
        total, nivel = 1, 1
        for f in fan_list:
            nivel *= f
            total += nivel
        if total > MAX_AGENTES:
            aviso(f"Esse fan-out gera {total} nós; o máximo suportado é {MAX_AGENTES}.")
            continue
        return resp, fan_list, total


def pedir_dimensionamento(topologia):
    """Devolve dict com total_agentes, num_perifericos e parâmetros específicos."""
    tid = topologia["id"]
    cfg = {"fan": "3,2,4", "celular": "4g",
           "n_subs": 3, "n_cons": 3, "n_meds": 5, "semente": 42}

    if tid == "estrela":
        titulo("2. NÚMERO DE PERIFÉRICOS")
        print(f"  Mínimo: {topologia['min']}  |  Máximo: {MAX_AGENTES}  (total = N + 1 com o central)")
        rodape_bloco()
        n = pedir_inteiro("Periféricos", topologia["min"], MAX_AGENTES, padrao=4)
        cfg["num_perifericos"] = n
        cfg["total_agentes"] = n + 1
        ok(f"{n} periférico(s) → {n + 1} agentes no total (1 central + {n}).")

    elif tid in ("malha", "anel"):
        titulo("2. NÚMERO DE AGENTES " + ("NA MALHA" if tid == "malha" else "NO ANEL"))
        print(f"  Mínimo: {topologia['min']}  |  Máximo: {MAX_AGENTES}  (todos são peers, sem central)")
        rodape_bloco()
        n = pedir_inteiro("Agentes", topologia["min"], MAX_AGENTES, padrao=5)
        cfg["num_perifericos"] = n
        cfg["total_agentes"] = n
        ok(f"{n} agentes " + ("conectados entre si." if tid == "malha" else "em ciclo fechado."))

    elif tid == "ieee13":
        titulo("2. REDE IEEE 13 BARRAS")
        print("  18 agentes fixos: Concentrador, DSO e Market na subestação e 15 barras.")
        rodape_bloco()
        cfg["num_perifericos"] = 17
        cfg["total_agentes"] = 18

    elif tid == "arvore":
        titulo("2. DIMENSIONAMENTO DA ÁRVORE")
        rodape_bloco()
        fan, fan_list, total = pedir_fanout()
        cfg["fan"] = fan
        ok(f"Fan-out {fan_list} → {total} nós totais na simulação.")
        cfg["celular"] = pedir_celular("nível concentrador")
        ok(f"Celular: {cfg['celular'].upper()}")
        cfg["total_agentes"] = total
        cfg["num_perifericos"] = total - 1

    else:  # hibrida
        titulo("2. DIMENSIONAMENTO DA REDE HÍBRIDA")
        rodape_bloco()
        while True:
            n_subs = pedir_inteiro("Subestações", 2, 20, padrao=3)
            n_cons = pedir_inteiro("Concentradores por subestação", 1, 20, padrao=3)
            n_meds = pedir_inteiro("Medidores por concentrador", 1, 50, padrao=5)
            total = 1 + n_subs + n_subs * n_cons + n_subs * n_cons * n_meds
            if total > MAX_AGENTES:
                aviso(f"Isso gera {total} nós; o máximo suportado é {MAX_AGENTES}. Reduza os valores.")
                continue
            break
        cfg["n_subs"], cfg["n_cons"], cfg["n_meds"] = n_subs, n_cons, n_meds
        cfg["celular"] = pedir_celular("backhaul")
        cfg["semente"] = pedir_inteiro("Semente aleatória", 0, 999999, padrao=42)
        cfg["total_agentes"] = total
        cfg["num_perifericos"] = total - 1
        ok(f"Total estimado: {total} nós "
           f"(1 CCO + {n_subs} subs + {n_subs * n_cons} cons + {n_subs * n_cons * n_meds} meds).")

    return cfg


def pedir_pool(padrao):
    """Pool de tecnologias. `padrao` = lista de chaves usada com ENTER."""
    titulo("3. TIPOS DE ENLACE — POOL DE TECNOLOGIAS")
    for k, (_, nome, desc) in REDES.items():
        print(f"  [{k}] {nome:<9} {desc}")
    print()
    nomes_padrao = ", ".join(REDES[c][1] for c in padrao)
    print(f"  Separe por vírgula para múltiplas. ENTER = {nomes_padrao}.")
    rodape_bloco()

    while True:
        resp = entrada(f"Tecnologias [1-{len(REDES)}]:")
        if resp == "":
            chaves = list(padrao)
        else:
            chaves = [c.strip() for c in resp.split(",") if c.strip()]
            if not chaves:
                aviso("Selecione ao menos um tipo de enlace.")
                continue
            invalidas = [c for c in chaves if c not in REDES]
            if invalidas:
                aviso(f"Opção(ões) inválida(s): {', '.join(invalidas)}. Use 1 a {len(REDES)}.")
                continue
        # remove duplicatas preservando a ordem
        chaves = list(dict.fromkeys(chaves))
        pool = [REDES[c][0] for c in chaves]
        ok(", ".join(REDES[c][1] for c in chaves))
        return pool


def pedir_tecnologia_por_agente(topologia_id, num_enlaces, pool):
    """
    Atribuição OPCIONAL de uma tecnologia a cada agente (como no Streamlit).
    Devolve a lista de ned-ids:
      - Nenhum agente fixado → devolve o próprio pool (distribuição cíclica padrão).
      - Algum fixado         → devolve uma tecnologia por enlace.
    """
    resp = entrada("Definir tecnologia por agente (opcional)? [s/N]:").lower()
    if resp not in ("s", "sim", "y", "yes"):
        return pool

    nome_por_ned = {ned: nome for _, (ned, nome, _) in REDES.items()}

    if topologia_id == "estrela":
        rotulos = [f"Periférico {i}" for i in range(1, num_enlaces + 1)]
        print("\n  Cada linha é o enlace daquele periférico com o nó central.")
    elif topologia_id == "ieee13":
        rotulos = [f"Barra {b}" for b in BARRAS_IEEE13]
        print("\n  Cada linha é o enlace da barra com o concentrador (DSO e Market ficam no cabo).")
    else:
        rotulos = [f"Agente {i} → Agente {(i % num_enlaces) + 1}"
                   for i in range(1, num_enlaces + 1)]
        print("\n  Cada linha é o enlace agente_i → agente_{i+1} (cíclico).")
    print("  ENTER = Auto (segue a ordem cíclica do pool).")

    print("\n  Opções:  [0] Auto (cíclico)")
    for idx, ned in enumerate(pool, start=1):
        print(f"           [{idx}] {nome_por_ned[ned]}")
    print()

    n_mostrar = min(len(rotulos), MAX_AGENTES_VISIVEIS)
    tipos_finais = []
    algum_fixo = False

    for i in range(n_mostrar):
        while True:
            r = entrada(f"  {rotulos[i]:<24} [0-{len(pool)}, ENTER=0]:")
            if r in ("", "0"):
                tipos_finais.append(pool[i % len(pool)])
                break
            if r.isdigit() and 1 <= int(r) <= len(pool):
                tipos_finais.append(pool[int(r) - 1])
                algum_fixo = True
                break
            aviso(f"Digite um número de 0 a {len(pool)}.")

    if len(rotulos) > n_mostrar:
        print(f"  … {len(rotulos) - n_mostrar} agente(s) restantes usam a distribuição cíclica do pool.")
        for i in range(n_mostrar, len(rotulos)):
            tipos_finais.append(pool[i % len(pool)])

    return tipos_finais if algum_fixo else pool


def pedir_tipos_rede(topologia, num_perifericos):
    """Estrela/Anel/IEEE 13: pool + atribuição opcional. Malha: pool.
    Árvore/Híbrida: canais fixos por camada."""
    tid = topologia["id"]
    chaves_padrao = [k for k, (ned, _, _) in REDES.items() if ned in TIPOS_REDE_PADRAO]
    if tid in ("estrela", "anel"):
        pool = pedir_pool(chaves_padrao)
        return pedir_tecnologia_por_agente(tid, num_perifericos, pool)
    if tid == "malha":
        return pedir_pool(chaves_padrao)
    if tid == "ieee13":
        lpwa = [k for k, (ned, _, _) in REDES.items() if ned == "Link_6TiSCH"]
        pool = pedir_pool(lpwa)
        return pedir_tecnologia_por_agente(tid, len(BARRAS_IEEE13), pool)

    titulo("3. TIPOS DE ENLACE")
    print("  Canais fixos por camada (não configuráveis):")
    if tid == "arvore":
        print("    raiz → subestações        : Fibra")
        print("    subestações → conc.       : Celular (configurado acima)")
        print("    concentradores → medidores: PLC")
    else:
        print("    CCO ↔ subestações (anel)  : Fibra")
        print("    subestações → conc.       : Celular (configurado acima)")
        print("    medidores nos clusters    : RF Mesh")
    rodape_bloco()
    return ["Link_Wired"]  # mesma convenção do streamlit


def nome_da_rede(ned):
    return TECNOLOGIAS[ned].rotulo if ned in TECNOLOGIAS else ned


def exibir_resumo(topologia, cfg, tipos_rede):
    tid = topologia["id"]
    titulo("RESUMO DA CONFIGURAÇÃO")

    if tid == "estrela":
        detalhe = f"1 central + {cfg['num_perifericos']} periféricos"
    elif tid == "malha":
        detalhe = f"{cfg['total_agentes']} agentes conectados entre si"
    elif tid == "anel":
        detalhe = f"{cfg['total_agentes']} agentes em ciclo"
    elif tid == "ieee13":
        detalhe = "Concentrador, DSO, Market e 15 barras"
    elif tid == "arvore":
        detalhe = f"{cfg['total_agentes']} nós (fan-out {cfg['fan']})"
    else:
        detalhe = (f"{cfg['total_agentes']} nós "
                   f"({cfg['n_subs']}S · {cfg['n_cons']}C · {cfg['n_meds']}M)")

    if tid in ("estrela", "malha", "anel", "ieee13"):
        redes = ", ".join(dict.fromkeys(nome_da_rede(t) for t in tipos_rede))
    else:
        redes = "Fibra / Celular / PLC-RF"

    print(f"  {'Topologia':<20}: {topologia['nome']}")
    print(f"  {'Agentes / Nós':<20}: {detalhe}")
    print(f"  {'Redes':<20}: {redes}")
    if tid == "arvore":
        print(f"  {'Fan-out':<20}: {cfg['fan']}")
        print(f"  {'Celular':<20}: {cfg['celular'].upper()}")
    elif tid == "hibrida":
        print(f"  {'Subs / Cons / Meds':<20}: {cfg['n_subs']} / {cfg['n_cons']} / {cfg['n_meds']}")
        print(f"  {'Celular':<20}: {cfg['celular'].upper()}")
        print(f"  {'Semente':<20}: {cfg['semente']}")
    rodape_bloco()


def confirmar():
    while True:
        resp = entrada("Iniciar simulação? [s/n]:").lower()
        if resp in ("s", "sim", "y", "yes"):
            return True
        if resp in ("n", "nao", "não", "no"):
            return False
        aviso("Digite 's' para sim ou 'n' para não.")


def montar_env(topologia_id, cfg, tipos_rede):
    env = {
        "TOPOLOGY":        topologia_id,
        "NUM_PERIFERICOS": str(cfg["num_perifericos"]),
        "TIPOS_REDE":      ",".join(tipos_rede),
    }
    if topologia_id == "arvore":
        env["ARVORE_FANOUT"] = cfg["fan"]
        env["CELULAR_ARVORE"] = cfg["celular"]
    elif topologia_id == "hibrida":
        env["SUBESTACOES"] = str(cfg["n_subs"])
        env["CONCENTRADORES"] = str(cfg["n_cons"])
        env["MEDIDORES_CLUSTER"] = str(cfg["n_meds"])
        env["CELULAR_HIBRIDA"] = cfg["celular"]
        env["SEMENTE_HIBRIDA"] = str(cfg["semente"])
    return env


def limpar_residuos():
    """Remove DynamicNetwork.ned residual e gráficos de rodadas anteriores."""
    ned_residual = os.path.join(RAIZ, "omnet-dir", "DynamicNetwork.ned")
    if os.path.exists(ned_residual):
        try:
            os.remove(ned_residual)
        except OSError:
            pass

    if os.path.isdir(MOSAIK_DIR):
        for f in os.listdir(MOSAIK_DIR):
            if f.startswith("grafico_") and f.endswith((".svg", ".png")):
                try:
                    os.remove(os.path.join(MOSAIK_DIR, f))
                except OSError:
                    pass


def rodar(topologia_id, cfg, tipos_rede):
    env = os.environ.copy()
    env.update(montar_env(topologia_id, cfg, tipos_rede))

    limpar_residuos()

    print("\n  Iniciando docker compose...\n")

    resultado = subprocess.run(
        ["docker", "compose", "up", "--build", "--force-recreate",
         "--abort-on-container-exit",
         "--exit-code-from", "mosaik_master"],
        cwd=RAIZ,
        env=env,
    )

    print()
    if resultado.returncode == 0:
        ok("Co-simulação concluída com sucesso.")
        print("    Os gráficos foram salvos em mosaik-dir/")
    else:
        aviso(f"docker compose encerrou com código {resultado.returncode}.")
        print("    Se algum gráfico foi gerado, ele está em mosaik-dir/")

    return resultado.returncode


def parar():
    print("\n  Derrubando containers...")
    subprocess.run(["docker", "compose", "down"], cwd=RAIZ)
    ok("Containers parados.")


def main():
    cabecalho()

    if len(sys.argv) > 1 and sys.argv[1] in ("--parar", "--down", "-d"):
        parar()
        return

    topologia = pedir_topologia()
    cfg = pedir_dimensionamento(topologia)
    tipos_rede = pedir_tipos_rede(topologia, cfg["num_perifericos"])

    exibir_resumo(topologia, cfg, tipos_rede)

    if not confirmar():
        print("\n  Cancelado.\n")
        sys.exit(0)

    codigo = rodar(topologia["id"], cfg, tipos_rede)
    sys.exit(codigo)


if __name__ == "__main__":
    main()
