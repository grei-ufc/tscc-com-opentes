// Modo de consulta por mensagem (servidor de rotas); implementado em ServidorConsulta.cc.
// É instanciado como `servidorConsulta` no lugar do `mosaikBridge`, no
// DynamicNetwork.ned gerado por `python -m cosim.ieee13`.
simple ServidorConsulta
{
    parameters:
        // Porta ZMQ das consultas; a variável de ambiente OMNET_PORT tem precedência,
        // como no MosaikBridge.
        int porta = default(5556);
        // Limite de tempo simulado de uma consulta. Passado dele sem entrega nem
        // descarte avisado, a mensagem é dada como perdida.
        double guarda_s @unit(s) = default(100000s);
        @display("i=block/network2");
}
