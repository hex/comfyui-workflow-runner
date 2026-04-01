// ABOUTME: ComfyUI frontend extension that auto-exports expanded API format.
// ABOUTME: Exports on queue (via graphToPrompt hook) and on save (via Ctrl+S listener).

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function getWorkflowName() {
  return app.extensionManager?.workflow?.activeWorkflow?.filename
    || app.extensionManager?.workflow?.activeWorkflow?.name
    || app.graph?.extra?.workflow?.name
    || null;
}

function exportApiFormat(output, workflow) {
  const name = getWorkflowName();
  if (!name) {
    console.warn("[workflow-runner] No workflow name found, skipping .api.json export");
    return;
  }

  api.fetchApi("/workflow-runner/save-api", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      api_workflow: output,
      ui_workflow: workflow,
    }),
  })
    .then((r) => {
      if (r.ok) console.log("[workflow-runner] Exported .api.json for:", name);
      else r.text().then((t) => console.error("[workflow-runner] Server error:", t));
    })
    .catch((err) => console.error("[workflow-runner] Failed to save .api.json:", err));
}

app.registerExtension({
  name: "workflow-runner.auto-export",

  setup() {
    // Hook graphToPrompt — fires on queue/run
    const originalGraphToPrompt = app.graphToPrompt.bind(app);
    app.graphToPrompt = async function (...args) {
      const result = await originalGraphToPrompt(...args);
      exportApiFormat(result.output, result.workflow);
      return result;
    };

    // Listen for save (Ctrl+S / Cmd+S) — graphToPrompt doesn't fire on save
    document.addEventListener("keydown", async (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        try {
          const result = await originalGraphToPrompt();
          exportApiFormat(result.output, result.workflow);
        } catch (err) {
          console.error("[workflow-runner] Failed to export on save:", err);
        }
      }
    });
  },
});
