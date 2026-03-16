from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from html import escape

import streamlit as st


# =========================
# Constants
# =========================
SHAPES = ["rectangle", "rounded", "circle", "diamond", "parallelogram", "hexagon"]
EDGE_STYLES = ["solid", "dashed", "dotted"]
LAYOUTS = ["grid", "horizontal", "vertical", "radial"]

THEMES = {
    "default": {
        "bg": "#f8fbff",
        "node": "#dbeafe",
        "stroke": "#2563eb",
        "text": "#1e3a8a",
        "edge": "#1d4ed8",
    },
    "midnight": {
        "bg": "#0b1324",
        "node": "#18233b",
        "stroke": "#6ea8fe",
        "text": "#dae8ff",
        "edge": "#8db6ff",
    },
    "forest": {
        "bg": "#eef8f2",
        "node": "#d4f2e0",
        "stroke": "#2f855a",
        "text": "#1f5136",
        "edge": "#2f855a",
    },
    "sunset": {
        "bg": "#fff4ef",
        "node": "#ffe2d2",
        "stroke": "#d97706",
        "text": "#9a3412",
        "edge": "#c2410c",
    },
}

SVG_WIDTH = 1200
SVG_HEIGHT = 820
NODE_W = 152
NODE_H = 88
CIRCLE_R = 48
GRID_X = 240
GRID_Y = 150
START_X = 140
START_Y = 110

SESSION_KEY = "lines_studio_state"
DSL_KEY = "lines_studio_dsl"
MESSAGE_KEY = "lines_studio_message"
ERROR_KEY = "lines_studio_error"

SAMPLE_DSL = """graph theme=midnight layout=radial
node Start circle "Start"
node Ingest parallelogram "Ingest Data"
node Validate diamond "Validation"
node Process rounded "Processing"
node Report hexagon "Report"
edge Start -> Ingest "kickoff" style=solid
edge Ingest -> Validate "schema checks" style=dotted
edge Validate -> Process "approved" style=solid
edge Process -> Report "compile" style=dashed"""


# =========================
# Models
# =========================
@dataclass
class Node:
    id: str
    label: str = ""
    shape: str = "rectangle"

    def __post_init__(self) -> None:
        self.id = sanitize_token(self.id)
        if not self.id:
            raise ValueError("Node ID cannot be empty.")
        if self.shape not in SHAPES:
            raise ValueError(f"Unsupported shape: {self.shape}")


@dataclass
class Edge:
    from_node: str
    to_node: str
    label: str = ""
    style: str = "solid"

    def __post_init__(self) -> None:
        self.from_node = sanitize_token(self.from_node)
        self.to_node = sanitize_token(self.to_node)
        if not self.from_node or not self.to_node:
            raise ValueError("Edge references must be valid node IDs.")
        if self.style not in EDGE_STYLES:
            raise ValueError(f"Unsupported edge style: {self.style}")


@dataclass
class GraphState:
    theme: str = "default"
    layout: str = "grid"
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.theme not in THEMES:
            raise ValueError(f"Unsupported theme: {self.theme}")
        if self.layout not in LAYOUTS:
            raise ValueError(f"Unsupported layout: {self.layout}")
        ensure_unique_node_ids(self.nodes)
        validate_edge_refs(self.nodes, self.edges)

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "layout": self.layout,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GraphState":
        theme = payload.get("theme", "default")
        layout = payload.get("layout", "grid")
        nodes = [Node(**node) for node in payload.get("nodes", [])]
        edges = [Edge(**edge) for edge in payload.get("edges", [])]
        return cls(theme=theme, layout=layout, nodes=nodes, edges=edges)


# =========================
# Helpers
# =========================
def sanitize_token(token: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(token or ""))


def escape_text(value: str) -> str:
    return escape(str(value or ""), quote=True)


def ensure_unique_node_ids(nodes: list[Node]) -> None:
    seen: set[str] = set()
    for node in nodes:
        if node.id in seen:
            raise ValueError(f'Duplicate node id found: "{node.id}"')
        seen.add(node.id)


def validate_edge_refs(nodes: list[Node], edges: list[Edge]) -> None:
    node_ids = {node.id for node in nodes}
    for edge in edges:
        if edge.from_node not in node_ids or edge.to_node not in node_ids:
            raise ValueError(f"Invalid edge reference: {edge.from_node} -> {edge.to_node}")


def create_node(index: int) -> Node:
    node_id = f"N{index + 1}"
    return Node(id=node_id, label=f"Box {index + 1}", shape=SHAPES[index % len(SHAPES)])


