/*
  QuickMast: firmware do medidor de condutividade (NodeMCU / ESP8266)

  Hardware
    - Sensor de condutividade (módulo TDS com um resistor de 1 kΩ) no A0. Leite normal lê ~300.
    - Sem botão: o teste avança com Enter no Monitor Série, ou pela página /ubere (lá, cada teto
      tem a sua captura e pode ser feito por qualquer ordem).
    - LED da placa (GPIO2, D4): pisca depressa se houver suspeita de mastite; fica aceso 1,5 s se não.
    Sem sensor de temperatura (o DS18B20 saiu) e sem pH (ainda em análise).

  Teste (Monitor Série a 9600 baud, com o fim de linha "Nova linha")
    1. Escrever o brinco da vaca e Enter.
    2. Sonda no teto pedido e Enter. Repetir nos 4 tetos; "x" cancela o teste.
    3. A placa mostra o diagnóstico e envia o teste para o servidor. Sem Wi-Fi ou sem servidor,
       o teste fica na fila (em RAM: perde-se se a placa desligar) e segue quando a ligação voltar.

  Servidor QuickMast (Flask)
    - Entra com uma conta de operador (POST /login, como o formulário) e guarda o cookie de sessão.
    - POST /api/testes  {"brinco": "BR-102", "leituras": [{"teto": 1, "cond": 312}, ...]}
      O servidor recalcula o diagnóstico (servicos/diagnostico.py) e é esse que fica no histórico;
      a placa compara-o com o seu e avisa se forem diferentes.
    - Continua a responder a GET /read com {"cond": N}: a página /ubere usa-o (o Nginx da box
      encaminha o /read para esta placa), para quem prefere conduzir o teste pelo telemóvel.

  Rede própria (REDE_PROPRIA 1 no configuracao.h): para apresentações e lugares sem um Wi-Fi de
  confiança. A placa cria a rede REDE_PROPRIA_SSID e fica sempre em 192.168.4.1; o PC liga-se a
  ela e o QuickMast vai buscar as leituras (PLACA_URL=http://192.168.4.1 no .env). Quem chama é o
  PC, por isso a placa não precisa de saber o IP dele nem de entrar com a conta. O teste é conduzido
  pela página /ubere; os do Monitor Série dão o diagnóstico na placa mas ficam na fila (sem envio).

  Configuração: copiar configuracao.example.h para configuracao.h e preencher.
  Placa no Arduino IDE: "NodeMCU 1.0 (ESP-12E Module)" (core esp8266 3.x).
*/
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <WiFiClientSecureBearSSL.h>

#if __has_include("configuracao.h")
#include "configuracao.h"
#else
#error "Falta o configuracao.h: copie configuracao.example.h para configuracao.h e preencha a rede e a conta."
#endif
#ifndef REDE_PROPRIA
#error "O configuracao.h é anterior à rede própria: copie as linhas REDE_PROPRIA do configuracao.example.h."
#endif
#include "diagnostico.h"

// ---------- Pinos ----------
const int PINO_SENSOR = A0;
const int PINO_LED = LED_BUILTIN;   // GPIO2 (D4): acende em LOW

// ---------- Leitura do sensor ----------
const int AMOSTRAS = 15;               // fica a média das 5 do meio: os picos de ruído saem
const int INTERVALO_AMOSTRA_MS = 20;   // analogRead seguido demais faz o ESP8266 perder o Wi-Fi
const int ESTABILIZAR_MS = 1000;       // a sonda assenta no leite depois do Enter
const int LEITURA_MINIMA = 50;         // abaixo disto a sonda está fora do leite

// Iguais aos da página /ubere (stetic/js/ubere.js)
const char *const NOMES_TETOS[4] = {"Anterior Direito", "Anterior Esquerdo",
                                    "Posterior Direito", "Posterior Esquerdo"};

