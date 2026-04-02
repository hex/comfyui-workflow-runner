# Workflow Runner

A ComfyUI extension that auto-exports expanded API-format workflows and provides server routes to run them programmatically.

## Why

ComfyUI workflows are saved in LiteGraph UI format — they contain components, virtual nodes, and widget references that need expansion before execution. The browser's `graphToPrompt()` is the only complete implementation that handles this expansion. This extension captures that expanded output and persists it as `.api.json`, so external tools can load and run workflows without reimplementing the expansion logic.

## How it works

```
DESIGN TIME (browser):
  Save/auto-save triggers in editor
  -> Extension detects save via fetchApi intercept
  -> Calls graphToPrompt() to get expanded API format
  -> POSTs to /workflow-runner/save-api
  -> Saves {name}.api.json alongside the UI workflow
  -> Scans UI workflow for color-coded input/output nodes
  -> Saves {name}.schema.json with group info for phase-splitting

RUNTIME (server):
  POST /workflow-runner/run { workflow: "name", inputs: { "client-name": "Tesla" } }
  -> Loads name.api.json (pre-expanded)
  -> Injects inputs by node title (or by schema for precision)
  -> Optionally prunes to specific output nodes + transitive deps
  -> Queues to prompt execution
  -> Returns prompt_id
```

Every save produces three files:

```
my-workflow.json          # UI workflow (ComfyUI native)
my-workflow.api.json      # Expanded API format (ready for /prompt)
my-workflow.schema.json   # Input/output schema with groups
```

## Install

Symlink or clone into your ComfyUI `custom_nodes/` directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/hex/comfyui-workflow-runner.git
```

Restart ComfyUI. The extension loads automatically — no dependencies beyond what ComfyUI already provides.

## Schema

The schema is auto-generated from the UI workflow using color conventions:

- **Input nodes**: color `#332922` inside green groups (`#8A8`)
- **Output nodes**: color `#232` inside green groups (`#8A8`)

Each entry includes the production group name, enabling phase-based execution:

```json
{
  "inputs": [
    { "node_id": "968", "slug": "client-name", "class_type": "String Literal", "group": "1-client-info-page" },
    { "node_id": "977", "slug": "avatar-select", "class_type": "ImageFromBatch", "group": "3-avatar-proposals" }
  ],
  "outputs": [
    { "node_id": "972", "slug": "client-intelligence", "class_type": "PreviewAny", "output_type": "text", "group": "1-client-info-page" },
    { "node_id": "980", "slug": "avatar-proposals", "class_type": "SaveImage", "output_type": "image", "group": "3-avatar-proposals" },
    { "node_id": "923", "slug": "demo-video-1", "class_type": "SaveVideo", "output_type": "video", "group": "5-videos" }
  ]
}
```

Phase-splitting from the schema without hardcoded slugs:

```python
schema = json.load(open("my-workflow.schema.json"))
phase1_outputs = [o for o in schema["outputs"] if o["group"] in PHASE1_GROUPS]
```

## API

### `POST /workflow-runner/save-api`

Save an expanded API-format workflow. Called automatically by the frontend extension. Also generates `.schema.json` when `ui_workflow` is provided.

```json
{ "name": "my-workflow", "api_workflow": { ... }, "ui_workflow": { ... } }
```

### `POST /workflow-runner/run`

Run a saved workflow with injected inputs.

```json
{
  "workflow": "my-workflow",
  "inputs": {
    "client-name": "Tesla",
    "client-market": "electric vehicles"
  },
  "outputs": ["demo-video-1"],
  "schema_inputs": null
}
```

- `workflow` — name of the `.api.json` file (without extension)
- `inputs` — key-value pairs matched to nodes by `_meta.title`
- `outputs` — (optional) prune to these output nodes and their dependencies
- `schema_inputs` — (optional) explicit `[{node_id, slug}]` list for precise input targeting when titles are ambiguous

### `GET /workflow-runner/schema/{name}`

Returns detected inputs and outputs for a workflow (from the `.api.json`, not the persisted schema).

## Input injection

Inputs are matched by `_meta.title` — the node's display title in the editor. The value is set on the node's primary input key (`string`, `batch_index`, `seed`, etc.).

When multiple nodes share the same title, all are injected. Use `schema_inputs` for precise targeting.

## Dependency pruning

When `outputs` is specified, only the listed output nodes and their transitive dependencies are submitted. This lets you run a single output pipeline from a large multi-output workflow.

## Tests

```bash
uv venv .venv && source .venv/bin/activate
uv pip install pytest
pytest
```

Tests require workflow fixtures in `tests/fixtures/` (not included in the repo — extract from a captured `/prompt` POST).