def create_edge(from_id: str, to_id: str, index: int) -> Edge:
    return Edge(
        from_node=from_id,
        to_node=to_id,
        label=f"Link {index + 1}",
        style=EDGE_STYLES[index % len(EDGE_STYLES)],
    )


def auto_build(count: int) -> GraphState:
    bounded = max(1, min(50, int(count or 1)))
    nodes = [create_node(i) for i in range(bounded)]
    edges: list[Edge] = []

    for i in range(bounded - 1):
        edges.append(create_edge(nodes[i].id, nodes[i + 1].id, i))

    if bounded > 3:
        edges.append(Edge(from_node=nodes[0].id, to_node=nodes[-1].id, label="Wrap", style="dashed"))

    return GraphState(theme="default", layout="grid", nodes=nodes, edges=edges)


def midpoint(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    return (x1 + x2) / 2, (y1 + y2) / 2


def shrink_line_to_shape_boundary(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    padding_start: float = 56,
    padding_end: float = 56,
) -> tuple[float, float, float, float]:
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist == 0:
        return x1, y1, x2, y2
    ux = dx / dist
    uy = dy / dist
    return (
        x1 + ux * padding_start,
        y1 + uy * padding_start,
        x2 - ux * padding_end,
        y2 - uy * padding_end,
    )


# =========================
# DSL
# =========================
NODE_RE = re.compile(r'^node\s+(\S+)\s+(\S+)\s+"(.*)"$')
EDGE_RE = re.compile(r'^edge\s+(\S+)\s+->\s+(\S+)\s+"(.*)"(?:\s+style=(\w+))?$')


def state_to_dsl(state: GraphState) -> str:
    lines = [f"graph theme={state.theme} layout={state.layout}"]
    for node in state.nodes:
        label = node.label.replace('"', "'")
        lines.append(f'node {node.id} {node.shape} "{label}"')
    for edge in state.edges:
        label = edge.label.replace('"', "'")
        lines.append(f'edge {edge.from_node} -> {edge.to_node} "{label}" style={edge.style}')
    return "\n".join(lines)


def apply_dsl(text: str, current_state: GraphState) -> tuple[GraphState | None, list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    next_theme = current_state.theme
    next_layout = current_state.layout
    next_nodes: list[Node] = []
    next_edges: list[Edge] = []
    errors: list[str] = []

    for index, line in enumerate(lines, start=1):
        if line.startswith("#"):
            continue

        if line.startswith("graph"):
            theme = re.search(r"theme=([\w-]+)", line)
            layout = re.search(r"layout=([\w-]+)", line)
            if theme:
                theme_value = theme.group(1)
                if theme_value in THEMES:
                    next_theme = theme_value
                else:
                    errors.append(f"Line {index}: unknown theme '{theme_value}'")
            if layout:
                layout_value = layout.group(1)
                if layout_value in LAYOUTS:
                    next_layout = layout_value
                else:
                    errors.append(f"Line {index}: unknown layout '{layout_value}'")
            continue

        if line.startswith("node"):
            match = NODE_RE.match(line)
            if not match:
                errors.append(f"Line {index}: invalid node syntax")
                continue
            node_id, shape, label = match.groups()
            node_id = sanitize_token(node_id)
            if not node_id:
                errors.append(f"Line {index}: invalid empty node id")
                continue
            if shape not in SHAPES:
                errors.append(f"Line {index}: unknown shape '{shape}'")
                continue
            if any(existing.id == node_id for existing in next_nodes):
                errors.append(f"Line {index}: duplicate node id '{node_id}'")
                continue
            next_nodes.append(Node(id=node_id, shape=shape, label=label))
            continue

        if line.startswith("edge"):
            match = EDGE_RE.match(line)
            if not match:
                errors.append(f"Line {index}: invalid edge syntax")
                continue
            from_id, to_id, label, style = match.groups()
            style = style or "solid"
            if style not in EDGE_STYLES:
                errors.append(f"Line {index}: unknown style '{style}'")
                continue
            try:
                next_edges.append(
                    Edge(
                        from_node=sanitize_token(from_id),
                        to_node=sanitize_token(to_id),
                        label=label,
                        style=style,
                    )
                )
            except Exception as exc:
                errors.append(f"Line {index}: {exc}")
            continue

        errors.append(f"Line {index}: unsupported command")

    if not next_nodes:
        errors.append("Graph must include at least one node.")

    if not errors:
        node_ids = {node.id for node in next_nodes}
        for edge in next_edges:
            if edge.from_node not in node_ids or edge.to_node not in node_ids:
                errors.append(f"Edge reference invalid: {edge.from_node} -> {edge.to_node}")

    if errors:
        return None, errors

    try:
        graph = GraphState(theme=next_theme, layout=next_layout, nodes=next_nodes, edges=next_edges)
    except Exception as exc:
        return None, [str(exc)]

    return graph, []


# =========================
# Layout + SVG rendering
# =========================
def apply_layout(nodes: list[Node], layout: str) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}

    if not nodes:
        return positions

    if layout == "horizontal":
        for i, node in enumerate(nodes):
            positions[node.id] = (START_X + i * GRID_X, START_Y + 170)
        return positions

    if layout == "vertical":
        for i, node in enumerate(nodes):
            positions[node.id] = (START_X + 240, START_Y + i * GRID_Y)
        return positions

    if layout == "radial":
        center_x = SVG_WIDTH / 2
        center_y = SVG_HEIGHT / 2
        radius = min(260, max(130, 28 * len(nodes)))
        for i, node in enumerate(nodes):
            angle = (2 * math.pi * i) / max(1, len(nodes))
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            positions[node.id] = (x, y)
        return positions

    cols = max(2, math.ceil(math.sqrt(len(nodes))))
    for i, node in enumerate(nodes):
        col = i % cols
        row = i // cols
        positions[node.id] = (START_X + col * GRID_X, START_Y + row * GRID_Y)
    return positions


def _svg_text(
    x: float,
    y: float,
    text: str,
    fill: str,
    size: int,
    anchor: str = "middle",
    weight: str = "400",
) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif" font-weight="{weight}" fill="{fill}">{escape_text(text)}</text>'
    )