// ---------- Rede ----------
const unsigned long TIMEOUT_HTTP_MS = 8000;
const unsigned long ESPERA_WIFI_MIN_MS = 15000;    // dá tempo ao religar automático antes de forçar
const unsigned long ESPERA_WIFI_MAX_MS = 60000;
const unsigned long ESPERA_ENVIO_MIN_MS = 5000;
const unsigned long ESPERA_ENVIO_MAX_MS = 300000;  // 5 min: também é a janela do bloqueio do login

// ---------- Estado ----------
struct Teste {
  char brinco[51];    // o servidor aceita até 50 caracteres
  int cond[4];        // tetos 1 a 4
  bool suspeito[4];   // diagnóstico da placa
};

// Testes por enviar (fila circular em RAM)
const int TAMANHO_FILA = 20;
Teste fila[TAMANHO_FILA];
int filaInicio = 0;
int filaTotal = 0;

enum Fase { PEDIR_BRINCO, MEDIR };
Fase fase = PEDIR_BRINCO;
Teste atual;
int tetoAtual = 0;   // índice 0-3 do teto a medir

enum Resultado { SUCESSO, FALHA_REDE, SESSAO_EXPIRADA, DADOS_RECUSADOS, CONTA_RECUSADA };

String cookieSessao;          // "session=..."; vazio = ainda não entrou
bool contaRecusada = false;   // configuração errada: parar (cada falha conta para o bloqueio do login)

bool wifiLigado = false;
unsigned long momentoWifi = 0;
unsigned long esperaWifi = ESPERA_WIFI_MIN_MS;

unsigned long momentoFalhaEnvio = 0;
unsigned long esperaEnvio = 0;   // 0 = pode enviar já

String linhaSerial;
bool ultimoFoiCR = false;

#if USAR_HTTPS
BearSSL::WiFiClientSecure cliente;
#else
WiFiClient cliente;
#endif
ESP8266WebServer servidorLocal(80);


// ---------- Sensor ----------
int lerCondutividade() {
  int v[AMOSTRAS];
  for (int i = 0; i < AMOSTRAS; i++) {
    v[i] = analogRead(PINO_SENSOR);
    delay(INTERVALO_AMOSTRA_MS);
  }
  for (int i = 1; i < AMOSTRAS; i++) {   // ordena (insertion sort: são 15 valores)
    int x = v[i], j = i - 1;
    while (j >= 0 && v[j] > x) {
      v[j + 1] = v[j];
      j--;
    }
    v[j + 1] = x;
  }
  long soma = 0;
  for (int i = AMOSTRAS / 2 - 2; i <= AMOSTRAS / 2 + 2; i++) soma += v[i];
  return (soma + 2) / 5;
}

// GET /read: a página /ubere lê o sensor por aqui
void responderRead() {
  int valor = lerCondutividade();
  servidorLocal.sendHeader("Cache-Control", "no-store");
  servidorLocal.send(200, "application/json", String("{\"cond\":") + valor + '}');
}


// ---------- Teste dos 4 tetos ----------
void pedirBrinco() {
  Serial.println();
  if (filaTotal > 0) Serial.printf("(%d teste(s) à espera de envio)\n", filaTotal);
  Serial.println("Escreva o brinco da vaca e prima Enter:");
}

void pedirTeto() {
  Serial.printf("Insira a sonda no teto %d (%s) e prima Enter. "
                "x cancela.\n", tetoAtual + 1, NOMES_TETOS[tetoAtual]);
}

void sinalizar(bool mastite) {
  if (mastite) {
    for (int i = 0; i < 10; i++) {
      digitalWrite(PINO_LED, LOW);
      delay(100);
      digitalWrite(PINO_LED, HIGH);
      delay(100);
    }
  } else {
    digitalWrite(PINO_LED, LOW);
    delay(1500);
    digitalWrite(PINO_LED, HIGH);
  }
}

