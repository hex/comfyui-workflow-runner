// ABOUTME: ComfyUI frontend extension that auto-exports expanded API format.
// ABOUTME: Exports on queue (graphToPrompt hook) and any save (fetchApi intercept).

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function getWorkflowName() {
  return app.extensionManager?.workflow?.activeWorkflow?.filename
    || app.extensionManager?.workflow?.activeWorkflow?.name
    || app.graph?.extra?.workflow?.name
    || null;
}

let _exportInFlight = false;

async function exportApiFormat(originalGraphToPrompt) {
  if (_exportInFlight) return;
  _exportInFlight = true;

  try {
    const name = getWorkflowName();
    if (!name) {
      console.warn("[workflow-runner] No workflow name found, skipping export");
      return;
    }

    const result = await originalGraphToPrompt();

    const resp = await api.fetchApi("/workflow-runner/save-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        api_workflow: result.output,
        ui_workflow: result.workflow,
      }),
    });

    if (resp.ok) {
      console.log("[workflow-runner] Exported .api.json for:", name);
    } else {
      const t = await resp.text();
      console.error("[workflow-runner] Server error:", t);
    }
  } catch (err) {
    console.error("[workflow-runner] Export failed:", err);
  } finally {
    _exportInFlight = false;
  }
}

app.registerExtension({
  name: "workflow-runner.auto-export",

  setup() {
    const originalGraphToPrompt = app.graphToPrompt.bind(app);

    // Hook graphToPrompt — fires on queue/run
    app.graphToPrompt = async function (...args) {
      const result = await originalGraphToPrompt(...args);
      exportApiFormat(originalGraphToPrompt);
      return result;
    };

    // Intercept fetchApi to detect any workflow save (manual, auto-save, save-as).
    // ComfyUI saves workflows via POST/PUT to /api/userdata/workflows/
    const originalFetchApi = api.fetchApi.bind(api);
    api.fetchApi = async function (route, options, ...rest) {
      const resp = await originalFetchApi(route, options, ...rest);

      if (route.includes("/userdata/") && route.includes("workflows/")) {
        const method = options?.method?.toUpperCase() || "GET";
        if (method === "POST" || method === "PUT") {
          console.log("[workflow-runner] Workflow save detected, exporting .api.json");
          exportApiFormat(originalGraphToPrompt);
        }
      }

      return resp;
    };
  },
});
