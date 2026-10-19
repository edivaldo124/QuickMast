// Regras de diagnóstico de mastite: as mesmas de servicos/diagnostico.py no servidor.
// O servidor recalcula sempre e é o diagnóstico dele que fica no histórico; a placa calcula
// para dar o resultado na hora, mesmo sem rede. Mudar os valores nos dois sítios ao mesmo tempo.
// C++ simples, sem Arduino: dá para compilar e testar no PC.
#pragma once

// Condutividade em valor bruto do analogRead (0-1023). Com o resistor de 1 kΩ no módulo TDS,
// o leite normal lê ~300.
const double COND_REF = 300.0;
const double MARGEM_COND = 1.30;        // alerta absoluto: acima de 390
const double LIMIAR_RELATIVO = 0.20;    // alerta relativo: 20% acima da mediana dos outros tetos...
const double DIFERENCA_MINIMA = 40.0;   // ...e pelo menos 40 pontos, para o ruído não dar alarme

struct DiagnosticoTeto {
  bool relativo;   // condutividade acima dos outros tetos
  bool absoluto;   // acima do valor de referência
  bool suspeito;   // um dos dois
};

inline int mediana3(int a, int b, int c) {
  if (a > b) { int t = a; a = b; b = t; }   // a <= b
  if (b > c) b = c;                         // b = min(b, c)
  return a > b ? a : b;                     // max(a, min(b, c))
}

// cond: leituras dos tetos 1 a 4, por ordem. Os cálculos são em double, como no Python,
// para os dois lados darem o mesmo resultado mesmo nos valores de fronteira.
inline void diagnosticar(const int cond[4], DiagnosticoTeto res[4]) {
  for (int i = 0; i < 4; i++) {
    int outros[3], k = 0;
    for (int j = 0; j < 4; j++) {
      if (j != i) outros[k++] = cond[j];
    }
    double med = mediana3(outros[0], outros[1], outros[2]);
    double diff = cond[i] - med;
    double rel = med != 0 ? diff / med : 0;
    res[i].relativo = diff > DIFERENCA_MINIMA && rel > LIMIAR_RELATIVO;
    res[i].absoluto = cond[i] > COND_REF * MARGEM_COND;
    res[i].suspeito = res[i].relativo || res[i].absoluto;
  }
}
