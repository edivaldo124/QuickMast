#!/usr/bin/env node
'use strict';
const fs = require('fs');

function fail(msg) { console.error(msg); process.exit(1); }

const inPath = process.argv[2];
const outPath = process.argv[3];
if (!inPath || !outPath) fail('uso: node ua-arch-analyze.js <input.json> <output.json>');

let input;
try { input = JSON.parse(fs.readFileSync(inPath, 'utf8')); } catch (e) { fail('Falha ao ler entrada: ' + e.message); }

const fileNodes = input.fileNodes || [];
const importEdges = input.importEdges || [];
const allEdges = input.allEdges || [];

const byId = new Map(fileNodes.map(n => [n.id, n]));

// ---- A. Directory grouping ----
function dirParts(p) { const parts = p.split('/'); parts.pop(); return parts; }
const allDirParts = fileNodes.map(n => dirParts(n.filePath));
let commonPrefix = [];
if (allDirParts.length) {
  const first = allDirParts[0];
  for (let i = 0; i < first.length; i++) {
    if (allDirParts.every(d => d[i] === first[i])) commonPrefix.push(first[i]); else break;
  }
}
const prefixLen = commonPrefix.length;

function groupOf(node) {
  const parts = node.filePath.split('/');
  if (parts.length - 1 > prefixLen) return parts[prefixLen];
  return '(raiz)';
}
const directoryGroups = {};
const groupByNode = {};
for (const n of fileNodes) {
  const g = groupOf(n);
  (directoryGroups[g] = directoryGroups[g] || []).push(n.id);
  groupByNode[n.id] = g;
}

// ---- B. Node type grouping ----
const nodeTypeGroups = {};
for (const n of fileNodes) (nodeTypeGroups[n.type] = nodeTypeGroups[n.type] || []).push(n.id);

// ---- C. Fan-in / fan-out ----
const fileFanIn = {}, fileFanOut = {};
const adjacency = {};
for (const e of importEdges) {
  if (!byId.has(e.source) || !byId.has(e.target)) continue;
  fileFanOut[e.source] = (fileFanOut[e.source] || 0) + 1;
  fileFanIn[e.target] = (fileFanIn[e.target] || 0) + 1;
  (adjacency[e.source] = adjacency[e.source] || []).push(e.target);
}

// ---- D. Cross-category ----
const crossMap = {};
for (const e of allEdges) {
  const s = byId.get(e.source), t = byId.get(e.target);
  if (!s || !t) continue;
  if (s.type === t.type && e.type === 'imports') continue;
  const k = `${s.type}|${t.type}|${e.type}`;
  crossMap[k] = (crossMap[k] || 0) + 1;
}
const crossCategoryEdges = Object.entries(crossMap)
  .map(([k, count]) => { const [fromType, toType, edgeType] = k.split('|'); return { fromType, toType, edgeType, count }; })
  .filter(x => x.fromType !== x.toType)
  .sort((a, b) => b.count - a.count);

// non-code -> code connections
const nonCodeLinks = {};
for (const e of allEdges) {
  const s = byId.get(e.source), t = byId.get(e.target);
  if (!s || !t) continue;
  if (s.type !== 'file' && t.type === 'file' && ['configures', 'documents', 'deploys', 'triggers', 'depends_on', 'related'].includes(e.type)) {
    (nonCodeLinks[s.id] = nonCodeLinks[s.id] || []).push({ to: t.id, type: e.type });
  }
}

// ---- E. Inter-group import frequency ----
const interMap = {};
const intraMap = {};
const totalMap = {};
for (const e of importEdges) {
  const gs = groupByNode[e.source], gt = groupByNode[e.target];
  if (!gs || !gt) continue;
  totalMap[gs] = (totalMap[gs] || 0) + 1;
  if (gs === gt) { intraMap[gs] = (intraMap[gs] || 0) + 1; continue; }
  totalMap[gt] = (totalMap[gt] || 0) + 1;
  const k = gs + '->' + gt;
  interMap[k] = (interMap[k] || 0) + 1;
}
const interGroupImports = Object.entries(interMap)
  .map(([k, count]) => { const [from, to] = k.split('->'); return { from, to, count }; })
  .sort((a, b) => b.count - a.count);

