"""Separa o utilizador da aplicação do dono do banco (menor privilégio).

Uso (uma vez): python3 configurar_banco_app.py && flask --app servidor iniciar

No .env, o DATABASE_URL atual (dono do banco, superuser no Docker) passa a DATABASE_URL_ADMIN,
usado só pelo "flask --app servidor iniciar". O DATABASE_URL passa a usar o utilizador
quickmast_app, com uma senha aleatória, que só lê e escreve dados (sem criar ou apagar tabelas).
Nenhuma senha é mostrada no ecrã.
"""
import os
import re
import secrets

from dotenv import dotenv_values
from sqlalchemy import make_url

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
UTILIZADOR_APP = 'quickmast_app'

if not os.path.exists(ENV):
    raise SystemExit('Não há .env: copie primeiro o .env.example (cp .env.example .env).')

valores = dotenv_values(ENV)   # com as ${VARIAVEIS} já substituídas
if valores.get('DATABASE_URL_ADMIN'):
    raise SystemExit('O .env já tem DATABASE_URL_ADMIN: nada a fazer. Corra: flask --app servidor iniciar')
if not valores.get('DATABASE_URL'):
    raise SystemExit('O .env não tem DATABASE_URL.')

url_admin = make_url(valores['DATABASE_URL'])
if not url_admin.drivername.startswith('postgresql'):
    raise SystemExit('Só faz sentido com PostgreSQL.')
if url_admin.username == UTILIZADOR_APP:
    raise SystemExit(f'O DATABASE_URL já usa {UTILIZADOR_APP}: falta só o DATABASE_URL_ADMIN do dono.')

url_app = url_admin.set(username=UTILIZADOR_APP, password=secrets.token_urlsafe(32))

linhas = open(ENV).read().splitlines()
i = next(n for n, l in enumerate(linhas) if re.match(r'\s*DATABASE_URL\s*=', l))
valor_original = linhas[i].split('=', 1)[1].strip()
linhas[i:i + 1] = [
    '# Dono do banco: só para "flask --app servidor iniciar" (criar/alterar tabelas)',
    f'DATABASE_URL_ADMIN={valor_original}',
    f'# Aplicação: utilizador {UTILIZADOR_APP}, só lê e escreve dados',
    # Aspas simples: nem o python-dotenv nem o docker compose interpretam o conteúdo
    f"DATABASE_URL='{url_app.render_as_string(hide_password=False)}'",
]
with open(ENV, 'w') as f:
    f.write('\n'.join(linhas) + '\n')
os.chmod(ENV, 0o600)
print(f'.env atualizado. Agora crie o utilizador {UTILIZADOR_APP} no banco: flask --app servidor iniciar')
