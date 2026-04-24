//
 // @file NetworkNode.h
 // @brief Definição do nó dinâmico da rede OMNeT++.
 //
 // Declara a classe NetworkNode, que simula o comportamento físico/lógico
 // de um dispositivo de rede. É projetado para ser instanciado em tempo de
 // execução pelo MosaikBridge. Escuta e reage a parâmetros com a anotação @mutable,
 // lendo injeções de dados e disparando pacotes de rede internos.
 //
simple NetworkNode
{
    parameters:
        string status = default("active");
        
        volatile double data_in @mutable = default(0.0); 
        volatile double data_out @mutable = default(0.0); 
        
        // Novas Métricas de Rede
        volatile double packets_sent @mutable = default(0.0);
        volatile double packets_received @mutable = default(0.0);
        volatile double last_latency @mutable = default(0.0);
        volatile double last_packet_size @mutable = default(0.0);

        @display("i=device/laptop");

    gates:
        input in[];
        output out[];
}