"""Regras de senha: tamanho e recusa de senhas comuns ou fáceis de adivinhar (ASVS 6.2.4)."""
import os
import re

MIN, MAX = 8, 128

_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'senhas_comuns.txt')
with open(_ARQUIVO, encoding='utf-8') as _f:
    _COMUNS = frozenset(l.strip() for l in _f if l.strip() and not l.startswith('#'))


def problema_senha(senha, email=''):
    """Devolve a mensagem de erro para mostrar ao utilizador, ou None se a senha serve."""
    if not MIN <= len(senha) <= MAX:
        return f'A senha precisa de {MIN} a {MAX} caracteres.'
    s = senha.lower()
    base = re.sub(r'[\d\W_]+$', '', s)   # números e símbolos no fim não ajudam: password123! -> password
    nome_email = email.split('@')[0].lower()
    if (s in _COMUNS or (len(base) >= 4 and base in _COMUNS) or len(set(s)) <= 2
            or (len(nome_email) >= 4 and nome_email in s)):
        return 'Essa senha é muito comum ou fácil de adivinhar. Escolha outra.'
    return None
