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
    3. A placa mostra o diagnóstico, grava o teste na memória flash (LittleFS: não se perde se
       desligar a placa no curral) e envia-o ao servidor quando houver Wi-Fi. O teste só é apagado
       da placa depois de o servidor confirmar que o gravou no banco de dados.

  Servidor QuickMast (Flask)
    - Entra com uma conta de operador (POST /login, como o formulário) e guarda o cookie de sessão.
    - POST /api/testes  {"brinco": "BR-102", "leituras": [{"teto": 1, "cond": 312}, ...]}
      O servidor recalcula o diagnóstico (servicos/diagnostico.py) e é esse que fica no histórico;
      a placa compara-o com o seu e avisa se forem diferentes. O servidor também compara cada teto
      com o histórico da vaca (cada vaca tem o seu nível), por isso pode achar mais tetos suspeitos.
    - Continua a responder a GET /read com {"cond": N, "pendentes": M}: a página /ubere usa-o
      (o Nginx da box encaminha o /read para esta placa), para quem prefere conduzir o teste pelo telemóvel.

  Rede própria (REDE_PROPRIA 1, no bloco CONFIGURAÇÃO): para apresentações e lugares sem um Wi-Fi de
  confiança. A placa cria a rede REDE_PROPRIA_SSID e fica sempre em 192.168.4.1; o PC liga-se a
  ela e o QuickMast vai buscar as leituras (PLACA_URL=http://192.168.4.1 no .env). Quem chama é o
  PC, por isso a placa não precisa de saber o IP dele nem de entrar com a conta: os testes salvos na
  placa no curral também são recolhidos pelo servidor (GET /fila) e só são apagados da placa quando
  o servidor confirma a gravação (POST /fila/confirmar).

  Tudo está neste arquivo só. O que se muda (rede, senhas, servidor) fica no bloco
  CONFIGURAÇÃO, logo abaixo deste comentário.
  Placa no Arduino IDE: "NodeMCU 1.0 (ESP-12E Module)" (core esp8266 3.x).
*/
// ============================ CONFIGURAÇÃO ============================
// É o único sítio a editar. Para a apresentação basta ter REDE_PROPRIA 1.

// 1 = a placa cria a rede Wi-Fi REDE_PROPRIA_SSID (sempre em 192.168.4.1) e o notebook liga-se a ela.
//     O teste é conduzido pela página /ubere; a placa só responde às leituras.
// 0 = a placa entra no Wi-Fi de casa (WIFI_*) e envia os testes ao servidor (SERVIDOR_URL, API_*).
#define REDE_PROPRIA        1

// --- Com REDE_PROPRIA 1 ---
#define REDE_PROPRIA_SSID   "QuickMast"
#define REDE_PROPRIA_SENHA  "12345678"   // WPA2: 8 a 63 caracteres

// --- Só com REDE_PROPRIA 0 (produção) ---
// Não ponha aqui as senhas verdadeiras se este arquivo for para o GitHub.
#define WIFI_SSID           "Zefinha"
#define WIFI_SENHA          "226204ZEF"
#define SERVIDOR_URL        "http://192.168.1.50"   // endereço do QuickMast (o Nginx), sem barra no fim
#define API_EMAIL           "sensor@quickmast.local"   // conta de OPERADOR (o admin pede 2.º passo)
#define API_SENHA           "senha-da-conta-da-placa"
#define USAR_HTTPS          0   // 1 se o SERVIDOR_URL for https://
#define HTTPS_FINGERPRINT   "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00"   // SHA-1 do certificado
// ======================================================================

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <WiFiClientSecureBearSSL.h>
#include <LittleFS.h>

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

// ---------- Estado e armazenamento na placa (LittleFS) ----------
struct Teste {
  uint32_t seq;       // número único na placa, para confirmar qual teste o servidor gravou
  char brinco[51];    // o servidor aceita até 50 caracteres
  int cond[4];        // tetos 1 a 4
  bool suspeito[4];   // diagnóstico da placa
};

// Cabeçalho gravado na memória flash (/fila.bin) com soma de verificação (CRC)
const char *const ARQUIVO_FILA = "/fila.bin";
const char *const ARQUIVO_FILA_TMP = "/fila.tmp";
const uint32_t MAGIA_FILA = 0x514D4631UL;   // "QMF1"

struct CabecalhoFila {
  uint32_t magia;
  uint32_t proximoSeq;
  uint16_t total;
  uint16_t tamanhoTeste;
  uint32_t crc;
};

// Testes por enviar (em RAM e espelhados na flash LittleFS para não se perderem se desligar a placa)
const int TAMANHO_FILA = 50;
Teste fila[TAMANHO_FILA];
int filaInicio = 0;
int filaTotal = 0;
uint32_t proximoSeq = 1;
bool flashPronta = false;

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


// ATENÇÃO À ORDEM: todos os tipos (struct e enum) ficam ACIMA da primeira função do arquivo.
// A Arduino IDE insere os protótipos das funções antes da primeira função; um tipo definido
// depois dela dá o erro "does not name a type". Por isso a secção Diagnóstico vem aqui, depois
// do struct Teste e dos enum, e não no início.

// ---------- Diagnóstico ----------
// Regras de diagnóstico de mastite: a comparação entre tetos de servicos/diagnostico.py no servidor.
// O servidor recalcula sempre e é o diagnóstico dele que fica no histórico; a placa calcula
// para dar o resultado na hora, mesmo sem rede. Mudar os valores nos dois sítios ao mesmo tempo.
// O servidor também compara cada teto com o histórico da vaca, que a placa não guarda.

// Condutividade em valor bruto do analogRead (0-1023). Com o resistor de 1 kΩ no módulo TDS,
// o leite normal lê ~300, mas cada vaca tem o seu nível: não há um limite fixo que sirva para todas.
const double LIMIAR_RELATIVO = 0.20;    // alerta: 20% acima da mediana dos outros tetos...
const double DIFERENCA_MINIMA = 40.0;   // ...e pelo menos 40 pontos, para o ruído não dar alarme

struct DiagnosticoTeto {
  bool relativo;   // condutividade acima dos outros tetos
  bool suspeito;   // por agora, o mesmo que relativo (a única regra que a placa sabe calcular)
};

inline int mediana3(int a, int b, int c) {
  if (a > b) { int t = a; a = b; b = t; }   // a <= b
  if (b > c) b = c;                         // b = min(b, c)
  return a > b ? a : b;                     // max(a, min(b, c))
}

// cond: leituras dos tetos 1 a 4, por ordem. Os cálculos são em double, como no Python,
// para os dois lados darem o mesmo resultado mesmo nos valores de fronteira.
inline void diagnosticar(const int cond[4], DiagnosticoTeto res[4]) {
  for (int i = 0; i < 4; i++) {
    int outros[3], k = 0;
    for (int j = 0; j < 4; j++) {
      if (j != i) outros[k++] = cond[j];
    }
    double med = mediana3(outros[0], outros[1], outros[2]);
    double diff = cond[i] - med;
    double rel = med != 0 ? diff / med : 0;
    res[i].relativo = diff > DIFERENCA_MINIMA && rel > LIMIAR_RELATIVO;
    res[i].suspeito = res[i].relativo;
  }
}

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

// GET /read: a página /ubere lê o sensor por aqui (inclui quantos testes estão salvos na placa)
void responderRead() {
  int valor = lerCondutividade();
  servidorLocal.sendHeader("Cache-Control", "no-store");
  servidorLocal.send(200, "application/json",
                     String("{\"cond\":") + valor + ",\"pendentes\":" + filaTotal + '}');
}


// ---------- Persistência na memória flash (LittleFS) ----------
uint32_t atualizarCrc(uint32_t crc, const uint8_t *dados, size_t tam) {
  for (size_t i = 0; i < tam; i++) {
    crc ^= dados[i];
    crc *= 16777619UL;   // FNV-1a de 32 bits
  }
  return crc;
}

uint32_t calcularCrcFila(uint32_t seq, uint16_t total) {
  uint32_t crc = 2166136261UL;
  crc = atualizarCrc(crc, (const uint8_t *)&seq, sizeof(seq));
  crc = atualizarCrc(crc, (const uint8_t *)&total, sizeof(total));
  for (uint16_t i = 0; i < total; i++) {
    const Teste &t = fila[(filaInicio + i) % TAMANHO_FILA];
    crc = atualizarCrc(crc, (const uint8_t *)&t, sizeof(Teste));
  }
  return crc;
}

// Grava primeiro em /fila.tmp e substitui /fila.bin no fim: se faltar energia no curral a meio da
// escrita, os testes anteriores não se corrompem. Quando a fila esvazia, apaga o arquivo da placa.
bool gravarFila() {
  if (!flashPronta) return false;
  if (filaTotal == 0) {
    LittleFS.remove(ARQUIVO_FILA_TMP);
    return !LittleFS.exists(ARQUIVO_FILA) || LittleFS.remove(ARQUIVO_FILA);
  }
  File f = LittleFS.open(ARQUIVO_FILA_TMP, "w");
  if (!f) return false;

  CabecalhoFila cab;
  cab.magia = MAGIA_FILA;
  cab.proximoSeq = proximoSeq;
  cab.total = (uint16_t)filaTotal;
  cab.tamanhoTeste = (uint16_t)sizeof(Teste);
  cab.crc = calcularCrcFila(cab.proximoSeq, cab.total);

  bool ok = f.write((const uint8_t *)&cab, sizeof(cab)) == sizeof(cab);
  for (int i = 0; i < filaTotal && ok; i++) {
    const Teste &t = fila[(filaInicio + i) % TAMANHO_FILA];
    ok = f.write((const uint8_t *)&t, sizeof(Teste)) == sizeof(Teste);
  }
  f.flush();
  f.close();

  if (!ok) {
    LittleFS.remove(ARQUIVO_FILA_TMP);
    return false;
  }
  if (!LittleFS.rename(ARQUIVO_FILA_TMP, ARQUIVO_FILA)) {
    LittleFS.remove(ARQUIVO_FILA);
    if (!LittleFS.rename(ARQUIVO_FILA_TMP, ARQUIVO_FILA)) return false;
  }
  return true;
}

void carregarFila() {
  flashPronta = LittleFS.begin();
  if (!flashPronta) {
    flashPronta = LittleFS.format() && LittleFS.begin();
  }
  if (!flashPronta) {
    Serial.println("Aviso: memória flash indisponível; os testes ficarão apenas em RAM.");
    return;
  }
  if (!LittleFS.exists(ARQUIVO_FILA) && LittleFS.exists(ARQUIVO_FILA_TMP)) {
    LittleFS.rename(ARQUIVO_FILA_TMP, ARQUIVO_FILA);
  } else if (LittleFS.exists(ARQUIVO_FILA_TMP)) {
    LittleFS.remove(ARQUIVO_FILA_TMP);
  }
  if (!LittleFS.exists(ARQUIVO_FILA)) return;

  File f = LittleFS.open(ARQUIVO_FILA, "r");
  if (!f) return;

  CabecalhoFila cab;
  bool ok = f.read((uint8_t *)&cab, sizeof(cab)) == sizeof(cab)
            && cab.magia == MAGIA_FILA
            && cab.tamanhoTeste == sizeof(Teste)
            && cab.total > 0 && cab.total <= TAMANHO_FILA;
  for (uint16_t i = 0; i < cab.total && ok; i++) {
    ok = f.read((uint8_t *)&fila[i], sizeof(Teste)) == sizeof(Teste);
    fila[i].brinco[sizeof(fila[i].brinco) - 1] = '\0';
  }
  f.close();

  filaInicio = 0;
  filaTotal = ok ? cab.total : 0;
  if (!ok || calcularCrcFila(cab.proximoSeq, cab.total) != cab.crc) {
    filaTotal = 0;
    Serial.println("Aviso: arquivo da fila na flash estava corrompido e foi ignorado.");
    LittleFS.remove(ARQUIVO_FILA);
    return;
  }
  proximoSeq = cab.proximoSeq ? cab.proximoSeq : (uint32_t)filaTotal + 1;
  for (int i = 0; i < filaTotal; i++) {
    if (fila[i].seq >= proximoSeq) proximoSeq = fila[i].seq + 1;
  }
  Serial.printf("Memória da placa: %d teste(s) salvo(s) à espera de envio ao servidor.\n", filaTotal);
}

void enfileirarTeste(Teste t) {
  t.seq = proximoSeq++;
  if (proximoSeq == 0) proximoSeq = 1;
  fila[(filaInicio + filaTotal) % TAMANHO_FILA] = t;
  filaTotal++;
  if (gravarFila()) {
    Serial.printf("Leituras da vaca %s salvas na placa (%d na fila).\n", t.brinco, filaTotal);
  } else {
    Serial.printf("Aviso: falha ao gravar na flash; vaca %s guardada em RAM (%d na fila).\n",
                  t.brinco, filaTotal);
  }
}

void apagarPrimeiroDaFila() {
  if (filaTotal <= 0) return;
  Teste removido = fila[filaInicio];
  filaInicio = (filaInicio + 1) % TAMANHO_FILA;
  filaTotal--;
  if (!gravarFila() && flashPronta) {
    Serial.println("Aviso: não foi possível atualizar a fila na flash.");
  }
  Serial.printf("Leituras da vaca %s apagadas da placa (%d restante(s) na fila).\n",
                removido.brinco, filaTotal);
}


// ---------- Teste dos 4 tetos ----------
// Igual a _normalizar_brinco em blueprints/testes.py: "br 102", "Br_102" -> "BR-102"
String normalizarBrinco(const String &bruto) {
  String r;
  bool sep = true;
  for (unsigned int i = 0; i < bruto.length(); i++) {
    char c = bruto[i];
    if (c == ' ' || c == '\t' || c == '_' || c == '-') {
      if (!sep) {
        r += '-';
        sep = true;
      }
    } else {
      if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
      r += c;
      sep = false;
    }
  }
  if (r.endsWith("-")) r.remove(r.length() - 1);
  return r;
}

void pedirBrinco() {
  Serial.println();
  if (filaTotal > 0) Serial.printf("(%d teste(s) salvo(s) na placa à espera de envio)\n", filaTotal);
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
    Serial.println();
    if (d[i].suspeito) {
      if (mastite) afetados += ", ";
      afetados += i + 1;
      mastite = true;
    }
  }
  if (mastite) Serial.printf("ALERTA: suspeita de mastite no(s) teto(s) %s\n", afetados.c_str());
  else Serial.println("Todos os tetos normais.");

  // Salva na memória flash ANTES do piscar do LED: mesmo se desligarem a placa já, não se perde
  enfileirarTeste(atual);
  esperaEnvio = 0;   // tenta enviar já se houver Wi-Fi
  sinalizar(mastite);

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
    String brinco = normalizarBrinco(linha);
    if (brinco.isEmpty()) {
      pedirBrinco();
    } else if (brinco.length() >= sizeof(atual.brinco)) {
      Serial.println("Brinco demasiado longo (máx. 50 caracteres).");
    } else if (filaTotal == TAMANHO_FILA) {
      // Melhor parar do que perder testes: a fila só esvazia com o servidor ao alcance
      Serial.println("Memória da placa cheia: ligue ao Wi-Fi do servidor antes de testar mais vacas.");
    } else {
      memset(&atual, 0, sizeof(atual));
      brinco.toCharArray(atual.brinco, sizeof(atual.brinco));
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
      Serial.println("Sem Wi-Fi: as leituras ficam salvas na placa até haver rede.");
    }
  }
  if (!ligado && millis() - momentoWifi >= esperaWifi) {
    if (estado == WL_NO_SSID_AVAIL) Serial.printf("Rede \"%s\" não encontrada.\n", WIFI_SSID);
    else if (estado == WL_WRONG_PASSWORD) Serial.println("Senha do Wi-Fi errada (WIFI_SENHA, no bloco CONFIGURAÇÃO).");
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
    Serial.println("Não foi possível criar a rede própria: a REDE_PROPRIA_SENHA (bloco CONFIGURAÇÃO) "
                   "precisa de 8 a 63 caracteres.");
    return;
  }
  String ip = WiFi.softAPIP().toString();
  Serial.printf("Rede própria \"%s\" criada. Ligue o PC a ela; no .env do PC: PLACA_URL=http://%s\n",
                REDE_PROPRIA_SSID, ip.c_str());
  Serial.printf("Teste no browser do PC: http://%s/read deve mostrar {\"cond\":...}\n", ip.c_str());
  Serial.println("As leituras salvas na placa são enviadas ao servidor assim que o PC se ligar.");
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

