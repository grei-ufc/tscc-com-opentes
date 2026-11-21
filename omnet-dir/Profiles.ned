



// ============================================================================
// BIBLIOTECA DE PERFIS DE REDE
// ============================================================================

// 1. Conexão Cabeada (Fibra/Ethernet): Extremamente rápida e confiável
channel Link_Wired extends ned.DatarateChannel {
    delay = 1ms;             // Atraso de propagação fixo
    datarate = 1Gbps;        // Velocidade alta
    per = 0.0;               // Sem perdas de pacote
}

// 2. Conexão 5G: Rápida, mas sofre pequena variação estatística (Jitter)
channel Link_5G extends ned.DatarateChannel {
    // truncnormal gera variação. Média de 5ms, com desvio padrão de 1ms, nunca menor que 2ms
    delay = truncnormal(5ms, 1ms); 
    datarate = 500Mbps;
    per = 0.00001;           // Probabilidade de perda: 0.001%
}

// 3. Conexão 4G (LTE): Velocidade menor, variação maior
channel Link_4G extends ned.DatarateChannel {
    delay = truncnormal(35ms, 8ms);
    datarate = 50Mbps;
    per = 0.005;             // Probabilidade de perda: 0.5%
}

// 4. Rede 2G/GPRS: Atraso alto, muita perda, baixa banda (Antigo IoT)
channel Link_2G extends ned.DatarateChannel {
    delay = exponential(200ms); // Atraso estocástico agressivo
    datarate = 250kbps;
    per = 0.15;                 // 15% de perda
}

// 5. Wireless (Wi-Fi / WLAN local): tecnologia sem fio diferente da
//    celular (5G/4G/2G) — rede local tipo roteador, sem torre de operadora.
//    Rápida e com baixa variação como a cabeada, mas ainda sofre um pouco
//    de perda por interferência (paredes, outros dispositivos no ar etc.).
channel Link_Wireless extends ned.DatarateChannel {
    delay = truncnormal(2ms, 0.5ms); // baixo atraso, pequena variação
    datarate = 300Mbps;
    per = 0.001;                     // 0.1% de perda
}

// ============================================================================
// CANAIS PARA TOPOLOGIAS ÁRVORE E HÍBRIDA (IEC 61850 / AMI Smart Grid)
// ============================================================================

// 6. Fibra óptica — backbone IEC 61850: interliga subestações no anel
channel Fibra extends ned.DatarateChannel {
    datarate = 1Gbps;
    delay = 0.05ms;
    per = 0;
}

// 7-10. Backhaul celular — estrela subestação → concentrador
//       Escolha via CELULAR_ARVORE / CELULAR_HIBRIDA na geração da topologia.
channel Celular2G extends ned.DatarateChannel {
    datarate = 100kbps;
    delay = 500ms;
    per = 0.02;
}

channel Celular3G extends ned.DatarateChannel {
    datarate = 2Mbps;
    delay = 150ms;
    per = 0.01;
}

channel Celular4G extends ned.DatarateChannel {
    datarate = 50Mbps;
    delay = 50ms;
    per = 0.005;
}

channel Celular5G extends ned.DatarateChannel {
    datarate = 200Mbps;
    delay = 10ms;
    per = 0.001;
}

// 11. RFMesh (Wi-SUN / IEEE 802.15.4g) — malha parcial de medidores
channel RFMesh extends ned.DatarateChannel {
    datarate = 150kbps;
    delay = 20ms;
    per = 0.03;
}

// 12. PLC de banda estreita — último milha na topologia árvore
channel PLC extends ned.DatarateChannel {
    datarate = 100kbps;
    delay = 30ms;
    per = 0.02;
}