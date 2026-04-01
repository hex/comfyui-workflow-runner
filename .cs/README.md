# Session: comfyui-workflow-runner

**Started:** 2026-04-01 22:44:09
**Location:** hex-macbook-air:/Users/hex/.claude-sessions

## Objective

Build a ComfyUI extension (`comfyui-workflow-runner`) that auto-exports expanded API-format workflows on save and provides server routes to run them with injected inputs.

**Two parts:**
1. Frontend JS extension — hooks save, calls graphToPrompt(), persists .api.json
2. Python server routes — loads .api.json, injects inputs by node title, prunes deps, submits to /prompt

## Environment

- ComfyUI custom node extension structure
- Reference data: ../avatara/response.json (312-node captured /prompt POST)
- Existing code: ../modal/comfyui_app.py (inject/prune functions), ../modal/workflow_sync.py
- 5 input nodes (client-name, client-market, client-region, avatar-select, avatar-edits-request)
- 11 output nodes (3 text, 5 image, 3 video)

## Outcome

[To be filled when session is complete - summarize what was accomplished]
