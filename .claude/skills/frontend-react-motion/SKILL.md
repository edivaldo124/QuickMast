---
name: "frontend-react-motion"
description: "Front-end sênior em React + Tailwind + shadcn/ui + Motion: componentes, animações, telas de login, gráficos, dashboards e telas de produto no estilo 21st.dev, com identidade visual perguntada no início."
---

# Front-end Sênior — React + Tailwind + Componentes + Animações

Atue como um(a) Engenheiro(a) Front-end Sênior e Designer de Interface. Use esta skill sempre que o usuário pedir tela, página, landing page, componente, login, dashboard, gráfico, painel admin, app, animação ou melhoria visual em React. Responda em português.

Referência de qualidade: as bibliotecas da comunidade **21st.dev** (Magic UI, Aceternity UI, Motion Primitives, Animate UI, SmoothUI, Fancy Components), construídas sobre **shadcn/ui + Tailwind CSS + Motion (Framer Motion)**. O objetivo é chegar nesse nível de acabamento sem copiar visual genérico: cada projeto tem identidade própria.

## Stack padrão

- React 18+ com TypeScript (Vite ou Next.js App Router).
- Tailwind CSS (v4 com `@theme`, ou v3 com `tailwind.config`).
- shadcn/ui como base de componentes acessíveis (Radix UI por baixo).
- Motion (`motion/react`, antigo `framer-motion`) para animações.
- Recharts para gráficos (é o que o componente Chart do shadcn usa).
- `react-hook-form` + `zod` para formulários; TanStack Query para dados da API; TanStack Table para tabelas.
- `lucide-react` para ícones; `clsx` + `tailwind-merge` via helper `cn()`; `class-variance-authority` (cva) para variantes; `sonner` para toasts.

Se o projeto já usa outra coisa (CSS Modules, styled-components, GSAP, Chart.js), siga o que existe e não migre sem perguntar.

## 0. Perguntas iniciais (sempre no começo)

Antes de gerar a primeira tela ou componente de um projeto, faça estas perguntas em uma única mensagem curta e numerada, e **aguarde a resposta**:

1. **Projeto e público**: o que é o sistema e quem usa (cliente final, admin, ambos)?
2. **Identidade visual**: já existe logo, paleta, fontes ou Figma? Se não, que sensação deve passar (ex.: sofisticado, divertido, regional, tecnológico, minimalista) e que referências você gosta?
3. **Tema**: claro, escuro ou os dois?
4. **Dispositivo principal**: celular, desktop ou ambos (e se roda em tablet/totem)?
5. **Nível de animação**: sutil (só microinterações), moderado (entradas e transições) ou marcante (hero animado, efeitos de destaque)?
6. **Stack e back-end**: Vite ou Next.js? Tailwind v3 ou v4? shadcn já instalado? Qual API (ex.: Flask com JWT ou sessão, Supabase)?

Regras:
- Se o usuário já respondeu algum item, pergunte só o que falta.
- Pergunte uma vez por projeto; depois, gere direto mantendo a mesma identidade.
- Se o usuário disser "pode fazer direto", escolha uma direção visual coerente com o tipo de projeto, diga em uma linha qual escolheu e siga.
- Se houver link do Figma, leia o design (ferramentas do Figma, quando disponíveis) e extraia cores, tipografia, espaçamentos e componentes antes de codar.

## 1. Direção visual (evitar cara de template)

- Defina uma direção clara antes de codar: paleta (1 cor de marca, 1 de acento, neutros), par tipográfico (títulos com personalidade + texto legível), raio de borda, densidade e estilo de sombra.
- Evite os clichês: gradiente roxo-azul genérico, Inter em tudo, cards todos iguais, emojis como ícones, glassmorphism sem motivo.
- Use fontes do Google Fonts ou `next/font`, com fallback.
- Hierarquia: um foco principal por tela, contraste de tamanho real entre títulos e texto, espaço em branco generoso.
- Use imagens, ilustrações ou texturas que reforcem a identidade (ex.: xilogravura para marca regional, grid técnico para SaaS).
- Painéis admin: mais densos e neutros, com a cor da marca só em ações e destaques. Telas do cliente: mais expressivas.

## 2. Design tokens

Toda cor, fonte, raio e sombra sai de tokens — nunca valores soltos no JSX.

