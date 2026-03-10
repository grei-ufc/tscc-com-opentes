simple NetworkNode
{
    parameters:
        string status = default("active");
        
        // O @mutable diz ao OMNeT++ que o C++ tem permissão para alterar este valor
        volatile double data_in @mutable = default(0.0); 
        volatile double data_out @mutable = default(0.0); 

        @display("i=device/laptop");

    gates:
        input in[];
        output out[];
}