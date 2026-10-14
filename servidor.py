import logging
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

# Lê o .env antes dos imports abaixo: o dao.banco usa DATABASE_URL logo ao ser importado
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from blueprints import registrar_blueprints
from dao import banco
from servicos.autenticacao import garantir_admin

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# A pasta de ficheiros estáticos (CSS, JS, imagens) chama-se "stetic"
app = Flask(__name__, static_folder='stetic')

# ---------- Configuração ----------
# A chave assina o cookie de sessão. Defina SECRET_KEY no .env
# (ex.: python3 -c "import secrets; print(secrets.token_hex(32))").
_chave = os.environ.get('SECRET_KEY')
if not _chave:
    _chave = secrets.token_hex(32)   # aleatória: as sessões perdem-se ao reiniciar
    app.logger.warning('SECRET_KEY não definida: a usar chave temporária!')
app.config.update(
    SECRET_KEY=_chave,
    SESSION_COOKIE_HTTPONLY=True,      # o JavaScript não consegue ler o cookie
    SESSION_COOKIE_SAMESITE='Lax',     # não é enviado em pedidos de outros sites (anti-CSRF)
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SEGURO') == '1',   # 1 se usar HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    PERMITIR_REGISTO=os.environ.get('PERMITIR_REGISTO', '1') == '1',
)

# Rotas organizadas por área em blueprints/ (ver blueprints/__init__.py)
registrar_blueprints(app)


if __name__ == '__main__':
    banco.criar_tabela()
    garantir_admin()
    app.run(debug=True)
