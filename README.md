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

RUNTIME (server):
  POST /workflow-runner/run { workflow: "name", inputs: { "client-name": "Tesla" } }
  -> Loads name.api.json (pre-expanded)
  -> Injects inputs by node title
  -> Optionally prunes to specific output nodes + transitive deps
  -> Queues to prompt execution
  -> Returns prompt_id
```

## Install

Symlink or clone into your ComfyUI `custom_nodes/` directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/hex/comfyui-workflow-runner.git
```

Restart ComfyUI. The extension loads automatically — no dependencies beyond what ComfyUI already provides.

## API

### `POST /workflow-runner/save-api`

Save an expanded API-format workflow. Called automatically by the frontend extension.

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

Returns detected inputs and outputs for a workflow.

```json
{
  "inputs": [
    { "node_id": "968", "slug": "client-name", "class_type": "String Literal" }
  ],
  "outputs": [
    { "node_id": "923", "slug": "demo-video-1", "class_type": "SaveVideo", "output_type": "video" }
  ]
}
```

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

Tests require a workflow fixture in `tests/fixtures/test_workflow.api.json` (not included in the repo — extract from a captured `/prompt` POST).
