import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const SAIDA = fileURLToPath(new URL('../stetic/landing', import.meta.url))
const PARCIAL = fileURLToPath(new URL('../templates/_landing_assets.html', import.meta.url))

// O Nginx guarda /stetic/ por 7 dias, por isso os ficheiros levam hash no nome. Este plugin escreve
// templates/_landing_assets.html com os nomes do build, para o index.html os incluir com url_for.
function parcialJinja(): Plugin {
  return {
    name: 'quickmast:parcial-jinja',
    apply: 'build',
    writeBundle(_opcoes, bundle) {
      const entrada = Object.values(bundle).find(f => f.type === 'chunk' && f.isEntry)
      if (!entrada || entrada.type !== 'chunk') throw new Error('O build não tem ponto de entrada.')
      const url = (ficheiro: string) => `{{ url_for('static', filename='landing/${ficheiro}') }}`
      const linhas = [
        '{# Gerado por frontend/vite.config.ts (npm run build). Não editar à mão: os nomes levam hash. #}',
        '{% macro estilos() -%}',
        ...[...(entrada.viteMetadata?.importedCss ?? [])].map(f => `<link rel="stylesheet" href="${url(f)}">`),
        '{%- endmacro %}',
        '{% macro scripts() -%}',
        ...entrada.imports.map(f => `<link rel="modulepreload" href="${url(f)}">`),
        `<script type="module" src="${url(entrada.fileName)}"></script>`,
        '{%- endmacro %}',
        '',
      ]
      writeFileSync(PARCIAL, linhas.join('\n'))
    },
  }
}

export default defineConfig(({ command }) => ({
  // Caminhos relativos: os chunks carregados depois (a cena 3D) resolvem-se a partir do próprio ficheiro
  base: './',
  // No `npm run dev` o stetic/ serve de pasta pública (quickmast.css e fontes); no build não é copiado
  publicDir: command === 'serve' ? '../stetic' : false,
  plugins: [react(), parcialJinja()],
  build: {
    outDir: SAIDA,
    emptyOutDir: true,
    target: 'es2022',
    modulePreload: { polyfill: false },
    rolldownOptions: {
      input: fileURLToPath(new URL('./src/main.tsx', import.meta.url)),
    },
  },
}))
