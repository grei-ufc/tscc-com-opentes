network SimpleNetwork {
    parameters:
        int msgSize = <MSG_SIZE>;
    submodules:
        node1: StandardHost;
        node2: StandardHost;
    connections:
        node1.out --> { delay = msgSize * 0.001s; } --> node2.in;
}