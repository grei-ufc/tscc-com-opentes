"""
cosim.ned: Escrita do DynamicNetwork.ned a partir de uma topologia.

Fonte única da geração do NED: o scenario.py (modo Mosaik, com o
`mosaikBridge`) e o cosim.ieee13 (modo de consulta, com o `servidorConsulta`)
escrevem a rede pela mesma função.
"""

import os

__all__ = ['PONTES', 'escrever_ned']

# Módulo de ponte com o mundo externo -> nome da instância no NED
PONTES = {'MosaikBridge': 'mosaikBridge', 'ServidorConsulta': 'servidorConsulta'}


def _canal(link):
    """'Link_X' ou 'Link_X { per_enlace = 0.15; cells = 2; }' quando o enlace tem parâmetros."""
    params = link.get('params')
    if not params:
        return link['tipo']
    corpo = ' '.join(f'{k} = {v};' for k, v in params.items())
    return f"{link['tipo']} {{ {corpo} }}"


def escrever_ned(agentes_info, links, arquivo_saida, ponte='MosaikBridge'):
    """Escreve o DynamicNetwork.ned.

    agentes_info : list[dict], cada item tem 'id', 'x', 'y'.
    links        : list[dict], 'origem', 'destino', 'tipo' e, opcional, 'params'
                   (valores já como literais NED, por exemplo {'per_enlace': '0.15'}).
    ponte        : 'MosaikBridge' (co-simulação passo a passo) ou 'ServidorConsulta'
                   (consulta por mensagem).

    A escrita é atômica (arquivo .tmp + os.replace): o OMNeT++ espera o arquivo
    aparecer e não pode ler uma versão pela metade.
    """
    if ponte not in PONTES:
        raise ValueError(f'ponte desconhecida: {ponte!r} ({", ".join(PONTES)})')
    os.makedirs(os.path.dirname(os.path.abspath(arquivo_saida)), exist_ok=True)
    arquivo_tmp = arquivo_saida + '.tmp'
    with open(arquivo_tmp, 'w', encoding='utf-8') as f:
        f.write("network DynamicNetwork\n{\n")
        f.write("    submodules:\n")
        f.write(f"        {PONTES[ponte]}: {ponte};\n\n")

        for ag in agentes_info:
            f.write(f"        {ag['id']}: AgentNode {{\n")
            f.write(f"            xPos = {ag['x']};\n")
            f.write(f"            yPos = {ag['y']};\n")
            f.write("        }\n")

        f.write("\n    connections:\n")
        for link in links:
            f.write(
                f"        {link['origem']}.port++ <--> "
                f"{_canal(link)} <--> "
                f"{link['destino']}.port++;\n"
            )
        f.write("}\n")
    os.replace(arquivo_tmp, arquivo_saida)
