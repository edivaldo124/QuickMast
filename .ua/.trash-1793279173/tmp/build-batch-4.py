import json
nodes=[]; edges=[]
def file_node(path, summary, tags, cx, notes=None):
    n={"id":f"file:{path}","type":"file","name":path.split('/')[-1],"filePath":path,"summary":summary,"tags":tags,"complexity":cx}
    if notes: n["languageNotes"]=notes
    nodes.append(n)
def fn(path,name,rng,summary,tags,cx="simple",kind="function"):
    nodes.append({"id":f"{kind}:{path}:{name}","type":kind,"name":name,"filePath":path,"lineRange":rng,"summary":summary,"tags":tags,"complexity":cx})
    edges.append({"source":f"file:{path}","target":f"{kind}:{path}:{name}","type":"contains","direction":"forward","weight":1.0})
def e(s,t,ty,w):
    edges.append({"source":s,"target":t,"type":ty,"direction":"forward","weight":w})

A="blueprints/auth.py"; C="blueprints/conta.py"; D="definir_senha_admin.py"; L="servicos/limite.py"; S="servicos/senhas.py"

file_node(A,"Blueprint Flask 'auth' com as páginas de entrada: login por senha, segundo passo MFA (TOTP), registo e logout. Aplica limites de tentativas por IP, e-mail e conta, mitiga open redirect e user enumeration (hash falso) e audita eventos de segurança.",
 ["blueprint","autenticacao","seguranca","mfa","rate-limiting"],"complex",
 "Usa decoradores de rota do Flask 2 (@auth.get/@auth.post), um context processor global e estado de sessão em cookie assinado (uid, ver, mfa_uid, mfa_ate) com versão de sessão para invalidar cookies copiados.")
file_node(C,"Blueprint Flask 'conta' (área 'A minha conta'): troca de senha com verificação da senha atual e limite de tentativas, e configuração da verificação em dois passos (TOTP) com QR code. Reaproveita os limitadores definidos em blueprints/auth.py.",
 ["blueprint","conta-usuario","mfa","seguranca","troca-de-senha"],"moderate")
file_node(D,"Script de linha de comando que pede a senha do admin inicial, valida-a com problema_senha e grava apenas o hash (ADMIN_SENHA_HASH) no .env, substituindo qualquer ADMIN_SENHA em texto simples e restringindo o arquivo a chmod 600.",
 ["script","cli","admin","seguranca","configuracao"],"simple",
 "Script executado no nível do módulo (sem funções). O hash é escrito entre aspas simples para que python-dotenv e docker compose não interpretem o '$'.")
file_node(L,"Limitador em memória de tentativas falhadas numa janela de tempo deslizante, protegido por threading.Lock; usado no login, no código MFA e na troca de senha. Pensado para 1 worker gunicorn com threads; para vários servidores deve ser trocado por Flask-Limiter + Redis.",
 ["rate-limiting","seguranca","utilitario","thread-safe"],"simple")
file_node(S,"Regras de qualidade de senha (tamanho de 8 a 128 e recusa de senhas comuns ou derivadas do e-mail), carregando a lista servicos/senhas_comuns.txt na importação; implementa a recomendação ASVS 6.2.4.",
 ["validacao","senhas","seguranca","utilitario"],"simple")

# auth.py functions
fn(A,"injetar_usuario",[36,38],"Context processor global que disponibiliza a variável 'usuario' (usuário autenticado ou None) em todos os templates.",["context-processor","template","autenticacao"])
fn(A,"_destino_seguro",[41,46],"Valida o parâmetro 'next' do login aceitando só caminhos internos e devolvendo '/ubere' caso contrário, para evitar open redirect.",["seguranca","open-redirect","validacao"])
fn(A,"_bloqueado",[49,51],"Indica se o IP (ou a combinação IP+e-mail) excedeu o limite de falhas na janela atual.",["rate-limiting","seguranca"])
fn(A,"_login_falhou",[54,58],"Regista uma falha de login nos contadores por IP, IP+e-mail e conta, audita o evento e emite alerta 'conta_sob_ataque' à 20.ª falha.",["rate-limiting","auditoria","seguranca"])
fn(A,"_iniciar_sessao",[61,65],"Cria a sessão autenticada: limpa a sessão antiga, grava uid e versão da sessão e a torna permanente.",["sessao","autenticacao","seguranca"])
fn(A,"login",[73,77],"Rota GET /login: redireciona quem já está autenticado ou renderiza a página de login.",["rota","api-handler","autenticacao"])
fn(A,"login_post",[81,110],"Rota POST /login: normaliza e limita as entradas, aplica limites de tentativas, compara a senha em tempo constante (hash falso se o e-mail não existe) e inicia a sessão ou o fluxo MFA.",["rota","api-handler","autenticacao","seguranca"],"moderate")
fn(A,"_mfa_pendente",[113,119],"Devolve o usuário que acertou a senha e ainda não confirmou o código MFA, ou None se não há pendência ou se ela expirou.",["mfa","sessao","autenticacao"])
fn(A,"login_mfa",[127,130],"Rota GET /login/mfa: mostra a página do código MFA se há login pendente, senão volta ao login.",["rota","api-handler","mfa"])
fn(A,"login_mfa_post",[134,155],"Rota POST /login/mfa: verifica o código TOTP com limites de tentativas e proteção contra reuso do passo, e conclui o login auditando o resultado.",["rota","api-handler","mfa","seguranca"],"moderate")
fn(A,"registrar",[159,184],"Rota POST /registrar: valida nome, e-mail e senha, impede e-mails duplicados, cria o usuário com hash da senha e inicia a sessão (só se PERMITIR_REGISTO estiver ativo).",["rota","api-handler","registo","validacao"],"moderate")
fn(A,"logout",[188,194],"Rota POST /logout: audita, encerra as sessões do usuário no banco (invalidando cópias do cookie) e limpa a sessão.",["rota","api-handler","sessao","autenticacao"])

