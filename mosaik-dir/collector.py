"""
Módulo Coletor (Data Collector) para o Mosaik.

Este simulador atua como um sumidouro (sink) de dados do tipo *event-based*.
A sua principal função é subscrever as variáveis de saída de outras entidades
(como os nós do OMNeT++) e gravar essas métricas em tempo real num ficheiro
CSV ('results.csv') utilizando o formato longo de série temporal (Time-Series).

Attributes:
    META (dict): Metadados de configuração do simulador. O parâmetro 'any_inputs': True 
                 permite que ele receba variáveis arbitrárias sem declaração prévia.
"""

import mosaik_api_v3 as mosaik_api
import csv

META = {
    'type': 'event-based',
    'models': {
        'Monitor': {
            'public': True,
            'any_inputs': True,
            'attrs': [], # <- Faltava esta linha!
        },
    },
}

class Coletor(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.eid = 'monitor_0'
        self.csv_file = None
        self.csv_writer = None

    def init(self, sid, time_resolution):
        # Cria e prepara o ficheiro CSV com os cabeçalhos
        self.csv_file = open('results.csv', mode='w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['Tempo', 'Origem', 'Atributo', 'Valor'])
        return self.meta

    def create(self, num, model):
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs, max_advance):
        # Extrai os dados que o OMNeT++ enviou e guarda no CSV
        if self.eid in inputs:
            for atributo, origens in inputs[self.eid].items():
                for no_origem, valor in origens.items():
                    self.csv_writer.writerow([time, no_origem, atributo, valor])
        
        # Força a gravação no disco para podermos ver em tempo real
        self.csv_file.flush()
        return None 

    def finalize(self):
        # Fecha o ficheiro quando a simulação acaba
        if self.csv_file:
            self.csv_file.close()

if __name__ == '__main__':
    mosaik_api.start_simulation(Coletor())