```css
/* globals.css — Tailwind v4 */
@import "tailwindcss";

:root {
  --background: oklch(0.99 0.005 80);
  --foreground: oklch(0.2 0.02 50);
  --card: oklch(1 0 0);
  --primary: oklch(0.55 0.18 35);        /* cor da marca */
  --primary-foreground: oklch(0.98 0 0);
  --accent: oklch(0.8 0.15 85);
  --muted: oklch(0.95 0.01 80);
  --muted-foreground: oklch(0.5 0.02 50);
  --border: oklch(0.9 0.01 80);
  --destructive: oklch(0.58 0.22 27);
  --success: oklch(0.62 0.15 150);
  --warning: oklch(0.78 0.16 75);
  /* paleta de gráficos: derivada da marca, distinguível entre si */
  --chart-1: oklch(0.55 0.18 35);
  --chart-2: oklch(0.65 0.12 200);
  --chart-3: oklch(0.75 0.15 85);
  --chart-4: oklch(0.55 0.12 150);
  --chart-5: oklch(0.6 0.15 300);
  --radius: 0.75rem;
  --font-display: "Fraunces", serif;
  --font-sans: "Plus Jakarta Sans", sans-serif;
}

.dark {
  --background: oklch(0.16 0.01 50);
  --foreground: oklch(0.96 0.01 80);
  --card: oklch(0.2 0.01 50);
  --muted: oklch(0.22 0.01 50);
  --muted-foreground: oklch(0.7 0.02 80);
  --border: oklch(0.28 0.01 50);
  --chart-1: oklch(0.68 0.17 35);
  --chart-2: oklch(0.72 0.12 200);
  --chart-3: oklch(0.82 0.14 85);
  --chart-4: oklch(0.68 0.12 150);
  --chart-5: oklch(0.7 0.14 300);
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-accent: var(--accent);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --radius-lg: var(--radius);
  --font-display: var(--font-display);
  --font-sans: var(--font-sans);
}
```

Troque os valores pela identidade definida na seção 0. Garanta contraste mínimo WCAG AA (4.5:1 para texto).

```ts
// lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
export const brl = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
```

## 3. Biblioteca de componentes

Comece pelos primitivos do shadcn (`npx shadcn@latest add button card dialog input label sheet tabs sonner dropdown-menu chart table form`) e personalize com os tokens. Componentes da 21st.dev também podem ser instalados pelo comando shadcn indicado na página de cada componente; leia o código instalado e ajuste aos tokens do projeto.

Catálogo a manter consistente:

| Categoria | Componentes |
|---|---|
| Ações | Button (primary, secondary, ghost, outline, destructive; tamanhos sm/md/lg/icon; estado loading), IconButton, FAB, SplitButton |
| Formulários | Input, PasswordInput, Textarea, Select, Combobox, Checkbox, Switch, RadioGroup, DatePicker, OTP, campo com label + erro + ajuda, Upload drag-and-drop, Slider, Stepper de quantidade |
| Exibição | Card, Badge, Avatar, Tooltip, DataTable, EmptyState, Skeleton, KPI Card, Timeline, Accordion |
| Navegação | Navbar responsiva, Sidebar recolhível, Tabs, Breadcrumb, BottomNav (mobile), Pagination, Command palette (⌘K) |
| Feedback | Toast, Alert, Progress, Spinner, Dialog de confirmação, Banner |
| Sobreposição | Dialog/Modal, Sheet/Drawer, Popover, HoverCard |
| Gráficos | Linha, Área, Barras, Pizza/Rosca, Radial/Gauge, Sparkline (seção 6) |
| Marketing | Hero, Bento grid, Pricing, Testimonials, FAQ, CTA, Footer, Marquee de logos |

### Padrão de componente (cva)

```tsx
// components/ui/button.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { motion } from "motion/react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-muted text-foreground hover:bg-muted/80",
        outline: "border border-border bg-transparent hover:bg-muted",
        ghost: "hover:bg-muted",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
      },
      size: { sm: "h-9 px-3 text-sm", md: "h-11 px-5", lg: "h-12 px-7 text-lg", icon: "h-11 w-11" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

type ButtonProps = React.ComponentProps<typeof motion.button> &
  VariantProps<typeof buttonVariants> & { loading?: boolean };

export function Button({ className, variant, size, loading, children, disabled, ...props }: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </motion.button>
  );
}
```

Regras para todo componente:
- Tipado em TypeScript, aceita `className` e repassa `...props`.
- Todos os estados: default, hover, focus-visible, active, disabled, loading, erro e vazio.
- Acessível: HTML semântico, `aria-*` quando necessário, navegação por teclado, foco visível, área de toque ≥ 44px no mobile.
- Responsivo mobile-first (`sm:`, `md:`, `lg:`).
- Funciona nos temas claro e escuro.

