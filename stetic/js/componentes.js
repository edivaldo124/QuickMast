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

// ---------- Item do histórico (cartão). Com link, abre o histórico da vaca. ----------
function formatarData(iso) {
    const d = new Date(iso);
    const dois = n => String(n).padStart(2, '0');
    return dois(d.getDate()) + '/' + dois(d.getMonth() + 1) + '/' + d.getFullYear() +
           ' ' + dois(d.getHours()) + ':' + dois(d.getMinutes());
}

function itemHistorico(t, comLink) {
    const item = criar(comLink ? 'a' : 'div', 'cartao item');
    if (comLink) item.href = '/vacas/' + encodeURIComponent(t.vaca);

    const selo = criar('span', 'selo ' + (t.tem_mastite ? 'selo--suspeita' : 'selo--normal'));
    selo.append(
        icone(t.tem_mastite ? 'ic--alerta' : 'ic--check'),
        criar('span', null, t.tem_mastite ? 'Teto(s) ' + t.tetos_afetados.join(', ') : 'Normal')
    );

    item.append(
        criar('span', 'item__data', formatarData(t.data)),
        criar('span', 'item__operador', t.operador || '-'),
        criar('span', 'item__vaca', t.vaca),
        selo
    );
    return item;
}
