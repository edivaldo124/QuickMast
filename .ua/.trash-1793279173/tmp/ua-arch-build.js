const fs=require('fs');
const r=JSON.parse(fs.readFileSync('.ua/tmp/ua-arch-results.json','utf8'));
const g=r.directoryGroups;
const rootPick=(ids)=>ids.filter(id=>g['(raiz)'].includes(id));
const layers=[
 {id:'layer:api',name:'Camada de Rotas (Blueprints Flask)',
  description:'Blueprints Flask que expõem as páginas HTML, a autenticação, a conta com MFA, a API de testes de mastite, a gestão de usuários, o recebimento do sensor ESP8266, o health check, a exportação CSV e o tratamento de erros.',
  nodeIds:[...g.blueprints]},
 {id:'layer:service',name:'Camada de Serviços',
  description:'Regras de negócio e de segurança usadas pelas rotas: autenticação e sessão, MFA/TOTP, política de senhas (com lista de senhas comuns), limite de tentativas, proteções globais (CSRF, cabeçalhos, auditoria) e diagnóstico de mastite.',
  nodeIds:[...g.servicos]},
 {id:'layer:data',name:'Camada de Dados e Persistência',
  description:'Modelos ORM do SQLAlchemy (usuário, vaca, teste e leitura) e DAOs que cuidam do engine, da migração do esquema e do acesso ao PostgreSQL.',
  nodeIds:[...g.dao,...g.modelos]},
 {id:'layer:core',name:'Núcleo da Aplicação e Scripts de Administração',
  description:'Ponto de entrada servidor.py (configuração do Flask, logs, sessão, registro dos blueprints e comandos de CLI) e scripts de uso único para definir a senha do admin e separar o usuário do banco com menor privilégio.',
  nodeIds:rootPick(['file:servidor.py','file:definir_senha_admin.py','file:configurar_banco_app.py'])},
 {id:'layer:web-ui',name:'Interface Web (Templates Jinja e Estáticos)',
  description:'Páginas Jinja renderizadas pelo Flask (layout base, login, MFA, painel, histórico da vaca, usuários, úbere) e os arquivos estáticos de stetic/ (CSS do design system, JavaScript do navegador e fontes).',
  nodeIds:[...g.templates,...g.stetic]},
 {id:'layer:landing-react',name:'Landing Page React com Cena 3D',
  description:'Aplicação React + Vite em frontend/ com a landing page, a cena 3D em Three.js (React Three Fiber), manchetes, tokens de design e a configuração de build (package.json, tsconfig, vite.config) que gera os assets servidos pelo Flask.',
  nodeIds:[...g.frontend]},
 {id:'layer:firmware',name:'Firmware do Sensor (ESP8266)',
  description:'Sketch Arduino do NodeMCU/ESP8266 que lê o sensor TDS de condutividade, conduz o teste dos 4 tetos, calcula o diagnóstico de mastite e envia os testes à API do QuickMast (também responde ao GET /read usado pela página do úbere).',
  nodeIds:[...g.firmware]},
 {id:'layer:infrastructure',name:'Infraestrutura, CI/CD e Configuração de Ambiente',
  description:'Dockerfile, Docker Compose (app, banco e simulador), configuração do gunicorn, script de apresentação, pipeline de segurança no GitHub Actions, modelo de variáveis de ambiente e dependências Python fixadas com hashes.',
  nodeIds:rootPick(['service:Dockerfile','service:Dockerfile:python','service:docker-compose.yml','service:docker-compose.yml:db','service:docker-compose.yml:app','service:docker-compose.simulador.yml','config:.dockerignore','file:gunicorn.conf.py','file:apresentacao.sh','config:.env.example','config:requirements.in','document:requirements.txt']).concat(g['.github'])},
 {id:'layer:documentation',name:'Documentação e Ferramentas de IA',
  description:'README, guia de deploy para IA (PROMPT_DEPLOY_GEMINI), instruções do CLAUDE.md e o lockfile de skills do agente, que são metadados de documentação e de ferramentas fora do código da aplicação.',
  nodeIds:rootPick(['document:README.md','document:PROMPT_DEPLOY_GEMINI.md','document:CLAUDE.md','config:skills-lock.json'])},
];
// validation
const input=JSON.parse(fs.readFileSync('.ua/tmp/ua-arch-input.json','utf8'));
const all=input.fileNodes.map(n=>n.id);
const seen=new Map();
for(const l of layers) for(const id of l.nodeIds){ if(seen.has(id)) throw new Error('dup '+id); seen.set(id,l.id); }
const missing=all.filter(id=>!seen.has(id)); const extra=[...seen.keys()].filter(id=>!all.includes(id));
const total=layers.reduce((a,l)=>a+l.nodeIds.length,0);
console.log('layers',layers.length,'total',total,'expected',all.length,'missing',missing,'extra',extra);
if(missing.length||extra.length||total!==all.length) process.exit(1);
for(const l of layers) console.log(l.id,l.nodeIds.length);
fs.writeFileSync('.ua/intermediate/layers.json',JSON.stringify(layers,null,2));
