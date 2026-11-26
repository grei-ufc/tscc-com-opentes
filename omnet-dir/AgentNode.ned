simple AgentNode // (Substitui o NetworkNode)
{
    parameters:
        string agent_id;

        // ==========================================================
        // DADOS I/O DO MOSAIK
        // ==========================================================
        string status @mutable = default("idle");
        double data_out @mutable = default(0.0);
        string val_in @mutable = default("");
        string val_out @mutable = default("");
        
        // ==========================================================
        // MÉTRICAS E TELEMETRIA
        // ==========================================================
        double xPos = default(0.0);
        double yPos = default(0.0);

        double packets_sent @mutable = default(0);
        double packets_received @mutable = default(0);
        double packets_dropped @mutable = default(0);
        double packets_forwarded @mutable = default(0);   // pacotes de passagem encaminhados (roteamento)
        
        double last_latency @mutable = default(0.0);
        double last_packet_size @mutable = default(0.0);
        double current_jitter @mutable = default(0.0);

        string latencies_out @mutable = default("");
        string packet_sizes_out @mutable = default("");
        string jitters_out @mutable = default("");
        

        // ==========================================================
        // EXTENSÕES DO OPENTES (ExtensaoOpenTES.h)
        // ==========================================================
        // Roteamento: "saltos" (BFS, menor número de saltos, o original) ou "etx"
        // (menor número esperado de transmissões da mensagem, pelo tamanho dela,
        // como na rede 6TiSCH da tese).
        string roteamento = default("saltos");
        // Atraso de propagação dos meios não guiados, em s/m. O padrão é o valor
        // original do repositório; a propagação da luz é 3.336e-9 s/m.
        double propagacao_radio_s_m = default(0.00005);
        // Tabela opcional "nome do agente PADE,nó" (por exemplo prosumer611,agent_611).
        string arquivo_nomes = default("");

        // Ícone visual para a interface gráfica (opcional)
        @display("i=device/pc;is=s");

    gates:
        inout port[];
        input consulta @directIn;   // pacotes do modo de consulta (ServidorConsulta)
}