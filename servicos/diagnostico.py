"""Regras de diagnóstico de mastite.

A comparação entre tetos espelha a função diagnosticar() do firmware do ESP8266 (secção Diagnóstico
de firmware/quickmast_esp8266/quickmast_esp8266.ino): mudar esses valores nos dois sítios ao mesmo tempo.
A comparação com o histórico da vaca só existe aqui (a placa não guarda histórico).
Ajustar os valores abaixo depois da calibração com dados reais.
"""
from statistics import median

# Condutividade: valor bruto do analogRead (0-1023). Com o resistor de 1 kΩ no módulo TDS,
# o leite normal lê ~300, mas cada vaca tem o seu nível (raça, fase da lactação, gordura do leite):
# não há um valor fixo que sirva para todas. Por isso cada teto é comparado com os outros tetos
# da mesma vaca e com o histórico dessa vaca, nunca com um número fixo.
REL_THRESHOLD = 0.20       # entre tetos: 20% acima da mediana dos outros tetos...
MIN_ABS_DIFF_COND = 40.0   # ...e pelo menos 40 pontos, para o ruído não dar alarme (vale também no histórico)

# Histórico: cada teto contra a sua linha de base, feita só com as leituras sadias desse teto
BASE_TESTES = 5            # linha de base = mediana das últimas 5 leituras sadias do teto
BASE_MINIMO = 3            # com menos de 3 leituras sadias, o teto ainda não tem linha de base
BASE_THRESHOLD = 0.15      # alerta: 15% acima da linha de base (e pelo menos MIN_ABS_DIFF_COND)

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


def linha_de_base(anteriores):
    """Mediana das últimas leituras sadias de um teto (da mais recente para a mais antiga),
    ou None se ainda forem menos de BASE_MINIMO."""
    if len(anteriores) < BASE_MINIMO:
        return None
    return float(median(anteriores[:BASE_TESTES]))


def diagnosticar(leituras, historico=None):
    """Recebe 4 leituras [{'temp': float | None, 'cond': int}, ...] (tetos 1 a 4, por ordem) e o
    histórico da vaca: 4 listas com as condutividades das leituras sadias anteriores de cada teto,
    da mais recente para a mais antiga. Vaca nova (sem histórico): só vale a comparação entre tetos.

    Devolve uma lista de 4 dicts: {'suspeito': bool, 'motivo': str | None, 'base': float | None}.
    """
    historico = historico or [[], [], [], []]
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
        base = linha_de_base(historico[i])
        if base is not None:
            diff_b = conds[i] - base
            if diff_b > MIN_ABS_DIFF_COND and (diff_b / base if base else 0) > BASE_THRESHOLD:
                motivos.append('acima do histórico desta vaca')
        if com_temp and temps[i] > TEMP_REF * MARGIN_TEMP:
            motivos.append('temperatura acima da referência')

        resultado.append({
            'suspeito': bool(motivos),
            'motivo': '; '.join(motivos) if motivos else None,
            'base': base,
        })
    return resultado
