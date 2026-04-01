# Discoveries & Notes

## response.json is already pruned (2026-04-01)

The captured `/prompt` POST in response.json contains 312 nodes, but this is already
the pruned dependency tree for a single output: `demo-video-1` (node 923). The other
10 output nodes (avatar-proposals, client-intelligence, etc.) are NOT present because
they're on separate output paths that weren't queued.

Implication: the full `.api.json` from `graphToPrompt()` will contain MORE than 312 nodes
(all output paths). The fixture is useful for testing inject/prune but doesn't represent
the full unexpanded workflow.

## Duplicate node titles exist (2026-04-01)

Two nodes share the title "client-region":
- Node 933: the actual user input (value: "europe uk")
- Node 984: a prompt template prefix (value: "Client region of activity is:\n")

Title-based injection hits both nodes. The schema sidecar (using color-coded groups to
identify specific input nodes by position) is needed to disambiguate. For now,
`inject_inputs` supports an optional `schema_inputs` list for precise targeting.

## Output node types in fixture (2026-04-01)

Only 2 output class_types found: SaveVideo (1 named), CreateVideo (5 intermediate).
No SaveImage or PreviewAny nodes — those are on the other output paths not captured.

## workflow_sync.py already handles .api.json (2026-04-01)

No changes needed. The `.api` suffix becomes part of the filename stem during
flat<->repo mapping. `flat_to_repo_path("avatara-dev-x.api.json")` correctly
produces `avatara/dev/x.api.json` and round-trips back. The `.endswith(".json")`
filter in scan functions passes both `.json` and `.api.json`.

## ComfyUI Frontend Extension API (researched 2026-04-01)

### Import paths
```js
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
```
The `../../` is relative to the served extension path — it resolves to the ComfyUI web root regardless of where `WEB_DIRECTORY` points on disk.

### Extension registration
```js
app.registerExtension({ name: "unique.extension.name", ...hooks });
```

### Extension hooks (from ComfyExtension interface in src/types/comfy.ts)
Full list of official hooks — all are optional methods on the extension object:
- `init(app)` — after canvas created, before nodes registered. Good place to monkey-patch app methods.
- `setup(app)` — after full startup. Good place for event listeners.
- `addCustomNodeDefs(defs, app)`
- `getCustomWidgets(app)`
- `beforeRegisterNodeDef(nodeType, nodeData, app)`
- `beforeRegisterVueAppNodeDefs(defs, app)`
- `registerCustomNodes(app)`
- `loadedGraphNode(node, app)`
- `nodeCreated(node, app)`
- `beforeConfigureGraph(graphData, missingNodeTypes, app)`
- `afterConfigureGraph(missingNodeTypes, app)`
- `onAuthUserResolved(user, app)`
- `onAuthTokenRefreshed()`
- `onAuthUserLogout()`

There is NO built-in hook for the save workflow event. Save goes through
`workflowService.saveWorkflow(workflow)` (called by the `Comfy.SaveWorkflow` command) — this is internal Vue app code with no extension hook.

### How to intercept save: monkey-patch graphToPrompt
The universal approach used across the ecosystem is to wrap `app.graphToPrompt` inside `setup()` or `init()`:
```js
setup(app) {
    const _original = app.graphToPrompt.bind(app);
    app.graphToPrompt = async function (...args) {
        const result = await _original(...args);
        // result = { workflow: ComfyWorkflowJSON, output: ComfyApiWorkflow }
        // do work here
        return result;
    };
}
```
Note: The official docs mark monkey-patching as deprecated, but there is no alternative hook for save.

### graphToPrompt return value (from src/utils/executionUtil.ts)
```ts
Promise<{ workflow: ComfyWorkflowJSON; output: ComfyApiWorkflow }>
```
- `output` — the API format: `{ [node_id: string]: { class_type: string, inputs: {...}, _meta: { title: string } } }`
  - widget values stored directly; node connections stored as `[upstream_node_id_string, slot_index_int]`
  - muted/bypassed nodes excluded
- `workflow` — the LiteGraph serialization format (nodes, links, groups, extra, etc.)

### api.fetchApi signature (from src/scripts/api.ts)
```ts
async fetchApi(route: string, options?: RequestInit): Promise<Response>
```
Returns a standard `fetch` Response. Example POST:
```js
const resp = await api.fetchApi("/my_custom_route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
});
```

### WEB_DIRECTORY setup (Python side, __init__.py)
```python
WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
```
All `.js` files in that directory are auto-loaded. Only `.js` files — CSS must be loaded programmatically.
