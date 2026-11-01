// Componentes da biblioteca no Figma criados pelo JavaScript (banner, item do histórico).
// Os que vêm prontos do servidor estão em templates/_componentes.html.

// Cria um elemento. textContent evita injetar HTML.
function criar(tag, classe, texto) {
    const el = document.createElement(tag);
    if (classe) el.className = classe;
    if (texto !== undefined && texto !== null) el.textContent = texto;
    return el;
}

// Ícone decorativo (o estado também está escrito ao lado)
function icone(classe) {
    const el = criar('span', 'ic ' + classe);
    el.setAttribute('aria-hidden', 'true');
    return el;
}

// ---------- Banner de diagnóstico: tipo = 'ok' | 'alerta' | 'analisando' ----------
const ICONE_BANNER = { ok: 'ic--check', alerta: 'ic--alerta', analisando: 'ic--carregando' };

function banner(el, tipo, mensagem, detalhes) {
    el.className = 'banner banner--' + tipo;
    el.setAttribute('role', tipo === 'alerta' ? 'alert' : 'status');
    const texto = criar('div', 'banner__texto');
    texto.append(criar('p', 'banner__mensagem', mensagem));
    (detalhes || []).forEach(d => texto.append(criar('p', 'banner__detalhe', d)));
    el.replaceChildren(icone('banner__icone ' + ICONE_BANNER[tipo]), texto);
}

function limparBanner(el) {
    el.className = '';
    el.removeAttribute('role');
    el.replaceChildren();
}

// ---------- Tetos: número no firmware → sigla, e a ordem em que aparecem no úbere ----------
const SIGLAS = { 1: 'AD', 2: 'AE', 3: 'PD', 4: 'PE' };
const ORDEM_UBERE = [2, 1, 4, 3];   // AE AD / PE PD, como no ecrã de medição

// "Teto AD", "Tetos AE e AD", "Tetos AE, AD e PD" (pela ordem do úbere)
function textoTetos(numeros) {
    const s = ORDEM_UBERE.filter(n => numeros.includes(n)).map(n => SIGLAS[n]);
    if (s.length === 1) return 'Teto ' + s[0];
    return 'Tetos ' + s.slice(0, -1).join(', ') + ' e ' + s[s.length - 1];
}

// Brinco: a etiqueta amarela com o número estampado (classe extra: tamanho ou lugar na grelha)
function brinco(texto, classe) {
    return criar('span', 'brinco' + (classe ? ' ' + classe : ''), texto);
}

// Mini-úbere: os 4 tetos na posição real, os suspeitos a vermelho (o texto ao lado diz o mesmo)
function miniUbere(suspeitos) {
    const el = criar('span', 'mini-ubere');
    el.setAttribute('aria-hidden', 'true');
    ORDEM_UBERE.forEach(n => el.append(criar('i', suspeitos.includes(n) ? 'mini-ubere__suspeito' : null)));
    return el;
}

// ---------- Item do histórico (uma linha). Com link, abre o histórico da vaca. ----------
function formatarData(iso) {
    const d = new Date(iso);
    const dois = n => String(n).padStart(2, '0');
    return dois(d.getDate()) + '/' + dois(d.getMonth() + 1) + '/' + d.getFullYear() +
           ' ' + dois(d.getHours()) + ':' + dois(d.getMinutes());
}

// Selo do resultado de um teste: "Normal" ou os tetos com suspeita
function seloTeste(t) {
    const selo = criar('span', 'selo ' + (t.tem_mastite ? 'selo--suspeita' : 'selo--normal'));
    selo.append(
        icone(t.tem_mastite ? 'ic--alerta' : 'ic--check'),
        criar('span', null, t.tem_mastite ? textoTetos(t.tetos_afetados) : 'Normal')
    );
    return selo;
}

// Estado de um teste: o mini-úbere por cima de "Normal" ou dos tetos com suspeita
function estadoTeste(t) {
    const estado = criar('span', 'item__estado');
    estado.append(
        miniUbere(t.tetos_afetados),
        criar('span', null, t.tem_mastite ? textoTetos(t.tetos_afetados) : 'Normal')
    );
    return estado;
}

// Nas linhas das listas: "hoje 08:36", "ontem 11:36", "28/10 11:36" (com o ano só se não for este)
function dataCurta(iso) {
    const d = new Date(iso);
    const dois = n => String(n).padStart(2, '0');
    const hora = dois(d.getHours()) + ':' + dois(d.getMinutes());
    const dia = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const hoje = new Date();
    const dias = Math.round((new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate()) - dia) / 864e5);
    if (dias === 0) return 'hoje ' + hora;
    if (dias === 1) return 'ontem ' + hora;
    const ano = d.getFullYear() === hoje.getFullYear() ? '' : '/' + d.getFullYear();
    return dois(d.getDate()) + '/' + dois(d.getMonth() + 1) + ano + ' ' + hora;
}

function dataItem(iso) {
    const el = criar('time', 'item__data', dataCurta(iso));
    el.dateTime = iso;
    el.title = formatarData(iso);
    return el;
}

function itemHistorico(t, comLink) {
    const item = criar(comLink ? 'a' : 'div', 'item' + (t.tem_mastite ? ' item--suspeita' : ''));
    if (comLink) item.href = '/vacas/' + encodeURIComponent(t.vaca);

    item.append(
        brinco(t.vaca, 'item__vaca'),   // .item__vaca: a procura do ubere.js filtra pelo texto dele
        dataItem(t.data),
        criar('span', 'item__operador', t.operador || '-'),
        estadoTeste(t)
    );
    return item;
}