// O formato que o POST /api/testes espera (blueprints/testes.py). Inclui "seq" para não duplicar
// se o Wi-Fi cair depois de o servidor gravar mas antes de a confirmação chegar à placa.
String montarJson(const Teste &t) {
  String json = "{\"seq\":";
  json += t.seq;
  json += ",\"brinco\":\"";
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

// Garante que o servidor realmente gravou o teste no banco: exige "ok":true, "id" > 0 e a lista
// "tetos_afetados" completa (uma resposta cortada a meio pela queda do Wi-Fi não passa).
bool confirmadoPeloServidor(const String &resposta, long &idTeste) {
  int pOk = posicaoValor(resposta, "ok");
  if (pOk < 0 || !resposta.substring(pOk).startsWith("true")) return false;
  int pId = posicaoValor(resposta, "id");
  if (pId < 0) return false;
  idTeste = resposta.substring(pId).toInt();
  if (idTeste <= 0) return false;
  int pTetos = posicaoValor(resposta, "tetos_afetados");
  return pTetos >= 0 && resposta.indexOf(']', pTetos) > pTetos;
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
    Serial.println("Login: email ou senha errados (API_EMAIL/API_SENHA, no bloco CONFIGURAÇÃO), ou conta desativada.");
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
void compararComServidor(const Teste &t, const String &resposta, long idTeste) {
  Serial.printf("Teste #%ld da vaca %s confirmado pelo servidor.\n", idTeste, t.brinco);

  int p = posicaoValor(resposta, "tetos_afetados");
  if (p < 0 || resposta[p] != '[') return;
  bool servidor[4] = {false, false, false, false};
  for (int i = p + 1; i < (int)resposta.length() && resposta[i] != ']'; i++) {
    int teto = resposta[i] - '0';
    if (teto >= 1 && teto <= 4) servidor[teto - 1] = true;
  }
  // O servidor faz a mesma comparação entre tetos e ainda compara com o histórico da vaca:
  // pode achar mais tetos suspeitos do que a placa, nunca menos.
  for (int i = 0; i < 4; i++) {
    if (servidor[i] && !t.suspeito[i]) {
      Serial.printf("Teto %d: o servidor achou suspeita pelo histórico desta vaca (a placa não tem o "
                    "histórico). Vale o do servidor.\n", i + 1);
    } else if (!servidor[i] && t.suspeito[i]) {
      Serial.println("Atenção: o diagnóstico do servidor é diferente do da placa (vale o do servidor). "
                     "Confira se a secção Diagnóstico deste arquivo e servicos/diagnostico.py têm os mesmos limites.");
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
    long idTeste = 0;
    if (!confirmadoPeloServidor(resposta, idTeste)) {
      Serial.println("Envio: resposta incompleta do servidor; o teste continua salvo na placa.");
      return FALHA_REDE;
    }
    compararComServidor(t, resposta, idTeste);
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

// Envia o teste mais antigo da fila. Só apaga da placa quando há certeza de que o servidor gravou.
// Em falha de rede espera 5 s, 10 s, 20 s... até 5 min.
void enviarFila() {
  if (filaTotal == 0 || contaRecusada || !wifiLigado) return;
  if (esperaEnvio && millis() - momentoFalhaEnvio < esperaEnvio) return;

  Resultado r = enviarTeste(fila[filaInicio]);
  if (r == SUCESSO) {
    apagarPrimeiroDaFila();
    esperaEnvio = 0;
  } else if (r == FALHA_REDE || r == DADOS_RECUSADOS) {
    if (r == DADOS_RECUSADOS && filaTotal > 1) {
      // Nunca apaga sem certeza de gravação no servidor: passa para o fim da fila para não travar os outros
      fila[(filaInicio + filaTotal) % TAMANHO_FILA] = fila[filaInicio];
      filaInicio = (filaInicio + 1) % TAMANHO_FILA;
      gravarFila();
    }
    momentoFalhaEnvio = millis();
    esperaEnvio = esperaEnvio ? min(esperaEnvio * 2, ESPERA_ENVIO_MAX_MS) : ESPERA_ENVIO_MIN_MS;
    Serial.printf("Nova tentativa em %lu s (%d teste(s) salvo(s) na placa).\n",
                  esperaEnvio / 1000, filaTotal);
  } else {   // CONTA_RECUSADA: a fila continua salva na flash mesmo se desligar ou regravar a placa
    Serial.printf("Envio parado: %d teste(s) continuam salvos na placa.\n", filaTotal);
  }
}

// GET /fila: quando o servidor fala com a placa (REDE_PROPRIA 1 ou PLACA_URL), lê daqui o teste
// mais antigo salvo no curral. O teste NÃO é apagado no GET: só em POST /fila/confirmar.
void responderFila() {
  servidorLocal.sendHeader("Cache-Control", "no-store");
  if (filaTotal == 0) {
    servidorLocal.send(200, "application/json", "{\"pendentes\":0}");
    return;
  }
  const Teste &t = fila[filaInicio];
  String json = String("{\"pendentes\":") + filaTotal + ',' + montarJson(t).substring(1);
  servidorLocal.send(200, "application/json", json);
}

// POST /fila/confirmar: o servidor confirma que já gravou o teste no PostgreSQL (envia seq e id > 0).
// Só depois desta confirmação o teste é apagado da memória da placa.
void responderConfirmarFila() {
  servidorLocal.sendHeader("Cache-Control", "no-store");
  if (filaTotal == 0) {
    servidorLocal.send(404, "application/json", "{\"ok\":false,\"erro\":\"fila vazia\"}");
    return;
  }
  uint32_t seq = (uint32_t)servidorLocal.arg("seq").toInt();
  long idTeste = servidorLocal.arg("id").toInt();
  String tetos = servidorLocal.arg("tetos_afetados");
  if (seq == 0 || seq != fila[filaInicio].seq || idTeste <= 0) {
    servidorLocal.send(400, "application/json",
                       "{\"ok\":false,\"erro\":\"confirmação inválida\"}");
    return;
  }
  String resposta = String("{\"ok\":true,\"id\":") + idTeste
                    + ",\"tetos_afetados\":[" + tetos + "]}";
  compararComServidor(fila[filaInicio], resposta, idTeste);
  apagarPrimeiroDaFila();
  servidorLocal.send(200, "application/json",
                     String("{\"ok\":true,\"pendentes\":") + filaTotal + '}');
}


void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, HIGH);

  Serial.println();
  Serial.println("QuickMast: medidor de condutividade");
  carregarFila();
  WiFi.persistent(false);   // não grava a rede na flash a cada arranque
#if REDE_PROPRIA
  criarRedePropria();
#else
  Serial.printf("Servidor %s, conta %s\n", SERVIDOR_URL, API_EMAIL);
  if ((strncmp(SERVIDOR_URL, "https://", 8) == 0) != (USAR_HTTPS == 1)) {
    Serial.println("Aviso: SERVIDOR_URL e USAR_HTTPS não combinam (bloco CONFIGURAÇÃO).");
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
  servidorLocal.on("/fila", HTTP_GET, responderFila);
  servidorLocal.on("/fila/confirmar", HTTP_POST, responderConfirmarFila);
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
