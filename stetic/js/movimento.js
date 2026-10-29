// Movimento e retorno ao toque, partilhados por todas as páginas do app (base.html).
// Com "reduzir movimento" ligado no sistema, tudo salta direto para o estado final.

function reduzirMovimento() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Número que conta do valor atual até ao novo (estatísticas, médias).
// formatar recebe o número já com as casas decimais do valor final.
function contar(el, valor, formatar = String) {
    const casas = Number.isInteger(valor) ? 0 : (String(valor).split('.')[1] || '').length;
    const de = parseFloat(el.textContent) || 0;
    if (reduzirMovimento() || de === valor) {
        el.textContent = formatar(valor);
        return;
    }
    const inicio = performance.now();
    const DURACAO = 700;
    const passo = agora => {
        const t = Math.min(1, (agora - inicio) / DURACAO);
        const k = 1 - Math.pow(1 - t, 3);   // desacelera no fim
        el.textContent = formatar(t < 1 ? Number((de + (valor - de) * k).toFixed(casas)) : valor);
        if (t < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
}

// Vibração curta no telemóvel: o operador pode estar a olhar para a vaca e não para o ecrã
function vibrar(padrao) {
    if (navigator.vibrate) navigator.vibrate(padrao);
}

// Volta a correr a animação de uma classe (sai e entra). i = posição na cascata (--i no CSS).
function revelar(el, classe, i = 0) {
    el.style.setProperty('--i', i);
    el.classList.remove(classe);
    void el.offsetWidth;   // o navegador tem de ver a classe sair para a animação recomeçar
    el.classList.add(classe);
}

// Listas com data-entrada: os itens entram em cascata só na primeira vez.
// Quando a lista volta a ser desenhada (um teste novo, um utilizador alterado), não deslizam outra vez.
function primeiraEntrada(lista) {
    setTimeout(() => lista.removeAttribute('data-entrada'), 800);
}

// Inclinação 3D que segue o rato ([data-tilt]). Só com rato: no toque, o dedo está a fazer outra coisa.
document.querySelectorAll('[data-tilt]').forEach(el => {
    el.addEventListener('pointermove', e => {
        if (e.pointerType !== 'mouse' || reduzirMovimento()) return;
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        el.style.setProperty('--incl-x', (-y * 8).toFixed(2) + 'deg');
        el.style.setProperty('--incl-y', (x * 10).toFixed(2) + 'deg');
    });
    el.addEventListener('pointerleave', () => {
        el.style.removeProperty('--incl-x');
        el.style.removeProperty('--incl-y');
    });
});
