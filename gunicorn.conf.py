"""Configuração do gunicorn em produção. O gunicorn lê este ficheiro sozinho quando é lançado
nesta pasta: gunicorn servidor:app (opções na linha de comandos passam por cima destas)."""

# Só nesta máquina, atrás do Nginx. Nunca 0.0.0.0: com ATRAS_DE_PROXY=1 o cliente
# falaria direto com o gunicorn e forjaria o X-Forwarded-For (e o limite de tentativas).
bind = '127.0.0.1:8000'

# 1 processo com várias threads: o contador de tentativas falhadas (servicos/limite.py)
# vive na memória do processo; com vários workers, cada um teria o seu e o limite multiplicava.
workers = 1
threads = 8

timeout = 30
graceful_timeout = 30
# Pedidos HTTP com cabeçalhos enormes são recusados antes de chegarem ao Flask
limit_request_line = 4094
limit_request_fields = 50

accesslog = '-'   # stdout: o systemd/journald recolhe
errorlog = '-'
