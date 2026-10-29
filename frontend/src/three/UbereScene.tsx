import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { PerformanceMonitor } from '@react-three/drei'
import { easing } from 'maath'
import { useReducedMotion, type MotionValue } from 'motion/react'
import { useEffect, useMemo, useRef, useState, type Ref } from 'react'
import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { toCreasedNormals } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import { MANCHETES } from '../manchetes'
import { cores } from '../tokens'

type Props = {
  progresso: MotionValue<number>   // 0 a 1 ao longo do trilho (Landing.tsx)
  ativa: boolean                   // fora do ecrã não desenha quadros
  aoFicarPronta: () => void        // primeiro quadro desenhado: o logo SVG de reserva pode sair
}

// O ícone do QuickMast em volume: a placa verde com os quatro tetos. Ao descer, a sonda mede os
// tetos pela ordem do firmware, o teto 3 fica em suspeita e a placa acaba de frente, igual ao logo.

// Tetos como no ecrã de medição, vistos de frente: AE | AD em cima, PE | PD em baixo.
// n = número do teto no firmware, que é também a ordem de medição.
const TETOS = [
  { n: 1, x: 0.38, y: 0.38 },    // AD
  { n: 2, x: -0.38, y: 0.38 },   // AE
  { n: 3, x: 0.38, y: -0.38 },   // PD: o da suspeita, no sítio do "!" do logo
  { n: 4, x: -0.38, y: -0.38 },  // PE
]
const PONTA_Z = 0.77   // ponta dos tetos; a frente da placa está em z = 0.21

// Uma parte do scroll por manchete; dentro da 2.ª ("Ao vivo"), um quarto por teto
const PARTE = 1 / MANCHETES.length
const PASSO_TETO = PARTE / 4

type Estado = 'vazio' | 'a-ler' | 'sadio' | 'suspeita' | 'logo'

const COR_ESTADO: Record<Estado, THREE.Color> = {
  vazio: new THREE.Color(cores.tetoVazio),
  'a-ler': new THREE.Color(cores.aLer),
  sadio: new THREE.Color(cores.sadio),
  suspeita: new THREE.Color(cores.suspeita),
  logo: new THREE.Color(cores.branco),
}

// O teto que a sonda está a medir (1 a 4)
function tetoEmLeitura(p: number) {
  return Math.min(4, Math.max(1, Math.floor((p - PARTE) / PASSO_TETO) + 1))
}

// Como no app: vazio → a ler → sadio; o teto 3 acaba em suspeita e os outros voltam ao branco do logo
function estadoDoTeto(n: number, p: number): Estado {
  if (p < PARTE) return 'vazio'
  if (p < 2 * PARTE) {
    const atual = tetoEmLeitura(p)
    return n < atual ? 'sadio' : n === atual ? 'a-ler' : 'vazio'
  }
  if (p < 3 * PARTE + 0.03) return n === 3 && p > 2 * PARTE + 0.03 ? 'suspeita' : 'sadio'
  return n === 3 ? 'suspeita' : 'logo'
}

// Rotação da placa em cada fronteira de manchete; entre elas, uma curva suave
const POSES: [number, number, number][] = [
  [-0.3, -0.72, 0.1],    // início: de lado, com os tetos em relevo
  [-0.34, 0.4, -0.05],   // a medição começa
  [-0.3, -0.32, 0.03],   // os quatro medidos
  [-0.1, 0.3, 0],        // o teto 3 vira-se para a câmara
  [0, 0, 0],             // fim: de frente, é o logo
]
const POSE_PARADA: [number, number, number] = [-0.22, 0.34, 0]   // com movimento reduzido

function poseEm(p: number, alvo: THREE.Euler) {
  const s = Math.min(POSES.length - 1, Math.max(0, p * (POSES.length - 1)))
  const i = Math.min(POSES.length - 2, Math.floor(s))
  const t = s - i
  const k = t * t * (3 - 2 * t)
  const a = POSES[i]
  const b = POSES[i + 1]
  alvo.set(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)
}

// Placa quadrada com os cantos do logo (rx 30 em 120) e as arestas chanfradas
function criarPlaca(lado: number, raio: number, espessura: number, chanfro: number) {
  const s = lado / 2 - chanfro
  const r = raio - chanfro
  const forma = new THREE.Shape()
  forma.moveTo(-s + r, -s)
  forma.lineTo(s - r, -s)
  forma.absarc(s - r, -s + r, r, -Math.PI / 2, 0, false)
  forma.lineTo(s, s - r)
  forma.absarc(s - r, s - r, r, 0, Math.PI / 2, false)
  forma.lineTo(-s + r, s)
  forma.absarc(-s + r, s - r, r, Math.PI / 2, Math.PI, false)
  forma.lineTo(-s, -s + r)
  forma.absarc(-s + r, -s + r, r, Math.PI, Math.PI * 1.5, false)
  const geometria = new THREE.ExtrudeGeometry(forma, {
    depth: espessura - 2 * chanfro,
    bevelEnabled: true,
    bevelThickness: chanfro,
    bevelSize: chanfro,
    bevelSegments: 5,
    curveSegments: 24,
  })
  geometria.center()
  return toCreasedNormals(geometria, 0.4)
}

