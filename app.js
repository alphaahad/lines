const SHAPES = ["rectangle", "rounded", "circle", "diamond", "parallelogram", "hexagon"];
const EDGE_STYLES = ["solid", "dashed", "dotted"];

const THEMES = {
  default: { bg: "#f8fbff", node: "#dbeafe", stroke: "#2563eb", text: "#1e3a8a", edge: "#1d4ed8" },
  midnight: { bg: "#0b1324", node: "#18233b", stroke: "#6ea8fe", text: "#dae8ff", edge: "#8db6ff" },
  forest: { bg: "#eef8f2", node: "#d4f2e0", stroke: "#2f855a", text: "#1f5136", edge: "#2f855a" },
  sunset: { bg: "#fff4ef", node: "#ffe2d2", stroke: "#d97706", text: "#9a3412", edge: "#c2410c" },
};

const state = {
  theme: "default",
  layout: "grid",
  nodes: [],
  edges: [],
};

const ui = {
  nodeCountInput: document.getElementById("node-count-input"),
  themeSelect: document.getElementById("theme-select"),
  layoutSelect: document.getElementById("layout-select"),
  nodesList: document.getElementById("nodes-list"),
  edgesList: document.getElementById("edges-list"),
  preview: document.getElementById("preview"),
  dslInput: document.getElementById("dsl-input"),
  messages: document.getElementById("messages"),
};

function createNode(index) {
  const id = `N${index + 1}`;
  return { id, label: `Box ${index + 1}`, shape: SHAPES[index % SHAPES.length] };
}

function createEdge(from, to, index) {
  return { from, to, label: `Link ${index + 1}`, style: EDGE_STYLES[index % EDGE_STYLES.length] };
}

function autoBuild(count) {
  const bounded = Math.max(1, Math.min(50, Number(count) || 1));
  state.nodes = Array.from({ length: bounded }, (_, i) => createNode(i));
  state.edges = [];
  for (let i = 0; i < bounded - 1; i += 1) {
    state.edges.push(createEdge(state.nodes[i].id, state.nodes[i + 1].id, i));
  }
  if (bounded > 3) {
    state.edges.push({ from: state.nodes[0].id, to: state.nodes[bounded - 1].id, label: "Wrap", style: "dashed" });
  }
}

