# Project Commands
Auto-discovered CLI commands from prior sessions.


## Other
- `jq -r '.[].text' /Users/hex/.claude/projects/-Users-hex--claude-sessions-comfyui-workflow-runner/5d9fd23c-ad89-4985-9050-0e471c0a7dc7/tool-results/mcp-mcp-omnisearch-web_extract-1775073212639.txt | grep -n "SaveWorkflow|saveWorkflow|graphToPrompt|fetchApi|beforeSave|workflow-saved|dispatchEvent|addEventListener|afterSave" | head -60` -- [1x, last: 2026-04-01]
- `grep -n "fetchApi|fetchApiJson|fileURL|getExtensions|init(" /var/folders/26/0gfp98ds1bs06klp4tphlmj00000gn/T/mcp-web_extract-fd646e95-03a2-48b6-967b-0af9aed95c54.txt | head -60` -- [1x, last: 2026-04-01]
- `grep -n "graphToPrompt|registerExtension|saveWorkflow|fetchApi|beforeSave|afterSave|beforeQueuePrompt|extensionManager|ComfyExtension|setup(|init(|nodeCreated|loadedGraphNode" /var/folders/26/0gfp98ds1bs06klp4tphlmj00000gn/T/mcp-web_extract-251cdad7-84a9-457a-bec9-338eff26753d.txt | head -100` -- [1x, last: 2026-04-01]

## Test
- `.venv/bin/python -m pytest tests/test_workflow_runner.py -v 2>&1` -- [3x, last: 2026-04-01]

## Dev
- `jq -r '.[].text' /Users/hex/.claude/projects/-Users-hex--claude-sessions-comfyui-workflow-runner/5d9fd23c-ad89-4985-9050-0e471c0a7dc7/tool-results/mcp-mcp-omnisearch-web_extract-1775073212639.txt 2>/dev/null | grep -o ".{0,120}[Ss]ave[Ww]orkflow.{0,120}" | head -30` -- [1x, last: 2026-04-01]
