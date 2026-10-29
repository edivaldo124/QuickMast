import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Landing } from './Landing'
import './landing.css'

// templates/index.html traz dentro de #landing uma versão simples (logo, título, Entrar),
// que fica sem JavaScript. O React troca-a pela landing completa no primeiro render.
const raiz = document.getElementById('landing')
if (raiz) {
  createRoot(raiz).render(
    <StrictMode>
      <Landing />
    </StrictMode>,
  )
}