function renderNodeRows() {
  ui.nodesList.innerHTML = "";
  state.nodes.forEach((node, index) => {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <input value="${node.id}" aria-label="node id" />
      <input value="${escapeHtml(node.label)}" aria-label="node label" />
      <select aria-label="node shape">${SHAPES.map((shape) => `<option value="${shape}" ${shape === node.shape ? "selected" : ""}>${shape}</option>`).join("")}</select>
      <button type="button">Delete</button>
    `;

    const [idInput, labelInput, shapeSelect, deleteBtn] = row.children;
    idInput.addEventListener("input", () => {
      const oldId = node.id;
      node.id = sanitizeToken(idInput.value) || oldId;
      state.edges.forEach((edge) => {
        if (edge.from === oldId) edge.from = node.id;
        if (edge.to === oldId) edge.to = node.id;
      });
      renderAll();
    });

    labelInput.addEventListener("input", () => {
      node.label = labelInput.value;
      renderPreview();
    });

    shapeSelect.addEventListener("change", () => {
      node.shape = shapeSelect.value;
      renderPreview();
    });

    deleteBtn.addEventListener("click", () => {
      state.nodes.splice(index, 1);
      state.edges = state.edges.filter((edge) => edge.from !== node.id && edge.to !== node.id);
      renderAll();
    });

    ui.nodesList.append(row);
  });
}

function renderEdgeRows() {
  ui.edgesList.innerHTML = "";
  state.edges.forEach((edge, index) => {
    const row = document.createElement("div");
    row.className = "list-row edge";
    row.innerHTML = `
      ${nodeOptions(edge.from)}
      <span>→</span>
      ${nodeOptions(edge.to)}
      <input value="${escapeHtml(edge.label)}" aria-label="edge label" />
      <select aria-label="edge style">${EDGE_STYLES.map((style) => `<option value="${style}" ${style === edge.style ? "selected" : ""}>${style}</option>`).join("")}</select>
      <button type="button">Delete</button>
    `;

    const [fromSelect, , toSelect, labelInput, styleSelect, deleteBtn] = row.children;
    fromSelect.addEventListener("change", () => {
      edge.from = fromSelect.value;
      renderPreview();
    });
    toSelect.addEventListener("change", () => {
      edge.to = toSelect.value;
      renderPreview();
    });
    labelInput.addEventListener("input", () => {
      edge.label = labelInput.value;
      renderPreview();
    });
    styleSelect.addEventListener("change", () => {
      edge.style = styleSelect.value;
      renderPreview();
    });
    deleteBtn.addEventListener("click", () => {
      state.edges.splice(index, 1);
      renderAll();
    });

    ui.edgesList.append(row);
  });
}

function nodeOptions(selected) {
  return `<select>${state.nodes.map((node) => `<option value="${node.id}" ${node.id === selected ? "selected" : ""}>${node.id}</option>`).join("")}</select>`;
}

function applyLayout(nodes) {
  const spacingX = 220;
  const spacingY = 140;
  const startX = 130;
  const startY = 90;
  const positions = new Map();

  if (state.layout === "horizontal") {
    nodes.forEach((node, i) => positions.set(node.id, { x: startX + i * spacingX, y: startY + 140 }));
  } else if (state.layout === "vertical") {
    nodes.forEach((node, i) => positions.set(node.id, { x: startX + 220, y: startY + i * spacingY }));
  } else if (state.layout === "radial") {
    const centerX = 360;
    const centerY = 280;
    const radius = Math.max(120, 40 * nodes.length);
    nodes.forEach((node, i) => {
      const angle = (Math.PI * 2 * i) / Math.max(1, nodes.length);
      positions.set(node.id, { x: centerX + Math.cos(angle) * radius, y: centerY + Math.sin(angle) * radius });
    });
  } else {
    const cols = Math.max(2, Math.ceil(Math.sqrt(nodes.length)));
    nodes.forEach((node, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      positions.set(node.id, { x: startX + col * spacingX, y: startY + row * spacingY });
    });
  }

  return positions;
}

function renderPreview() {
  ui.preview.innerHTML = "";
  if (!state.nodes.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Add at least one box to start.";
    ui.preview.append(empty);
    return;
  }

  const theme = THEMES[state.theme];
  ui.preview.style.background = theme.bg;
  const positions = applyLayout(state.nodes);

  const width = 900;
  const height = 700;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const defs = document.createElementNS(svg.namespaceURI, "defs");
  const marker = document.createElementNS(svg.namespaceURI, "marker");
  marker.setAttribute("id", "arrow");
  marker.setAttribute("markerWidth", "10");
  marker.setAttribute("markerHeight", "8");
  marker.setAttribute("refX", "9");
  marker.setAttribute("refY", "4");
  marker.setAttribute("orient", "auto");
  const path = document.createElementNS(svg.namespaceURI, "path");
  path.setAttribute("d", "M0,0 L10,4 L0,8 z");
  path.setAttribute("fill", theme.edge);
  marker.append(path);
  defs.append(marker);
  svg.append(defs);

  state.edges.forEach((edge) => {
    const from = positions.get(edge.from);
    const to = positions.get(edge.to);
    if (!from || !to) return;
    const line = document.createElementNS(svg.namespaceURI, "line");
    line.setAttribute("x1", from.x);
    line.setAttribute("y1", from.y);
    line.setAttribute("x2", to.x);
    line.setAttribute("y2", to.y);
    line.setAttribute("stroke", theme.edge);
    line.setAttribute("stroke-width", "2.2");
    if (edge.style === "dashed") line.setAttribute("stroke-dasharray", "8 6");
    if (edge.style === "dotted") line.setAttribute("stroke-dasharray", "2 6");
    line.setAttribute("marker-end", "url(#arrow)");
    svg.append(line);

    if (edge.label) {
      const lx = (from.x + to.x) / 2;
      const ly = (from.y + to.y) / 2 - 8;
      const text = createSvgText(svg, lx, ly, edge.label, theme.text, "12");
      svg.append(text);
    }
  });

  state.nodes.forEach((node) => {
    const pos = positions.get(node.id);
    const group = document.createElementNS(svg.namespaceURI, "g");
    drawShape(svg, group, node.shape, pos.x, pos.y, theme);
    const text = createSvgText(svg, pos.x, pos.y + 4, node.label, theme.text, "14", true);
    group.append(text);
    const idLabel = createSvgText(svg, pos.x, pos.y - 26, node.id, theme.text, "11");
    group.append(idLabel);
    svg.append(group);
  });

  ui.preview.append(svg);
}

function drawShape(svg, group, shape, x, y, theme) {
  const make = (tag) => document.createElementNS(svg.namespaceURI, tag);
  let el;
  if (shape === "circle") {
    el = make("circle");
    el.setAttribute("cx", x);
    el.setAttribute("cy", y);
    el.setAttribute("r", 45);
  } else if (shape === "diamond") {
    el = make("polygon");
    el.setAttribute("points", `${x},${y - 48} ${x + 70},${y} ${x},${y + 48} ${x - 70},${y}`);
  } else if (shape === "parallelogram") {
    el = make("polygon");
    el.setAttribute("points", `${x - 70},${y + 40} ${x - 35},${y - 40} ${x + 70},${y - 40} ${x + 35},${y + 40}`);
  } else if (shape === "hexagon") {
    el = make("polygon");
    el.setAttribute("points", `${x - 70},${y} ${x - 38},${y - 42} ${x + 38},${y - 42} ${x + 70},${y} ${x + 38},${y + 42} ${x - 38},${y + 42}`);
  } else {
    el = make("rect");
    el.setAttribute("x", x - 72);
    el.setAttribute("y", y - 42);
    el.setAttribute("width", 144);
    el.setAttribute("height", 84);
    if (shape === "rounded") el.setAttribute("rx", "18");
  }
  el.setAttribute("fill", theme.node);
  el.setAttribute("stroke", theme.stroke);
  el.setAttribute("stroke-width", "2");
  group.append(el);
}

function createSvgText(svg, x, y, content, fill, size, center = true) {
  const text = document.createElementNS(svg.namespaceURI, "text");
  text.setAttribute("x", x);
  text.setAttribute("y", y);
  if (center) text.setAttribute("text-anchor", "middle");
  text.setAttribute("font-size", size);
  text.setAttribute("fill", fill);
  text.textContent = content;
  return text;
}

function stateToDsl() {
  const lines = [`graph theme=${state.theme} layout=${state.layout}`];
  state.nodes.forEach((node) => lines.push(`node ${node.id} ${node.shape} "${node.label.replaceAll("\"", "'")}"`));
  state.edges.forEach((edge) => {
    lines.push(`edge ${edge.from} -> ${edge.to} "${edge.label.replaceAll("\"", "'")}" style=${edge.style}`);
  });
  return lines.join("\n");
}

