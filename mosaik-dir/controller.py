"""
Módulo Controlador (Traffic Generator) para o Mosaik.

Este simulador atua como um injetor de dados *time-based*. A cada passo
da simulação, ele gera um valor de tráfego constante que será enviado
para um nó correspondente no OMNeT++ alterar seus parâmetros em tempo real.

Attributes:
    META (dict): Metadados de configuração do simulador requeridos pela API Mosaik.
"""

import mosaik_api

META = {
    'type': 'time-based',
    'models': {
        'TrafficGen': {
            'public': True,
            'params': ['valor_injecao'],
            'attrs': ['sinal_saida', 'retroalimentacao'], # A variável que vamos ligar ao OMNeT++
        },
    },
}

class Controlador(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.valor = 0
        self.eid = 'gen_0'

    def init(self, sid, time_resolution):
        return self.meta

    def create(self, num, model, valor_injecao):
        self.valor = valor_injecao
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs, max_advance):
        # 1 Verifica se chegou algum dado de feedback do OMNeT++
        if self.eid in inputs and 'retroalimentacao' in inputs[self.eid]:
            # Pega o valor que o OMNeT++ enviou no passo anterior
            valores_recebidos = inputs[self.eid]['retroalimentacao']
            pacotes_enviados_pelo_omnet = list(valores_recebidos.values())[0]
            
            # 2 Mudando o comportamento do Gerador
            # Exemplo: Se o OMNeT++ mandou mais de 10 pacotes, o Gerador diminui a taxa de injeção pela metade para não sobrecarregar a rede.
            if pacotes_enviados_pelo_omnet > 10:
                self.valor = 7.5
                print(f"[Gerador t={time}] A rede está cheia! Reduzindo injeção para {self.valor}")
            else:
                self.valor = 15.0

        # Avança o tempo
        return time + 1

    def get_data(self, outputs):
        # A cada passo, o Mosaik recolhe este valor e envia para quem estiver conectado
        return {self.eid: {'sinal_saida': self.valor}}

if __name__ == '__main__':
    mosaik_api.start_simulation(Controlador())
