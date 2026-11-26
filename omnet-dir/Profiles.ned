



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

// Rede LPWA 6TiSCH (IEEE 802.15.4g modo 1 - 915 MHz, 50 kbps)
channel Link_6TiSCH extends ned.DatarateChannel {
    delay = truncnormal(40ms, 10ms);
    datarate = 50kbps;
    per = 0.02;
}

// Rede Wi-SUN FAN (IEEE 802.15.4g SUN FSK modo 3 - 150 kbps)
channel Link_WiSUN extends ned.DatarateChannel {
    delay = truncnormal(15ms, 4ms);
    datarate = 150kbps;
    per = 0.01;
}

// ============================================================================
// CANAIS DO MODELO DA TESE (Melo, 2022, seção 6.1.5): OpenTES, IEEE 13 barras
// ============================================================================
// Nestes dois canais o atraso e a perda de cada salto vêm do MAC do rádio,
// calculados no AgentNode (ExtensaoOpenTES.h), e não da taxa e do atraso fixos:
// o envio é feito com duração zero e o atraso do salto. O PER de
// cada enlace (per_enlace) sai da montagem da topologia (cosim/radio.py:
// Friis em 915 MHz, Pister-Hack e a tabela de PER de Prando et al.). A taxa
// declarada abaixo é a da camada física e entra no cálculo do Wi-SUN.

// 6TiSCH: TSCH com um quadro de 127 B por cell, `cells` cells por slotframe de 4,04 s.
channel Link_6TiSCH_TSCH extends ned.DatarateChannel {
    datarate = 50kbps;
    delay = 0s;
    per = 0;
    string mac = "tsch";
    double per_enlace = default(0);
    double slotframe @unit(s) = default(4.04s);
    int cells = default(2);
    int quadro_bytes = default(127);
    int max_retries = default(3);
}

// Wi-SUN FAN: CSMA/CA com salto de canal assíncrono, quadro de até 1280 B.
// A taxa da camada física é 50 kbps; `taxa_bps` a troca por enlace (150 ou 300 kbps).
channel Link_WiSUN_FAN extends ned.DatarateChannel {
    datarate = 50kbps;
    delay = 0s;
    per = 0;
    string mac = "wisun";
    double per_enlace = default(0);
    double taxa_bps = default(0);   // 0: a datarate acima
    int quadro_bytes = default(1280);
    int max_retries = default(3);
    int min_be = default(3);
    int max_be = default(5);
    double unit_backoff @unit(s) = default(1.16ms);
    double turnaround @unit(s) = default(1ms);
    int shr_phr_bytes = default(12);
    int ack_bytes = default(30);
}
