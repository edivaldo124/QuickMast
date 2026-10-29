"""Regras de diagnóstico de mastite.

Espelha a função diagnosticar() do firmware do ESP8266 (secção Diagnóstico de firmware/quickmast_esp8266/quickmast_esp8266.ino).
Ajustar os valores abaixo depois da calibração com dados reais, nos dois sítios ao mesmo tempo.
"""

# Condutividade: valor bruto do analogRead (0-1023). Com o resistor de 1 kΩ no módulo TDS,
# o leite normal lê ~300.
COND_REF = 300.0
MARGIN_COND = 1.30         # alerta absoluto: acima de 390
REL_THRESHOLD = 0.20       # alerta relativo: 20% acima da mediana dos outros tetos...
MIN_ABS_DIFF_COND = 40.0   # ...e pelo menos 40 pontos, para o ruído não dar alarme

# Temperatura: só conta se os 4 tetos a trouxerem (a placa atual não tem o DS18B20)
TEMP_REF = 40.0
MARGIN_TEMP = 1.20
MIN_ABS_DIFF_TEMP = 1.0


def _mediana_outros(valores, idx):
    """Mediana dos outros 3 tetos (ignora o teto idx)."""
    outros = sorted(v for i, v in enumerate(valores) if i != idx)
    return outros[1]


def _relativa(valores, i):
    """Diferença do teto i para a mediana dos outros: (absoluta, relativa)."""
    med = _mediana_outros(valores, i)
    diff = valores[i] - med
    return diff, (diff / med if med != 0 else 0)


def diagnosticar(leituras):
    """Recebe 4 leituras [{'temp': float | None, 'cond': int}, ...] (tetos 1 a 4, por ordem).

    Devolve uma lista de 4 dicts: {'suspeito': bool, 'motivo': str | None}.
    """
    temps = [l.get('temp') for l in leituras]
    conds = [l['cond'] for l in leituras]
    com_temp = all(t is not None for t in temps)
    resultado = []

    for i in range(4):
        motivos = []
        if com_temp:
            diff_t, rel_t = _relativa(temps, i)
            if diff_t > MIN_ABS_DIFF_TEMP and rel_t > REL_THRESHOLD:
                motivos.append('temperatura acima dos outros tetos')
        diff_c, rel_c = _relativa(conds, i)
        if diff_c > MIN_ABS_DIFF_COND and rel_c > REL_THRESHOLD:
            motivos.append('condutividade acima dos outros tetos')
        if conds[i] > COND_REF * MARGIN_COND or (com_temp and temps[i] > TEMP_REF * MARGIN_TEMP):
            motivos.append('acima do valor de referência')

        resultado.append({
            'suspeito': bool(motivos),
            'motivo': '; '.join(motivos) if motivos else None,
        })
    return resultado
