const msg = document.getElementById('mensagem');
const lista = document.getElementById('listaUsuarios');
const PERFIS = ['operador', 'veterinario', 'admin'];
const MEU_ID = Number(document.body.dataset.meuId);

async function alterar(id, campos) {
    const r = await fetch('/api/usuarios/' + id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(campos)
    });
    const corpoResp = await r.json();
    if (r.ok) banner(msg, 'ok', 'Guardado.');
    else banner(msg, 'alerta', corpoResp.erro);
    carregar();
}

// Cartão de um utilizador: nome, email, Perfil (lista) e Ativo (interruptor com Sim/Não)
function cartao(u) {
    const eu = u.id === MEU_ID;
    const li = criar('li', 'cartao cartao-usuario');

    const cabecalho = criar('div', 'cartao-usuario__cabecalho');
    cabecalho.append(
        criar('p', 'cartao-usuario__nome', u.nome + (eu ? ' (você)' : '')),
        criar('p', 'cartao-usuario__email', u.email)
    );

    const sel = criar('select', 'seletor');
    sel.id = 'perfil-' + u.id;
    PERFIS.forEach(p => {
        const o = document.createElement('option');
        o.value = p; o.textContent = p; o.selected = p === u.perfil;
        sel.appendChild(o);
    });
    sel.disabled = eu;
    sel.addEventListener('change', () => alterar(u.id, { perfil: sel.value }));

    const rotuloPerfil = criar('label', 'linha__rotulo', 'Perfil');
    rotuloPerfil.htmlFor = sel.id;
    const linhaPerfil = criar('div', 'linha');
    linhaPerfil.append(rotuloPerfil, sel);

    const chk = criar('input', 'interruptor');
    chk.type = 'checkbox'; chk.checked = u.ativo; chk.disabled = eu;
    chk.setAttribute('role', 'switch');
    const estado = criar('span', 'linha__estado', u.ativo ? 'Sim' : 'Não');
    estado.setAttribute('aria-hidden', 'true');
    chk.addEventListener('change', () => {
        estado.textContent = chk.checked ? 'Sim' : 'Não';
        alterar(u.id, { ativo: chk.checked });
    });

    // A linha inteira é o rótulo: tocar em qualquer ponto liga/desliga
    const linhaAtivo = criar('label', 'linha');
    linhaAtivo.append(criar('span', 'linha__rotulo', 'Ativo'), estado, chk);

    li.append(cabecalho, linhaPerfil, linhaAtivo);
    return li;
}

async function carregar() {
    const r = await fetch('/api/usuarios');
    if (!r.ok) { banner(msg, 'alerta', 'Sem permissão.'); return; }
    const usuarios = await r.json();
    lista.replaceChildren(...usuarios.map(cartao));
}

carregar();
