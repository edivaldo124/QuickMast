import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useMotionValueEvent, useReducedMotion, useScroll } from 'motion/react'
import { LogoQuickMast } from './LogoQuickMast'
import { MANCHETES } from './manchetes'

// A cena 3D (three + R3F) só começa a descarregar depois de a página estar pronta:
// o texto e o botão Entrar nunca esperam por ela.
const UbereScene = lazy(() => import('./three/UbereScene'))

// A abertura sai mesmo que o evento load demore (rede lenta no curral)
const ESPERA_MAXIMA = 2500

function classeDaManchete(i: number, ativa: number) {
  return i === ativa ? 'manchete--ativa' : i < ativa ? 'manchete--antes' : 'manchete--depois'
}

export function Landing() {
  const [paginaPronta, setPaginaPronta] = useState(false)
  const [cenaPronta, setCenaPronta] = useState(false)
  const [ativa, setAtiva] = useState(0)
  const [noEcra, setNoEcra] = useState(true)
  const indiceRef = useRef(0)
  const trilhoRef = useRef<HTMLElement>(null)
  const enchimentoRef = useRef<HTMLSpanElement>(null)
  const valorRef = useRef<HTMLSpanElement>(null)
  const reduzir = useReducedMotion() ?? false

  // 0 com o topo do trilho no topo do ecrã, 1 quando o fim dele chega ao fundo do ecrã
  const { scrollYProgress } = useScroll({ target: trilhoRef, offset: ['start start', 'end end'] })

  // O medidor muda por ref e a manchete só quando troca: nada de setState a cada quadro
  function mostrarProgresso(valor: number) {
    const p = Math.min(1, Math.max(0, valor))
    if (enchimentoRef.current) enchimentoRef.current.style.transform = `scaleY(${Math.max(0.04, p)})`
    if (valorRef.current) valorRef.current.textContent = String(Math.round(p * 100)).padStart(2, '0')
    const proxima = Math.min(MANCHETES.length - 1, Math.floor(p * MANCHETES.length))
    if (indiceRef.current !== proxima) {
      indiceRef.current = proxima
      setAtiva(proxima)
    }
  }
  useMotionValueEvent(scrollYProgress, 'change', mostrarProgresso)
  // A página pode abrir já a meio (ao recarregar)
  useEffect(() => mostrarProgresso(scrollYProgress.get()), [scrollYProgress])

  // Abertura: sai quando a página e as fontes estão prontas
  useEffect(() => {
    document.body.classList.add('landing-carregando')
    const pagina = new Promise<void>(resolve => {
      if (document.readyState === 'complete') resolve()
      else window.addEventListener('load', () => resolve(), { once: true })
    })
    const vigia = window.setTimeout(() => setPaginaPronta(true), ESPERA_MAXIMA)
    Promise.all([pagina, document.fonts?.ready]).then(() => setPaginaPronta(true))
    return () => {
      window.clearTimeout(vigia)
      document.body.classList.remove('landing-carregando')
    }
  }, [])

  useEffect(() => {
    if (paginaPronta) document.body.classList.remove('landing-carregando')
  }, [paginaPronta])

  // Já no rodapé, a cena deixa de desenhar quadros
  useEffect(() => {
    const trilho = trilhoRef.current
    if (!trilho) return
    const observador = new IntersectionObserver(([registo]) => setNoEcra(registo.isIntersecting))
    observador.observe(trilho)
    return () => observador.disconnect()
  }, [])

  // "Continuar": desce até ao início da manchete n
  function irPara(n: number) {
    const trilho = trilhoRef.current
    if (!trilho) return
    const inicio = trilho.getBoundingClientRect().top + window.scrollY
    const percurso = trilho.offsetHeight - window.innerHeight
    window.scrollTo({ top: inicio + (percurso * n) / MANCHETES.length + 2, behavior: reduzir ? 'auto' : 'smooth' })
  }

  return (
    <>
      <div className={'abertura' + (paginaPronta ? ' abertura--fim' : '')} aria-hidden={paginaPronta} aria-live="polite">
        <div className="abertura__topo">
          <span className="landing__marca"><LogoQuickMast className="landing__logo" />QuickMast</span>
          <span>Detetor de mastite</span>
        </div>
        <div className="abertura__centro">
          <p className="micro">A preparar a sonda</p>
          <span className="abertura__barra" aria-hidden="true"><span /></span>
          <p className="micro abertura__estado">A carregar</p>
        </div>
        <div className="abertura__base">
          <span>Quatro tetos</span>
          <span>Uma sonda</span>
        </div>
      </div>

      <div className="landing">
        <section className="trilho" id="topo" ref={trilhoRef} aria-labelledby="landingTitulo">
          <h1 id="landingTitulo" className="sr-only">Quick Mast – Detetor rápido de mastite</h1>

          <div className={'trilho__cena' + (cenaPronta ? ' trilho__cena--pronta' : '')} aria-hidden="true">
            <div className="cena-reserva"><LogoQuickMast /></div>
            {paginaPronta && (
              <Suspense fallback={null}>
                <UbereScene progresso={scrollYProgress} ativa={noEcra} aoFicarPronta={() => setCenaPronta(true)} />
              </Suspense>
            )}
          </div>
          <div className="trilho__veu" aria-hidden="true" />

          <div className="palco">
            <header className="landing__nav">
              <a className="landing__marca" href="#topo"><LogoQuickMast className="landing__logo" />QuickMast</a>
              <a className="landing__entrar" href="/login">Entrar</a>
            </header>

            <div className="manchetes">
              <div className="manchetes__pilha" aria-live="polite">
                {MANCHETES.map((m, i) => (
                  <div className={'manchete ' + classeDaManchete(i, ativa)} key={m.titulo.join(' ')} inert={i !== ativa}>
                    <p className="micro sobretitulo">
                      <span className={'ponto-estado' + (cenaPronta ? ' ponto-estado--pronto' : '')} />
                      {m.sobretitulo}
                    </p>
                    <h2>
                      {m.titulo.map(linha => (
                        <span className="manchete__linha" key={linha}><span>{linha}</span></span>
                      ))}
                    </h2>
                    <div className="manchete__base">
                      <p>{m.detalhe}</p>
                      {i < MANCHETES.length - 1 ? (
                        <button type="button" className="seta-circulo" onClick={() => irPara(i + 1)}>
                          <span>Continuar</span>
                          <span className="seta-circulo__icone seta-circulo__icone--baixo" aria-hidden="true" />
                        </button>
                      ) : (
                        <a className="seta-circulo" href="/login">
                          <span>Entrar</span>
                          <span className="seta-circulo__icone" aria-hidden="true" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="medidor" aria-hidden="true">
              <span className="micro medidor__rotulo">Desça para medir os quatro tetos</span>
              <span className="medidor__linha"><span ref={enchimentoRef} /></span>
              <span ref={valorRef} className="micro medidor__valor">00</span>
            </div>
          </div>
        </section>

        <footer className="landing__rodape">
          <span className="landing__marca"><LogoQuickMast className="landing__logo" />QuickMast</span>
          <p>Detetor rápido de mastite</p>
          <a className="landing__entrar" href="/login">Entrar</a>
        </footer>
      </div>
    </>
  )
}
