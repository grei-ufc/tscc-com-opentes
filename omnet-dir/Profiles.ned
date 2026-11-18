



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

// 6. Rede LPWA 6TiSCH (IEEE 802.15.4g modo 1 - 915 MHz, TSCH slotframe = 4.04s, 2 cells)
//    Extraído de simulators/comm-opentes/Tisch.ned (Melo, 2022, seção 6.1.5)
channel Link_6TiSCH extends ned.DatarateChannel {
    delay = truncnormal(40ms, 10ms); // 1 timeslot TSCH (~40ms) + jitter de escalonamento
    datarate = 50kbps;               // IEEE 802.15.4g SUN FSK modo 1 (50 kbps)
    per = 0.02;                      // PER base do enlace de rádio (somada à atenuação espacial do AgentNode.cc)
}

// 7. Rede Wi-SUN FAN (IEEE 802.15.4g CSMA/CA não sincronizado, 50-150 kbps)
channel Link_WiSUN extends ned.DatarateChannel {
    delay = truncnormal(15ms, 4ms);  // CSMA/CA backoff (macMinBE=3..5, unit_backoff=1.16ms)
    datarate = 150kbps;              // IEEE 802.15.4g SUN FSK modo 3
    per = 0.01;
}