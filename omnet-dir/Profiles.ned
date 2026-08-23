



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