def _shape_svg(shape: str, x: float, y: float, node_fill: str, stroke: str) -> str:
    if shape == "circle":
        return f'<circle cx="{x}" cy="{y}" r="{CIRCLE_R}" fill="{node_fill}" stroke="{stroke}" stroke-width="2.2" />'
    if shape == "diamond":
        points = f"{x},{y - 50} {x + 74},{y} {x},{y + 50} {x - 74},{y}"
        return f'<polygon points="{points}" fill="{node_fill}" stroke="{stroke}" stroke-width="2.2" />'
    if shape == "parallelogram":
        points = f"{x - 72},{y + 42} {x - 34},{y - 42} {x + 72},{y - 42} {x + 34},{y + 42}"
        return f'<polygon points="{points}" fill="{node_fill}" stroke="{stroke}" stroke-width="2.2" />'
    if shape == "hexagon":
        points = f"{x - 72},{y} {x - 40},{y - 44} {x + 40},{y - 44} {x + 72},{y} {x + 40},{y + 44} {x - 40},{y + 44}"
        return f'<polygon points="{points}" fill="{node_fill}" stroke="{stroke}" stroke-width="2.2" />'

    rx = ' rx="18"' if shape == "rounded" else ""
    return (
        f'<rect x="{x - NODE_W / 2}" y="{y - NODE_H / 2}" width="{NODE_W}" height="{NODE_H}"{rx} '
        f'fill="{node_fill}" stroke="{stroke}" stroke-width="2.2" />'
    )


def render_svg(state: GraphState) -> str:
    theme = THEMES[state.theme]
    positions = apply_layout(state.nodes, state.layout)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" style="display:block;width:100%;height:auto;">',
        "<defs>",
        (
            f'<marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">'
            f'<path d="M0,0 L10,4 L0,8 z" fill="{theme["edge"]}" />'
            "</marker>"
        ),
        "</defs>",
        f'<rect x="0" y="0" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" fill="{theme["bg"]}" rx="16" />',
    ]

    for edge in state.edges:
        from_pos = positions.get(edge.from_node)
        to_pos = positions.get(edge.to_node)
        if not from_pos or not to_pos:
            continue

        x1, y1, x2, y2 = shrink_line_to_shape_boundary(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
        dash = ""
        if edge.style == "dashed":
            dash = ' stroke-dasharray="8 6"'
        elif edge.style == "dotted":
            dash = ' stroke-dasharray="2 6"'

        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{theme["edge"]}" '
            f'stroke-width="2.4" marker-end="url(#arrow)"{dash} />'
        )

        if edge.label:
            lx, ly = midpoint(x1, y1, x2, y2)
            parts.append(_svg_text(lx, ly - 10, edge.label, theme["text"], 12))

    for node in state.nodes:
        x, y = positions[node.id]
        parts.append(_shape_svg(node.shape, x, y, theme["node"], theme["stroke"]))
        parts.append(_svg_text(x, y + 5, node.label, theme["text"], 14, weight="600"))
        parts.append(_svg_text(x, y - 30, node.id, theme["text"], 11))

    parts.append("</svg>")
    return "\n".join(parts)


