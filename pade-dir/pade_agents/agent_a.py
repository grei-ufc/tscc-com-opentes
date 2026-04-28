import json
from pade.core.agent import Agent

class AgenteA(Agent):
    def __init__(self, aid):
        super().__init__(aid=aid, debug=False)
        # Inicializa a variável com uma string vazia (mais seguro que None para o Mosaik)
        self.val_out = "" 

    # O on_start é o método padrão do PADE executado quando o agente "acorda"
    def on_start(self):
        super().on_start()
        # Dispara a mensagem logo no início da simulação
        self.preparar_mensagem("Olá, Agente B! Testando a latência da rede.")

    # Lógica que prepara e expõe a mensagem
    def preparar_mensagem(self, conteudo):
        dicionario_msg = {
            'origem': self.aid.localname,
            'destino': 'AgenteB',
            'payload': conteudo,
            'tamanho': len(conteudo)
        }
        
        # CRÍTICO: Converte o dicionário Python para uma String JSON!
        # É essa string que vai viajar dentro do cPacket no OMNeT++
        self.val_out = json.dumps(dicionario_msg)
        
        print(f"[{self.aid.localname}] Mensagem pronta na porta de saída: {self.val_out}")