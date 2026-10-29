// O ícone do QuickMast (stetic/img/logo-icone.svg) em linha: não depende do caminho do /stetic
// e serve de reserva enquanto a cena 3D não chega (ou se o aparelho não tiver WebGL).
export function LogoQuickMast({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" aria-hidden="true" focusable="false">
      <rect width="120" height="120" rx="30" fill="#2E7D32" />
      <circle cx="41" cy="41" r="19" fill="#FFFFFF" />
      <circle cx="79" cy="41" r="19" fill="#FFFFFF" />
      <circle cx="41" cy="79" r="19" fill="#FFFFFF" />
      <circle cx="79" cy="79" r="21" fill="#C62828" stroke="#FFFFFF" strokeWidth="5" />
      <rect x="76" y="66" width="6" height="16" rx="3" fill="#FFFFFF" />
      <circle cx="79" cy="89" r="3.4" fill="#FFFFFF" />
    </svg>
  )
}