# conta.py
fn(C,"pagina",[19,20],"Rota GET /conta: renderiza a página 'A minha conta' para o usuário autenticado.",["rota","api-handler","conta-usuario"])
fn(C,"trocar_senha",[25,53],"Rota POST /conta/senha: confere a senha atual, valida a nova, altera o hash e sobe a versão da sessão para derrubar os outros dispositivos, com limite de tentativas e auditoria.",["rota","api-handler","troca-de-senha","seguranca"],"moderate")
fn(C,"_pagina_mfa",[56,59],"Renderiza a página de configuração MFA com o QR code SVG e o segredo formatado para digitação manual.",["mfa","template","helper"])
fn(C,"mfa",[64,71],"Rota GET /conta/mfa: gera (e mantém na sessão até confirmar) um novo segredo TOTP e mostra o QR code de configuração.",["rota","api-handler","mfa"])
fn(C,"mfa_post",[76,98],"Rota POST /conta/mfa: confirma o código TOTP com limite de tentativas, ativa o MFA no banco e atualiza a versão da sessão para encerrar sessões abertas só com a senha.",["rota","api-handler","mfa","seguranca"],"moderate")

# limite.py / senhas.py
fn(L,"Limitador",[10,43],"Contador thread-safe de falhas por chave numa janela deslizante, com métodos quantas, excedido, contar (várias chaves de uma vez) e limpar, e limpeza de chaves expiradas quando passa de max_chaves.",["rate-limiting","classe","thread-safe","seguranca"],"moderate","class")
fn(S,"problema_senha",[12,22],"Devolve a mensagem de erro se a senha não cumpre o tamanho, é comum, tem poucos caracteres distintos ou contém o nome do e-mail; devolve None se a senha serve.",["validacao","senhas","seguranca"],"simple")

# imports (1:1 with batchImportData)
imp={A:["servicos/autenticacao.py","servicos/limite.py","servicos/seguranca.py","servicos/senhas.py"],
     C:[A,"servicos/autenticacao.py","servicos/seguranca.py","servicos/senhas.py"],
     D:[S],L:[],S:[]}
for s,ts in imp.items():
    for t in ts: e(f"file:{s}",f"file:{t}","imports",0.7)

# exports
e(f"file:{L}",f"class:{L}:Limitador","exports",0.8)
e(f"file:{S}",f"function:{S}:problema_senha","exports",0.8)

# calls
UA="function:servicos/autenticacao.py:usuario_atual"
AUD="function:servicos/seguranca.py:auditar"
EX="function:servicos/autenticacao.py:exigir_login"
PS=f"function:{S}:problema_senha"
for f_ in ["injetar_usuario","login","logout"]: e(f"function:{A}:{f_}",UA,"calls",0.8)
for f_ in ["_login_falhou","login_post","login_mfa_post","logout"]: e(f"function:{A}:{f_}",AUD,"calls",0.8)
e(f"function:{A}:registrar",PS,"calls",0.8)
e(f"file:{A}",f"class:{L}:Limitador","calls",0.8)
for f_ in ["trocar_senha","mfa","mfa_post"]: e(f"function:{C}:{f_}",UA,"calls",0.8)
for f_ in ["trocar_senha","mfa_post"]: e(f"function:{C}:{f_}",AUD,"calls",0.8)
e(f"function:{C}:trocar_senha",PS,"calls",0.8)
e(f"file:{C}",EX,"calls",0.8)
e(f"file:{D}",PS,"calls",0.8)
# depends_on (project modules not resolved in batchImportData)
for src in (A,C):
    e(f"file:{src}","file:dao/usuario_dao.py","depends_on",0.6)
    e(f"file:{src}","file:servicos/mfa.py","depends_on",0.6)

json.dump({"nodes":nodes,"edges":edges},open(".ua/intermediate/batch-4.json","w"),ensure_ascii=False,indent=1)
ids={n["id"] for n in nodes}
assert len(ids)==len(nodes)
print(len(nodes),len(edges))
print(sum(1 for x in edges if x["type"]=="imports"), sum(len(v) for v in imp.values()))
for x in edges:
    assert x["source"]!=x["target"]
    for k in("source","target"):
        if x[k] not in ids: print("external",x[k])
