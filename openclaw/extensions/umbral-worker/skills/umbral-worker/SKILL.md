---
name: umbral-worker
description: >-
  Use the Umbral Worker bridge tools to discover tasks, inspect provider
  status, execute repo-native domain tasks through typed Umbral tools, enqueue
  async work, and poll queued task state.
metadata:
  openclaw:
    requires:
      env:
        - WORKER_TOKEN
---

# Umbral Worker Skill

Use this skill when the agent needs to reach the Worker API directly instead of
just reasoning about it. Prefer the typed `umbral_*` tools first; they mirror
the services the repo already exposes through the Worker.

## Tool selection

- `umbral_notion_*`: Use for Control Room comments, report pages, dashboard
  updates, Bitacora enrichment, and transcript ingestion in Notion.
- `umbral_research_web` and `umbral_composite_research_report`: Use for Tavily
  search and research-report generation.
- `umbral_linear_*`: Use for issue creation, team lookup, and status updates in
  Linear.
- `umbral_google_calendar_*` and `umbral_gmail_*`: Use for Google Calendar and
  Gmail operations.
- `umbral_figma_*`: Use for Figma file inspection, exports, and comments.
- `umbral_document_*`: Use for Word, PDF, and PowerPoint generation.
- `umbral_granola_*`: Use for transcript processing and proactive follow-up.
- `umbral_windows_*`: Use for VM filesystem or automation tasks.
- `umbral_llm_generate`: Use when you need the Worker's routed Gemini, Vertex,
  Azure GPT/Kimi, OpenAI, or Claude execution instead of a gateway model
  response.
- `umbral_azure_audio_generate`: Use for Azure `gpt-realtime` text-to-speech
  generation.
- `umbral_google_audio_generate`: Use for Gemini preview text-to-speech
  generation.
- `umbral_provider_status`: Use for quota, provider-health, model-routing, or
  LLM availability checks.
- `umbral_worker_tools_inventory`: Use when you need to discover the exact
  Worker task inventory or confirm whether a handler exists.
- `umbral_worker_run`: Use for short synchronous tasks that should complete in
  the current turn when a typed tool does not exist yet.
- `umbral_worker_enqueue`: Use for asynchronous, longer-running, or externally
  triggered work.
- `umbral_worker_task_status`: Use after enqueueing, or when the user gives you
  a `task_id` and wants the current status.

## Rules

- Prefer typed `umbral_*` tools over `umbral_worker_run`.
- Prefer `umbral_worker_tools_inventory` before calling an unfamiliar task.
- Prefer `umbral_worker_run` only as a fallback for tasks without typed tools.
- Prefer `umbral_worker_enqueue` if the result may take time or should survive
  beyond the current turn.
- Keep using the domain skills (`notion`, `linear`, `document-generation`,
  `research`, `provider-status`, `google-calendar`, `gmail`, `figma`,
  `observability`, `windows`) for workflow knowledge; use this bridge when you
  need actual execution against the Worker API.