// ---- F. Intra-group density ----
const intraGroupDensity = {};
for (const g of Object.keys(directoryGroups)) {
  const internal = intraMap[g] || 0;
  const total = totalMap[g] || 0;
  intraGroupDensity[g] = { internalEdges: internal, totalEdges: total, density: total ? +(internal / total).toFixed(2) : 0 };
}

// ---- G. Pattern matching ----
const dirPatterns = {
  api: ['routes', 'api', 'controllers', 'endpoints', 'handlers', 'serializers', 'controller', 'routers', 'blueprints'],
  service: ['services', 'servicos', 'core', 'lib', 'domain', 'logic', 'signals', 'internal', 'composables', 'mailers', 'jobs', 'channels'],
  data: ['models', 'modelos', 'db', 'data', 'dao', 'persistence', 'repository', 'entities', 'entity', 'migrations', 'sql', 'database', 'schema'],
  ui: ['components', 'views', 'pages', 'ui', 'layouts', 'screens', 'templates', 'frontend'],
  middleware: ['middleware', 'plugins', 'interceptors', 'guards'],
  utility: ['utils', 'helpers', 'common', 'shared', 'tools', 'templatetags', 'pkg'],
  config: ['config', 'constants', 'env', 'settings', 'management', 'commands'],
  test: ['__tests__', 'test', 'tests', 'spec', 'specs'],
  types: ['types', 'interfaces', 'schemas', 'contracts', 'dtos', 'dto', 'request', 'response'],
  hooks: ['hooks'],
  state: ['store', 'state', 'reducers', 'actions', 'slices'],
  assets: ['assets', 'static', 'public', 'stetic'],
  entry: ['cmd', 'bin'],
  documentation: ['docs', 'documentation', 'wiki'],
  infrastructure: ['deploy', 'deployment', 'infra', 'infrastructure', 'k8s', 'kubernetes', 'helm', 'charts', 'terraform', 'tf', 'docker'],
  'ci-cd': ['.github', '.gitlab', '.circleci'],
  firmware: ['firmware'],
};
const patternMatches = {};
for (const g of Object.keys(directoryGroups)) {
  for (const [label, names] of Object.entries(dirPatterns)) {
    if (names.includes(g.toLowerCase())) { patternMatches[g] = label; break; }
  }
}

const filePatternMatches = {};
function filePattern(n) {
  const p = n.filePath, base = p.split('/').pop();
  if (/\.(test|spec)\./.test(base) || /^test_.*\.py$/.test(base) || /_test\.go$/.test(base)) return 'test';
  if (/\.d\.ts$/.test(base)) return 'types';
  if (['index.ts', 'index.js', '__init__.py'].includes(base)) return 'entry';
  if (base === 'manage.py' && !p.includes('/')) return 'entry';
  if (['wsgi.py', 'asgi.py'].includes(base)) return 'config';
  if (/^(Dockerfile|docker-compose)/.test(base)) return 'infrastructure';
  if (/\.(tf|tfvars)$/.test(base)) return 'infrastructure';
  if (p.startsWith('.github/workflows/') || base === '.gitlab-ci.yml' || base === 'Jenkinsfile') return 'ci-cd';
  if (/\.sql$/.test(base)) return 'data';
  if (/\.(graphql|gql|proto)$/.test(base)) return 'types';
  if (/\.(md|rst)$/.test(base)) return 'documentation';
  if (base === 'Makefile') return 'infrastructure';
  if (['Cargo.toml', 'go.mod', 'Gemfile', 'pom.xml', 'build.gradle', 'composer.json'].includes(base)) return 'config';
  if (/\.ino$/.test(base)) return 'firmware';
  return null;
}
for (const n of fileNodes) { const m = filePattern(n); if (m) filePatternMatches[n.id] = m; }

