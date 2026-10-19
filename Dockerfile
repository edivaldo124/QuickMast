# Imagem do QuickMast para testes no PC (docker compose --profile app up -d --build).
# A produção na TV box roda sem containers (ver o passo a passo do deploy).
# Versão fixa: atualizar de propósito, como a do Postgres no docker-compose.yml
FROM python:3.13.16-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
# --require-hashes: instala exatamente os pacotes do requirements.txt, nada mais
RUN pip install --require-hashes -r requirements.txt

COPY . .
RUN useradd --system --no-create-home quickmast
USER quickmast

EXPOSE 8000
# O iniciar cria/atualiza as tabelas e o utilizador da aplicação no banco antes de subir.
# O gunicorn.conf.py desta pasta dá 1 worker com 8 threads; o -b troca o 127.0.0.1 por 0.0.0.0
# (só com ATRAS_DE_PROXY=0) na porta PORTA (8000 se não for definida).
CMD ["sh", "-c", "flask --app servidor iniciar && exec gunicorn -b \"0.0.0.0:${PORTA:-8000}\" servidor:app"]