// A sonda chega na diagonal, de cima e da esquerda: a pega fica dentro do quadro (no telemóvel,
// longe do botão Entrar) e vê-se de lado mesmo com a placa quase de frente
const DIRECAO_SONDA = new THREE.Vector3(-0.32, 0.5, 1).normalize()
const ROTACAO_SONDA = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), DIRECAO_SONDA)

function Sonda({ ref }: { ref: Ref<THREE.Group> }) {
  return (
    <group ref={ref} quaternion={ROTACAO_SONDA} scale={0.001}>
      <mesh position={[0, 0.49, 0]}>
        <cylinderGeometry args={[0.026, 0.026, 0.9, 16]} />
        <meshStandardMaterial color={cores.aco} metalness={0.85} roughness={0.28} />
      </mesh>
      <mesh position={[0, 0.04, 0]}>
        <sphereGeometry args={[0.038, 16, 12]} />
        <meshStandardMaterial color={cores.aco} metalness={0.85} roughness={0.28} />
      </mesh>
      <mesh position={[0, 0.88, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.066, 0.017, 8, 24]} />
        <meshStandardMaterial color={cores.aLer} emissive={cores.aLer} emissiveIntensity={1.4} toneMapped={false} />
      </mesh>
      <mesh position={[0, 1.15, 0]}>
        <cylinderGeometry args={[0.07, 0.07, 0.42, 24]} />
        <meshStandardMaterial color={cores.pega} roughness={0.6} />
      </mesh>
    </group>
  )
}

// Reflexos de um estúdio gerado aqui mesmo. O <Environment> do drei traz os leitores de HDR/EXR
// (~40 KB) e os presets dele descarregam o HDRI de um CDN, que a CSP e o curral sem internet barram.
function Reflexos() {
  const { gl, scene } = useThree()
  useEffect(() => {
    const gerador = new THREE.PMREMGenerator(gl)
    const estudio = new RoomEnvironment()
    const mapa = gerador.fromScene(estudio, 0.04).texture
    scene.environment = mapa
    scene.environmentIntensity = 0.85
    return () => {
      scene.environment = null
      mapa.dispose()
      gerador.dispose()
      estudio.dispose()
    }
  }, [gl, scene])
  return null
}

type PropsPlaca = {
  progresso: MotionValue<number>
  reduzir: boolean
  aoPrimeiroQuadro: () => void
}

