# Lines Studio

Lines Studio is a complete end-to-end line-based graph making web app inspired by Mermaid Live and flowchart tooling.

## Features

- Build graphs from a visual editor and a line-based script (DSL).
- Configure number of boxes quickly and auto-generate starter connections.
- Customize each box:
  - ID
  - Label/data text
  - Shape (`rectangle`, `rounded`, `circle`, `diamond`, `parallelogram`, `hexagon`)
- Customize each connection:
  - Start/end box
  - Label
  - Style (`solid`, `dashed`, `dotted`)
- Live SVG preview panel with themes and multiple layout modes.
- Export as SVG and JSON.
- Parse and apply custom scripts with inline validation errors.

## Run locally

Since this is a static app, run any simple web server from the repository root:

```bash
python3 -m http.server 4173
```

Then open <http://localhost:4173> in your browser.

## DSL reference

```txt
graph theme=default layout=grid
node N1 rectangle "Input"
node N2 diamond "Decision"
edge N1 -> N2 "next" style=solid
```

Rules:

- First line (optional): `graph theme=<theme> layout=<layout>`
- Node line: `node <id> <shape> "<label>"`
- Edge line: `edge <from> -> <to> "<label>" style=<style>`
- You can use `#` comments.
