#!/usr/bin/env bash
# Servidor do QuickMast para a apresentação: no notebook, com a placa na rede própria "QuickMast".
#
#   ./apresentacao.sh              sobe o banco e o servidor e confere tudo (o que fazer depois de ligar o notebook)
#   ./apresentacao.sh wifi         liga o notebook à rede da placa (QuickMast) e confere se ela responde
#   ./apresentacao.sh simulador    plano B: o /read devolve valores de teste, sem a placa
#   ./apresentacao.sh status       só confere, sem mudar nada
#   ./apresentacao.sh parar        desliga o servidor (fecha a porta 5000)
#
# Não precisa de internet. Recria o servidor de cada vez, para ele ler o .env de novo
# (um PLACA_URL acrescentado depois só vale com o servidor recriado).
set -u
cd "$(dirname "$(readlink -f "$0")")" || exit 1

URL=http://localhost:5000
PROBLEMAS=0

if [ -t 1 ]; then V=$'\e[32m'; X=$'\e[31m'; A=$'\e[33m'; N=$'\e[0m'; else V=; X=; A=; N=; fi
ok()    { printf '%s✓%s %s\n' "$V" "$N" "$*"; }
aviso() { printf '%s!%s %s\n' "$A" "$N" "$*"; }
falha() { printf '%s✗%s %s\n' "$X" "$N" "$*"; PROBLEMAS=$((PROBLEMAS + 1)); }

compose() { docker compose --profile app "$@"; }
no_app()  { compose exec -T app sh -c "$1" 2>/dev/null; }
http()    { curl -s -m "${2:-3}" -o /dev/null -w '%{http_code}' "$1" 2>/dev/null; }   # 000 = sem resposta

# O Podman recusa criar o container se o .env tiver uma linha que não seja NOME=valor.
# Só diz o número da linha: o conteúdo do .env tem senhas e não é mostrado.
checar_env() {
    local linhas
    [ -f .env ] || { falha "falta o arquivo .env (copie o .env.example e preencha)"; return 1; }
    linhas=$(grep -n -v -E '^[[:space:]]*(#.*)?$|^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=' .env | cut -d: -f1 | tr '\n' ' ')
    [ -z "$linhas" ] && return 0
    falha "o .env tem linha(s) inválida(s): ${linhas}(só vale NOME=valor, ou # comentário). Apague-as ou ponha um NOME= antes, salve (Ctrl+S) e rode ./apresentacao.sh"
    return 1
}

esperar_servidor() {
    for _ in $(seq 1 60); do
        [ "$(http "$URL/saude" 2)" = 200 ] && return 0
        sleep 1
    done
    return 1
}

# A placa só responde com o notebook ligado à rede dela (192.168.4.1)
verificar_placa() {
    local resposta wifi
    wifi=$(nmcli -t -f ACTIVE,SSID dev wifi 2>/dev/null | sed -n 's/^yes://p' | head -1)
    if resposta=$(curl -sf -m 4 "$1/read" 2>/dev/null) && [[ $resposta == *'"cond"'* ]]; then
        ok "a placa responde: $resposta"
    else
        aviso "a placa não responde em $1: ligue-a e conecte o notebook à rede QuickMast (Wi-Fi agora: ${wifi:-nenhum})"
    fi
}

conferir() {
    PROBLEMAS=0
    local placa simulador sensor_ligado=1 saida vacas testes
    if [ "$(http "$URL/saude")" = 200 ]; then
        ok "servidor responde em $URL"
    else
        falha "servidor não responde em $URL: rode ./apresentacao.sh"
        return
    fi

    placa=$(no_app 'printf %s "$PLACA_URL"')
    simulador=$(no_app 'printf %s "$SIMULADOR_SENSOR"')
    if [ -n "$placa" ]; then
        ok "o servidor lê o sensor da placa em $placa"
        verificar_placa "$placa"
    elif [ "$simulador" = 1 ]; then
        aviso "modo SIMULADOR: o /read devolve valores de teste (plano B), a placa não é usada"
    else
        sensor_ligado=0
        falha "PLACA_URL vazio no servidor: ponha PLACA_URL=http://192.168.4.1 no .env, salve (Ctrl+S) e rode ./apresentacao.sh"
    fi
    if [ "$sensor_ligado" = 1 ]; then
        # 302 = a rota existe e pede login; 404 = o /read nem foi registado
        [ "$(http "$URL/read")" = 302 ] && ok "rota /read ativa" || falha "rota /read ausente no servidor"
    fi

    [ "$(no_app 'printf %s "$PERMITIR_REGISTO"')" = 1 ] &&
        aviso "registo ABERTO: qualquer aparelho na rede cria conta. Depois de criar a sua, rode ./apresentacao.sh sem ABRIR_REGISTO"

    saida=$(compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from vacas union all select count(*) from testes"' 2>/dev/null | tr '\n' ' ')
    read -r vacas testes <<< "$saida"
    if [ -z "${vacas:-}" ]; then
        falha "banco não respondeu"
    elif [ "$vacas" = 0 ]; then
        aviso "banco vazio ($vacas vacas, $testes testes): faça 2 ou 3 testes antes, para o histórico e as sugestões de brinco aparecerem"
    else
        ok "banco: $vacas vacas, $testes testes"
    fi
}

case "${1:-iniciar}" in
    iniciar|simulador)
        checar_env || exit 1
        if [ "${1:-iniciar}" = simulador ]; then
            docker compose -f docker-compose.yml -f docker-compose.simulador.yml --profile app up -d --force-recreate app || exit 1
        else
            compose up -d --force-recreate app || exit 1
        fi
        if ! esperar_servidor; then
            echo "O servidor não subiu em 60 s. Últimas linhas do log:"
            compose logs --tail 20 app
            exit 1
        fi
        conferir
        echo
        echo "Abra $URL e entre com apresentacao@quickmast.local (senha em ~/backups/QuickMast/conta-apresentacao.txt)."
        echo "Placa fora da rede? ./apresentacao.sh wifi liga o notebook à rede dela."
        ;;
    wifi)
        # A rede e a senha vêm do firmware (REDE_PROPRIA_*): o notebook fica sem internet enquanto estiver nela
        cfg=firmware/quickmast_esp8266/quickmast_esp8266.ino
        ssid=$(sed -n 's/^#define REDE_PROPRIA_SSID *"\([^"]*\)".*/\1/p' "$cfg")
        senha=$(sed -n 's/^#define REDE_PROPRIA_SENHA *"\([^"]*\)".*/\1/p' "$cfg")
        [ -n "$ssid" ] && [ -n "$senha" ] || { falha "REDE_PROPRIA_SSID/SENHA não achados em $cfg"; exit 1; }
        echo "Ligando o notebook à rede $ssid..."
        nmcli dev wifi rescan >/dev/null 2>&1; sleep 2
        nmcli dev wifi connect "$ssid" password "$senha" || { falha "não consegui entrar na rede $ssid: a placa está ligada?"; exit 1; }
        sleep 3
        verificar_placa http://192.168.4.1
        ;;
    status)
        conferir
        exit $((PROBLEMAS > 0))
        ;;
    parar)
        compose stop app && ok "servidor parado (porta 5000 fechada); o banco continua"
        ;;
    *)
        echo "uso: ./apresentacao.sh [iniciar|wifi|simulador|status|parar]"
        exit 2
        ;;
esac