void finalizarTeste() {
  DiagnosticoTeto d[4];
  diagnosticar(atual.cond, d);

  bool mastite = false;
  String afetados;
  Serial.printf("---- Vaca %s ----\n", atual.brinco);
  for (int i = 0; i < 4; i++) {
    atual.suspeito[i] = d[i].suspeito;
    Serial.printf("Teto %d (%s): %d  %s", i + 1, NOMES_TETOS[i], atual.cond[i],
                  d[i].suspeito ? "SUSPEITA" : "normal");
    // Os mesmos motivos que o servidor grava no histórico
    if (d[i].relativo) Serial.print(" - condutividade acima dos outros tetos");
    if (d[i].absoluto) Serial.print(" - acima do valor de referência");
    Serial.println();
    if (d[i].suspeito) {
      if (mastite) afetados += ", ";
      afetados += i + 1;
      mastite = true;
    }
  }
  if (mastite) Serial.printf("ALERTA: suspeita de mastite no(s) teto(s) %s\n", afetados.c_str());
  else Serial.println("Todos os tetos normais.");
  sinalizar(mastite);

  fila[(filaInicio + filaTotal) % TAMANHO_FILA] = atual;
  filaTotal++;
  esperaEnvio = 0;   // tenta enviar já
  fase = PEDIR_BRINCO;
  pedirBrinco();
}

void capturarTeto() {
  Serial.printf("A ler o teto %d...\n", tetoAtual + 1);
  delay(ESTABILIZAR_MS);
  int valor = lerCondutividade();
  if (valor < LEITURA_MINIMA) {
    Serial.printf("Leitura %d: a sonda parece estar fora do leite. Repita o teto %d.\n",
                  valor, tetoAtual + 1);
    return;
  }
  atual.cond[tetoAtual] = valor;
  Serial.printf("Teto %d: condutividade %d\n", tetoAtual + 1, valor);
  tetoAtual++;
  if (tetoAtual < 4) pedirTeto();
  else finalizarTeste();
}

void tratarLinha(String linha) {
  if (fase == PEDIR_BRINCO) {
    if (linha.isEmpty()) {
      pedirBrinco();
    } else if (linha.length() >= sizeof(atual.brinco)) {
      Serial.println("Brinco demasiado longo (máx. 50 caracteres).");
    } else if (filaTotal == TAMANHO_FILA) {
      // Melhor parar do que perder testes: a fila só esvazia com o servidor ao alcance
      Serial.println("Fila cheia: ligue a placa ao Wi-Fi do servidor antes de testar mais vacas.");
    } else {
      memset(&atual, 0, sizeof(atual));
      linha.toCharArray(atual.brinco, sizeof(atual.brinco));
      tetoAtual = 0;
      fase = MEDIR;
      pedirTeto();
    }
  } else if (linha.equalsIgnoreCase("x")) {
    Serial.println("Teste cancelado.");
    fase = PEDIR_BRINCO;
    pedirBrinco();
  } else if (linha.isEmpty()) {
    capturarTeto();
  } else {
    Serial.println("Prima Enter para capturar, ou x para cancelar.");
  }
}

// Devolve true quando chega uma linha inteira do Monitor Série (aceita \n, \r e \r\n)
bool lerLinha(String &linha) {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' && ultimoFoiCR) {   // o \n de um \r\n: a linha já saiu no \r
      ultimoFoiCR = false;
      continue;
    }
    ultimoFoiCR = (c == '\r');
    if (c == '\r' || c == '\n') {
      linha = linhaSerial;
      linha.trim();
      linhaSerial = "";
      return true;
    }
    if (linhaSerial.length() < 64) linhaSerial += c;
  }
  return false;
}


