"""Verificação em dois passos (TOTP, RFC 6238): códigos de 6 dígitos de uma app autenticadora."""
import hmac
import re
import time

import pyotp
import segno

EMISSOR = 'QuickMast'
_PASSO_S = 30


def novo_segredo():
    return pyotp.random_base32()   # 160 bits, base32 (32 caracteres)


def qr_svg(segredo, email):
    """Imagem do código QR como data URI (a CSP aceita img-src data:, sem HTML inline)."""
    uri = pyotp.TOTP(segredo).provisioning_uri(name=email, issuer_name=EMISSOR)
    return segno.make(uri, error='m').svg_data_uri(scale=5, border=2)


def segredo_formatado(segredo):
    """Em grupos de 4 para escrever à mão na app: ABCD EFGH ..."""
    return ' '.join(segredo[i:i + 4] for i in range(0, len(segredo), 4))


def verificar(segredo, codigo, ultimo_passo=None):
    """Devolve o passo de tempo do código se for válido (aceita ±30 s de desvio do relógio), senão None.

    Um código já usado não volta a servir: passos iguais ou anteriores a ultimo_passo são recusados.
    """
    codigo = re.sub(r'\s', '', codigo or '')
    if not re.fullmatch(r'\d{6}', codigo):
        return None
    totp = pyotp.TOTP(segredo)
    agora = int(time.time()) // _PASSO_S
    for passo in (agora - 1, agora, agora + 1):
        if ultimo_passo is not None and passo <= ultimo_passo:
            continue
        if hmac.compare_digest(totp.at(passo * _PASSO_S), codigo):
            return passo
    return None
