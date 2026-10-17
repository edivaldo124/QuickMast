"""Define a senha do admin inicial: pede a senha e guarda só o HASH no .env (ADMIN_SENHA_HASH).

Uso: python3 definir_senha_admin.py
O admin é criado no próximo arranque do servidor, se o ADMIN_EMAIL ainda não existir no banco.
"""
import getpass
import os
import re

from werkzeug.security import generate_password_hash

from servicos.senhas import problema_senha

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

if not os.path.exists(ENV):
    raise SystemExit('Não há .env: copie primeiro o .env.example (cp .env.example .env).')

senha = getpass.getpass('Nova senha do admin: ')
erro = problema_senha(senha)
if erro:
    raise SystemExit(erro)
if getpass.getpass('Repita a senha: ') != senha:
    raise SystemExit('As senhas não coincidem.')

# Aspas simples: o hash tem '$' e assim nem o python-dotenv nem o docker compose o interpretam
nova = f"ADMIN_SENHA_HASH='{generate_password_hash(senha)}'"

linhas = open(ENV).read().splitlines()
antigas = [i for i, l in enumerate(linhas) if re.match(r'\s*ADMIN_SENHA(_HASH)?\s*=', l)]
if antigas:
    linhas[antigas[0]] = nova                     # substitui no mesmo sítio
    for i in reversed(antigas[1:]):               # e apaga ADMIN_SENHA em texto, se houver
        del linhas[i]
else:
    linhas.append(nova)

with open(ENV, 'w') as f:
    f.write('\n'.join(linhas) + '\n')
os.chmod(ENV, 0o600)
print('Hash da senha guardado no .env (ADMIN_SENHA_HASH).')
