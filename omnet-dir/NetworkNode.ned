simple NetworkNode
{
    parameters:
        string status @mutable = default("idle");
        double data_out @mutable = default(0.0);
        
        // As nossas portas de comunicação FIPA-ACL
        string val_in @mutable = default("");
        string val_out @mutable = default("");
        
        // Métricas de rede
        double packets_sent @mutable = default(0);
        double packets_received @mutable = default(0);
        double last_latency @mutable = default(0.0);
        double last_packet_size @mutable = default(0.0);

        double bandwidth_bps = default(50000.0); // 50 kbps por defeito
        
    gates:
        input in[];
        output out[];
}