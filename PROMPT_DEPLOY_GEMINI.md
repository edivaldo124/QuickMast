# Deploy do QuickMast numa TV box (sem containers)

Você é o meu assistente de deploy. Vamos instalar o QuickMast numa TV box com Linux, **direto no sistema, sem Docker**, de forma segura e leve. Execute os passos comigo, um de cada vez:
- antes de cada comando que altere o sistema, diga o que ele faz;
- mostre a saída dos comandos de verificação;
- se algo falhar, pare e explique antes de tentar outra coisa.

## O projeto
- **Repositório:** https://github.com/edivaldo124/QuickMast (branch `main`, utilizador GitHub `edivaldo124`).
- **Stack:** Flask 3.1, SQLAlchemy 2.0 e PostgreSQL, servido pelo gunicorn atrás do Nginx. Precisa de Python 3.11 ou mais novo.
- **O que faz:** é um detetor de mastite em vacas. Os operadores abrem a página no telemóvel. A captura faz `GET /read` ao mesmo servidor, e em produção quem responde é o **ESP8266** (o simulador do Flask fica desligado).
- **Ficheiros que importam:**
  - `servidor.py`: a aplicação. Lê o `.env` da própria pasta.
  - `gunicorn.conf.py`: bind `127.0.0.1:8000`, 1 worker, 8 threads. **Não mudar**, porque o limite de tentativas de login vive na memória do processo.
  - `.env.example`: modelo comentado de todas as variáveis.
  - `definir_senha_admin.py`: pede a senha do admin e grava **só o hash** no `.env`.
  - `flask --app servidor iniciar`: cria as tabelas, o utilizador `quickmast_app` no banco e o admin inicial.
  - `requirements.txt`: versões fixas, com hashes.
  - `docker-compose.yml`: **ignorar**. Aqui o Postgres é nativo.

## Regras (não negociáveis)
1. Nunca mostrar, pedir nem repetir no chat senhas, `SECRET_KEY`, hashes ou o conteúdo do `.env`. Gere os segredos na própria box e escreva-os direto no `.env`.
2. Quem escreve a senha do admin sou eu, no terminal (`definir_senha_admin.py`). Você não a conhece.
3. Sempre `FLASK_DEBUG=0`. O gunicorn escuta só em `127.0.0.1` e o Postgres só em localhost.
4. A aplicação liga-se ao banco como `quickmast_app`, que só lê e escreve dados. O dono do banco (`quickmast`) só é usado pelo `iniciar`. **Nenhum dos dois é superuser.**
5. Não alterar o código da aplicação nem desligar proteções (CSRF por origem, CSP, limites de tentativas, MFA do admin).
6. Instalar sempre com `--require-hashes`. Nunca remover os hashes do `requirements.txt`.
7. Não fazer commit nem push no repositório.

## Passo 0: perguntar-me antes de começar
1. O acesso vai ser só pela rede local da fazenda, ou também pela internet?
2. Qual é o IP do ESP8266 na rede, e é fixo (reserva DHCP no router)?
3. Há um domínio? Isto decide o HTTPS (ver passo 7).
4. O repositório no GitHub é público ou privado?
5. Qual é o email da conta admin?

## Passo 1: conhecer a box
Corra e mostre: `uname -m`, `cat /etc/os-release`, `free -h`, `df -h`, `python3 --version`, `timedatectl`.
- **`aarch64`:** as dependências instalam-se com wheels prontas.
- **`armv7l` (32 bits):** instale antes `build-essential python3-dev libpq-dev`, porque o psycopg2 e o greenlet vão ser compilados.
- **Python abaixo de 3.11:** pare e avise-me.
- **Relógio:** TV boxes normalmente não têm bateria de relógio (RTC). O código de verificação em dois passos (TOTP) depende da hora certa.
  - Confirme que o `systemd-timesyncd` (ou o chrony) está ativo e que aparece `System clock synchronized: yes`.
  - Se a box arrancar sem rede, a hora fica errada e o admin não consegue entrar.

## Passo 2: sistema
```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv postgresql nginx ufw unattended-upgrades
sudo useradd --system --create-home --home-dir /opt/quickmast --shell /usr/sbin/nologin quickmast
```
- **Firewall:** `ufw default deny incoming` e `ufw default allow outgoing`. Permita SSH só a partir da rede local (ex.: `ufw allow from 192.168.0.0/16 to any port 22`) e o 80/443. Depois `ufw enable`.
- **SSH:** só com chave, com `PermitRootLogin no` e `PasswordAuthentication no`. **Antes de desligar a senha, confirme que eu consigo entrar com a minha chave.**
- **Logs:** limite o journald para poupar o eMMC/cartão SD (`SystemMaxUse=100M` em `/etc/systemd/journald.conf`).

