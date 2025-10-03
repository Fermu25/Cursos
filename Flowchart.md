flowchart TD
  A[Arranque] --> B[setup()]
  B --> B1[Serial.begin(115200)]
  B1 --> B2[Wire.begin()]
  B2 --> B3[initSD()<br/>sdSPI.begin(pins)<br/>SD.begin(CS, VSPI, 10MHz)<br/>mkdir /logs<br/>crear/checar cabecera]
  B3 --> B4[calibrar TM7711 #1 → zeroOffset1<br/>(promedio 50, extiende signo)]
  B4 --> B5[calibrar TM7711 #2 → zeroOffset2]
  B5 --> B6[iniciarMLX(mlx1, canal 2)<br/>tcaselect(2) → begin() → emisividad 0.98]
  B6 --> B7[iniciarMLX(mlx2, canal 3)<br/>tcaselect(3) → begin() → emisividad 0.98]
  B7 --> B8[sensors1..4.begin()]
  B8 --> C{loop()}

  subgraph CICLO_100ms
    C --> D1[Leer TM7711 #1 raw]
    D1 --> D2[Extiende signo → signed1]
    D2 --> D3[pressure1 = abs((signed1 - zero1) * scale)]
    C --> E1[Leer TM7711 #2 raw]
    E1 --> E2[Extiende signo → signed2]
    E2 --> E3[pressure2 = abs((signed2 - zero2) * scale)]
    C --> F1[tcaselect(2)]
    F1 --> F2[MLX1: obj1, amb1]
    C --> G1[tcaselect(3)]
    G1 --> G2[MLX2: obj2, amb2]
    C --> H1[DS18B20: requestTemperatures() buses 1..4]
    H1 --> H2[Leer ds1..ds4 (index 0)]
    C --> I[Serial.printf: presiones, IR ch2/ch3, T1..T4]
    C --> J[escribirFilaCSV(millis, p1, p2, obj1, amb1, obj2, amb2, ds1..ds4)]
    J --> J1[SD.open APPEND o WRITE + seek]
    J1 --> J2[Escribir línea CSV<br/>flush() + close()]
    J2 --> K[delay(100)]
    K --> C
  end
