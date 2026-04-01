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

// Match the workflow save endpoint (path separator may be URL-encoded as %2F)
function isWorkflowSave(route, method) {
  if (method !== "POST" && method !== "PUT") return false;
  if (route.startsWith("/workflow-runner/")) return false;
  return route.includes("/userdata/") && route.includes("workflow");
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

    // Intercept fetchApi to detect workflow saves (manual, auto-save, save-as)
    const originalFetchApi = api.fetchApi.bind(api);
    api.fetchApi = async function (route, options, ...rest) {
      const method = options?.method?.toUpperCase() || "GET";
      if (method !== "GET") {
        console.log(`[workflow-runner] fetchApi ${method} ${route}`);
      }

      const resp = await originalFetchApi(route, options, ...rest);

      if (isWorkflowSave(route, method)) {
        console.log(`[workflow-runner] Workflow save detected: ${method} ${route}`);
        exportApiFormat(originalGraphToPrompt);
      }

      return resp;
    };
  },
});
