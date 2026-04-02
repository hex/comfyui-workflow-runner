# ABOUTME: ComfyUI extension entry point. Registers server routes for saving
# ABOUTME: and running pre-expanded .api.json workflows.

import json
import logging
import os

log = logging.getLogger("workflow-runner")

try:
    from .workflow_runner import (
        detect_schema,
        inject_inputs,
        load_api_workflow,
        prune_to_outputs,
        scan_schema,
    )
except ImportError:
    from workflow_runner import (
        detect_schema,
        inject_inputs,
        load_api_workflow,
        prune_to_outputs,
        scan_schema,
    )

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

WORKFLOWS_DIR = os.environ.get(
    "COMFYUI_WORKFLOWS_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                 "user", "default", "workflows"),
)

# Route registration requires ComfyUI's server module. Guard the import so
# this file can be loaded during testing (where aiohttp/server are absent).
try:
    from aiohttp import web
    from server import PromptServer

    @PromptServer.instance.routes.post("/workflow-runner/save-api")
    async def save_api_format(request):
        """Receive expanded API format from the frontend and save as .api.json.

        Also generates .schema.json from the UI workflow if provided.
        """
        data = await request.json()
        name = data.get("name")
        api_workflow = data.get("api_workflow")
        ui_workflow = data.get("ui_workflow")

        if not name or not api_workflow:
            log.warning("save-api: missing 'name' or 'api_workflow'")
            return web.json_response(
                {"error": "Missing 'name' or 'api_workflow'"},
                status=400,
            )

        stem = name
        if stem.endswith(".json"):
            stem = stem[:-5]

        os.makedirs(WORKFLOWS_DIR, exist_ok=True)
        api_path = os.path.join(WORKFLOWS_DIR, f"{stem}.api.json")

        with open(api_path, "w") as f:
            json.dump(api_workflow, f, indent=2)

        log.info("Saved %s (%d nodes)", api_path, len(api_workflow))

        schema = None
        if ui_workflow:
            schema = scan_schema(ui_workflow)
            schema_path = os.path.join(WORKFLOWS_DIR, f"{stem}.schema.json")
            with open(schema_path, "w") as f:
                json.dump(schema, f, indent=2)
            log.info("Saved %s (%d inputs, %d outputs)",
                     schema_path, len(schema["inputs"]), len(schema["outputs"]))

        return web.json_response({
            "status": "ok",
            "path": api_path,
            "nodes": len(api_workflow),
            "schema": schema,
        })

    @PromptServer.instance.routes.post("/workflow-runner/run")
    async def run_workflow(request):
        """Load a pre-expanded workflow, inject inputs, optionally prune, and submit.

        POST body:
            workflow: str - workflow name (without .api.json extension)
            inputs: dict - {slug: value} mapping for input injection
            outputs: list[str] | null - output slugs to prune to (null = full)
            schema_inputs: list[dict] | null - explicit [{node_id, slug}]
        """
        data = await request.json()
        workflow_name = data.get("workflow")
        input_data = data.get("inputs", {})
        output_slugs = data.get("outputs")
        schema_inputs = data.get("schema_inputs")

        if not workflow_name:
            log.warning("run: missing 'workflow'")
            return web.json_response(
                {"error": "Missing 'workflow'"}, status=400,
            )

        stem = workflow_name
        if stem.endswith(".api.json"):
            stem = stem[:-9]
        elif stem.endswith(".json"):
            stem = stem[:-5]

        api_path = os.path.join(WORKFLOWS_DIR, f"{stem}.api.json")
        if not os.path.isfile(api_path):
            return web.json_response(
                {"error": f"Workflow not found: {stem}.api.json"},
                status=404,
            )

        workflow = load_api_workflow(api_path)
        inject_inputs(workflow, input_data, schema_inputs=schema_inputs)

        if output_slugs:
            schema = detect_schema(workflow)
            output_ids = {
                out["node_id"] for out in schema["outputs"]
                if out["slug"] in output_slugs
            }
            if output_ids:
                workflow = prune_to_outputs(workflow, output_ids)

        import uuid
        import execution

        prompt_id = str(uuid.uuid4())
        extra_data = {"extra_pnginfo": {"workflow": {"nodes": []}}}
        valid = execution.validate_prompt(workflow)
        if not valid[0]:
            return web.json_response(
                {"error": "Prompt validation failed", "details": valid[1]},
                status=400,
            )

        PromptServer.instance.prompt_queue.put(
            (0, prompt_id, workflow, extra_data, valid[2])
        )

        log.info("Queued %s (%d nodes) as %s", stem, len(workflow), prompt_id)

        return web.json_response({
            "status": "ok",
            "prompt_id": prompt_id,
            "nodes_submitted": len(workflow),
        })

    @PromptServer.instance.routes.get("/workflow-runner/schema/{name}")
    async def get_workflow_schema(request):
        """Return detected input/output schema for a workflow."""
        name = request.match_info["name"]
        stem = name
        if stem.endswith(".api.json"):
            stem = stem[:-9]
        elif stem.endswith(".json"):
            stem = stem[:-5]

        api_path = os.path.join(WORKFLOWS_DIR, f"{stem}.api.json")
        if not os.path.isfile(api_path):
            return web.json_response(
                {"error": f"Workflow not found: {stem}.api.json"},
                status=404,
            )

        workflow = load_api_workflow(api_path)
        schema = detect_schema(workflow)

        return web.json_response(schema)

except ImportError:
    pass