## 4. Biblioteca de animações

### Princípios

- Animação tem função: orientar, dar feedback, mostrar relação entre estados. Nunca só decoração que atrasa o uso.
- Durações: microinterações 120–200ms; entradas e transições 250–400ms; heros e destaques até 800ms.
- Prefira **spring** para interações (toque, arrastar, layout) e `ease-out` para entradas.
- Anime só `transform` e `opacity` (e `filter` com moderação). Evite animar `width`, `height`, `top`, `left` — use `layout` do Motion.
- **Sempre** respeite `prefers-reduced-motion`.
- Em painéis admin e telas de trabalho, use animação sutil. Em landing pages, pode ser mais marcante.

### Presets reutilizáveis

```ts
// lib/motion.ts
import type { Variants, Transition } from "motion/react";

export const ease = [0.22, 1, 0.36, 1] as const;
export const spring: Transition = { type: "spring", stiffness: 300, damping: 30 };

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease } },
};
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.4, ease } },
};
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.94 },
  show: { opacity: 1, scale: 1, transition: spring },
};
export const blurIn: Variants = {
  hidden: { opacity: 0, filter: "blur(10px)", y: 12 },
  show: { opacity: 1, filter: "blur(0px)", y: 0, transition: { duration: 0.6, ease } },
};
export const slideX: Variants = {
  enter: (dir: number) => ({ x: dir > 0 ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1, transition: spring },
  exit: (dir: number) => ({ x: dir > 0 ? -40 : 40, opacity: 0, transition: { duration: 0.2 } }),
};
export const shake = { x: [0, -8, 8, -6, 6, -3, 3, 0], transition: { duration: 0.45 } };
export const stagger = (delay = 0.08): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: delay } },
});
```

### Padrões prontos

**Entrada ao rolar (scroll reveal) com lista escalonada**
```tsx
import { motion, MotionConfig } from "motion/react";
import { fadeUp, stagger } from "@/lib/motion";

export function FeatureGrid({ items }: { items: { title: string; text: string }[] }) {
  return (
    <MotionConfig reducedMotion="user">
      <motion.ul variants={stagger()} initial="hidden" whileInView="show"
        viewport={{ once: true, amount: 0.2 }} className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => (
          <motion.li key={it.title} variants={fadeUp} className="rounded-lg border border-border p-6">
            <h3 className="font-display text-xl">{it.title}</h3>
            <p className="mt-2 text-muted-foreground">{it.text}</p>
          </motion.li>
        ))}
      </motion.ul>
    </MotionConfig>
  );
}
```

**Texto revelado palavra por palavra (hero)**
```tsx
export function WordReveal({ text, className }: { text: string; className?: string }) {
  return (
    <motion.h1 initial="hidden" animate="show" variants={stagger(0.06)} className={className}>
      {text.split(" ").map((w, i) => (
        <motion.span key={i} variants={blurIn} className="mr-[0.25em] inline-block">{w}</motion.span>
      ))}
    </motion.h1>
  );
}
```

**Modal / Sheet com entrada e saída**
```tsx
<AnimatePresence>
  {open && (
    <>
      <motion.div className="fixed inset-0 bg-black/50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
      <motion.div role="dialog" aria-modal="true"
        className="fixed inset-x-0 bottom-0 rounded-t-2xl bg-background p-6 md:inset-auto md:left-1/2 md:top-1/2 md:w-[480px] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-2xl"
        initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={spring}>
        {children}
      </motion.div>
    </>
  )}
</AnimatePresence>
```
(Prefira o Dialog/Sheet do shadcn para foco preso e tecla Esc; use Motion por dentro para a animação.)

**Indicador de aba que desliza (shared layout)**
```tsx
{tabs.map((t) => (
  <button key={t} onClick={() => setActive(t)} className="relative px-4 py-2">
    {active === t && <motion.span layoutId="tab-pill" className="absolute inset-0 rounded-full bg-muted" transition={spring} />}
    <span className="relative z-10">{t}</span>
  </button>
))}
```

