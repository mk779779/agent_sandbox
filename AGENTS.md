# Repo Agent Instructions

## Workspace
- Use `/Users/masaCoding/codingmain/agent_sandbox/agents_workspace` as the primary workspace for notes, designs, and documentation.
- Store design documents under:
  - `/Users/masaCoding/codingmain/agent_sandbox/agents_workspace/designs`
- Store general documentation under:
  - `/Users/masaCoding/codingmain/agent_sandbox/agents_workspace/docs`
- Do not place new design/docs artifacts under `outputs/` unless the user explicitly asks.
- Save runtime/generated artifacts under:
  - `/Users/masaCoding/codingmain/agent_sandbox/outputs/`
- For Farsight agent outputs, use:
  - `/Users/masaCoding/codingmain/agent_sandbox/outputs/farsight/<ticker>/`

## Reporting
- If the user asks for a report, add a markdown report file under:
  - `/Users/masaCoding/codingmain/agent_sandbox/agents_workspace/codex_sessions`
- Report files should summarize technical changes, commands run, outcomes, and any follow-up actions.
- Reports must be incremental (delta-only): include only new information since the most recent prior report in `codex_sessions`.
- Do not repeat unchanged background/context from older reports.
- At the top of each new report, include a `Previous report:` line that references the prior report filename (if one exists).
- Use filename format: `N_MM-DD-YY.md` (example: `1_02-27-26.md`).
- `N` is the report sequence for that calendar day (local date), starting at `1` for the first report of the day, then `2`, `3`, etc.