# =========================
# Session state
# =========================
def init_session() -> None:
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = auto_build(4)
    if DSL_KEY not in st.session_state:
        st.session_state[DSL_KEY] = state_to_dsl(st.session_state[SESSION_KEY])
    if MESSAGE_KEY not in st.session_state:
        st.session_state[MESSAGE_KEY] = "Ready. Edit controls or the script to design your graph."
    if ERROR_KEY not in st.session_state:
        st.session_state[ERROR_KEY] = False


def get_state() -> GraphState:
    return st.session_state[SESSION_KEY]


def set_state(graph: GraphState) -> None:
    st.session_state[SESSION_KEY] = graph
    st.session_state[DSL_KEY] = state_to_dsl(graph)


def set_message(message: str, error: bool = False) -> None:
    st.session_state[MESSAGE_KEY] = message
    st.session_state[ERROR_KEY] = error


# =========================
# UI blocks
# =========================
def top_actions() -> None:
    state = get_state()
    st.subheader("Graph Controls")
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("Add box", use_container_width=True):
            state.nodes.append(create_node(len(state.nodes)))
            set_state(state)
            st.rerun()

    with c2:
        if st.button("Add connection", use_container_width=True):
            if len(state.nodes) < 2:
                set_message("Need at least two boxes to create a connection.", True)
            else:
                state.edges.append(create_edge(state.nodes[0].id, state.nodes[-1].id, len(state.edges)))
                set_state(state)
                st.rerun()

    with c3:
        count = st.number_input("Auto build count", min_value=1, max_value=50, value=max(1, len(state.nodes)), step=1)
        if st.button("Auto build", use_container_width=True):
            fresh = auto_build(int(count))
            fresh.theme = state.theme
            fresh.layout = state.layout
            set_state(fresh)
            set_message(f"Created {len(fresh.nodes)} boxes with starter connections.")
            st.rerun()


def graph_settings() -> None:
    state = get_state()
    st.subheader("Quick Config")
    c1, c2 = st.columns(2)
    theme = c1.selectbox("Theme", options=list(THEMES.keys()), index=list(THEMES.keys()).index(state.theme))
    layout = c2.selectbox("Layout", options=LAYOUTS, index=LAYOUTS.index(state.layout))
    if theme != state.theme or layout != state.layout:
        state.theme = theme
        state.layout = layout
        set_state(state)


def edit_nodes() -> None:
    state = get_state()
    st.subheader("Boxes")

    if not state.nodes:
        st.info("No boxes yet.")
        return

    delete_index: int | None = None
    updated_nodes: list[Node] = []
    assigned_ids: set[str] = set()

    for i, node in enumerate(state.nodes):
        with st.container(border=True):
            cols = st.columns([1.0, 1.4, 1.0, 0.65])
            raw_id = cols[0].text_input("ID", value=node.id, key=f"node_id_{i}")
            label = cols[1].text_input("Label", value=node.label, key=f"node_label_{i}")
            shape = cols[2].selectbox("Shape", SHAPES, index=SHAPES.index(node.shape), key=f"node_shape_{i}")
            if cols[3].button("Delete", key=f"node_delete_{i}", use_container_width=True):
                delete_index = i

            clean_id = sanitize_token(raw_id) or node.id
            if clean_id in assigned_ids:
                suffix = 2
                candidate = f"{clean_id}_{suffix}"
                while candidate in assigned_ids:
                    suffix += 1
                    candidate = f"{clean_id}_{suffix}"
                clean_id = candidate
            assigned_ids.add(clean_id)
            updated_nodes.append(Node(id=clean_id, label=label, shape=shape))

    if delete_index is not None:
        deleted_id = state.nodes[delete_index].id
        state.nodes.pop(delete_index)
        state.edges = [e for e in state.edges if e.from_node != deleted_id and e.to_node != deleted_id]
        set_state(state)
        set_message(f'Deleted box "{deleted_id}" and related connections.')
        st.rerun()

    old_to_new = {old.id: new.id for old, new in zip(state.nodes, updated_nodes)}
    state.nodes = updated_nodes
    for edge in state.edges:
        edge.from_node = old_to_new.get(edge.from_node, edge.from_node)
        edge.to_node = old_to_new.get(edge.to_node, edge.to_node)
    set_state(state)