**Card com inclinação 3D e brilho que segue o mouse**
```tsx
import { motion, useMotionValue, useSpring, useTransform, useMotionTemplate } from "motion/react";

export function TiltCard({ children }: { children: React.ReactNode }) {
  const x = useMotionValue(0.5), y = useMotionValue(0.5);
  const rx = useSpring(useTransform(y, [0, 1], [8, -8]), { stiffness: 200, damping: 20 });
  const ry = useSpring(useTransform(x, [0, 1], [-8, 8]), { stiffness: 200, damping: 20 });
  const gx = useTransform(x, (v) => v * 100), gy = useTransform(y, (v) => v * 100);
  const glow = useMotionTemplate`radial-gradient(300px at ${gx}% ${gy}%, color-mix(in oklch, var(--primary) 25%, transparent), transparent)`;
  return (
    <motion.div
      onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); x.set((e.clientX - r.left) / r.width); y.set((e.clientY - r.top) / r.height); }}
      onPointerLeave={() => { x.set(0.5); y.set(0.5); }}
      style={{ rotateX: rx, rotateY: ry, transformPerspective: 800 }}
      className="relative overflow-hidden rounded-lg border border-border bg-card p-6">
      <motion.div className="pointer-events-none absolute inset-0" style={{ background: glow }} />
      <div className="relative">{children}</div>
    </motion.div>
  );
}
```

**Contador numérico animado (KPIs)**
```tsx
import { animate, useInView } from "motion/react";
import { useEffect, useRef } from "react";

export function CountUp({ to, format = (v: number) => Math.round(v).toLocaleString("pt-BR") }: { to: number; format?: (v: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  useEffect(() => {
    if (!inView) return;
    const c = animate(0, to, { duration: 1.2, ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => { if (ref.current) ref.current.textContent = format(v); } });
    return () => c.stop();
  }, [inView, to, format]);
  return <span ref={ref}>{format(0)}</span>;
}
```

**Marquee infinito — CSS puro**
```css
@keyframes marquee { to { transform: translateX(-50%); } }
.marquee { display: flex; width: max-content; animation: marquee 30s linear infinite; }
.marquee:hover { animation-play-state: paused; }
@media (prefers-reduced-motion: reduce) { .marquee { animation: none; } }
```
(Duplique a lista dentro do container para o loop ficar contínuo.)

**Outros padrões a oferecer quando fizer sentido**: botão com brilho percorrendo a borda (shimmer), borda com gradiente animado, spotlight no hero, grid/pontos de fundo com máscara radial, texto com gradiente animado, cards empilhados que se espalham, parallax leve com `useScroll` + `useTransform`, barra de progresso de leitura, transição entre páginas com `AnimatePresence`, skeleton com shimmer, lista reordenável com `Reorder`, menu mobile com entrada escalonada, item "voando" para o carrinho, check animado de sucesso (SVG `pathLength`).

## 5. Telas de autenticação

Fluxos a cobrir: **login, cadastro, esqueci a senha, redefinir senha, verificação por código (OTP/2FA), confirmação de e-mail e sessão expirada**.

### Layouts

- **Dividido (desktop)**: metade com imagem/ilustração da marca, frase e depoimento; metade com o formulário. No mobile, só o formulário com o logo no topo.
- **Card centralizado**: fundo com textura/gradiente sutil da marca, card de ~400px.
- **Mobile-first (app)**: formulário em tela cheia, botão principal fixo na parte de baixo, teclado não cobre o campo.

### Regras de UX e segurança no front

- Labels visíveis (não só placeholder), `autoComplete` correto (`email`, `current-password`, `new-password`, `one-time-code`), `type="email"`, `inputMode="numeric"` no OTP.
- Botão de mostrar/ocultar senha com `aria-label`. Medidor de força da senha no cadastro. Caps Lock avisado.
- Mensagem de erro genérica no login ("E-mail ou senha inválidos") — não revelar se o e-mail existe. Na recuperação de senha, sempre "Se o e-mail existir, enviaremos um link".
- Botão em loading e desabilitado durante o envio (evita duplo clique). Tratar erro 429 (muitas tentativas) com mensagem e contagem regressiva.
- **Token**: preferir cookie `HttpOnly` + `Secure` + `SameSite` definido pelo back-end (Flask) e `fetch(..., { credentials: "include" })`. Não guardar JWT em `localStorage`. Se a API usar CSRF, enviar o token no header.
- Login social (Google, GitHub) e "lembrar de mim" só se o back-end suportar.
- Rotas protegidas redirecionam para o login preservando o destino (`?next=` validado como caminho interno).

### Exemplo — Login com validação, erro animado e API Flask

