const fs = require("fs");
try {
  const [,, inPath, outPath] = process.argv;
  if (!inPath || !outPath) throw new Error("usage: node script input output");
  const data = JSON.parse(fs.readFileSync(inPath, "utf8"));
  const nodes = data.nodes || [], edges = data.edges || [], layers = data.layers || [];
  const ids = new Set(nodes.map(n => n.id));
  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
  const fanIn = {}, fanOut = {};
  nodes.forEach(n => { fanIn[n.id] = 0; fanOut[n.id] = 0; });
  const fwd = {};
  edges.forEach(e => {
    if (!ids.has(e.source) || !ids.has(e.target)) return;
    fanOut[e.source]++; fanIn[e.target]++;
    if (e.type === "imports" || e.type === "calls") (fwd[e.source] = fwd[e.source] || []).push(e.target);
  });
  const rank = (m, key) => Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 20)
    .map(([id, v]) => ({ id, [key]: v, name: byId[id].name }));
  const fanInRanking = rank(fanIn, "fanIn"), fanOutRanking = rank(fanOut, "fanOut");

  const codeNames = new Set(["index.ts","index.js","main.ts","main.js","app.ts","app.js","server.ts","server.js","mod.rs","main.go","main.py","main.rs","manage.py","app.py","wsgi.py","asgi.py","run.py","__main__.py","Application.java","Main.java","Program.cs","config.ru","index.php","App.swift","Application.kt","main.cpp","main.c"]);
  const outVals = Object.values(fanOut).sort((a, b) => b - a);
  const inVals = Object.values(fanIn).sort((a, b) => a - b);
  const topOutThreshold = outVals[Math.max(0, Math.ceil(outVals.length * 0.1) - 1)];
  const lowInThreshold = inVals[Math.max(0, Math.floor(inVals.length * 0.25) - 1)];
  const scored = nodes.map(n => {
    let s = 0;
    const fp = n.filePath || "";
    const depth = fp.split("/").length - 1;
    if (n.type === "document") {
      if (/^README\.md$/i.test(fp)) s += 5;
      else if (/\.md$/i.test(fp) && depth === 0) s += 2;
    } else if (n.type === "file") {
      if (codeNames.has(n.name)) s += 3;
      if (depth <= 1) s += 1;
      if (fanOut[n.id] >= topOutThreshold && fanOut[n.id] > 0) s += 1;
      if (fanIn[n.id] <= lowInThreshold) s += 1;
    }
    return { id: n.id, score: s, name: n.name, summary: n.summary };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score);
  const entryPointCandidates = scored.slice(0, 5);

  const startNode = (scored.find(c => byId[c.id].type === "file") || {}).id
    || (byId["file:servidor.py"] ? "file:servidor.py" : nodes[0].id);
  const order = [], depthMap = {}, q = [startNode];
  depthMap[startNode] = 0;
  while (q.length) {
    const c = q.shift(); order.push(c);
    (fwd[c] || []).forEach(t => { if (!(t in depthMap)) { depthMap[t] = depthMap[c] + 1; q.push(t); } });
  }
  const byDepth = {};
  order.forEach(id => (byDepth[depthMap[id]] = byDepth[depthMap[id]] || []).push(id));

  const sm = n => ({ id: n.id, name: n.name, type: n.type, summary: n.summary });
  const nonCodeFiles = { documentation: [], infrastructure: [], data: [], config: [] };
  nodes.forEach(n => {
    if (n.type === "document") nonCodeFiles.documentation.push(sm(n));
    else if (["service","pipeline","resource"].includes(n.type)) nonCodeFiles.infrastructure.push(sm(n));
    else if (["table","schema","endpoint"].includes(n.type)) nonCodeFiles.data.push(sm(n));
    else if (n.type === "config") nonCodeFiles.config.push(sm(n));
  });

  // clusters
  const pairKey = (a, b) => a < b ? a + "||" + b : b + "||" + a;
  const dirSet = new Set(), cnt = {};
  edges.forEach(e => {
    if (!ids.has(e.source) || !ids.has(e.target)) return;
    if (e.type === "imports" || e.type === "calls") dirSet.add(e.source + "->" + e.target);
    cnt[pairKey(e.source, e.target)] = (cnt[pairKey(e.source, e.target)] || 0) + 1;
  });
  const groups = [];
  for (const k of dirSet) {
    const [a, b] = k.split("->");
    if (a < b && dirSet.has(b + "->" + a)) groups.push(new Set([a, b]));
  }
  const adj = {};
  edges.forEach(e => { if (!ids.has(e.source)||!ids.has(e.target)) return;
    (adj[e.source] = adj[e.source] || new Set()).add(e.target);
    (adj[e.target] = adj[e.target] || new Set()).add(e.source); });
  groups.forEach(g => {
    let changed = true;
    while (changed && g.size < 5) {
      changed = false;
      for (const n of Object.keys(adj)) {
        if (g.has(n)) continue;
        let c = 0; g.forEach(m => { if (adj[n].has(m)) c++; });
        if (c >= 2 && g.size < 5) { g.add(n); changed = true; }
      }
    }
  });
  const clusters = groups.map(g => {
    const arr = [...g]; let ec = 0;
    for (let i = 0; i < arr.length; i++) for (let j = i + 1; j < arr.length; j++) ec += cnt[pairKey(arr[i], arr[j])] || 0;
    return { nodes: arr, edgeCount: ec };
  }).sort((a, b) => b.edgeCount - a.edgeCount).slice(0, 10);

  const nodeSummaryIndex = {};
  nodes.forEach(n => nodeSummaryIndex[n.id] = { name: n.name, type: n.type, summary: n.summary });
  const edgeTypes = {}; edges.forEach(e => edgeTypes[e.type] = (edgeTypes[e.type]||0)+1);

  fs.writeFileSync(outPath, JSON.stringify({
    scriptCompleted: true, entryPointCandidates, fanInRanking, fanOutRanking,
    bfsTraversal: { startNode, order, depthMap, byDepth },
    nonCodeFiles, clusters,
    layers: { count: layers.length, list: layers },
    nodeSummaryIndex, edgeTypes, totalNodes: nodes.length, totalEdges: edges.length
  }, null, 2));
} catch (e) { console.error(e.message); process.exit(1); }