## Passo 3: código e dependências
- **Repositório público:**
  ```bash
  sudo -u quickmast git clone https://github.com/edivaldo124/QuickMast.git /opt/quickmast/app
  ```
- **Repositório privado:** use uma deploy key só de leitura.
  1. Gere uma chave ed25519 em `/opt/quickmast/.ssh/`.
  2. Mostre-me **só a chave pública**, para eu a colar em GitHub → Settings → Deploy keys, **sem** "Allow write access".
  3. Clone por `git@github.com:edivaldo124/QuickMast.git`.
- **Ambiente virtual e dependências:**
  ```bash
  cd /opt/quickmast/app
  sudo -u quickmast python3 -m venv .venv
  sudo -u quickmast .venv/bin/pip install --upgrade pip
  sudo -u quickmast .venv/bin/pip install --require-hashes -r requirements.txt
  ```
- **Se a instalação falhar por versão do Python ou plataforma:** gere de novo o ficheiro na box a partir do `requirements.in`, com hashes, e avise-me. Nunca instale sem hashes.
  ```bash
  sudo -u quickmast .venv/bin/pip install pip-tools
  sudo -u quickmast .venv/bin/pip-compile --generate-hashes --strip-extras -o requirements.txt requirements.in
  ```

## Passo 4: PostgreSQL nativo
Crie o dono do banco com uma senha gerada na hora, sem a mostrar e sem a deixar no histórico do shell. Guarde-a no `.env` no passo 5.
```bash
PW_DONO=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
sudo -u postgres psql -v pw="$PW_DONO" <<'SQL'
CREATE ROLE quickmast LOGIN CREATEROLE PASSWORD :'pw';
CREATE DATABASE quickmast OWNER quickmast;
SQL
```
- **`CREATEROLE`:** é o que permite ao `iniciar` criar e atualizar o `quickmast_app`. **Não dê `SUPERUSER`.**
- **Postgres abaixo de 15** (`psql --version`): corra também `sudo -u postgres psql -d quickmast -c "REVOKE CREATE ON SCHEMA public FROM PUBLIC"`. Da versão 15 em diante, já é assim por omissão.
- **Rede:** confirme `listen_addresses = 'localhost'` e que o `pg_hba.conf` usa `scram-sha-256` para 127.0.0.1.
- **Pouca RAM:** `shared_buffers = 128MB` e `max_connections = 30` chegam.

## Passo 5: `.env`
Crie `/opt/quickmast/app/.env` a partir do `.env.example`, com dono `quickmast` e `chmod 600`. Preencha:

| Variável | Valor |
|---|---|
| `SECRET_KEY` | gerado: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_USER` / `POSTGRES_DB` | `quickmast` / `quickmast` |
| `POSTGRES_PASSWORD` | a `$PW_DONO` do passo 4 |
| `APP_DB_PASSWORD` | outra senha gerada (o `iniciar` cria o `quickmast_app` com ela) |
| `DATABASE_URL_ADMIN` e `DATABASE_URL` | iguais ao modelo, mas com a porta **5432** em vez de 5433 (5433 era a do Docker) |
| `FLASK_DEBUG` | `0` |
| `PERMITIR_REGISTO` | `0` (contas novas: ligar só enquanto alguém se regista) |
| `SIMULADOR_SENSOR` | `0` |
| `LOG_JSON` | `1` |
| `ATRAS_DE_PROXY` | `1` (o Nginx fica na frente) |
| `COOKIE_SEGURO` | `1` com HTTPS. `0` **só** se ficar em HTTP na rede local (decisão do passo 0) |
| `ADMIN_EMAIL` / `ADMIN_NOME` | os que eu indicar |

Depois, **eu** escrevo a senha do admin, e a seguir corre-se o `iniciar`:
```bash
cd /opt/quickmast/app
sudo -u quickmast .venv/bin/python definir_senha_admin.py
sudo -u quickmast .venv/bin/flask --app servidor iniciar
```
No log do `iniciar` têm de aparecer "Utilizador da aplicação quickmast_app pronto" e "Admin inicial criado".

O `ADMIN_SENHA_HASH` só é usado quando o admin ainda não existe no banco. Depois de criada a conta, a senha troca-se na aplicação, em "A minha conta".

## Passo 6: gunicorn com systemd
Crie `/etc/systemd/system/quickmast.service`:
```ini
[Unit]
Description=QuickMast (gunicorn)
After=network-online.target postgresql.service time-sync.target
Wants=network-online.target time-sync.target
Requires=postgresql.service