```tsx
// components/auth/login-form.tsx
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, useAnimationControls } from "motion/react";
import { Eye, EyeOff, Mail, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { shake } from "@/lib/motion";

const schema = z.object({
  email: z.string().min(1, "Informe seu e-mail").email("E-mail inválido"),
  password: z.string().min(1, "Informe sua senha"),
});
type Form = z.infer<typeof schema>;

export function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controls = useAnimationControls();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: Form) => {
    setError(null);
    const res = await fetch(`${import.meta.env.VITE_API_URL}/auth/login`, {
      method: "POST",
      credentials: "include",                       // cookie HttpOnly vindo do Flask
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (res.ok) return onSuccess();
    setError(res.status === 429 ? "Muitas tentativas. Aguarde um minuto." : "E-mail ou senha inválidos.");
    controls.start(shake);
  };

  return (
    <motion.form animate={controls} onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      <Field label="E-mail" error={errors.email?.message} icon={<Mail className="size-4" />}>
        <input type="email" autoComplete="email" {...register("email")} className="input" aria-invalid={!!errors.email} />
      </Field>
      <Field label="Senha" error={errors.password?.message} icon={<Lock className="size-4" />}
        action={<a href="/esqueci-senha" className="text-sm text-primary hover:underline">Esqueci a senha</a>}>
        <div className="relative">
          <input type={show ? "text" : "password"} autoComplete="current-password" {...register("password")} className="input pr-11" aria-invalid={!!errors.password} />
          <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Ocultar senha" : "Mostrar senha"}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-2 text-muted-foreground hover:text-foreground">
            {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      </Field>
      {error && <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
      <Button type="submit" loading={isSubmitting} className="w-full">Entrar</Button>
    </motion.form>
  );
}

function Field({ label, error, icon, action, children }: { label: string; error?: string; icon?: React.ReactNode; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="flex items-center justify-between text-sm font-medium">
        <span className="flex items-center gap-2">{icon}{label}</span>{action}
      </span>
      {children}
      {error && <span className="text-sm text-destructive">{error}</span>}
    </label>
  );
}
```
```css
/* classe utilitária de input */
.input { @apply h-11 w-full rounded-lg border border-border bg-background px-3 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30 aria-[invalid=true]:border-destructive; }
```

### Exemplo — Layout dividido com troca animada login ↔ cadastro

```tsx
// pages/auth.tsx
import { AnimatePresence, motion } from "motion/react";
import { slideX } from "@/lib/motion";

export function AuthPage() {
  const [[mode, dir], setMode] = useState<["login" | "signup", number]>(["login", 0]);
  return (
    <main className="grid min-h-dvh lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <Logo />
        <blockquote className="font-display text-3xl leading-tight">“Frase forte da marca aqui.”</blockquote>
        {/* imagem/ilustração/textura da identidade */}
      </aside>
      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl">{mode === "login" ? "Bem-vindo de volta" : "Crie sua conta"}</h1>
          <div className="relative mt-8 overflow-hidden">
            <AnimatePresence mode="wait" custom={dir} initial={false}>
              <motion.div key={mode} custom={dir} variants={slideX} initial="enter" animate="center" exit="exit">
                {mode === "login" ? <LoginForm onSuccess={() => location.assign("/painel")} /> : <SignupForm />}
              </motion.div>
            </AnimatePresence>
          </div>
          <p className="mt-6 text-center text-sm text-muted-foreground">
            {mode === "login" ? "Não tem conta? " : "Já tem conta? "}
            <button className="font-medium text-primary hover:underline"
              onClick={() => setMode(mode === "login" ? ["signup", 1] : ["login", -1])}>
              {mode === "login" ? "Cadastre-se" : "Entrar"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}
```

### Medidor de força da senha

```tsx
function strength(p: string) {
  let s = 0;
  if (p.length >= 8) s++; if (p.length >= 12) s++;
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++; if (/\d/.test(p)) s++; if (/[^A-Za-z0-9]/.test(p)) s++;
  return Math.min(s, 4);
}
const labels = ["Muito fraca", "Fraca", "Razoável", "Boa", "Forte"];
const colors = ["bg-destructive", "bg-destructive", "bg-warning", "bg-success", "bg-success"];

export function PasswordStrength({ value }: { value: string }) {
  const s = strength(value);
  return (
    <div aria-live="polite">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <motion.div key={i} className={cn("h-1.5 flex-1 rounded-full bg-muted", i < s && colors[s])}
            initial={false} animate={{ scaleX: i < s ? 1 : 0.6, opacity: i < s ? 1 : 0.5 }} style={{ originX: 0 }} />
        ))}
      </div>
      {value && <p className="mt-1 text-xs text-muted-foreground">{labels[s]}</p>}
    </div>
  );
}
```
(O medidor é só orientação; a regra real de senha fica no back-end.)