function applyDsl(text) {
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const nextState = { theme: state.theme, layout: state.layout, nodes: [], edges: [] };
  const errors = [];

  lines.forEach((line, index) => {
    if (line.startsWith("#")) return;
    if (line.startsWith("graph")) {
      const theme = line.match(/theme=([\w-]+)/)?.[1];
      const layout = line.match(/layout=([\w-]+)/)?.[1];
      if (theme && THEMES[theme]) nextState.theme = theme;
      if (layout && ["grid", "horizontal", "vertical", "radial"].includes(layout)) nextState.layout = layout;
      return;
    }
    if (line.startsWith("node")) {
      const m = line.match(/^node\s+(\S+)\s+(\S+)\s+"(.*)"$/);
      if (!m) {
        errors.push(`Line ${index + 1}: invalid node syntax`);
        return;
      }
      const [, id, shape, label] = m;
      if (!SHAPES.includes(shape)) {
        errors.push(`Line ${index + 1}: unknown shape '${shape}'`);
        return;
      }
      nextState.nodes.push({ id: sanitizeToken(id), shape, label });
      return;
    }
    if (line.startsWith("edge")) {
      const m = line.match(/^edge\s+(\S+)\s+->\s+(\S+)\s+"(.*)"(?:\s+style=(\w+))?$/);
      if (!m) {
        errors.push(`Line ${index + 1}: invalid edge syntax`);
        return;
      }
      const [, from, to, label, style = "solid"] = m;
      if (!EDGE_STYLES.includes(style)) {
        errors.push(`Line ${index + 1}: unknown style '${style}'`);
        return;
      }
      nextState.edges.push({ from, to, label, style });
      return;
    }
    errors.push(`Line ${index + 1}: unsupported command`);
  });

  if (nextState.nodes.length === 0) errors.push("Graph must include at least one node.");
  if (errors.length) {
    printMessage(errors.join("\n"), true);
    return;
  }

  const nodeIds = new Set(nextState.nodes.map((node) => node.id));
  nextState.edges = nextState.edges.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  Object.assign(state, nextState);
  printMessage("Script applied successfully.");
  renderAll();
}

