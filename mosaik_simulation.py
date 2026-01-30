#!/usr/bin/env python3
"""
Exemplo de simulação MOSAIK para Smart Grid
"""

import mosaik
import mosaik.util

# Configuração da simulação
SIM_CONFIG = {
    'ExampleSim': {
        'python': 'mosaik_demo.simulators:ExampleSim',
    },
    'Collector': {
        'python': 'mosaik_demo.simulators:Collector',
    },
}

def main():
    # Criar mundo de simulação
    world = mosaik.World(SIM_CONFIG)
    
    # Iniciar simuladores
    example_sim = world.start('ExampleSim', eid_prefix='Model_')
    collector = world.start('Collector')
    
    # Criar instâncias de modelo
    model_a = example_sim.ExampleModel(init_val=0)
    model_b = example_sim.ExampleModel(init_val=10)
    
    # Criar coletor de dados
    monitor = collector.Monitor()
    
    # Conectar modelos ao coletor
    world.connect(model_a, monitor, 'val', 'delta')
    world.connect(model_b, monitor, 'val', 'delta')
    
    # Conectar modelos entre si
    world.connect(model_a, model_b, 'val', 'val_in')
    
    # Executar simulação
    world.run(until=100)
    
    print("Simulação MOSAIK concluída!")
    print(f"Resultados salvos em: {monitor.data}")

if __name__ == '__main__':
    main()
