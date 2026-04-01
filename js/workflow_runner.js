// ABOUTME: ComfyUI frontend extension that auto-exports expanded API format on save.
// ABOUTME: Intercepts graphToPrompt() and persists .api.json via server route.

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "workflow-runner.auto-export",

  setup() {
    const originalGraphToPrompt = app.graphToPrompt.bind(app);

    app.graphToPrompt = async function (...args) {
      const result = await originalGraphToPrompt(...args);

      const workflowName = app.graph?.extra?.workflow?.name
        || app.extensionManager?.workflow?.activeWorkflow?.filename
        || null;

      if (!workflowName) {
        console.warn("[workflow-runner] No workflow name found, skipping .api.json export");
        return result;
      }

      api.fetchApi("/workflow-runner/save-api", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: workflowName,
          api_workflow: result.output,
          ui_workflow: result.workflow,
        }),
      }).catch((err) =>
        console.error("[workflow-runner] Failed to save .api.json:", err)
      );

      return result;
    };
  },
});