// ---------- Wi-Fi ----------
// O ESP8266 tenta religar sozinho (setAutoReconnect). Se a rede continuar em baixo, a ligação
// recomeça de raiz, cada vez com mais espera. Nada aqui bloqueia: sem rede, a medição continua.
void manterWifi() {
  wl_status_t estado = WiFi.status();
  bool ligado = estado == WL_CONNECTED;
  if (ligado != wifiLigado) {
    wifiLigado = ligado;
    momentoWifi = millis();
    if (ligado) {
      Serial.printf("Wi-Fi ligado (IP %s).\n", WiFi.localIP().toString().c_str());
      esperaWifi = ESPERA_WIFI_MIN_MS;
      esperaEnvio = 0;   // envia já o que estiver na fila
    } else {
      Serial.println("Wi-Fi em baixo: os testes ficam na fila até a rede voltar.");
    }
  }
  if (!ligado && millis() - momentoWifi >= esperaWifi) {
    if (estado == WL_NO_SSID_AVAIL) Serial.printf("Rede \"%s\" não encontrada.\n", WIFI_SSID);
    else if (estado == WL_WRONG_PASSWORD) Serial.println("Senha do Wi-Fi errada (WIFI_SENHA no configuracao.h).");
    Serial.println("A religar ao Wi-Fi...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_SENHA);
    momentoWifi = millis();
    esperaWifi = min(esperaWifi * 2, ESPERA_WIFI_MAX_MS);
  }
}

// REDE_PROPRIA: a placa é o ponto de acesso (192.168.4.1) e o PC liga-se a ela
void criarRedePropria() {
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP(REDE_PROPRIA_SSID, REDE_PROPRIA_SENHA)) {
    Serial.println("Não foi possível criar a rede própria: a REDE_PROPRIA_SENHA (configuracao.h) "
                   "precisa de 8 a 63 caracteres.");
    return;
  }
  String ip = WiFi.softAPIP().toString();
  Serial.printf("Rede própria \"%s\" criada. Ligue o PC a ela; no .env do PC: PLACA_URL=http://%s\n",
                REDE_PROPRIA_SSID, ip.c_str());
  Serial.printf("Teste no browser do PC: http://%s/read deve mostrar {\"cond\":...}\n", ip.c_str());
  Serial.println("Conduza o teste pela página /ubere: daqui a placa não envia testes ao servidor.");
}

// Avisa no Monitor Série quando o PC (ou outro aparelho) entra ou sai da rede própria
void vigiarRedePropria() {
  static int anteriores = 0;
  int agora = WiFi.softAPgetStationNum();
  if (agora != anteriores) {
    Serial.printf("Aparelhos ligados à rede própria: %d\n", agora);
    anteriores = agora;
  }
}


// ---------- Pedidos ao servidor ----------
String urlServidor(const char *caminho) {
  return String(SERVIDOR_URL) + caminho;
}

String codificarUrl(const char *s) {
  const char *hex = "0123456789ABCDEF";
  String r;
  for (; *s; s++) {
    unsigned char c = *s;
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
      r += (char)c;
    } else {
      r += '%';
      r += hex[c >> 4];
      r += hex[c & 15];
    }
  }
  return r;
}

String escaparJson(const char *s) {
  String r;
  for (; *s; s++) {
    unsigned char c = *s;
    if (c == '"' || c == '\\') {
      r += '\\';
      r += (char)c;
    } else if (c < 0x20) {
      char b[7];
      snprintf(b, sizeof(b), "\\u%04x", c);
      r += b;
    } else {
      r += (char)c;
    }
  }
  return r;
}

// O formato que o POST /api/testes espera (blueprints/testes.py). Sem "temp": é opcional.
String montarJson(const Teste &t) {
  String json = "{\"brinco\":\"";
  json += escaparJson(t.brinco);
  json += "\",\"leituras\":[";
  for (int i = 0; i < 4; i++) {
    if (i) json += ',';
    json += "{\"teto\":";
    json += i + 1;
    json += ",\"cond\":";
    json += t.cond[i];
    json += '}';
  }
  json += "]}";
  return json;
}

// Posição do valor de "chave" no JSON, ou -1. Sem biblioteca: a resposta é pequena e conhecida.
int posicaoValor(const String &json, const char *chave) {
  String procura = String('"') + chave + '"';
  int p = json.indexOf(procura);
  if (p < 0) return -1;
  p += procura.length();
  while (p < (int)json.length() && (json[p] == ' ' || json[p] == ':')) p++;
  return p < (int)json.length() ? p : -1;
}

void guardarCookie(const String &setCookie) {
  int fim = setCookie.indexOf(';');
  cookieSessao = fim < 0 ? setCookie : setCookie.substring(0, fim);
}

