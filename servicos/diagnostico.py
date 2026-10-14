"""Regras de diagnóstico de mastite.

Espelha a função calcularResultados() do firmware do ESP8266.
Ajustar os valores abaixo depois da calibração com dados reais.
"""

TEMP_REF = 40.0
COND_REF = 400.0
MARGIN = 1.20
REL_THRESHOLD = 0.20
MIN_ABS_DIFF_TEMP = 1.0
MIN_ABS_DIFF_COND = 50.0


def _mediana_outros(valores, idx):
    """Mediana dos outros 3 tetos (ignora o teto idx)."""
    outros = sorted(v for i, v in enumerate(valores) if i != idx)
    return outros[1]


def diagnosticar(leituras):
    """Recebe 4 leituras [{'temp':..,'cond':..}, ...] (tetos 1 a 4, por ordem).

    Devolve uma lista de 4 dicts: {'suspeito': bool, 'motivo': str | None}.
    """
    temps = [l['temp'] for l in leituras]
    conds = [l['cond'] for l in leituras]
    resultado = []

    for i in range(4):
        med_t = _mediana_outros(temps, i)
        med_c = _mediana_outros(conds, i)
        diff_t = temps[i] - med_t
        diff_c = conds[i] - med_c
        rel_t = diff_t / med_t if med_t != 0 else 0
        rel_c = diff_c / med_c if med_c != 0 else 0

        motivos = []
        if diff_t > MIN_ABS_DIFF_TEMP and rel_t > REL_THRESHOLD:
            motivos.append('temperatura acima dos outros tetos')
        if diff_c > MIN_ABS_DIFF_COND and rel_c > REL_THRESHOLD:
            motivos.append('condutividade acima dos outros tetos')
        if temps[i] > TEMP_REF * MARGIN or conds[i] > COND_REF * MARGIN:
            motivos.append('acima do valor de referência')

        resultado.append({
            'suspeito': bool(motivos),
            'motivo': '; '.join(motivos) if motivos else None,
        })
    return resultado

