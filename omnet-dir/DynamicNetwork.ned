network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        cco: AgentNode {
            xPos = 0.0;
            yPos = 0.0;
        }
        sub0: AgentNode {
            xPos = 2500.0;
            yPos = 0.0;
        }
        sub1: AgentNode {
            xPos = 1250.0;
            yPos = 2165.06;
        }
        sub2: AgentNode {
            xPos = -1250.0;
            yPos = 2165.06;
        }
        sub3: AgentNode {
            xPos = -2500.0;
            yPos = 0.0;
        }
        sub4: AgentNode {
            xPos = -1250.0;
            yPos = -2165.06;
        }
        sub5: AgentNode {
            xPos = 1250.0;
            yPos = -2165.06;
        }
        con0_0: AgentNode {
            xPos = 2980.92;
            yPos = -324.01;
        }
        med0_0_0: AgentNode {
            xPos = 2995.69;
            yPos = -465.91;
        }
        med0_0_1: AgentNode {
            xPos = 2973.54;
            yPos = -204.64;
        }
        med0_0_2: AgentNode {
            xPos = 3096.75;
            yPos = -402.79;
        }
        med0_0_3: AgentNode {
            xPos = 2925.56;
            yPos = -351.32;
        }
        med0_0_4: AgentNode {
            xPos = 2853.9;
            yPos = -245.1;
        }
        med0_0_5: AgentNode {
            xPos = 3048.44;
            yPos = -272.81;
        }
        con0_1: AgentNode {
            xPos = 2946.33;
            yPos = -144.9;
        }
        med0_1_0: AgentNode {
            xPos = 2968.02;
            yPos = -63.29;
        }
        med0_1_1: AgentNode {
            xPos = 3019.29;
            yPos = -192.09;
        }
        med0_1_2: AgentNode {
            xPos = 2839.65;
            yPos = -92.53;
        }
        med0_1_3: AgentNode {
            xPos = 2982.34;
            yPos = -243.77;
        }
        med0_1_4: AgentNode {
            xPos = 3045.34;
            yPos = -89.27;
        }
        med0_1_5: AgentNode {
            xPos = 2991.33;
            yPos = -134.81;
        }
        con0_2: AgentNode {
            xPos = 2713.43;
            yPos = 542.43;
        }
        med0_2_0: AgentNode {
            xPos = 2687.41;
            yPos = 664.31;
        }
        med0_2_1: AgentNode {
            xPos = 2740.08;
            yPos = 586.45;
        }
        med0_2_2: AgentNode {
            xPos = 2838.09;
            yPos = 560.85;
        }
        med0_2_3: AgentNode {
            xPos = 2757.94;
            yPos = 488.01;
        }
        med0_2_4: AgentNode {
            xPos = 2714.76;
            yPos = 559.47;
        }
        med0_2_5: AgentNode {
            xPos = 2662.95;
            yPos = 477.48;
        }
        con0_3: AgentNode {
            xPos = 2867.32;
            yPos = 426.66;
        }
        med0_3_0: AgentNode {
            xPos = 2786.05;
            yPos = 367.82;
        }
        med0_3_1: AgentNode {
            xPos = 2935.93;
            yPos = 524.96;
        }
        med0_3_2: AgentNode {
            xPos = 2774.61;
            yPos = 392.83;
        }
        med0_3_3: AgentNode {
            xPos = 2941.17;
            yPos = 550.94;
        }
        med0_3_4: AgentNode {
            xPos = 2948.63;
            yPos = 332.27;
        }
        med0_3_5: AgentNode {
            xPos = 2981.56;
            yPos = 423.79;
        }
        con0_4: AgentNode {
            xPos = 2366.07;
            yPos = 197.67;
        }
        med0_4_0: AgentNode {
            xPos = 2281.77;
            yPos = 129.97;
        }
        med0_4_1: AgentNode {
            xPos = 2228.38;
            yPos = 255.78;
        }
        med0_4_2: AgentNode {
            xPos = 2393.17;
            yPos = 154.66;
        }
        med0_4_3: AgentNode {
            xPos = 2371.08;
            yPos = 193.21;
        }
        med0_4_4: AgentNode {
            xPos = 2317.19;
            yPos = 129.07;
        }
        med0_4_5: AgentNode {
            xPos = 2347.53;
            yPos = 52.45;
        }
        con1_0: AgentNode {
            xPos = 649.67;
            yPos = 2049.18;
        }
        med1_0_0: AgentNode {
            xPos = 765.13;
            yPos = 2090.22;
        }
        med1_0_1: AgentNode {
            xPos = 724.51;
            yPos = 2117.31;
        }
        med1_0_2: AgentNode {
            xPos = 629.35;
            yPos = 2084.28;
        }
        med1_0_3: AgentNode {
            xPos = 648.88;
            yPos = 2003.38;
        }
        med1_0_4: AgentNode {
            xPos = 647.65;
            yPos = 2093.1;
        }
        med1_0_5: AgentNode {
            xPos = 606.57;
            yPos = 1979.07;
        }
        con1_1: AgentNode {
            xPos = 1360.89;
            yPos = 2196.76;
        }
        med1_1_0: AgentNode {
            xPos = 1381.14;
            yPos = 2301.59;
        }
        med1_1_1: AgentNode {
            xPos = 1383.96;
            yPos = 2198.52;
        }
        med1_1_2: AgentNode {
            xPos = 1306.37;
            yPos = 2102.46;
        }
        med1_1_3: AgentNode {
            xPos = 1416.25;
            yPos = 2259.66;
        }
        med1_1_4: AgentNode {
            xPos = 1416.15;
            yPos = 2252.75;
        }
        med1_1_5: AgentNode {
            xPos = 1307.48;
            yPos = 2242.06;
        }
        con1_2: AgentNode {
            xPos = 1357.82;
            yPos = 2480.19;
        }
        med1_2_0: AgentNode {
            xPos = 1322.34;
            yPos = 2586.16;
        }
        med1_2_1: AgentNode {
            xPos = 1448.98;
            yPos = 2401.01;
        }
        med1_2_2: AgentNode {
            xPos = 1349.72;
            yPos = 2482.9;
        }
        med1_2_3: AgentNode {
            xPos = 1402.8;
            yPos = 2590.86;
        }
        med1_2_4: AgentNode {
            xPos = 1243.6;
            yPos = 2557.74;
        }
        med1_2_5: AgentNode {
            xPos = 1426.46;
            yPos = 2435.92;
        }
        con1_3: AgentNode {
            xPos = 998.12;
            yPos = 2452.61;
        }
        med1_3_0: AgentNode {
            xPos = 977.11;
            yPos = 2410.43;
        }
        med1_3_1: AgentNode {
            xPos = 975.06;
            yPos = 2591.3;
        }
        med1_3_2: AgentNode {
            xPos = 894.83;
            yPos = 2558.22;
        }
        med1_3_3: AgentNode {
            xPos = 889.22;
            yPos = 2536.1;
        }
        med1_3_4: AgentNode {
            xPos = 952.14;
            yPos = 2463.64;
        }
        med1_3_5: AgentNode {
            xPos = 937.21;
            yPos = 2420.29;
        }
        con1_4: AgentNode {
            xPos = 1759.78;
            yPos = 1875.99;
        }
        med1_4_0: AgentNode {
            xPos = 1618.13;
            yPos = 1849.64;
        }
        med1_4_1: AgentNode {
            xPos = 1618.7;
            yPos = 1833.0;
        }
        med1_4_2: AgentNode {
            xPos = 1745.87;
            yPos = 1814.08;
        }
        med1_4_3: AgentNode {
            xPos = 1722.11;
            yPos = 2008.71;
        }
        med1_4_4: AgentNode {
            xPos = 1880.07;
            yPos = 1963.25;
        }
        med1_4_5: AgentNode {
            xPos = 1885.32;
            yPos = 1909.27;
        }
        con2_0: AgentNode {
            xPos = -1578.48;
            yPos = 1863.25;
        }
        med2_0_0: AgentNode {
            xPos = -1670.55;
            yPos = 1795.25;
        }
        med2_0_1: AgentNode {
            xPos = -1629.23;
            yPos = 1924.82;
        }
        med2_0_2: AgentNode {
            xPos = -1462.99;
            yPos = 1900.68;
        }
        med2_0_3: AgentNode {
            xPos = -1511.21;
            yPos = 1800.53;
        }
        med2_0_4: AgentNode {
            xPos = -1519.13;
            yPos = 1789.65;
        }
        med2_0_5: AgentNode {
            xPos = -1582.16;
            yPos = 1997.42;
        }
        con2_1: AgentNode {
            xPos = -1060.26;
            yPos = 2070.55;
        }
        med2_1_0: AgentNode {
            xPos = -1001.75;
            yPos = 2009.26;
        }
        med2_1_1: AgentNode {
            xPos = -1047.84;
            yPos = 1990.32;
        }
        med2_1_2: AgentNode {
            xPos = -973.39;
            yPos = 2065.21;
        }
        med2_1_3: AgentNode {
            xPos = -1051.01;
            yPos = 2103.61;
        }
        med2_1_4: AgentNode {
            xPos = -1030.27;
            yPos = 2104.52;
        }
        med2_1_5: AgentNode {
            xPos = -1051.19;
            yPos = 2051.27;
        }
        con2_2: AgentNode {
            xPos = -997.24;
            yPos = 2396.36;
        }
        med2_2_0: AgentNode {
            xPos = -914.12;
            yPos = 2499.03;
        }
        med2_2_1: AgentNode {
            xPos = -873.53;
            yPos = 2401.56;
        }
        med2_2_2: AgentNode {
            xPos = -1030.98;
            yPos = 2442.85;
        }
        med2_2_3: AgentNode {
            xPos = -983.41;
            yPos = 2504.31;
        }
        med2_2_4: AgentNode {
            xPos = -995.59;
            yPos = 2490.16;
        }
        med2_2_5: AgentNode {
            xPos = -1081.04;
            yPos = 2467.35;
        }
        con2_3: AgentNode {
            xPos = -1361.66;
            yPos = 1804.6;
        }
        med2_3_0: AgentNode {
            xPos = -1459.85;
            yPos = 1724.32;
        }
        med2_3_1: AgentNode {
            xPos = -1399.43;
            yPos = 1930.17;
        }
        med2_3_2: AgentNode {
            xPos = -1270.37;
            yPos = 1857.2;
        }
        med2_3_3: AgentNode {
            xPos = -1393.59;
            yPos = 1847.12;
        }
        med2_3_4: AgentNode {
            xPos = -1436.43;
            yPos = 1688.09;
        }
        med2_3_5: AgentNode {
            xPos = -1450.42;
            yPos = 1813.29;
        }
        con2_4: AgentNode {
            xPos = -674.27;
            yPos = 1772.67;
        }
        med2_4_0: AgentNode {
            xPos = -751.95;
            yPos = 1691.46;
        }
        med2_4_1: AgentNode {
            xPos = -754.99;
            yPos = 1676.21;
        }
        med2_4_2: AgentNode {
            xPos = -719.59;
            yPos = 1672.31;
        }
        med2_4_3: AgentNode {
            xPos = -672.39;
            yPos = 1643.08;
        }
        med2_4_4: AgentNode {
            xPos = -740.96;
            yPos = 1686.31;
        }
        med2_4_5: AgentNode {
            xPos = -721.91;
            yPos = 1823.11;
        }
        con3_0: AgentNode {
            xPos = -2887.43;
            yPos = -18.66;
        }
        med3_0_0: AgentNode {
            xPos = -2949.89;
            yPos = -7.11;
        }
        med3_0_1: AgentNode {
            xPos = -2842.75;
            yPos = -48.7;
        }
        med3_0_2: AgentNode {
            xPos = -2805.41;
            yPos = -96.28;
        }
        med3_0_3: AgentNode {
            xPos = -2768.4;
            yPos = -93.95;
        }
        med3_0_4: AgentNode {
            xPos = -2849.92;
            yPos = 50.42;
        }
        med3_0_5: AgentNode {
            xPos = -2765.46;
            yPos = -21.22;
        }
        con3_1: AgentNode {
            xPos = -2190.48;
            yPos = 183.12;
        }
        med3_1_0: AgentNode {
            xPos = -2122.32;
            yPos = 230.01;
        }
        med3_1_1: AgentNode {
            xPos = -2164.0;
            yPos = 196.77;
        }
        med3_1_2: AgentNode {
            xPos = -2091.34;
            yPos = 211.47;
        }
        med3_1_3: AgentNode {
            xPos = -2215.27;
            yPos = 79.07;
        }
        med3_1_4: AgentNode {
            xPos = -2248.51;
            yPos = 76.61;
        }
        med3_1_5: AgentNode {
            xPos = -2107.02;
            yPos = 277.43;
        }
        con3_2: AgentNode {
            xPos = -2953.0;
            yPos = -6.6;
        }
        med3_2_0: AgentNode {
            xPos = -2854.72;
            yPos = -30.93;
        }
        med3_2_1: AgentNode {
            xPos = -3005.16;
            yPos = -128.14;
        }
        med3_2_2: AgentNode {
            xPos = -3011.42;
            yPos = -0.58;
        }
        med3_2_3: AgentNode {
            xPos = -2923.25;
            yPos = 68.44;
        }
        med3_2_4: AgentNode {
            xPos = -2918.21;
            yPos = 81.79;
        }
        med3_2_5: AgentNode {
            xPos = -2833.29;
            yPos = 47.93;
        }
        con3_3: AgentNode {
            xPos = -2434.56;
            yPos = -554.57;
        }
        med3_3_0: AgentNode {
            xPos = -2381.97;
            yPos = -508.46;
        }
        med3_3_1: AgentNode {
            xPos = -2321.71;
            yPos = -637.86;
        }
        med3_3_2: AgentNode {
            xPos = -2454.24;
            yPos = -693.02;
        }
        med3_3_3: AgentNode {
            xPos = -2413.07;
            yPos = -476.86;
        }
        med3_3_4: AgentNode {
            xPos = -2529.46;
            yPos = -514.01;
        }
        med3_3_5: AgentNode {
            xPos = -2483.3;
            yPos = -498.6;
        }
        con3_4: AgentNode {
            xPos = -2385.22;
            yPos = -277.26;
        }
        med3_4_0: AgentNode {
            xPos = -2506.94;
            yPos = -336.46;
        }
        med3_4_1: AgentNode {
            xPos = -2334.54;
            yPos = -206.73;
        }
        med3_4_2: AgentNode {
            xPos = -2442.81;
            yPos = -221.59;
        }
        med3_4_3: AgentNode {
            xPos = -2263.55;
            yPos = -347.71;
        }
        med3_4_4: AgentNode {
            xPos = -2358.54;
            yPos = -249.31;
        }
        med3_4_5: AgentNode {
            xPos = -2473.35;
            yPos = -337.08;
        }
        con4_0: AgentNode {
            xPos = -616.36;
            yPos = -2016.06;
        }
        med4_0_0: AgentNode {
            xPos = -536.23;
            yPos = -2095.04;
        }
        med4_0_1: AgentNode {
            xPos = -560.78;
            yPos = -1980.97;
        }
        med4_0_2: AgentNode {
            xPos = -551.82;
            yPos = -2122.11;
        }
        med4_0_3: AgentNode {
            xPos = -752.65;
            yPos = -1966.46;
        }
        med4_0_4: AgentNode {
            xPos = -496.91;
            yPos = -1982.63;
        }
        med4_0_5: AgentNode {
            xPos = -549.56;
            yPos = -2134.87;
        }
        con4_1: AgentNode {
            xPos = -765.39;
            yPos = -1833.09;
        }
        med4_1_0: AgentNode {
            xPos = -874.84;
            yPos = -1879.52;
        }
        med4_1_1: AgentNode {
            xPos = -685.15;
            yPos = -1709.67;
        }
        med4_1_2: AgentNode {
            xPos = -715.04;
            yPos = -1843.29;
        }
        med4_1_3: AgentNode {
            xPos = -869.66;
            yPos = -1867.49;
        }
        med4_1_4: AgentNode {
            xPos = -847.3;
            yPos = -1803.96;
        }
        med4_1_5: AgentNode {
            xPos = -755.48;
            yPos = -1705.28;
        }
        con4_2: AgentNode {
            xPos = -1719.29;
            yPos = -2195.32;
        }
        med4_2_0: AgentNode {
            xPos = -1799.4;
            yPos = -2198.9;
        }
        med4_2_1: AgentNode {
            xPos = -1613.76;
            yPos = -2273.69;
        }
        med4_2_2: AgentNode {
            xPos = -1726.0;
            yPos = -2112.44;
        }
        med4_2_3: AgentNode {
            xPos = -1836.1;
            yPos = -2220.12;
        }
        med4_2_4: AgentNode {
            xPos = -1602.06;
            yPos = -2279.85;
        }
        med4_2_5: AgentNode {
            xPos = -1590.55;
            yPos = -2141.44;
        }
        con4_3: AgentNode {
            xPos = -719.89;
            yPos = -2118.82;
        }
        med4_3_0: AgentNode {
            xPos = -711.32;
            yPos = -2181.56;
        }
        med4_3_1: AgentNode {
            xPos = -714.55;
            yPos = -2079.09;
        }
        med4_3_2: AgentNode {
            xPos = -847.69;
            yPos = -2069.49;
        }
        med4_3_3: AgentNode {
            xPos = -589.51;
            yPos = -2118.1;
        }
        med4_3_4: AgentNode {
            xPos = -831.23;
            yPos = -2025.73;
        }
        med4_3_5: AgentNode {
            xPos = -814.45;
            yPos = -2157.0;
        }
        con4_4: AgentNode {
            xPos = -1396.6;
            yPos = -1537.25;
        }
        med4_4_0: AgentNode {
            xPos = -1518.74;
            yPos = -1509.41;
        }
        med4_4_1: AgentNode {
            xPos = -1468.64;
            yPos = -1652.29;
        }
        med4_4_2: AgentNode {
            xPos = -1410.44;
            yPos = -1490.71;
        }
        med4_4_3: AgentNode {
            xPos = -1352.33;
            yPos = -1427.56;
        }
        med4_4_4: AgentNode {
            xPos = -1376.2;
            yPos = -1518.31;
        }
        med4_4_5: AgentNode {
            xPos = -1469.63;
            yPos = -1439.35;
        }
        con5_0: AgentNode {
            xPos = 1410.28;
            yPos = -1821.88;
        }
        med5_0_0: AgentNode {
            xPos = 1515.87;
            yPos = -1717.49;
        }
        med5_0_1: AgentNode {
            xPos = 1535.91;
            yPos = -1902.0;
        }
        med5_0_2: AgentNode {
            xPos = 1349.52;
            yPos = -1891.33;
        }
        med5_0_3: AgentNode {
            xPos = 1395.85;
            yPos = -1735.49;
        }
        med5_0_4: AgentNode {
            xPos = 1431.37;
            yPos = -1930.43;
        }
        med5_0_5: AgentNode {
            xPos = 1505.92;
            yPos = -1718.27;
        }
        con5_1: AgentNode {
            xPos = 1295.42;
            yPos = -2222.3;
        }
        med5_1_0: AgentNode {
            xPos = 1384.48;
            yPos = -2163.64;
        }
        med5_1_1: AgentNode {
            xPos = 1160.73;
            yPos = -2200.97;
        }
        med5_1_2: AgentNode {
            xPos = 1332.1;
            yPos = -2078.14;
        }
        med5_1_3: AgentNode {
            xPos = 1261.93;
            yPos = -2175.41;
        }
        med5_1_4: AgentNode {
            xPos = 1425.33;
            yPos = -2239.05;
        }
        med5_1_5: AgentNode {
            xPos = 1311.97;
            yPos = -2282.09;
        }
        con5_2: AgentNode {
            xPos = 1626.31;
            yPos = -2250.65;
        }
        med5_2_0: AgentNode {
            xPos = 1489.37;
            yPos = -2221.28;
        }
        med5_2_1: AgentNode {
            xPos = 1644.46;
            yPos = -2233.82;
        }
        med5_2_2: AgentNode {
            xPos = 1547.03;
            yPos = -2322.62;
        }
        med5_2_3: AgentNode {
            xPos = 1766.38;
            yPos = -2298.0;
        }
        med5_2_4: AgentNode {
            xPos = 1540.49;
            yPos = -2153.25;
        }
        med5_2_5: AgentNode {
            xPos = 1752.02;
            yPos = -2232.11;
        }
        con5_3: AgentNode {
            xPos = 877.58;
            yPos = -2033.02;
        }
        med5_3_0: AgentNode {
            xPos = 854.94;
            yPos = -1932.7;
        }
        med5_3_1: AgentNode {
            xPos = 797.47;
            yPos = -2009.08;
        }
        med5_3_2: AgentNode {
            xPos = 904.68;
            yPos = -2028.7;
        }
        med5_3_3: AgentNode {
            xPos = 1014.64;
            yPos = -2015.5;
        }
        med5_3_4: AgentNode {
            xPos = 788.12;
            yPos = -1984.65;
        }
        med5_3_5: AgentNode {
            xPos = 915.47;
            yPos = -2054.81;
        }
        con5_4: AgentNode {
            xPos = 1521.19;
            yPos = -2767.11;
        }
        med5_4_0: AgentNode {
            xPos = 1407.28;
            yPos = -2713.18;
        }
        med5_4_1: AgentNode {
            xPos = 1614.21;
            yPos = -2752.62;
        }
        med5_4_2: AgentNode {
            xPos = 1649.27;
            yPos = -2754.24;
        }
        med5_4_3: AgentNode {
            xPos = 1663.1;
            yPos = -2793.98;
        }
        med5_4_4: AgentNode {
            xPos = 1387.47;
            yPos = -2789.18;
        }
        med5_4_5: AgentNode {
            xPos = 1516.25;
            yPos = -2777.0;
        }

    connections:
        sub0.port++ <--> Fibra <--> sub1.port++;
        sub1.port++ <--> Fibra <--> sub2.port++;
        sub2.port++ <--> Fibra <--> sub3.port++;
        sub3.port++ <--> Fibra <--> sub4.port++;
        sub4.port++ <--> Fibra <--> sub5.port++;
        sub5.port++ <--> Fibra <--> sub0.port++;
        cco.port++ <--> Fibra <--> sub0.port++;
        cco.port++ <--> Fibra <--> sub1.port++;
        sub0.port++ <--> Celular5G <--> con0_0.port++;
        med0_0_1.port++ <--> RFMesh <--> med0_0_5.port++;
        med0_0_1.port++ <--> RFMesh <--> med0_0_4.port++;
        med0_0_0.port++ <--> RFMesh <--> med0_0_3.port++;
        med0_0_0.port++ <--> RFMesh <--> med0_0_2.port++;
        con0_0.port++ <--> RFMesh <--> med0_0_5.port++;
        con0_0.port++ <--> RFMesh <--> med0_0_3.port++;
        sub0.port++ <--> Celular5G <--> con0_1.port++;
        med0_1_1.port++ <--> RFMesh <--> med0_1_5.port++;
        con0_1.port++ <--> RFMesh <--> med0_1_5.port++;
        med0_1_1.port++ <--> RFMesh <--> med0_1_3.port++;
        con0_1.port++ <--> RFMesh <--> med0_1_2.port++;
        med0_1_4.port++ <--> RFMesh <--> med0_1_5.port++;
        med0_1_0.port++ <--> RFMesh <--> med0_1_5.port++;
        sub0.port++ <--> Celular5G <--> con0_2.port++;
        con0_2.port++ <--> RFMesh <--> med0_2_5.port++;
        med0_2_1.port++ <--> RFMesh <--> med0_2_2.port++;
        con0_2.port++ <--> RFMesh <--> med0_2_3.port++;
        med0_2_0.port++ <--> RFMesh <--> med0_2_1.port++;
        med0_2_1.port++ <--> RFMesh <--> med0_2_4.port++;
        con0_2.port++ <--> RFMesh <--> med0_2_4.port++;
        con0_2.port++ <--> RFMesh <--> med0_2_1.port++;
        sub0.port++ <--> Celular5G <--> con0_3.port++;
        med0_3_1.port++ <--> RFMesh <--> med0_3_5.port++;
        med0_3_0.port++ <--> RFMesh <--> med0_3_2.port++;
        con0_3.port++ <--> RFMesh <--> med0_3_2.port++;
        med0_3_4.port++ <--> RFMesh <--> med0_3_5.port++;
        con0_3.port++ <--> RFMesh <--> med0_3_5.port++;
        med0_3_1.port++ <--> RFMesh <--> med0_3_3.port++;
        sub0.port++ <--> Celular5G <--> con0_4.port++;
        med0_4_0.port++ <--> RFMesh <--> med0_4_1.port++;
        med0_4_0.port++ <--> RFMesh <--> med0_4_4.port++;
        con0_4.port++ <--> RFMesh <--> med0_4_3.port++;
        med0_4_2.port++ <--> RFMesh <--> med0_4_3.port++;
        con0_4.port++ <--> RFMesh <--> med0_4_2.port++;
        med0_4_4.port++ <--> RFMesh <--> med0_4_5.port++;
        med0_4_2.port++ <--> RFMesh <--> med0_4_4.port++;
        sub1.port++ <--> Celular5G <--> con1_0.port++;
        con1_0.port++ <--> RFMesh <--> med1_0_4.port++;
        med1_0_3.port++ <--> RFMesh <--> med1_0_5.port++;
        med1_0_0.port++ <--> RFMesh <--> med1_0_1.port++;
        con1_0.port++ <--> RFMesh <--> med1_0_2.port++;
        med1_0_2.port++ <--> RFMesh <--> med1_0_4.port++;
        con1_0.port++ <--> RFMesh <--> med1_0_3.port++;
        med1_0_1.port++ <--> RFMesh <--> med1_0_4.port++;
        sub1.port++ <--> Celular5G <--> con1_1.port++;
        con1_1.port++ <--> RFMesh <--> med1_1_5.port++;
        con1_1.port++ <--> RFMesh <--> med1_1_2.port++;
        con1_1.port++ <--> RFMesh <--> med1_1_1.port++;
        med1_1_1.port++ <--> RFMesh <--> med1_1_4.port++;
        med1_1_0.port++ <--> RFMesh <--> med1_1_3.port++;
        med1_1_3.port++ <--> RFMesh <--> med1_1_4.port++;
        sub1.port++ <--> Celular5G <--> con1_2.port++;
        med1_2_1.port++ <--> RFMesh <--> med1_2_5.port++;
        med1_2_0.port++ <--> RFMesh <--> med1_2_3.port++;
        con1_2.port++ <--> RFMesh <--> med1_2_2.port++;
        med1_2_0.port++ <--> RFMesh <--> med1_2_2.port++;
        med1_2_0.port++ <--> RFMesh <--> med1_2_4.port++;
        con1_2.port++ <--> RFMesh <--> med1_2_5.port++;
        sub1.port++ <--> Celular5G <--> con1_3.port++;
        med1_3_0.port++ <--> RFMesh <--> med1_3_4.port++;
        med1_3_3.port++ <--> RFMesh <--> med1_3_4.port++;
        med1_3_2.port++ <--> RFMesh <--> med1_3_3.port++;
        con1_3.port++ <--> RFMesh <--> med1_3_0.port++;
        con1_3.port++ <--> RFMesh <--> med1_3_4.port++;
        med1_3_0.port++ <--> RFMesh <--> med1_3_5.port++;
        med1_3_4.port++ <--> RFMesh <--> med1_3_5.port++;
        med1_3_1.port++ <--> RFMesh <--> med1_3_2.port++;
        sub1.port++ <--> Celular5G <--> con1_4.port++;
        con1_4.port++ <--> RFMesh <--> med1_4_2.port++;
        con1_4.port++ <--> RFMesh <--> med1_4_3.port++;
        med1_4_1.port++ <--> RFMesh <--> med1_4_2.port++;
        med1_4_0.port++ <--> RFMesh <--> med1_4_1.port++;
        med1_4_4.port++ <--> RFMesh <--> med1_4_5.port++;
        con1_4.port++ <--> RFMesh <--> med1_4_5.port++;
        sub2.port++ <--> Celular5G <--> con2_0.port++;
        med2_0_2.port++ <--> RFMesh <--> med2_0_3.port++;
        med2_0_3.port++ <--> RFMesh <--> med2_0_4.port++;
        med2_0_1.port++ <--> RFMesh <--> med2_0_5.port++;
        con2_0.port++ <--> RFMesh <--> med2_0_0.port++;
        con2_0.port++ <--> RFMesh <--> med2_0_3.port++;
        con2_0.port++ <--> RFMesh <--> med2_0_1.port++;
        sub2.port++ <--> Celular5G <--> con2_1.port++;
        med2_1_0.port++ <--> RFMesh <--> med2_1_2.port++;
        con2_1.port++ <--> RFMesh <--> med2_1_4.port++;
        med2_1_3.port++ <--> RFMesh <--> med2_1_4.port++;
        con2_1.port++ <--> RFMesh <--> med2_1_5.port++;
        med2_1_3.port++ <--> RFMesh <--> med2_1_5.port++;
        med2_1_0.port++ <--> RFMesh <--> med2_1_1.port++;
        con2_1.port++ <--> RFMesh <--> med2_1_3.port++;
        med2_1_1.port++ <--> RFMesh <--> med2_1_5.port++;
        med2_1_4.port++ <--> RFMesh <--> med2_1_5.port++;
        sub2.port++ <--> Celular5G <--> con2_2.port++;
        med2_2_2.port++ <--> RFMesh <--> med2_2_4.port++;
        con2_2.port++ <--> RFMesh <--> med2_2_2.port++;
        med2_2_0.port++ <--> RFMesh <--> med2_2_1.port++;
        med2_2_0.port++ <--> RFMesh <--> med2_2_3.port++;
        med2_2_2.port++ <--> RFMesh <--> med2_2_5.port++;
        med2_2_3.port++ <--> RFMesh <--> med2_2_4.port++;
        sub2.port++ <--> Celular5G <--> con2_3.port++;
        med2_3_1.port++ <--> RFMesh <--> med2_3_3.port++;
        con2_3.port++ <--> RFMesh <--> med2_3_2.port++;
        med2_3_0.port++ <--> RFMesh <--> med2_3_4.port++;
        med2_3_0.port++ <--> RFMesh <--> med2_3_5.port++;
        med2_3_3.port++ <--> RFMesh <--> med2_3_5.port++;
        con2_3.port++ <--> RFMesh <--> med2_3_3.port++;
        sub2.port++ <--> Celular5G <--> con2_4.port++;
        med2_4_2.port++ <--> RFMesh <--> med2_4_3.port++;
        med2_4_0.port++ <--> RFMesh <--> med2_4_4.port++;
        con2_4.port++ <--> RFMesh <--> med2_4_4.port++;
        con2_4.port++ <--> RFMesh <--> med2_4_5.port++;
        med2_4_1.port++ <--> RFMesh <--> med2_4_2.port++;
        med2_4_1.port++ <--> RFMesh <--> med2_4_4.port++;
        med2_4_2.port++ <--> RFMesh <--> med2_4_4.port++;
        med2_4_0.port++ <--> RFMesh <--> med2_4_2.port++;
        med2_4_0.port++ <--> RFMesh <--> med2_4_1.port++;
        sub3.port++ <--> Celular5G <--> con3_0.port++;
        med3_0_2.port++ <--> RFMesh <--> med3_0_3.port++;
        con3_0.port++ <--> RFMesh <--> med3_0_4.port++;
        med3_0_3.port++ <--> RFMesh <--> med3_0_5.port++;
        med3_0_1.port++ <--> RFMesh <--> med3_0_2.port++;
        con3_0.port++ <--> RFMesh <--> med3_0_1.port++;
        con3_0.port++ <--> RFMesh <--> med3_0_0.port++;
        sub3.port++ <--> Celular5G <--> con3_1.port++;
        con3_1.port++ <--> RFMesh <--> med3_1_3.port++;
        med3_1_0.port++ <--> RFMesh <--> med3_1_5.port++;
        med3_1_3.port++ <--> RFMesh <--> med3_1_4.port++;
        med3_1_0.port++ <--> RFMesh <--> med3_1_1.port++;
        con3_1.port++ <--> RFMesh <--> med3_1_1.port++;
        med3_1_0.port++ <--> RFMesh <--> med3_1_2.port++;
        sub3.port++ <--> Celular5G <--> con3_2.port++;
        med3_2_3.port++ <--> RFMesh <--> med3_2_4.port++;
        con3_2.port++ <--> RFMesh <--> med3_2_3.port++;
        con3_2.port++ <--> RFMesh <--> med3_2_2.port++;
        med3_2_4.port++ <--> RFMesh <--> med3_2_5.port++;
        med3_2_0.port++ <--> RFMesh <--> med3_2_5.port++;
        med3_2_1.port++ <--> RFMesh <--> med3_2_2.port++;
        sub3.port++ <--> Celular5G <--> con3_3.port++;
        med3_3_0.port++ <--> RFMesh <--> med3_3_3.port++;
        con3_3.port++ <--> RFMesh <--> med3_3_0.port++;
        med3_3_3.port++ <--> RFMesh <--> med3_3_5.port++;
        con3_3.port++ <--> RFMesh <--> med3_3_2.port++;
        med3_3_4.port++ <--> RFMesh <--> med3_3_5.port++;
        con3_3.port++ <--> RFMesh <--> med3_3_1.port++;
        sub3.port++ <--> Celular5G <--> con3_4.port++;
        med3_4_0.port++ <--> RFMesh <--> med3_4_5.port++;
        con3_4.port++ <--> RFMesh <--> med3_4_5.port++;
        med3_4_1.port++ <--> RFMesh <--> med3_4_4.port++;
        con3_4.port++ <--> RFMesh <--> med3_4_2.port++;
        con3_4.port++ <--> RFMesh <--> med3_4_4.port++;
        med3_4_3.port++ <--> RFMesh <--> med3_4_4.port++;
        sub4.port++ <--> Celular5G <--> con4_0.port++;
        con4_0.port++ <--> RFMesh <--> med4_0_0.port++;
        med4_0_2.port++ <--> RFMesh <--> med4_0_5.port++;
        med4_0_0.port++ <--> RFMesh <--> med4_0_5.port++;
        con4_0.port++ <--> RFMesh <--> med4_0_3.port++;
        med4_0_1.port++ <--> RFMesh <--> med4_0_4.port++;
        med4_0_0.port++ <--> RFMesh <--> med4_0_2.port++;
        con4_0.port++ <--> RFMesh <--> med4_0_1.port++;
        sub4.port++ <--> Celular5G <--> con4_1.port++;
        con4_1.port++ <--> RFMesh <--> med4_1_4.port++;
        med4_1_3.port++ <--> RFMesh <--> med4_1_4.port++;
        med4_1_0.port++ <--> RFMesh <--> med4_1_3.port++;
        con4_1.port++ <--> RFMesh <--> med4_1_5.port++;
        con4_1.port++ <--> RFMesh <--> med4_1_2.port++;
        med4_1_1.port++ <--> RFMesh <--> med4_1_5.port++;
        sub4.port++ <--> Celular5G <--> con4_2.port++;
        med4_2_1.port++ <--> RFMesh <--> med4_2_5.port++;
        con4_2.port++ <--> RFMesh <--> med4_2_1.port++;
        con4_2.port++ <--> RFMesh <--> med4_2_2.port++;
        med4_2_1.port++ <--> RFMesh <--> med4_2_4.port++;
        con4_2.port++ <--> RFMesh <--> med4_2_0.port++;
        med4_2_0.port++ <--> RFMesh <--> med4_2_3.port++;
        sub4.port++ <--> Celular5G <--> con4_3.port++;
        con4_3.port++ <--> RFMesh <--> med4_3_5.port++;
        con4_3.port++ <--> RFMesh <--> med4_3_3.port++;
        con4_3.port++ <--> RFMesh <--> med4_3_1.port++;
        med4_3_2.port++ <--> RFMesh <--> med4_3_4.port++;
        med4_3_2.port++ <--> RFMesh <--> med4_3_5.port++;
        con4_3.port++ <--> RFMesh <--> med4_3_0.port++;
        sub4.port++ <--> Celular5G <--> con4_4.port++;
        med4_4_2.port++ <--> RFMesh <--> med4_4_3.port++;
        con4_4.port++ <--> RFMesh <--> med4_4_1.port++;
        med4_4_2.port++ <--> RFMesh <--> med4_4_5.port++;
        con4_4.port++ <--> RFMesh <--> med4_4_2.port++;
        med4_4_0.port++ <--> RFMesh <--> med4_4_5.port++;
        med4_4_2.port++ <--> RFMesh <--> med4_4_4.port++;
        con4_4.port++ <--> RFMesh <--> med4_4_4.port++;
        sub5.port++ <--> Celular5G <--> con5_0.port++;
        med5_0_2.port++ <--> RFMesh <--> med5_0_4.port++;
        med5_0_3.port++ <--> RFMesh <--> med5_0_5.port++;
        con5_0.port++ <--> RFMesh <--> med5_0_2.port++;
        con5_0.port++ <--> RFMesh <--> med5_0_3.port++;
        med5_0_0.port++ <--> RFMesh <--> med5_0_5.port++;
        med5_0_1.port++ <--> RFMesh <--> med5_0_4.port++;
        sub5.port++ <--> Celular5G <--> con5_1.port++;
        med5_1_0.port++ <--> RFMesh <--> med5_1_2.port++;
        med5_1_1.port++ <--> RFMesh <--> med5_1_3.port++;
        med5_1_0.port++ <--> RFMesh <--> med5_1_4.port++;
        con5_1.port++ <--> RFMesh <--> med5_1_3.port++;
        con5_1.port++ <--> RFMesh <--> med5_1_0.port++;
        con5_1.port++ <--> RFMesh <--> med5_1_5.port++;
        sub5.port++ <--> Celular5G <--> con5_2.port++;
        con5_2.port++ <--> RFMesh <--> med5_2_1.port++;
        med5_2_0.port++ <--> RFMesh <--> med5_2_2.port++;
        con5_2.port++ <--> RFMesh <--> med5_2_2.port++;
        med5_2_1.port++ <--> RFMesh <--> med5_2_5.port++;
        med5_2_0.port++ <--> RFMesh <--> med5_2_4.port++;
        med5_2_3.port++ <--> RFMesh <--> med5_2_5.port++;
        sub5.port++ <--> Celular5G <--> con5_3.port++;
        con5_3.port++ <--> RFMesh <--> med5_3_5.port++;
        med5_3_2.port++ <--> RFMesh <--> med5_3_5.port++;
        con5_3.port++ <--> RFMesh <--> med5_3_2.port++;
        med5_3_1.port++ <--> RFMesh <--> med5_3_4.port++;
        med5_3_0.port++ <--> RFMesh <--> med5_3_4.port++;
        con5_3.port++ <--> RFMesh <--> med5_3_1.port++;
        med5_3_3.port++ <--> RFMesh <--> med5_3_5.port++;
        sub5.port++ <--> Celular5G <--> con5_4.port++;
        con5_4.port++ <--> RFMesh <--> med5_4_1.port++;
        con5_4.port++ <--> RFMesh <--> med5_4_0.port++;
        med5_4_2.port++ <--> RFMesh <--> med5_4_3.port++;
        con5_4.port++ <--> RFMesh <--> med5_4_5.port++;
        med5_4_0.port++ <--> RFMesh <--> med5_4_4.port++;
        med5_4_1.port++ <--> RFMesh <--> med5_4_2.port++;
}