// Entra no QuickMast como o formulário da página /login e guarda o cookie da sessão
Resultado entrar() {
  HTTPClient http;
  http.setTimeout(TIMEOUT_HTTP_MS);
  http.setReuse(false);   // fecha a ligação no fim: nenhum socket (nem a RAM do TLS) fica preso
  if (!http.begin(cliente, urlServidor("/login"))) return FALHA_REDE;
  const char *cabecalhos[] = {"Set-Cookie", "Location"};
  http.collectHeaders(cabecalhos, 2);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int codigo = http.POST("email=" + codificarUrl(API_EMAIL) + "&senha=" + codificarUrl(API_SENHA));
  String cookie = http.header("Set-Cookie");
  String destino = http.header("Location");
  http.end();

  if (codigo < 0) {
    Serial.printf("Login: sem resposta do servidor (%s).\n", HTTPClient::errorToString(codigo).c_str());
    return FALHA_REDE;
  }
  if (codigo == 302 && destino.indexOf("/login/mfa") >= 0) {
    Serial.println("Login: a conta tem verificação em dois passos. Use uma conta de operador sem ela.");
    contaRecusada = true;
    return CONTA_RECUSADA;
  }
  if (codigo == 302 && cookie.startsWith("session=")) {
    guardarCookie(cookie);
    Serial.println("Sessão iniciada no servidor.");
    return SUCESSO;
  }
  if (codigo == 401) {
    Serial.println("Login: email ou senha errados (API_EMAIL/API_SENHA no configuracao.h), ou conta desativada.");
    contaRecusada = true;
    return CONTA_RECUSADA;
  }
  if (codigo == 429) {
    Serial.println("Login: o servidor bloqueou as tentativas durante 5 minutos.");
    return FALHA_REDE;
  }
  if (codigo == 301 || codigo == 308) {
    Serial.println("Login: o servidor só aceita HTTPS. Use https:// no SERVIDOR_URL e USAR_HTTPS 1.");
    contaRecusada = true;
    return CONTA_RECUSADA;
  }
  Serial.printf("Login: resposta inesperada (HTTP %d).\n", codigo);
  return FALHA_REDE;
}

// A resposta traz o diagnóstico do servidor: avisa se não bater com o da placa
void compararComServidor(const Teste &t, const String &resposta) {
  int p = posicaoValor(resposta, "id");
  Serial.printf("Teste #%ld da vaca %s gravado no servidor.\n",
                p >= 0 ? resposta.substring(p).toInt() : 0L, t.brinco);

  p = posicaoValor(resposta, "tetos_afetados");
  if (p < 0 || resposta[p] != '[') return;
  bool servidor[4] = {false, false, false, false};
  for (int i = p + 1; i < (int)resposta.length() && resposta[i] != ']'; i++) {
    int teto = resposta[i] - '0';
    if (teto >= 1 && teto <= 4) servidor[teto - 1] = true;
  }
  for (int i = 0; i < 4; i++) {
    if (servidor[i] != t.suspeito[i]) {
      Serial.println("Atenção: o diagnóstico do servidor é diferente do da placa (vale o do servidor). "
                     "Confira se diagnostico.h e servicos/diagnostico.py têm os mesmos limites.");
      return;
    }
  }
}

Resultado publicar(const Teste &t) {
  HTTPClient http;
  http.setTimeout(TIMEOUT_HTTP_MS);
  http.setReuse(false);   // fecha a ligação no fim: nenhum socket (nem a RAM do TLS) fica preso
  if (!http.begin(cliente, urlServidor("/api/testes"))) return FALHA_REDE;
  const char *cabecalhos[] = {"Set-Cookie"};
  http.collectHeaders(cabecalhos, 1);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Cookie", cookieSessao);
  int codigo = http.POST(montarJson(t));
  String resposta = codigo > 0 ? http.getString() : String();
  String cookie = http.header("Set-Cookie");
  http.end();

  // O Flask renova o cookie a cada pedido: guardar o novo adia o fim da sessão (12 h)
  if (cookie.startsWith("session=")) guardarCookie(cookie);

  if (codigo == 201) {
    compararComServidor(t, resposta);
    return SUCESSO;
  }
  if (codigo == 401) return SESSAO_EXPIRADA;
  if (codigo < 0) {
    Serial.printf("Envio: sem resposta do servidor (%s).\n", HTTPClient::errorToString(codigo).c_str());
    return FALHA_REDE;
  }
  if (codigo == 400) {
    Serial.printf("O servidor recusou o teste da vaca %s: %s\n", t.brinco, resposta.c_str());
    return DADOS_RECUSADOS;
  }
  if (codigo == 403) {
    Serial.printf("Sem permissão para gravar testes: %s\n", resposta.c_str());
    contaRecusada = true;
    return CONTA_RECUSADA;
  }
  Serial.printf("Envio: o servidor respondeu HTTP %d.\n", codigo);
  return FALHA_REDE;
}