function Placa({ progresso, reduzir, aoPrimeiroQuadro }: PropsPlaca) {
  const rig = useRef<THREE.Group>(null!)
  const placa = useRef<THREE.Group>(null!)
  const materialPlaca = useRef<THREE.MeshPhysicalMaterial>(null!)
  const materiaisTeto = useRef<(THREE.MeshPhysicalMaterial | null)[]>([])
  const sonda = useRef<THREE.Group>(null!)
  const anel = useRef<THREE.Mesh>(null!)
  const avisou = useRef(false)

  const geometriaPlaca = useMemo(() => criarPlaca(2.4, 0.6, 0.42, 0.07), [])
  const geometriaTeto = useMemo(() => new THREE.CapsuleGeometry(0.3, 0.34, 8, 24), [])
  useEffect(() => () => {
    geometriaPlaca.dispose()
    geometriaTeto.dispose()
  }, [geometriaPlaca, geometriaTeto])

  // Inclinar com o ponteiro só faz sentido com rato (no telemóvel o dedo está a fazer scroll)
  const comRato = useMemo(() => window.matchMedia('(hover: hover)').matches, [])
  const alvo = useMemo(() => ({ rotacao: new THREE.Euler(), posicao: new THREE.Vector3() }), [])

  useFrame((state, delta) => {
    const p = progresso.get()
    const t = state.clock.elapsedTime
    const { width: w, height: h } = state.viewport

    // Enquadramento: ao lado do texto no ecrã deitado, por cima dele no ecrã em pé (landing.css)
    const emPe = w < h
    const escala = emPe
      ? Math.min(1, (w * 0.7) / 2.7, (h * 0.3) / 2.7)
      : Math.min(1, (h * 0.62) / 2.7, (w * 0.36) / 2.7)
    const flutuar = reduzir ? 0 : Math.sin(t * 0.9) * 0.05 * escala
    rig.current.scale.setScalar(escala)
    rig.current.position.set(emPe ? 0 : w * 0.25, (emPe ? h * 0.25 : -0.04) + flutuar, 0)

    if (reduzir) {
      alvo.rotacao.set(...POSE_PARADA)
    } else {
      poseEm(p, alvo.rotacao)
      if (comRato) {
        alvo.rotacao.x -= state.pointer.y * 0.12
        alvo.rotacao.y += state.pointer.x * 0.18
      }
    }
    easing.dampE(placa.current.rotation, alvo.rotacao, 0.35, delta)

    // A placa só ganha o verde da marca no fim, quando vira logo. De frente ela reflete a luz do
    // teto do estúdio: com os reflexos fracos o escuro não fica prateado nem o verde fica menta.
    const logo = p > 3 * PARTE + 0.05
    easing.dampC(materialPlaca.current.color, logo ? cores.marca : cores.placaNoite, 0.3, delta)
    easing.damp(materialPlaca.current, 'envMapIntensity', logo ? 0.55 : 0.32, 0.3, delta)

    materiaisTeto.current.forEach((material, i) => {
      if (!material) return
      const estado = estadoDoTeto(TETOS[i].n, p)
      easing.dampC(material.color, COR_ESTADO[estado], 0.16, delta)
      material.emissive.copy(material.color)
      const pulso = reduzir ? 0.5 : 0.5 + 0.5 * Math.sin(t * (estado === 'a-ler' ? 7 : 3.5))
      const brilho = estado === 'a-ler' ? 0.2 + 0.35 * pulso : estado === 'suspeita' ? 0.12 + 0.3 * pulso : 0
      easing.damp(material, 'emissiveIntensity', brilho, 0.1, delta)
    })

    // Sonda: entra antes da 2.ª manchete e encosta a cada teto pela ordem de medição
    const naLeitura = !reduzir && p > PARTE * 0.72 && p < 2 * PARTE + 0.03
    const teto = TETOS[tetoEmLeitura(p) - 1]
    const fase = p < PARTE ? 0 : ((p - PARTE) % PASSO_TETO) / PASSO_TETO
    const encostada = p >= PARTE && fase > 0.18 && fase < 0.82
    alvo.posicao.set(teto.x, teto.y, PONTA_Z).addScaledVector(DIRECAO_SONDA, encostada ? 0.03 : 0.5)
    easing.damp3(sonda.current.position, alvo.posicao, 0.14, delta)
    easing.damp3(sonda.current.scale, naLeitura ? 1 : 0.001, 0.15, delta)

    // O anel branco à volta do teto 3 fecha o logo
    easing.damp3(anel.current.scale, p > 3 * PARTE + 0.08 ? 1 : 0.001, 0.2, delta)

    if (!avisou.current) {
      avisou.current = true
      aoPrimeiroQuadro()
    }
  })

  return (
    <group ref={rig}>
      <group ref={placa}>
        <mesh geometry={geometriaPlaca}>
          <meshPhysicalMaterial ref={materialPlaca} color={cores.placaNoite} envMapIntensity={0.32} roughness={0.55} clearcoat={0.25} clearcoatRoughness={0.5} />
        </mesh>
        {TETOS.map((teto, i) => (
          <mesh key={teto.n} geometry={geometriaTeto} position={[teto.x, teto.y, 0.3]} rotation={[Math.PI / 2, 0, 0]}>
            <meshPhysicalMaterial
              ref={material => { materiaisTeto.current[i] = material }}
              color={cores.tetoVazio}
              emissive={cores.tetoVazio}
              emissiveIntensity={0}
              roughness={0.32}
              clearcoat={0.5}
              clearcoatRoughness={0.25}
            />
          </mesh>
        ))}
        <mesh ref={anel} position={[0.38, -0.38, 0.5]} scale={0.001}>
          <torusGeometry args={[0.37, 0.045, 16, 64]} />
          <meshStandardMaterial color={cores.branco} roughness={0.35} />
        </mesh>
        <Sonda ref={sonda} />
      </group>
    </group>
  )
}

export default function UbereScene({ progresso, ativa, aoFicarPronta }: Props) {
  const reduzir = useReducedMotion() ?? false
  // Se o aparelho não aguentar, baixa a resolução (performance.md da skill de 3D)
  const [nitida, setNitida] = useState(true)

  return (
    <Canvas
      className="cena"
      dpr={nitida ? [1, 1.5] : 1}
      camera={{ position: [0, 0, 7], fov: 32 }}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance', toneMapping: THREE.NeutralToneMapping }}
      frameloop={ativa ? 'always' : 'never'}
      fallback={null}
    >
      <PerformanceMonitor onDecline={() => setNitida(false)} onIncline={() => setNitida(true)} flipflops={3} onFallback={() => setNitida(false)} />
      {/* Luz principal no alto à esquerda: as poses viram a placa para a direita, e assim o brilho
          da face larga não aponta para a câmara (com a luz à direita a placa ficava prateada) */}
      <ambientLight intensity={0.35} />
      <directionalLight position={[-4, 5, 4]} intensity={2.1} />
      <directionalLight position={[4, -1, 3]} intensity={0.6} color="#A5D6A7" />
      <Reflexos />
      <Placa progresso={progresso} reduzir={reduzir} aoPrimeiroQuadro={aoFicarPronta} />
    </Canvas>
  )
}
