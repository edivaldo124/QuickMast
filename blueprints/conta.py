"""A minha conta: trocar a senha e verificação em dois passos (obrigatória para admin)."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from blueprints.auth import MAX_FALHAS_MFA, tentativas, tentativas_mfa
from dao import usuario_dao
from servicos import mfa as totp
from servicos.autenticacao import exigir_login, usuario_atual
from servicos.seguranca import auditar
from servicos.senhas import problema_senha

conta = Blueprint('conta', __name__)

_MAX_FALHAS_SENHA = 5   # senha atual errada, em 5 minutos


@conta.get('/conta')
@exigir_login()
def pagina():
    return render_template('conta.html', erro=None)


@conta.post('/conta/senha')
@exigir_login()
def trocar_senha():
    u = usuario_atual()
    chave = f'senha|{u["id"]}'
    if tentativas.excedido(chave, _MAX_FALHAS_SENHA):
        auditar('senha_bloqueada')
        return render_template('conta.html', erro='Muitas tentativas. Aguarde 5 minutos.'), 429

    atual = request.form.get('senha_atual', '')[:128]
    nova = request.form.get('senha_nova', '')   # sem cortar: problema_senha recusa se passar de 128
    completo = usuario_dao.obter_por_id(u['id'], interno=True)
    if not check_password_hash(completo['senha_hash'], atual):
        tentativas.contar(chave)
        auditar('senha_atual_errada')
        erro = 'A senha atual está errada.'
    elif nova != request.form.get('senha_repetir', ''):
        erro = 'As senhas novas não coincidem.'
    elif nova == atual:
        erro = 'A nova senha tem de ser diferente da atual.'
    else:
        erro = problema_senha(nova, u['email'])
    if erro:
        return render_template('conta.html', erro=erro), 400

    # A versão da sessão sobe: os outros dispositivos saem, este continua com a versão nova
    session['ver'] = usuario_dao.alterar_senha(u['id'], generate_password_hash(nova))
    tentativas.limpar(chave)
    auditar('senha_alterada')
    flash('Senha alterada. As sessões noutros dispositivos foram terminadas.')
    return redirect(url_for('conta.pagina'))


def _pagina_mfa(u, segredo, erro=None, status=200):
    return render_template('mfa.html', modo='configurar', erro=erro,
                           qr=totp.qr_svg(segredo, u['email']),
                           segredo=totp.segredo_formatado(segredo)), status


@conta.get('/conta/mfa')
@exigir_login()
def mfa():
    u = usuario_atual()
    if u['mfa_ativo']:
        return redirect(url_for('conta.pagina'))
    # O mesmo segredo até confirmar (recarregar a página não troca o QR já lido)
    segredo = session.get('mfa_novo') or totp.novo_segredo()
    session['mfa_novo'] = segredo
    return _pagina_mfa(u, segredo)


@conta.post('/conta/mfa')
@exigir_login()
def mfa_post():
    u = usuario_atual()
    segredo = session.get('mfa_novo')
    if u['mfa_ativo'] or not segredo:
        return redirect(url_for('conta.mfa'))
    chave = f'mfa|{u["id"]}'
    if tentativas_mfa.excedido(chave, MAX_FALHAS_MFA):
        auditar('mfa_bloqueado', alvo=u['id'])
        return _pagina_mfa(u, segredo, 'Muitas tentativas. Aguarde e tente mais tarde.', 429)

    passo = totp.verificar(segredo, request.form.get('codigo', '')[:20])
    if passo is None:
        tentativas_mfa.contar(chave)
        return _pagina_mfa(u, segredo, 'Código inválido. Confira se a hora do telemóvel está certa '
                                       'e escreva o código que a app mostra agora.', 400)

    versao = usuario_dao.ativar_mfa(u['id'], segredo, passo)
    session.pop('mfa_novo', None)
    if versao is not None:
        session['ver'] = versao   # sessões abertas só com a senha (noutros dispositivos) terminam
        auditar('mfa_ativado')
        flash('Verificação em dois passos ativada. O próximo login vai pedir o código da app.')
    return redirect(url_for('conta.pagina'))
