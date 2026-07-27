import json

class MosaikPadeAgent:
    """
    Agente Mosaik Wrapper - Atualizado para FIPA-ACL e Roteamento OMNeT++
    """
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.val_in = ""
        self.val_out = ""
        
        # Se eu sou o 1, o meu alvo é o 2. Se sou o 2, meu alvo é o 1.
        if "1" in self.agent_id:
            self.target = "Agente_2@0.0.0.0:5680" # Ajuste a porta conforme a sua config PADE
        else:
            self.target = "Agente_1@0.0.0.0:5679"

    def step(self, time):
        # 1. Checa se recebeu algo pela física de redes do OMNeT++
        if self.val_in:
            print(f"[{self.agent_id}] t={time} | MENSAGEM RECEBIDA DA FÍSICA: {self.val_in[:50]}...")
            self.val_in = "" # Limpa o buffer de entrada
        
        # 2. Constrói o novo envelope FIPA-ACL para disparar no cabo
        msg = {
            "performative": "inform",
            "sender": f"{self.agent_id}@0.0.0.0:0000",
            "receivers": [self.target],
            "content": f"Ping point-to-point de {self.agent_id} em t={time}",
            "ontology": "telemetria"
        }
        
        self.val_out = json.dumps(msg)
        return self.val_out