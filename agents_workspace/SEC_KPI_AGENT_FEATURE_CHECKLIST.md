# SEC KPI Agent Feature Checklist

General feature checklist for `sec_kpi_orchestrator` (ADK + non-ADK features).
Updated on 2026-03-01.
Current ADK runtime in this repo: `google-adk==1.24.1`.

## Agent Architecture and Orchestration
- [x] `LoopAgent` (used by `sec_kpi_orchestrator`)
- [x] `SequentialAgent` (used by `sec_kpi_orchestrator`)
- [x] `ParallelAgent` (used by `sec_kpi_orchestrator`)
- [x] `LlmAgent` / `Agent` (used by `sec_kpi_orchestrator`)
- [ ] `Custom Agent` (extend `BaseAgent`)
- [x] Multi-agent composition patterns

## Runtime, Sessions, and Context
- [x] Runner/runtime event loop setup (`adk web`)
- [ ] Session service hardening (explicit DB/file config per environment)
- [x] State management (`session.state` via `output_key` and callbacks)
- [ ] Memory integration
- [ ] Resume stopped workflows (`ResumabilityConfig`, runtime resume APIs)
- [ ] Session rewind (`Runner.rewind_async`)
- [ ] Context caching (`ContextCacheConfig`)
- [ ] Context compaction (`EventsCompactionConfig`)

## Tools and Integrations
- [x] Function tools
- [ ] Tool confirmation / HITL for high-impact actions
- [ ] MCP tools (use MCP servers in ADK)
- [ ] OpenAPI tool generation (`OpenAPIToolset`)
- [ ] Skills (`SkillToolset`, `load_skill_from_dir`)
- [ ] Pre-built tools (Gemini / Google Cloud / third-party)
- [ ] Plugins for cross-cutting guardrails/telemetry
- [x] Artifact publishing (`save_artifact`)
- [ ] File-based artifact service configuration (for durable local artifacts)

## Observability and Tracing
- [x] End-to-end distributed tracing (OTel spans for tool calls and workflow save stages)
- [x] Tool-call tracing spans with status, latency, and error attributes
- [ ] Trace correlation IDs across session/request/model/tool events
- [x] OTel metrics baseline:
  - [x] Request count and error count (tool-call level)
  - [x] Stage/tool latency histograms (tool-call level)
  - [ ] Loop iteration and retry counters
  - [x] Artifact save success/failure counters
- [x] OTel exporter target selected (OTLP endpoint env-supported; console fallback)
- [ ] Basic alerting/SLOs from OTel metrics

## Quality and Operations
- [ ] Evaluation workflow (`adk web`, `pytest`, `adk eval`)
- [x] Observability/tracing setup (OpenTelemetry baseline instrumentation added)
- [ ] Deployment target selected (Vertex Agent Engine / Cloud Run / GKE / container infra)
- [x] ADK web workflow for local testing
- [ ] API server workflow (`adk api_server`) with `/health` and `/version` checks
- [ ] Progressive SSE streaming usage
- [ ] User persona-based evals

## Recently Added ADK Features To Track
- [ ] Token-threshold + intra-invocation compaction tuning (v1.25.0, v1.26.0)
- [ ] Skills system adoption (v1.25.0, v1.26.0)
- [ ] Interactions API model mode where relevant (v1.21.0)
- [ ] Memory consolidation and explicit memory-write flows (v1.26.0, v1.21.0)
- [ ] A2A interceptor hooks for remote-agent governance (v1.26.0)
- [ ] API server `--auto_create_session` adoption (v1.25.0)

## References
- Main docs: https://google.github.io/adk-docs/
- Agents overview: https://google.github.io/adk-docs/agents/
- Workflow agents: https://google.github.io/adk-docs/agents/workflow-agents/
- Loop agents: https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/
- Runtime: https://google.github.io/adk-docs/runtime/
- Sessions/State/Memory: https://google.github.io/adk-docs/sessions/
- Tools: https://google.github.io/adk-docs/tools/
- MCP: https://google.github.io/adk-docs/mcp/
- Evaluation: https://google.github.io/adk-docs/evaluate/
- Deployment: https://google.github.io/adk-docs/deploy/
- Callbacks: https://google.github.io/adk-docs/callbacks/
- Plugins: https://google.github.io/adk-docs/plugins/
- Artifacts: https://google.github.io/adk-docs/artifacts/
- Resume: https://google.github.io/adk-docs/runtime/resume/
- Rewind: https://google.github.io/adk-docs/sessions/rewind/
- Context caching: https://google.github.io/adk-docs/context/caching/
- Context compaction: https://google.github.io/adk-docs/context/compaction/
- Tool confirmation (HITL): https://google.github.io/adk-docs/tools-custom/confirmation/
- OpenAPI tools: https://google.github.io/adk-docs/tools-custom/openapi-tools/
- API server: https://google.github.io/adk-docs/runtime/api-server/
- ADK Python release notes: https://github.com/google/adk-python/releases
