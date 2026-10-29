import logging
import os
import re
import secrets
from datetime import timedelta

import click
from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

# Lê o .env antes dos imports abaixo: o dao.banco usa DATABASE_URL logo ao ser importado
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from blueprints import registrar_blueprints
from dao import banco, usuario_dao
from servicos.autenticacao import garantir_admin, negar_por_omissao
from servicos.seguranca import FormatoJSON, configurar_seguranca, mascarar_email
from servicos.senhas import problema_senha

# Modo debug só no seu PC (FLASK_DEBUG=1): o depurador do Werkzeug executa código Python
DEBUG = os.environ.get('FLASK_DEBUG') == '1'

# Logs em JSON, um evento por linha (fácil de filtrar no journald/Fail2ban). LOG_JSON=0 volta ao texto;
# no modo debug o texto é o padrão. Eventos de segurança suspeitos saem com nível WARNING.
_saida = logging.StreamHandler()
if os.environ.get('LOG_JSON', '0' if DEBUG else '1') == '1':
    _saida.setFormatter(FormatoJSON())
else:
    _saida.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[_saida])

# A pasta de ficheiros estáticos (CSS, JS, imagens) chama-se "stetic"
app = Flask(__name__, static_folder='stetic')

# Atrás do Nginx (ATRAS_DE_PROXY=1): o IP real do cliente vem no X-Forwarded-For.
# Sem isto, todos os pedidos parecem vir do Nginx e o limite de tentativas do login fica partilhado.
# O Host não vem do X-Forwarded-Host (o cliente podia forjá-lo): o Nginx passa-o com proxy_set_header Host.
# O gunicorn deve escutar só em 127.0.0.1, senão o cliente fala direto e forja o X-Forwarded-For.
if os.environ.get('ATRAS_DE_PROXY') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# ---------- Configuração ----------
# A chave assina o cookie de sessão. Defina SECRET_KEY no .env
# (ex.: python3 -c "import secrets; print(secrets.token_hex(32))").
_chave = os.environ.get('SECRET_KEY')
if not _chave:
    if not DEBUG:
        raise RuntimeError('SECRET_KEY não definida no .env (obrigatória fora do modo debug).')
    _chave = secrets.token_hex(32)   # aleatória: as sessões perdem-se ao reiniciar
    app.logger.warning('SECRET_KEY não definida: a usar chave temporária!')

# Placa de verdade no PC, sem o Nginx da produção: o /read da página do úbere é repassado para ela
_placa_url = os.environ.get('PLACA_URL', '').strip().rstrip('/')
if _placa_url not in ('', 'auto') and not re.fullmatch(r'http://[\w.-]+(:\d{1,5})?', _placa_url):
    raise RuntimeError('PLACA_URL tem de ser "auto" ou http://<ip da placa> (a placa não tem HTTPS).')

app.config.update(
    SECRET_KEY=_chave,
    SESSION_COOKIE_HTTPONLY=True,      # o JavaScript não consegue ler o cookie
    SESSION_COOKIE_SAMESITE='Lax',     # não é enviado em pedidos de outros sites (anti-CSRF)
    # Só por HTTPS. Por omissão ligado; COOKIE_SEGURO=0 apenas no seu PC (http://localhost)
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SEGURO', '0' if DEBUG else '1') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=64 * 1024,      # nenhum pedido legítimo passa de poucos KB
    # Registo público desligado por omissão. Ainda não há "criar utilizador" no painel do admin:
    # para dar acesso a alguém, ligar PERMITIR_REGISTO=1 só enquanto a pessoa cria a conta.
    PERMITIR_REGISTO=os.environ.get('PERMITIR_REGISTO', '0') == '1',
    # Simulador do sensor em /read: só no seu PC. Em produção o /read é do ESP8266.
    SIMULADOR_SENSOR=os.environ.get('SIMULADOR_SENSOR', '1' if DEBUG else '0') == '1',
    # http://<ip da placa>, ou "auto" para a procurar na rede local (blueprints/sensor.py).
    # Em produção fica vazio: quem repassa o /read para o ESP8266 é o Nginx.
    PLACA_URL=_placa_url,
)

configurar_seguranca(app)
negar_por_omissao(app)

# Rotas organizadas por área em blueprints/ (ver blueprints/__init__.py)
registrar_blueprints(app)


@app.cli.command('iniciar')
def iniciar():
    """Cria/atualiza as tabelas, o utilizador da aplicação no banco e o admin inicial.
    Em produção, depois de cada atualização: flask --app servidor iniciar"""
    banco.criar_tabela()
    garantir_admin()


@app.cli.command('redefinir-mfa')
@click.argument('email')
def redefinir_mfa(email):
    """Apaga a verificação em dois passos de uma conta (telemóvel perdido).
    Uso: flask --app servidor redefinir-mfa EMAIL. No próximo login, a pessoa configura de novo."""
    email = email.strip().lower()
    if not usuario_dao.redefinir_mfa(email):
        raise click.ClickException('Não há nenhum utilizador com esse email.')
    logging.getLogger('quickmast.seguranca').warning('mfa_redefinido email=%s (linha de comandos)',
                                                     mascarar_email(email))
    click.echo('Verificação em dois passos apagada e sessões terminadas. Configure-a no próximo login.')


@app.cli.command('redefinir-senha')
@click.argument('email')
def redefinir_senha(email):
    """Troca a senha de uma conta que já existe (ex.: o admin, depois de mudar o ADMIN_SENHA_HASH:
    o garantir_admin só usa esse hash ao criar a conta, nunca a atualiza).
    Uso: flask --app servidor redefinir-senha EMAIL. Pede a senha no terminal; as sessões abertas terminam."""
    email = email.strip().lower()
    u = usuario_dao.obter_por_email(email)
    if u is None:
        raise click.ClickException('Não há nenhum utilizador com esse email.')
    nome_email = email.split('@')[0]
    while True:
        senha = click.prompt('Nova senha', hide_input=True, confirmation_prompt='Repita a senha')
        erro = problema_senha(senha, email)
        if erro is None:
            break
        click.echo(erro, err=True)
        click.echo('Recusadas: palavras comuns, mesmo com números ou símbolos no fim (quickmast2026, admin123); '
                   'uma senha que repete só 1 ou 2 caracteres'
                   + (f"; e qualquer senha que contenha '{nome_email}' (a parte do email antes do @)"
                      if len(nome_email) >= 4 else '')
                   + '.\nCostuma passar: 3 palavras sem relação, separadas por hífen, ou 12+ caracteres misturados.',
                   err=True)
    usuario_dao.alterar_senha(u['id'], generate_password_hash(senha))
    logging.getLogger('quickmast.seguranca').warning('senha_redefinida email=%s (linha de comandos)',
                                                     mascarar_email(email))
    click.echo('Senha trocada e sessões terminadas.')


if __name__ == '__main__':
    banco.criar_tabela()
    garantir_admin()
    app.run(debug=DEBUG)