// ---- H. Deployment topology ----
const infraFiles = fileNodes.filter(n => /(^|\/)(Dockerfile|docker-compose[^/]*|\.github\/workflows\/|gunicorn\.conf\.py|apresentacao\.sh)/.test(n.filePath) || n.type === 'service' || n.type === 'pipeline').map(n => n.filePath);
const deploymentTopology = {
  hasDockerfile: fileNodes.some(n => /(^|\/)Dockerfile/.test(n.filePath)),
  hasCompose: fileNodes.some(n => /docker-compose/.test(n.filePath)),
  hasK8s: fileNodes.some(n => /(^|\/)(k8s|kubernetes|helm|charts)\//.test(n.filePath)),
  hasTerraform: fileNodes.some(n => /\.tf(vars)?$/.test(n.filePath)),
  hasCI: fileNodes.some(n => n.filePath.startsWith('.github/workflows/') || n.type === 'pipeline'),
  infraFiles: [...new Set(infraFiles)],
};

// ---- I. Data pipeline ----
const dataPipeline = {
  schemaFiles: fileNodes.filter(n => /\.(sql|graphql|gql|proto|prisma)$/.test(n.filePath)).map(n => n.filePath),
  migrationFiles: fileNodes.filter(n => /migrat/i.test(n.filePath)).map(n => n.filePath),
  dataModelFiles: fileNodes.filter(n => /^(modelos|models|dao)\//.test(n.filePath)).map(n => n.filePath),
  apiHandlerFiles: fileNodes.filter(n => /^(blueprints|routes|api|controllers)\//.test(n.filePath)).map(n => n.filePath),
};

// ---- J. Doc coverage ----
const docs = fileNodes.filter(n => n.type === 'document');
const groupNames = Object.keys(directoryGroups).filter(g => g !== '(raiz)');
const undocumented = [];
let withDocs = 0;
for (const g of groupNames) {
  const hasReadme = docs.some(d => d.filePath.startsWith(g + '/') && /readme/i.test(d.filePath));
  const documented = hasReadme || allEdges.some(e => e.type === 'documents' && byId.get(e.source) && byId.get(e.source).type === 'document' && groupByNode[e.target] === g);
  if (documented) withDocs++; else undocumented.push(g);
}
const docCoverage = {
  groupsWithDocs: withDocs,
  totalGroups: groupNames.length,
  coverageRatio: groupNames.length ? +(withDocs / groupNames.length).toFixed(2) : 0,
  undocumentedGroups: undocumented,
};

// ---- K. Dependency direction ----
const seen = new Set();
const dependencyDirection = [];
for (const { from, to, count } of interGroupImports) {
  const key = [from, to].sort().join('|');
  if (seen.has(key)) continue;
  seen.add(key);
  const rev = interMap[to + '->' + from] || 0;
  if (count >= rev) dependencyDirection.push({ dependent: from, dependsOn: to, count, reverse: rev });
  else dependencyDirection.push({ dependent: to, dependsOn: from, count: rev, reverse: count });
}

// ---- Stats ----
const filesPerGroup = {};
for (const [g, ids] of Object.entries(directoryGroups)) filesPerGroup[g] = ids.length;
const nodeTypeCounts = {};
for (const [t, ids] of Object.entries(nodeTypeGroups)) nodeTypeCounts[t] = ids.length;

const results = {
  scriptCompleted: true,
  commonPrefix: commonPrefix.join('/'),
  directoryGroups,
  nodeTypeGroups,
  crossCategoryEdges,
  nonCodeLinks,
  interGroupImports,
  intraGroupDensity,
  patternMatches,
  filePatternMatches,
  deploymentTopology,
  dataPipeline,
  docCoverage,
  dependencyDirection,
  fileStats: { totalFileNodes: fileNodes.length, filesPerGroup, nodeTypeCounts },
  fileFanIn,
  fileFanOut,
  adjacency,
};

fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
process.exit(0);
