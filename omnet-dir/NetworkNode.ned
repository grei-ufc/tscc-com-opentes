simple NetworkNode
{
    parameters:
        string status @mutable = default("idle");
        double data_out @mutable = default(0.0);
        string val_in @mutable = default("");
        string val_out @mutable = default("");
        
        // Métricas base
        double packets_sent @mutable = default(0);
        double packets_received @mutable = default(0);
        double last_latency @mutable = default(0.0);
        double last_packet_size @mutable = default(0.0);
        
        double bandwidth_bps = default(50000.0);
        
        double drop_probability = default(0.0); // De 0.0 a 1.0 (ex: 0.1 = 10% de perda)
        double jitter_mean = default(0.0);      // Média do atraso estocástico em segundos
        
        double packets_dropped @mutable = default(0);
        double current_jitter @mutable = default(0.0);

        string latencies_out @mutable = default("");
        string packet_sizes_out @mutable = default("");
        string jitters_out @mutable = default("");
        
    gates:
        input in[];
        output out[];
}