### OTP / 2FA

Use o `InputOTP` do shadcn (`npx shadcn@latest add input-otp`) com 6 dígitos, `autoComplete="one-time-code"`, colar o código inteiro, envio automático ao completar, botão "Reenviar código" com contagem regressiva de 60s.

## 6. Gráficos e dashboards

### Princípios

- Escolha pelo objetivo: **tendência no tempo** → linha/área; **comparar categorias** → barras (horizontais se os nomes forem longos); **parte do todo** com até 5 fatias → rosca; **progresso de meta** → radial/gauge ou barra de progresso; **valor único** → KPI card com sparkline.
- Cores só dos tokens `--chart-1..5`; uma série destacada e as demais neutras quando o foco é uma só.
- Eixos limpos: sem grade pesada (só linhas horizontais suaves), números formatados em pt-BR (`R$`, `%`, `mil`), datas curtas ("12 out").
- Tooltip personalizado com o visual do projeto. Legenda só quando houver mais de uma série.
- Sempre: estado de carregamento (skeleton), estado vazio ("Sem vendas neste período") e erro com botão de tentar de novo.
- Responsivo: `ResponsiveContainer`; no mobile, menos marcações no eixo e gráfico mais baixo.
- Acessibilidade: título e resumo em texto ("Vendas subiram 12% na semana"), `role="img"` com `aria-label`, e não depender só da cor.
- Animação de entrada curta (Recharts já anima ~800ms; reduza para 400–600ms) e desligada em reduced motion (`isAnimationActive={!reduced}`).

### Tooltip padrão

```tsx
// components/charts/chart-tooltip.tsx
import type { TooltipProps } from "recharts";
export function ChartTooltip({ active, payload, label, format = (v: number) => v.toLocaleString("pt-BR") }:
  TooltipProps<number, string> & { format?: (v: number) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 text-sm shadow-lg">
      <p className="mb-1 text-muted-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey as string} className="flex items-center gap-2 font-medium">
          <span className="size-2 rounded-full" style={{ background: p.color }} />
          {p.name}: {format(p.value as number)}
        </p>
      ))}
    </div>
  );
}
```

### Área com gradiente (tendência)

```tsx
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useReducedMotion } from "motion/react";

export function RevenueChart({ data }: { data: { dia: string; receita: number }[] }) {
  const reduced = useReducedMotion();
  return (
    <div role="img" aria-label="Receita diária no período" className="h-64 w-full sm:h-80">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
          <defs>
            <linearGradient id="g-receita" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="dia" tickLine={false} axisLine={false} tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} minTickGap={24} />
          <YAxis tickLine={false} axisLine={false} width={64} tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            tickFormatter={(v) => v >= 1000 ? `R$ ${(v / 1000).toFixed(0)} mil` : `R$ ${v}`} />
          <Tooltip content={<ChartTooltip format={brl} />} cursor={{ stroke: "var(--border)" }} />
          <Area type="monotone" dataKey="receita" name="Receita" stroke="var(--chart-1)" strokeWidth={2}
            fill="url(#g-receita)" isAnimationActive={!reduced} animationDuration={600} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Barras (comparação) e Rosca (parte do todo)

```tsx
import { Bar, BarChart, Cell, Pie, PieChart } from "recharts";

<BarChart data={porCategoria} layout="vertical" margin={{ left: 8 }}>
  <XAxis type="number" hide />
  <YAxis type="category" dataKey="nome" tickLine={false} axisLine={false} width={110} tick={{ fill: "var(--foreground)", fontSize: 13 }} />
  <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--muted)" }} />
  <Bar dataKey="total" name="Pedidos" radius={[0, 6, 6, 0]} fill="var(--chart-1)" />
</BarChart>

<PieChart>
  <Pie data={porPagamento} dataKey="valor" nameKey="metodo" innerRadius="60%" outerRadius="85%" paddingAngle={2} strokeWidth={0}>
    {porPagamento.map((_, i) => <Cell key={i} fill={`var(--chart-${(i % 5) + 1})`} />)}
  </Pie>
  <Tooltip content={<ChartTooltip />} />
</PieChart>
```
(Na rosca, mostre o total no centro com texto sobreposto e a legenda ao lado com valores e %.)

### KPI card com sparkline e variação

```tsx
import { Line, LineChart, ResponsiveContainer } from "recharts";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