[Service]
User=quickmast
Group=quickmast
WorkingDirectory=/opt/quickmast/app
# Sem -w nem -b: o gunicorn.conf.py desta pasta trata disso
ExecStart=/opt/quickmast/app/.venv/bin/gunicorn servidor:app
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictNamespaces=yes
LockPersonality=yes
CapabilityBoundingSet=
UMask=0077

[Install]
WantedBy=multi-user.target
```
Ative e verifique:
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now quickmast
curl -s http://127.0.0.1:8000/saude    # esperado: {"banco":"ok","servidor":"ok"}
```

## Passo 7: Nginx
Crie `/etc/nginx/sites-available/quickmast`. Substitua `<IP_DO_ESP>` pelo IP do passo 0 e ajuste as redes do `allow` à rede da fazenda.
```nginx
server {
    listen 80;
    server_name _;
    server_tokens off;
    client_max_body_size 64k;

    # Ficheiros estáticos direto do disco (o Flask usa o prefixo /stetic/)
    location /stetic/ {
        alias /opt/quickmast/app/stetic/;
        expires 7d;
        add_header X-Content-Type-Options nosniff always;
    }

    # Leitura do sensor: vai direto ao ESP8266, só para a rede local
    location = /read {
        allow 192.168.0.0/16;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        deny all;
        proxy_pass http://<IP_DO_ESP>/read;
        proxy_connect_timeout 3s;
        proxy_read_timeout 5s;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $http_host;            # com a porta: a proteção CSRF compara-o com o Origin
        proxy_set_header X-Forwarded-For $remote_addr;   # substitui (não acrescenta) o que o cliente mandar
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```
Ative o site e recarregue:
```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/quickmast /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**HTTPS (conforme o passo 0):**
- **Domínio e acesso pela internet:** `certbot --nginx`, redirecionamento de 80 para 443 e `COOKIE_SEGURO=1`. No router, abra só o 443. Em alternativa, use o Cloudflare Tunnel ou o Tailscale, sem portas abertas.
- **Só rede local:** use o mkcert para um certificado do IP/nome da box e instale a CA nos telemóveis. Assim fica `COOKIE_SEGURO=1`.
- **HTTP simples na rede local:** só se eu aceitar o risco, porque a sessão passa sem cifra no Wi-Fi. Fica `COOKIE_SEGURO=0`.

Depois de mudar o `.env`, reinicie a aplicação: `sudo systemctl restart quickmast`.

## Passo 8: verificar
```bash
ss -ltnp                              # só 127.0.0.1:8000 (gunicorn) e 127.0.0.1:5432 (postgres); nginx em 80/443
curl -sI http://<ip-da-box>/          # tem Content-Security-Policy, X-Frame-Options, X-Content-Type-Options
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Origin: https://mal.example' http://<ip-da-box>/login   # 403
curl -s http://<ip-da-box>/read       # JSON {"temp":..,"cond":..} vindo do ESP8266
journalctl -u quickmast -n 50 --no-pager
```
- **Senha errada no login:** aparece no journal uma linha JSON `login_falhou`, sem a senha.
- **Primeiro acesso do admin:** pelo telemóvel. O sistema obriga a ativar a verificação em dois passos (QR code num app autenticador). Confirme o relógio antes.

## Passo 9: operação
- **Atualizar** (crie `/opt/quickmast/atualizar.sh`). O `iniciar` tem de correr **antes** do restart: sem as colunas novas, o login dá erro 500.
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  cd /opt/quickmast/app
  sudo -u quickmast git pull --ff-only
  sudo -u quickmast .venv/bin/pip install --require-hashes -r requirements.txt
  sudo -u quickmast .venv/bin/flask --app servidor iniciar
  sudo systemctl restart quickmast
  ```
- **Backup diário:** um timer do systemd com `pg_dump -Fc quickmast` (como utilizador `postgres`) para um disco USB ou outra máquina. Guarde 7 cópias. Teste um restauro uma vez.
- **Telemóvel do admin perdido:**
  ```bash
  cd /opt/quickmast/app && sudo -u quickmast .venv/bin/flask --app servidor redefinir-mfa EMAIL
  ```
- **Fail2ban (opcional):** jail do `sshd`. Os eventos suspeitos da aplicação saem no journal como JSON com `"nivel": "WARNING"` (`login_bloqueado`, `mfa_falhou`, `conta_sob_ataque`, `origem_recusada`).

## No fim, entregue-me
- Um resumo do que foi feito.
- O que ficou por decidir.
- A saída dos comandos do passo 8.
