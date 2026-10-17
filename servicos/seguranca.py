"""Proteções globais: origem dos pedidos (anti-CSRF), cabeçalhos de segurança e auditoria."""
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import abort, request, session

log = logging.getLogger('quickmast.seguranca')

# Eventos que merecem alerta (Fail2ban, monitorização): saem com nível WARNING
_ALERTAS = {'login_bloqueado', 'mfa_bloqueado', 'mfa_falhou', 'senha_bloqueada', 'origem_recusada',
            'acesso_negado', 'conta_sob_ataque'}


class FormatoJSON(logging.Formatter):
    """Uma linha JSON por registo: data UTC, nível, origem e, na auditoria, os campos do evento."""
    def format(self, r):
        campos = getattr(r, 'campos', None) or {}
        # Os campos do evento vêm primeiro: um campo com valor do cliente (ex.: origem = cabeçalho
        # Origin) nunca tapa a data, o nível ou o logger do próprio registo
        d = {**campos,
             'ts': datetime.fromtimestamp(r.created, timezone.utc).isoformat(timespec='milliseconds'),
             'nivel': r.levelname, 'logger': r.name, 'msg': campos.get('evento') or r.getMessage()}
        if r.exc_info:
            d['excecao'] = self.formatException(r.exc_info)
        return json.dumps(d, ensure_ascii=False, default=str)   # o JSON escapa quebras de linha

_METODOS_SEGUROS = {'GET', 'HEAD', 'OPTIONS'}

# Só recursos do próprio servidor. style-src-attr: o painel usa style="--alfa: ..."
CSP = '; '.join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


def mascarar_email(email):
    """a***@exemplo.com: dá para investigar ataques sem guardar o email inteiro no log."""
    nome, _, dominio = (email or '').partition('@')
    return f'{nome[:1]}***@{dominio}' if dominio else '***'


def auditar(evento, **dados):
    """Regista um evento de segurança. Nunca passar senhas, hashes, códigos MFA ou cookies."""
    if 'email' in dados:
        dados['email'] = mascarar_email(dados['email'])
    campos = {'evento': evento, 'ip': request.remote_addr, 'uid': session.get('uid'), **dados}
    extra = ' '.join(f'{k}={v!r}' for k, v in dados.items())   # !r: sem quebras de linha no log
    nivel = logging.WARNING if evento in _ALERTAS else logging.INFO
    log.log(nivel, '%s ip=%s uid=%s %s', evento, campos['ip'], campos['uid'], extra,
            extra={'campos': campos})


def _origem_valida():
    """O browser diz de onde vem o pedido; um site alheio não consegue falsificar estes cabeçalhos."""
    site = request.headers.get('Sec-Fetch-Site')
    if site is not None:
        return site in ('same-origin', 'none')
    origem = request.headers.get('Origin')
    if origem is not None:
        return urlparse(origem).netloc == request.host
    return True   # sem nenhum dos dois não é um browser, e sem browser não há CSRF


def configurar_seguranca(app):
    @app.before_request
    def bloquear_pedidos_de_outros_sites():
        if request.method not in _METODOS_SEGUROS and not _origem_valida():
            auditar('origem_recusada', rota=request.path,
                    origem=request.headers.get('Origin'), site=request.headers.get('Sec-Fetch-Site'))
            abort(403)

    @app.after_request
    def cabecalhos_de_seguranca(resp):
        h = resp.headers
        h.setdefault('Content-Security-Policy', CSP)
        h.setdefault('X-Content-Type-Options', 'nosniff')
        h.setdefault('X-Frame-Options', 'DENY')
        h.setdefault('Referrer-Policy', 'same-origin')
        h.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if app.config['SESSION_COOKIE_SECURE']:
            h.setdefault('Strict-Transport-Security', 'max-age=31536000')
        if request.path.startswith('/api/') or request.path == '/exportar.csv':
            h.setdefault('Cache-Control', 'no-store')   # dados de utilizadores não ficam em caches
        return resp
