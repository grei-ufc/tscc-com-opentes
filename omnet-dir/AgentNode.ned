

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
        double packets_sent @mutable = default(0);
        double packets_received @mutable = default(0);
        double packets_dropped @mutable = default(0);
        
        double last_latency @mutable = default(0.0);
        double last_packet_size @mutable = default(0.0);
        double current_jitter @mutable = default(0.0);

        string latencies_out @mutable = default("");
        string packet_sizes_out @mutable = default("");
        string jitters_out @mutable = default("");
        

        // Ícone visual para a interface gráfica (opcional)
        @display("i=device/pc;is=s");

    gates:
        inout port[];
}