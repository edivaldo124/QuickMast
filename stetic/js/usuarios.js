const msg = document.getElementById('mensagem');
const lista = document.getElementById('listaUsuarios');
const formNovo = document.getElementById('formNovoUsuario');
const btnCadastrar = document.getElementById('btnCadastrar');
const camposForm = {
    nome: document.getElementById('novoNome'),
    email: document.getElementById('novoEmail'),
    perfil: document.getElementById('novoPerfil'),
    senha: document.getElementById('novoSenha')
};
const PERFIS = ['operador', 'veterinario', 'admin'];
const NOMES_PERFIL = { operador: 'Operário', veterinario: 'Veterinário', admin: 'Administrador' };
const MEU_ID = Number(document.body.dataset.meuId);
let apagarGuardado = null;   // o "Guardado." some sozinho; um erro fica até à próxima alteração

function limparErrosForm() {
    Object.values(camposForm).forEach(c => c?.removeAttribute('aria-invalid'));
}

Object.values(camposForm).forEach(c => {
    c?.addEventListener('input', () => c.removeAttribute('aria-invalid'));
});

async function cadastrar(e) {
    e.preventDefault();
    limparErrosForm();
    let r = null;
    let corpoResp = {};
    try {
        r = await fetch('/api/usuarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome: camposForm.nome.value.trim(),
                email: camposForm.email.value.trim(),
                perfil: camposForm.perfil.value,
                senha: camposForm.senha.value
            })
        });
        corpoResp = (await r.json()) || {};
    } catch (err) {
        corpoResp = { erro: 'Erro de comunicação com o servidor.' };
    } finally {
        delete formNovo.dataset.aEnviar;
        btnCadastrar.removeAttribute('aria-busy');
    }

    clearTimeout(apagarGuardado);
    if (r && r.ok) {
        formNovo.reset();
        banner(msg, 'ok', (NOMES_PERFIL[corpoResp.perfil] || 'Utilizador') + ' ' + corpoResp.nome + ' cadastrado.');
        apagarGuardado = setTimeout(() => limparBanner(msg), 4000);
        await carregar();
        lista.querySelector('[data-id="' + corpoResp.id + '"]')?.classList.add('cartao--guardado');
    } else {
        banner(msg, 'alerta', corpoResp.erro || 'Não foi possível cadastrar.');
        const alvo = camposForm[corpoResp.campo];
        if (alvo) {
            alvo.setAttribute('aria-invalid', 'true');
            alvo.focus();
        }
    }
}

formNovo?.addEventListener('submit', cadastrar);

async function alterar(id, campos) {
    const r = await fetch('/api/usuarios/' + id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(campos)
    });
    const corpoResp = await r.json();
    clearTimeout(apagarGuardado);
    if (r.ok) {
        banner(msg, 'ok', 'Guardado.');
        apagarGuardado = setTimeout(() => limparBanner(msg), 4000);
    } else {
        banner(msg, 'alerta', corpoResp.erro);
    }
    await carregar();
    // O cartão alterado acende um instante (a lista foi desenhada de novo)
    if (r.ok) lista.querySelector('[data-id="' + id + '"]')?.classList.add('cartao--guardado');
}

// Linha de um utilizador: inicial, nome, email, Perfil (lista) e Ativo (interruptor com Sim/Não)
function cartao(u) {
    const eu = u.id === MEU_ID;
    const li = criar('li', 'usuario' + (u.ativo ? '' : ' usuario--inativo'));
    li.dataset.id = u.id;

    const avatar = criar('span', 'avatar avatar--usuario', u.nome.slice(0, 1).toUpperCase());
    avatar.setAttribute('aria-hidden', 'true');
    const texto = criar('div', 'usuario__texto');
    texto.append(
        criar('p', 'usuario__nome', u.nome + (eu ? ' (você)' : '')),
        criar('p', 'usuario__email', u.email)
    );
    const cabecalho = criar('div', 'usuario__cabecalho');
    cabecalho.append(avatar, texto);

    const sel = criar('select', 'seletor');
    sel.id = 'perfil-' + u.id;
    PERFIS.forEach(p => {
        const o = document.createElement('option');
        o.value = p; o.textContent = NOMES_PERFIL[p]; o.selected = p === u.perfil;
        sel.appendChild(o);
    });
    sel.disabled = eu;
    sel.addEventListener('change', () => alterar(u.id, { perfil: sel.value }));

    const rotuloPerfil = criar('label', 'linha__rotulo', 'Perfil');
    rotuloPerfil.htmlFor = sel.id;
    const linhaPerfil = criar('div', 'linha linha--perfil');
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
    const linhaAtivo = criar('label', 'linha linha--ativo');
    linhaAtivo.append(criar('span', 'linha__rotulo', 'Ativo'), estado, chk);

    li.append(cabecalho, linhaPerfil, linhaAtivo);
    return li;
}

async function carregar() {
    const r = await fetch('/api/usuarios');
    if (!r.ok) {
        lista.replaceChildren();   // sai o esqueleto
        banner(msg, 'alerta', 'Sem permissão.');
        return;
    }
    const usuarios = await r.json();
    lista.replaceChildren(...usuarios.map(cartao));
    primeiraEntrada(lista);
}

carregar();