def edit_edges() -> None:
    state = get_state()
    st.subheader("Connections")

    if len(state.nodes) < 2:
        st.info("Add at least two boxes to manage connections.")
        return

    node_ids = [node.id for node in state.nodes]
    if not state.edges:
        st.info("No connections yet.")
        return

    delete_index: int | None = None
    updated_edges: list[Edge] = []

    for i, edge in enumerate(state.edges):
        with st.container(border=True):
            cols = st.columns([1.0, 0.15, 1.0, 1.4, 0.9, 0.65])
            from_idx = node_ids.index(edge.from_node) if edge.from_node in node_ids else 0
            to_idx = node_ids.index(edge.to_node) if edge.to_node in node_ids else 0
            from_id = cols[0].selectbox("From", node_ids, index=from_idx, key=f"edge_from_{i}")
            cols[1].markdown("<div style='padding-top:2rem;text-align:center;'>→</div>", unsafe_allow_html=True)
            to_id = cols[2].selectbox("To", node_ids, index=to_idx, key=f"edge_to_{i}")
            label = cols[3].text_input("Label", value=edge.label, key=f"edge_label_{i}")
            style = cols[4].selectbox("Style", EDGE_STYLES, index=EDGE_STYLES.index(edge.style), key=f"edge_style_{i}")
            if cols[5].button("Delete", key=f"edge_delete_{i}", use_container_width=True):
                delete_index = i
            updated_edges.append(Edge(from_node=from_id, to_node=to_id, label=label, style=style))

    if delete_index is not None:
        state.edges.pop(delete_index)
        set_state(state)
        set_message("Connection deleted.")
        st.rerun()

    state.edges = updated_edges
    set_state(state)


def dsl_editor() -> None:
    state = get_state()
    st.subheader("Line-based graph script")
    c1, c2, c3 = st.columns(3)

    if c1.button("Sync to script", use_container_width=True):
        st.session_state[DSL_KEY] = state_to_dsl(state)
        set_message("UI synced to script editor.")

    if c2.button("Apply script", use_container_width=True):
        maybe_state, errors = apply_dsl(st.session_state[DSL_KEY], state)
        if errors:
            set_message("\n".join(errors), True)
        elif maybe_state is not None:
            set_state(maybe_state)
            set_message("Script applied successfully.")
            st.rerun()

    if c3.button("Load sample", use_container_width=True):
        st.session_state[DSL_KEY] = SAMPLE_DSL
        maybe_state, errors = apply_dsl(SAMPLE_DSL, state)
        if errors:
            set_message("\n".join(errors), True)
        elif maybe_state is not None:
            set_state(maybe_state)
            set_message("Loaded sample graph.")
            st.rerun()

    st.text_area(
        "DSL",
        key=DSL_KEY,
        height=280,
        help='Format: graph theme=default layout=grid | node id shape "Label" | edge from -> to "Label" style=solid',
    )

    if st.session_state[ERROR_KEY]:
        st.error(st.session_state[MESSAGE_KEY])
    else:
        st.success(st.session_state[MESSAGE_KEY])


def import_export_panel() -> None:
    state = get_state()
    st.subheader("Import / Export")

    svg_text = render_svg(state)
    json_text = json.dumps(state.to_dict(), indent=2)

    c1, c2 = st.columns(2)
    c1.download_button(
        "Export SVG",
        data=svg_text.encode("utf-8"),
        file_name="lines-graph.svg",
        mime="image/svg+xml",
        use_container_width=True,
    )
    c2.download_button(
        "Download JSON",
        data=json_text.encode("utf-8"),
        file_name="lines-graph.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded = st.file_uploader("Import JSON graph", type=["json"])
    if uploaded is not None:
        try:
            payload = json.loads(uploaded.read().decode("utf-8"))
            graph = GraphState.from_dict(payload)
            set_state(graph)
            set_message("JSON graph imported successfully.")
            st.rerun()
        except Exception as exc:
            set_message(f"Failed to import JSON: {exc}", True)


def preview_panel() -> None:
    st.subheader("Live Preview")
    svg = render_svg(get_state())
    st.components.v1.html(svg, height=860, scrolling=True)


# =========================
# App
# =========================
st.set_page_config(page_title="Lines Studio", page_icon=" ", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 1.5rem;
    }
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
    }
    .subtle {
        color: #6b7280;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_session()

st.markdown('<div class="main-title">Lines Studio</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">Single-file production-oriented Streamlit graph builder with live SVG preview, DSL editing, and JSON/SVG export.</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([1.05, 1.15], gap="large")

with left:
    top_actions()
    st.divider()
    graph_settings()
    st.divider()
    edit_nodes()
    st.divider()
    edit_edges()
    st.divider()
    dsl_editor()
    st.divider()
    import_export_panel()

with right:
    preview_panel()
