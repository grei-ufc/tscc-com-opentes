"""
cosim — Fonte única de verdade compartilhada pelos componentes da co-simulação.

  catalogo    topologias e tecnologias de enlace (rótulos, cores, mapeamentos)
  canais      leitura dos perfis de canal de omnet-dir/Profiles.ned
  topologias  montagem das redes (nós, posições e enlaces) de cada topologia

É usado no host (menus, testes) e dentro dos containers pade e mosaik_master,
onde o docker-compose.yml monta esta pasta em /opt/cosim (PYTHONPATH).
Só depende da biblioteca padrão do Python.
"""