Resultado enviarTeste(const Teste &t) {
  if (cookieSessao.isEmpty()) {
    Resultado r = entrar();
    if (r != SUCESSO) return r;
  }
  Resultado r = publicar(t);
  if (r == SESSAO_EXPIRADA) {   // passaram as 12 h, ou a sessão foi terminada: entra de novo, uma vez
    cookieSessao = "";
    r = entrar();
    if (r == SUCESSO) r = publicar(t);
    if (r == SESSAO_EXPIRADA) r = FALHA_REDE;
  }
  return r;
}

// Envia o teste mais antigo da fila. Em falha de rede espera 5 s, 10 s, 20 s... até 5 min.
void enviarFila() {
  if (filaTotal == 0 || contaRecusada || !wifiLigado) return;
  if (esperaEnvio && millis() - momentoFalhaEnvio < esperaEnvio) return;

  Resultado r = enviarTeste(fila[filaInicio]);
  if (r == SUCESSO || r == DADOS_RECUSADOS) {   // recusado: repetir daria o mesmo erro
    filaInicio = (filaInicio + 1) % TAMANHO_FILA;
    filaTotal--;
    esperaEnvio = 0;
  } else if (r == FALHA_REDE) {
    momentoFalhaEnvio = millis();
    esperaEnvio = esperaEnvio ? min(esperaEnvio * 2, ESPERA_ENVIO_MAX_MS) : ESPERA_ENVIO_MIN_MS;
    Serial.printf("Nova tentativa em %lu s (%d teste(s) na fila).\n", esperaEnvio / 1000, filaTotal);
  } else {   // CONTA_RECUSADA: a fila fica guardada até corrigir o configuracao.h e reiniciar a placa
    Serial.printf("Envio parado: %d teste(s) ficam na fila.\n", filaTotal);
  }
}


void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, HIGH);

  Serial.println();
  Serial.println("QuickMast: medidor de condutividade");
  WiFi.persistent(false);   // não grava a rede na flash a cada arranque
#if REDE_PROPRIA
  criarRedePropria();
#else
  Serial.printf("Servidor %s, conta %s\n", SERVIDOR_URL, API_EMAIL);
  if ((strncmp(SERVIDOR_URL, "https://", 8) == 0) != (USAR_HTTPS == 1)) {
    Serial.println("Aviso: SERVIDOR_URL e USAR_HTTPS não combinam (configuracao.h).");
  }
#if USAR_HTTPS
  cliente.setFingerprint(HTTPS_FINGERPRINT);
#endif

  WiFi.mode(WIFI_STA);
  WiFi.hostname("quickmast-sensor");
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  momentoWifi = millis();
#endif

  servidorLocal.on("/read", HTTP_GET, responderRead);
  servidorLocal.begin();

  pedirBrinco();
}

void loop() {
#if REDE_PROPRIA
  vigiarRedePropria();
#else
  manterWifi();   // fora da rede própria: o WiFi.begin dele poria a placa a procurar o WIFI_SSID
                  // e o ponto de acesso ficava instável (o ESP8266 tem um rádio só)
#endif
  servidorLocal.handleClient();

  String linha;
  if (lerLinha(linha)) tratarLinha(linha);

  enviarFila();
}
