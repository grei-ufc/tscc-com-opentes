"""
cosim.ieee13: Monta a rede IEEE 13 barras para o modo de consulta por mensagem.

Gera o DynamicNetwork.ned com o `servidorConsulta` no lugar do `mosaikBridge`,
para o mercado transativo do OpenTES consultar a rede a cada mensagem. Grava
também o levantamento dos enlaces no formato `tisch_links.csv`.

    python -m cosim.ieee13 --posicoes nodes_xy.csv --canal Link_6TiSCH_TSCH \\
        --topologia malha --subestacao radio --ned omnet-dir/DynamicNetwork.ned

Todos os canais de Profiles.ned servem: os do repositório (Link_6TiSCH,
Link_WiSUN, RFMesh, PLC, Link_4G...) e os da tese (Link_6TiSCH_TSCH,
Link_WiSUN_FAN). Vários canais separados por vírgula se alternam entre os enlaces.
"""

import argparse
import random

from cosim import radio as _radio
from cosim.ned import escrever_ned
from cosim.topologias import montar_ieee13


def levantamento_da_rede(rede, radio, enlaces, semente):
    """Linhas do `tisch_links.csv` da rede montada: adjacent = o enlace existe."""
    linhas = [dict(r) for r in rede.levantamento]
    if not linhas:
        # Rede só com canais do repositório, em estrela: o levantamento é informativo.
        nos = [{**n, 'nome': n.get('nome', n['id'])} for n in rede.nos]
        linhas = (_radio.ler_enlaces(enlaces, nos) if enlaces
                  else _radio.levantar_enlaces(nos, radio, random.Random(semente)))
    existe = {frozenset((lk['origem'], lk['destino'])) for lk in rede.links}
    for r in linhas:
        r['adjacent'] = int(frozenset((r['id_i'], r['id_j'])) in existe)
    return linhas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--posicoes', required=True, help='nodes_xy.csv do caso (node,x_m,y_m)')
    ap.add_argument('--canal', default='Link_6TiSCH_TSCH', help='canal(is) de Profiles.ned, separados por vírgula')
    ap.add_argument('--topologia', default='estrela', choices=('estrela', 'malha'))
    ap.add_argument('--subestacao', default='cabo', choices=('cabo', 'radio'))
    ap.add_argument('--enlaces', default='', help='tisch_links.csv a repetir (vazio: sorteio com a semente)')
    ap.add_argument('--semente', type=int, default=0)
    ap.add_argument('--cells', type=int, default=0, help='cells por slotframe do Link_6TiSCH_TSCH (0: padrão do canal)')
    ap.add_argument('--taxa', type=float, default=50000, help='taxa do Link_WiSUN_FAN, em bps')
    ap.add_argument('--central', default='0', help='nome do concentrador no nodes_xy.csv')
    ap.add_argument('--ned', required=True, help='DynamicNetwork.ned a gravar')
    ap.add_argument('--enlaces-csv', default='', help='onde gravar o levantamento dos enlaces')
    a = ap.parse_args(argv)

    canais = [c.strip() for c in a.canal.split(',') if c.strip()]
    radio = _radio.Radio(taxa_bps=a.taxa)
    rede = montar_ieee13(canais, posicoes=a.posicoes, topologia=a.topologia, subestacao=a.subestacao,
                         enlaces=a.enlaces or None, radio=radio, semente=a.semente,
                         cells=a.cells or None, central=a.central)
    escrever_ned(rede.nos, rede.links, a.ned, ponte='ServidorConsulta')
    if a.enlaces_csv:
        _radio.gravar_enlaces(levantamento_da_rede(rede, radio, a.enlaces or None, a.semente), a.enlaces_csv)
    tipos = sorted({lk['tipo'] for lk in rede.links})
    print(f"[TSCC] rede IEEE 13: {len(rede.nos)} nos, {len(rede.links)} enlaces, "
          f"{a.topologia}, subestacao por {a.subestacao}, canais {', '.join(tipos)}", flush=True)


if __name__ == '__main__':
    main()
