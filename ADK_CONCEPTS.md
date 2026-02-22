# ADK Concepts

A quick concept map of Google Agent Development Kit (ADK), with official docs links.

## Core Architecture

- ADK overview and framework positioning (model-agnostic, modular)  
  https://google.github.io/adk-docs/

- Runtime engine and event loop model (`Runner`, events, execution flow)  
  https://google.github.io/adk-docs/runtime/

- Runtime behavior controls (`RunConfig`: streaming, limits, function-calling behavior)  
  https://google.github.io/adk-docs/runtime/runconfig/

- App container (optional): workflow-level config for compaction/caching/plugins/resume  
  https://google.github.io/adk-docs/apps/

## Agent Orchestration Patterns

- Workflow agents: sequential, parallel, loop control-flow patterns  
  https://google.github.io/adk-docs/agents/workflow-agents/

- Callbacks: intercept/modify control flow before/after stages  
  https://google.github.io/adk-docs/callbacks/

## Conversation Context and State

- Sessions overview: session/state/memory foundations  
  https://google.github.io/adk-docs/sessions/

- Session object details  
  https://google.github.io/adk-docs/sessions/session/

- Memory usage (`PreloadMemory`, `LoadMemory`, persistence via memory service)  
  https://google.github.io/adk-docs/sessions/memory/

- Session rewind: roll back state/artifacts to earlier invocation points  
  https://google.github.io/adk-docs/sessions/rewind/

## Context Engineering Features

- Context model and context objects (`InvocationContext`, `ToolContext`, `CallbackContext`)  
  https://google.github.io/adk-docs/context/

- Context compaction/compression for long-running sessions  
  https://google.github.io/adk-docs/context/compaction/

## Tools and Integrations

- Built-in Gemini code execution tool (model-executed code with constraints)  
  https://google.github.io/adk-docs/tools/gemini-api/code-execution/

- MCP (Model Context Protocol): consume/expose MCP tools and resources  
  https://google.github.io/adk-docs/mcp/

## Files, Media, and Artifacts

- Artifacts: versioned binary/session assets (images/files/audio)  
  https://google.github.io/adk-docs/artifacts/

## Streaming and Live Interaction

- Streaming quickstart (`run_live` patterns)  
  https://google.github.io/adk-docs/get-started/streaming/

- Bidi/live streaming (experimental; text/audio/video interaction)  
  https://google.github.io/adk-docs/streaming/

- Streaming tools (experimental): tools yielding intermediate updates  
  https://google.github.io/adk-docs/streaming/streaming-tools/

## Deployment and Runtime Hosting

- Deployment options overview  
  https://google.github.io/adk-docs/deploy/

- GKE deployment (`adk deploy gke` and manual options)  
  https://google.github.io/adk-docs/deploy/gke/

- Cloud Run deployment (`adk deploy cloud_run` + gcloud path)  
  https://google.github.io/adk-docs/deploy/cloud-run/

## Agent-to-Agent and Visual Authoring

- A2A protocol (experimental): expose/call agents remotely  
  https://google.github.io/adk-docs/a2a/quickstart-exposing/

- Visual Builder (experimental): visual workflow editing and code generation  
  https://google.github.io/adk-docs/visual-builder/

## Observability and Evaluation

- Freeplay integration for experiments, monitoring, and eval workflows  
  https://google.github.io/adk-docs/observability/freeplay/

- BigQuery Agent Analytics plugin (preview) for event logging and analysis  
  https://google.github.io/adk-docs/observability/bigquery-agent-analytics/
