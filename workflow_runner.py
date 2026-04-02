# ABOUTME: Core logic for running ComfyUI workflows from pre-expanded .api.json files.
# ABOUTME: Handles schema scanning, input injection, dependency pruning, and schema detection.

import json
import os


INPUT_NODE_COLOR = "#332922"
OUTPUT_NODE_COLOR = "#232"
PROD_GROUP_COLOR = "#8A8"


def _classify_output_type(class_type: str) -> str:
    if "SaveImage" in class_type:
        return "image"
    if "SaveVideo" in class_type:
        return "video"
    return "text"


def scan_schema(ui_workflow: dict) -> dict:
    """Scan a UI workflow for input/output nodes by color convention.

    Input nodes: color #332922 inside green production groups (#8A8)
    Output nodes: color #232 inside green production groups (#8A8)

    Returns {inputs: [...], outputs: [...]} with node_id, slug, class_type,
    group, and (for outputs) output_type.
    """
    prod_groups = [
        g for g in ui_workflow.get("groups", [])
        if g.get("color") == PROD_GROUP_COLOR
    ]

    inputs = []
    outputs = []

    for node in ui_workflow.get("nodes", []):
        color = node.get("color", "")
        if color not in (INPUT_NODE_COLOR, OUTPUT_NODE_COLOR):
            continue

        nx, ny = node["pos"][0], node["pos"][1]
        for group in prod_groups:
            gx, gy, gw, gh = group["bounding"]
            if gx <= nx <= gx + gw and gy <= ny <= gy + gh:
                entry = {
                    "node_id": str(node["id"]),
                    "slug": node.get("title", ""),
                    "class_type": node.get("type", ""),
                    "group": group["title"],
                }
                if color == INPUT_NODE_COLOR:
                    inputs.append(entry)
                else:
                    entry["output_type"] = _classify_output_type(entry["class_type"])
                    outputs.append(entry)
                break

    return {"inputs": inputs, "outputs": outputs}


def load_api_workflow(path: str) -> dict:
    """Load a pre-expanded .api.json workflow file."""
    with open(path) as f:
        return json.load(f)


def detect_schema(api_workflow: dict, input_slugs: list[str] | None = None) -> dict:
    """Detect input and output nodes from an API workflow by _meta.title.

    Input nodes are identified by matching their title against known slugs.
    Output nodes are identified by class_type (SaveImage, SaveVideo, PreviewAny).
    """
    OUTPUT_CLASSES = {"SaveImage", "SaveVideo", "CreateVideo", "PreviewAny"}

    inputs = []
    outputs = []

    for node_id, node in api_workflow.items():
        title = node.get("_meta", {}).get("title", "")
        class_type = node.get("class_type", "")

        if input_slugs and title in input_slugs:
            inputs.append({
                "node_id": node_id,
                "slug": title,
                "class_type": class_type,
            })

        if class_type in OUTPUT_CLASSES:
            if "SaveImage" in class_type:
                output_type = "image"
            elif "SaveVideo" in class_type or "CreateVideo" in class_type:
                output_type = "video"
            else:
                output_type = "text"
            outputs.append({
                "node_id": node_id,
                "slug": title,
                "class_type": class_type,
                "output_type": output_type,
            })

    return {"inputs": inputs, "outputs": outputs}


def set_node_input(node: dict, value) -> None:
    """Set the primary input value of a node, detecting the correct key."""
    inputs = node.get("inputs", {})
    for key in ("string", "String", "text", "value"):
        if key in inputs:
            inputs[key] = value
            return
    for key in ("number", "int", "float", "seed", "batch_index"):
        if key in inputs:
            inputs[key] = int(value) if isinstance(value, str) and value.isdigit() else value
            return


def inject_inputs(api_workflow: dict, input_data: dict,
                   schema_inputs: list[dict] | None = None) -> None:
    """Inject input values into workflow nodes.

    When schema_inputs is provided (list of {node_id, slug} dicts), targets
    exact node IDs. Otherwise falls back to matching all nodes by _meta.title.
    """
    if schema_inputs:
        slug_to_ids = {}
        for entry in schema_inputs:
            slug_to_ids.setdefault(entry["slug"], []).append(entry["node_id"])
    else:
        slug_to_ids = {}
        for node_id, node in api_workflow.items():
            title = node.get("_meta", {}).get("title", "")
            if title:
                slug_to_ids.setdefault(title, []).append(node_id)

    for slug, value in input_data.items():
        if not value:
            continue
        for node_id in slug_to_ids.get(slug, []):
            if node_id in api_workflow:
                set_node_input(api_workflow[node_id], value)


def prune_to_outputs(api_workflow: dict, output_ids: set[str]) -> dict:
    """Keep only output nodes and their transitive dependencies."""
    needed = set()
    queue = [nid for nid in output_ids if nid in api_workflow]
    while queue:
        nid = queue.pop()
        if nid in needed:
            continue
        needed.add(nid)
        node = api_workflow.get(nid, {})
        for val in node.get("inputs", {}).values():
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                dep_id = val[0]
                if dep_id in api_workflow and dep_id not in needed:
                    queue.append(dep_id)
    return {k: v for k, v in api_workflow.items() if k in needed}


def prepare_workflow(api_path: str, input_data: dict,
                     output_slugs: list[str] | None = None) -> dict:
    """Load, inject inputs, optionally prune, and return ready-to-submit workflow.

    Args:
        api_path: Path to .api.json file
        input_data: Dict of {slug: value} for input injection
        output_slugs: If provided, prune to only these output nodes + deps.
                      If None, submit the full workflow.

    Returns:
        The prepared API workflow dict, ready for /prompt submission.
    """
    workflow = load_api_workflow(api_path)
    inject_inputs(workflow, input_data)

    if output_slugs:
        schema = detect_schema(workflow)
        output_ids = {
            out["node_id"] for out in schema["outputs"]
            if out["slug"] in output_slugs
        }
        if output_ids:
            workflow = prune_to_outputs(workflow, output_ids)

    return workflow
