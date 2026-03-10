simple MosaikBridge
{
    @display("i=block/network2");
}

network CoSimulationNetwork
{
    submodules:
        bridge: MosaikBridge {
            @display("p=50,50");
        }
        // Os nós (NetworkNode) serão criados dinamicamente, não coloque eles aqui!
}