function printMessage(message, error = false) {
  ui.messages.textContent = message;
  ui.messages.style.color = error ? "#9f1239" : "#0c4a6e";
}

function sanitizeToken(token) {
  return String(token || "").replace(/[^a-zA-Z0-9_-]/g, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderAll() {
  renderNodeRows();
  renderEdgeRows();
  renderPreview();
  ui.dslInput.value = stateToDsl();
}

function setupEvents() {
  document.getElementById("add-node-btn").addEventListener("click", () => {
    const index = state.nodes.length;
    state.nodes.push(createNode(index));
    renderAll();
  });

  document.getElementById("add-edge-btn").addEventListener("click", () => {
    if (state.nodes.length < 2) {
      printMessage("Need at least two boxes to create a connection.", true);
      return;
    }
    state.edges.push(createEdge(state.nodes[0].id, state.nodes.at(-1).id, state.edges.length));
    renderAll();
  });

  document.getElementById("auto-generate-btn").addEventListener("click", () => {
    autoBuild(ui.nodeCountInput.value);
    renderAll();
    printMessage(`Created ${state.nodes.length} boxes with starter connections.`);
  });

  ui.themeSelect.addEventListener("change", () => {
    state.theme = ui.themeSelect.value;
    renderAll();
  });

  ui.layoutSelect.addEventListener("change", () => {
    state.layout = ui.layoutSelect.value;
    renderPreview();
    ui.dslInput.value = stateToDsl();
  });

  document.getElementById("sync-to-script-btn").addEventListener("click", () => {
    ui.dslInput.value = stateToDsl();
    printMessage("UI synced to script editor.");
  });

  document.getElementById("apply-script-btn").addEventListener("click", () => {
    applyDsl(ui.dslInput.value);
    ui.themeSelect.value = state.theme;
    ui.layoutSelect.value = state.layout;
  });

  document.getElementById("sample-btn").addEventListener("click", () => {
    ui.dslInput.value = `graph theme=midnight layout=radial\nnode Start circle "Start"\nnode Ingest parallelogram "Ingest Data"\nnode Validate diamond "Validation"\nnode Process rounded "Processing"\nnode Report hexagon "Report"\nedge Start -> Ingest "kickoff" style=solid\nedge Ingest -> Validate "schema checks" style=dotted\nedge Validate -> Process "approved" style=solid\nedge Process -> Report "compile" style=dashed`;
    applyDsl(ui.dslInput.value);
    ui.themeSelect.value = state.theme;
    ui.layoutSelect.value = state.layout;
  });

  document.getElementById("export-svg-btn").addEventListener("click", () => {
    const svg = ui.preview.querySelector("svg");
    if (!svg) return;
    const blob = new Blob([svg.outerHTML], { type: "image/svg+xml" });
    downloadBlob(blob, "lines-graph.svg");
  });

  document.getElementById("download-json-btn").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    downloadBlob(blob, "lines-graph.json");
  });
}

function downloadBlob(blob, filename) {
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(href);
}

autoBuild(4);
setupEvents();
renderAll();
printMessage("Ready. Edit controls or the script to design your graph.");