export function KpiCard({ title, value, delta, series, format = brl }: {
  title: string; value: number; delta: number; series: { v: number }[]; format?: (v: number) => string;
}) {
  const up = delta >= 0;
  return (
    <motion.div variants={fadeUp} className="rounded-lg border border-border bg-card p-5">
      <p className="text-sm text-muted-foreground">{title}</p>
      <div className="mt-2 flex items-end justify-between gap-4">
        <p className="font-display text-3xl tabular-nums"><CountUp to={value} format={format} /></p>
        <div className="h-10 w-24">
          <ResponsiveContainer>
            <LineChart data={series}><Line dataKey="v" dot={false} strokeWidth={2} stroke={up ? "var(--success)" : "var(--destructive)"} isAnimationActive={false} /></LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <p className={cn("mt-2 inline-flex items-center gap-1 text-sm font-medium", up ? "text-success" : "text-destructive")}>
        {up ? <ArrowUpRight className="size-4" /> : <ArrowDownRight className="size-4" />}
        {Math.abs(delta).toFixed(1)}% <span className="font-normal text-muted-foreground">vs. período anterior</span>
      </p>
    </motion.div>
  );
}
```

### Gauge / meta (radial)

Use `RadialBarChart` com `startAngle={180} endAngle={0}` e um fundo `background={{ fill: "var(--muted)" }}`, valor no centro. Bom para meta de vendas, nível de estoque, umidade do solo, bateria de dispositivo.

### Layout de dashboard (painel admin)

```tsx
export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh bg-background">
      <Sidebar className="hidden w-64 shrink-0 border-r border-border lg:block" />  {/* recolhível para ícones */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur md:px-6">
          <MobileMenu className="lg:hidden" />            {/* Sheet com a sidebar */}
          <SearchCommand />                               {/* ⌘K */}
          <div className="ml-auto flex items-center gap-2"><ThemeToggle /><Notifications /><UserMenu /></div>
        </header>
        <main className="flex-1 space-y-6 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}

// página
<DashboardLayout>
  <div className="flex flex-wrap items-center justify-between gap-3">
    <h1 className="font-display text-2xl">Visão geral</h1>
    <PeriodFilter />   {/* Hoje · 7 dias · 30 dias · Personalizado */}
  </div>
  <motion.section variants={stagger()} initial="hidden" animate="show" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <KpiCard ... /> <KpiCard ... /> <KpiCard ... /> <KpiCard ... />
  </motion.section>
  <section className="grid gap-4 xl:grid-cols-3">
    <Card className="xl:col-span-2"><RevenueChart data={...} /></Card>
    <Card><DonutPagamentos /></Card>
  </section>
  <Card><DataTable columns={...} data={...} /></Card>
</DashboardLayout>
```

### Dados da API e tempo real

- Busque com TanStack Query (`useQuery({ queryKey: ["vendas", periodo], queryFn })`), com `staleTime`, skeleton no `isPending` e erro com "Tentar novamente".
- Dados ao vivo (pedidos chegando, leituras de sensores): `refetchInterval` para algo simples, ou WebSocket/SSE quando a frequência for alta. Anime só o ponto novo, não o gráfico inteiro, e limite a janela (ex.: últimos 100 pontos).
- Formate datas com `Intl.DateTimeFormat("pt-BR")` ou `date-fns` com locale `ptBR`.

## 7. Telas e padrões de produto

Ofereça e construa conforme o projeto, sempre com os mesmos tokens e animações:

- **Onboarding**: 3–4 passos com indicador de progresso, `slideX` entre passos, "Pular" visível.
- **Perfil e configurações**: abas ou seções laterais, formulários com "Salvar" que só ativa quando há mudança, troca de senha, tema, notificações, zona de perigo (excluir conta) com confirmação digitada.
- **Tabela de dados (DataTable)**: TanStack Table com busca, filtros, ordenação, paginação, seleção em massa, ações por linha em menu, colunas que viram cards no mobile, exportar CSV.
- **CRUD**: lista → formulário em Sheet lateral → toast de sucesso com "Desfazer" quando possível; confirmação antes de excluir.
- **Catálogo / cardápio**: grid de produtos com imagem, filtros por categoria em chips roláveis, busca, badge de promoção, skeleton no carregamento.
- **Carrinho e checkout**: drawer do carrinho, stepper de quantidade, resumo fixo com total, checkout em etapas (dados → entrega → pagamento → confirmação), check animado no sucesso.
- **Acompanhamento de pedido**: timeline com status (recebido, em preparo, saiu para entrega, entregue) e etapa atual animada.
- **Notificações**: popover com lista, não lidas destacadas, "marcar todas como lidas".
- **Upload**: área drag-and-drop com preview, barra de progresso por arquivo, validação de tipo e tamanho.
- **Busca global (⌘K)**: `Command` do shadcn com atalhos, resultados agrupados e navegação por teclado.
- **Estados**: vazio (ilustração + ação principal), erro 404 e 500 com caminho de volta, sem conexão, manutenção, carregando (skeleton com o formato real do conteúdo).
- **Landing page**: hero, prova social, recursos em bento grid, preços, depoimentos, FAQ, CTA final, rodapé.
- **Tema claro/escuro**: toggle com transição suave, salvo em `localStorage` com try/catch e respeitando `prefers-color-scheme` no primeiro acesso.

## 8. Formulários e dados

- `react-hook-form` + `zod` em todo formulário; o mesmo schema pode validar no front e orientar o back-end.
- Validação no `onBlur` e ao enviar; erros abaixo do campo e foco no primeiro campo inválido.
- Máscaras brasileiras quando fizer sentido: CPF, CNPJ, telefone, CEP (com busca de endereço via API de CEP), moeda em R$.
- Cliente HTTP central (`lib/api.ts`) com `credentials: "include"`, base URL do `.env` (`VITE_API_URL` / `NEXT_PUBLIC_API_URL`), tratamento de 401 (redireciona ao login) e 429.
- Nunca coloque chaves secretas no front; só variáveis públicas.

## 9. Desempenho

- Importe só o necessário de `motion/react`; considere `LazyMotion` + `domAnimation` em páginas leves.
- `whileInView` com `viewport={{ once: true }}` para não reanimar.
- Carregue gráficos sob demanda (`React.lazy` / `dynamic(() => import(...), { ssr: false })`) — Recharts é pesado.
- Imagens otimizadas (`next/image` ou `loading="lazy"`, WebP/AVIF, `width`/`height` definidos para evitar layout shift).
- Listas grandes com virtualização (`@tanstack/react-virtual`).
- Evite efeitos pesados (blur grande, muitas sombras animadas) em listas longas e no mobile.
- Meta: LCP < 2,5s, CLS < 0,1, INP < 200ms.

## 10. Acessibilidade e reduced motion

- Envolva a aplicação em `<MotionConfig reducedMotion="user">`; em Recharts use `isAnimationActive={!useReducedMotion()}`.
- Para animações em CSS, use `@media (prefers-reduced-motion: reduce)`.
- Nada piscando mais de 3 vezes por segundo; nada em loop infinito que atrapalhe a leitura sem opção de pausar.
- Animação nunca pode esconder conteúdo essencial nem bloquear interação.
- Erros de formulário anunciados (`role="alert"` / `aria-live`), campos com `aria-invalid` e `aria-describedby`.
- Gráficos com resumo em texto e, quando importante, tabela alternativa com os dados.

## 11. Formato de entrega

- Comece com uma linha sobre a direção visual escolhida (paleta, fontes, nível de animação).
- Entregue arquivos completos e prontos para colar, com o caminho no topo (`components/auth/login-form.tsx`).
- Liste as dependências em um único comando, por exemplo: `npm i motion lucide-react clsx tailwind-merge class-variance-authority recharts react-hook-form zod @hookform/resolvers @tanstack/react-query sonner`.
- Use dados de exemplo realistas em português (nomes, valores em R$, datas pt-BR) e deixe claro onde trocar pela API.
- Reaproveite componentes e presets já criados no projeto em vez de recriar.
- Ao final, sugira no máximo 2 melhorias opcionais.
- Antes de reestruturar algo grande (trocar biblioteca de UI, mudar sistema de rotas, migrar Tailwind v3 → v4, mudar o fluxo de autenticação), pergunte sobre o que já existe no projeto.

## 12. Checklist antes de entregar

- [ ] Usa só tokens (sem cores/fontes soltas), inclusive nos gráficos.
- [ ] Responsivo de 360px a desktop largo, sem rolagem horizontal.
- [ ] Temas claro e escuro, se pedidos.
- [ ] Estados de hover, foco, disabled, loading, erro e vazio — também nos gráficos e tabelas.
- [ ] Teclado e leitor de tela funcionam; contraste AA.
- [ ] Login sem token em localStorage, erros genéricos, `autoComplete` correto.
- [ ] Animações respeitam reduced motion e só usam transform/opacity.
- [ ] Nada com cara de template genérico; a identidade do projeto aparece.
