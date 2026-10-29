// Configuração local do firmware. Copie este ficheiro para configuracao.h (na mesma pasta) e preencha.
// O configuracao.h tem as senhas do Wi-Fi e da conta: está no .gitignore e não vai para o GitHub.
//
// Conta da placa no QuickMast: crie uma conta de OPERADOR só para ela (ex.: sensor@quickmast.local).
//   - Ainda não há "criar utilizador" no painel: ligue PERMITIR_REGISTO=1 no .env, crie a conta
//     em /login > "Criar conta" e volte a pôr PERMITIR_REGISTO=0.
//   - Não use uma conta admin: o admin tem verificação em dois passos, que a placa não faz.
//   - A senha fica na flash da placa. Se a placa se perder, desative a conta em /usuarios.

// Rede própria: 1 = a placa cria a rede REDE_PROPRIA_SSID (fica em 192.168.4.1) e o PC liga-se a ela.
// Para apresentações e lugares sem Wi-Fi de confiança. No .env do PC: PLACA_URL=http://192.168.4.1
// e o teste é conduzido pela página /ubere. 0 = a placa entra na rede WIFI_SSID e envia os testes
// ao SERVIDOR_URL (as linhas abaixo da rede própria só contam com 0).
#define REDE_PROPRIA        0
#define REDE_PROPRIA_SSID   "QuickMast"
#define REDE_PROPRIA_SENHA  "senha-com-8-ou-mais"   // WPA2: 8 a 63 caracteres

#define WIFI_SSID   "nome-da-rede"
#define WIFI_SENHA  "senha-da-rede"

// Endereço da box onde corre o QuickMast (o Nginx), sem barra no fim
#define SERVIDOR_URL "http://192.168.1.50"

#define API_EMAIL "sensor@quickmast.local"
#define API_SENHA "senha-da-conta-da-placa"

// HTTPS: 1 se o SERVIDOR_URL for https:// (certificado do mkcert ou do certbot).
// A placa confere a impressão digital SHA-1 do certificado do servidor. Para a ver:
//   openssl s_client -connect 192.168.1.50:443 </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha1
// Quando o certificado for renovado, a impressão digital muda: atualizar aqui e gravar a placa de novo.
#define USAR_HTTPS 0
#define HTTPS_FINGERPRINT "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00"
