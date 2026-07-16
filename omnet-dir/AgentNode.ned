

simple AgentNode // (Substitui o NetworkNode)
{
    parameters:
        // ==========================================================
        // NOVO PARÂMETRO: Necessário para o C++ saber quem é quem
        // ==========================================================
        string agent_id;

        // ==========================================================
        // DADOS I/O DO MOSAIK (MANTIDOS EXATAMENTE IGUAIS)
        // ==========================================================
        string status @mutable = default("idle");
        double data_out @mutable = default(0.0);
        string val_in @mutable = default("");
        string val_out @mutable = default("");
        
        // ==========================================================
        // MÉTRICAS E TELEMETRIA (MANTIDAS EXATAMENTE IGUAIS)
        // ==========================================================
        double packets_sent @mutable = default(0);
        double packets_received @mutable = default(0);
        double packets_dropped @mutable = default(0);
        
        double last_latency @mutable = default(0.0);
        double last_packet_size @mutable = default(0.0);
        double current_jitter @mutable = default(0.0);

        string latencies_out @mutable = default("");
        string packet_sizes_out @mutable = default("");
        string jitters_out @mutable = default("");
        
        // ==========================================================
        // REMOVIDOS: bandwidth_bps, drop_probability, jitter_mean
        // Motivo: O nó não dita mais a rede. A rede será ditada pelo 
        // cabo (Link_5G, Link_4G, etc) que o Python vai conectar nele.
        // ==========================================================

        // Ícone visual para a interface gráfica (opcional)
        @display("i=device/pc;is=s");

    gates:
        // ==========================================================
        // PORTAS ATUALIZADAS
        // Substituímos input in[] e output out[] por inout port[].
        // Isso permite usar a sintaxe bidirecional (<-->) no arquivo NED 
        // gerado pelo Python, que é o padrão do OMNeT++ para redes.
        // ==========================================================
        inout port[];
}