import { randomUUID } from "node:crypto";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

type JsonObject = Record<string, unknown>;
type JsonSchema = Record<string, unknown>;

type PluginConfig = {
  baseUrl?: string;
  defaultTeam?: string;
  defaultTaskType?: string;
  timeoutMs?: number;
};

type RequestOptions = {
  auth?: boolean;
  body?: JsonObject;
  query?: Record<string, string | number | boolean | undefined>;
};

type TaskToolDefinition = {
  name: string;
  task: string;
  description: string;
  resultTitle: string;
  parameters: JsonSchema;
};

const MAX_RESULT_CHARS = 24000;

function getPluginConfig(api: OpenClawPluginApi): PluginConfig {
  return (api.pluginConfig ?? {}) as PluginConfig;
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function resolveBaseUrl(api: OpenClawPluginApi): string {
  const cfg = getPluginConfig(api);
  const raw =
    (typeof cfg.baseUrl === "string" && cfg.baseUrl.trim()) ||
    process.env.WORKER_URL ||
    "http://127.0.0.1:8088";
  return trimTrailingSlash(raw);
}

function resolveTimeoutMs(api: OpenClawPluginApi): number {
  const cfg = getPluginConfig(api);
  if (typeof cfg.timeoutMs === "number" && cfg.timeoutMs >= 1000) {
    return cfg.timeoutMs;
  }
  return 30000;
}

function resolveToken(): string {
  const token = process.env.WORKER_TOKEN?.trim() ?? "";
  if (!token) {
    throw new Error("WORKER_TOKEN is not set in the gateway environment.");
  }
  return token;
}

function requireObject(value: unknown, fieldName: string): JsonObject {
  if (value == null) {
    return {};
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${fieldName} must be a JSON object.`);
  }
  return value as JsonObject;
}

function truncateText(text: string): string {
  if (text.length <= MAX_RESULT_CHARS) {
    return text;
  }
  return `${text.slice(0, MAX_RESULT_CHARS)}\n\n[truncated ${text.length - MAX_RESULT_CHARS} chars]`;
}

function formatJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function renderResult(title: string, value: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: `${title}\n\n${truncateText(formatJson(value))}`,
      },
    ],
  };
}

function sanitizeBinaryPayload(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeBinaryPayload(item));
  }
  if (!isJsonObject(value)) {
    return value;
  }

  const result: JsonObject = {};
  for (const [key, raw] of Object.entries(value)) {
    if (key === "audio_b64" && typeof raw === "string") {
      result[key] =
        "[omitted from gateway response; use output_path or direct Worker call for binary audio]";
      result.audio_b64_chars = raw.length;
      continue;
    }
    result[key] = sanitizeBinaryPayload(raw);
  }
  return result;
}

function sanitizeWorkerResult(task: string, value: unknown): unknown {
  if (!task.endsWith(".audio.generate")) {
    return value;
  }
  return sanitizeBinaryPayload(value);
}

async function workerRequest(
  api: OpenClawPluginApi,
  method: "GET" | "POST",
  path: string,
  options: RequestOptions = {},
): Promise<unknown> {
  const baseUrl = resolveBaseUrl(api);
  const timeoutMs = resolveTimeoutMs(api);
  const url = new URL(`${baseUrl}${path}`);

  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value != null) {
      url.searchParams.set(key, String(value));
    }
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (options.auth !== false) {
    headers.Authorization = `Bearer ${resolveToken()}`;
  }
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });

  const raw = await response.text();
  const payload = raw ? safeJsonParse(raw) : null;
  if (!response.ok) {
    const detail =
      (isJsonObject(payload) && stringifyDetail(payload.detail)) ||
      raw ||
      `${response.status} ${response.statusText}`;
    throw new Error(`Worker ${method} ${path} failed (${response.status}): ${detail}`);
  }
  return payload;
}

function safeJsonParse(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function isJsonObject(value: unknown): value is JsonObject {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function stringifyDetail(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  return formatJson(value);
}

function buildRunEnvelope(api: OpenClawPluginApi, params: JsonObject): JsonObject {
  const cfg = getPluginConfig(api);
  const task = typeof params.task === "string" ? params.task.trim() : "";
  if (!task) {
    throw new Error("task is required.");
  }

  return {
    schema_version: "0.1",
    task_id: randomUUID(),
    trace_id: randomUUID(),
    team:
      (typeof params.team === "string" && params.team.trim()) ||
      cfg.defaultTeam ||
      "system",
    task_type:
      (typeof params.taskType === "string" && params.taskType.trim()) ||
      cfg.defaultTaskType ||
      "general",
    task,
    input: requireObject(params.input, "input"),
  };
}

function objectSchema(description: string): JsonSchema {
  return {
    type: "object",
    additionalProperties: true,
    properties: {},
    description,
  };
}

function stringSchema(description: string, extra: JsonSchema = {}): JsonSchema {
  return { type: "string", description, ...extra };
}

function integerSchema(description: string, extra: JsonSchema = {}): JsonSchema {
  return { type: "integer", description, ...extra };
}

function numberSchema(description: string, extra: JsonSchema = {}): JsonSchema {
  return { type: "number", description, ...extra };
}

function booleanSchema(description: string, extra: JsonSchema = {}): JsonSchema {
  return { type: "boolean", description, ...extra };
}

function arraySchema(items: JsonSchema, description: string, extra: JsonSchema = {}): JsonSchema {
  return {
    type: "array",
    items,
    description,
    ...extra,
  };
}

function enumStringSchema(values: string[], description: string): JsonSchema {
  return {
    type: "string",
    enum: values,
    description,
  };
}

function stringOrStringArraySchema(description: string): JsonSchema {
  return {
    description,
    anyOf: [
      { type: "string" },
      { type: "array", items: { type: "string" } },
    ],
  };
}

function taskToolSchema(
  properties: Record<string, JsonSchema>,
  required: string[] = [],
): JsonSchema {
  return {
    type: "object",
    additionalProperties: false,
    required,
    properties: {
      ...properties,
      workerTeam: stringSchema(
        "Optional Worker team override for routing or tracking. This is separate from task fields like notion/linear team.",
      ),
      workerTaskType: stringSchema("Optional Worker task_type override."),
    },
  };
}

function buildTaskInput(params: JsonObject): JsonObject {
  const input = { ...params };
  delete input.workerTeam;
  delete input.workerTaskType;
  return input;
}

async function runNamedTask(
  api: OpenClawPluginApi,
  task: string,
  params: JsonObject,
): Promise<unknown> {
  const payload = buildRunEnvelope(api, {
    task,
    input: buildTaskInput(params),
    team: params.workerTeam,
    taskType: params.workerTaskType,
  });
  return workerRequest(api, "POST", "/run", { body: payload });
}

function registerTaskTool(api: OpenClawPluginApi, definition: TaskToolDefinition) {
  api.registerTool(
    {
      name: definition.name,
      description: definition.description,
      parameters: definition.parameters,
      async execute(_id: string, params: JsonObject) {
        const result = await runNamedTask(api, definition.task, params);
        return renderResult(definition.resultTitle, sanitizeWorkerResult(definition.task, result));
      },
    },
    { optional: true },
  );
}

const TASK_TOOLS: TaskToolDefinition[] = [
  {
    name: "umbral_ping",
    task: "ping",
    description: "Echo a simple JSON payload through the Worker for connectivity checks.",
    resultTitle: "Ping result",
    parameters: taskToolSchema({
      message: stringSchema("Optional test message to echo."),
      payload: objectSchema("Optional JSON object to echo."),
    }),
  },

  // Notion
  {
    name: "umbral_notion_write_transcript",
    task: "notion.write_transcript",
    description: "Create a transcript page in the Notion Granola inbox database.",
    resultTitle: "Notion transcript result",
    parameters: taskToolSchema(
      {
        title: stringSchema("Transcript title."),
        content: stringSchema("Transcript content in plain text or markdown."),
        source: stringSchema("Optional transcript source, for example granola."),
        date: stringSchema("Optional ISO date for the transcript."),
      },
      ["title", "content"],
    ),
  },
  {
    name: "umbral_notion_add_comment",
    task: "notion.add_comment",
    description: "Add a comment to a Notion page, defaulting to the configured Control Room page.",
    resultTitle: "Notion comment result",
    parameters: taskToolSchema(
      {
        text: stringSchema("Comment body to post."),
        page_id: stringSchema("Optional Notion page ID override."),
      },
      ["text"],
    ),
  },
  {
    name: "umbral_notion_poll_comments",
    task: "notion.poll_comments",
    description: "Read recent comments from the configured Notion Control Room or another page.",
    resultTitle: "Notion comments result",
    parameters: taskToolSchema({
      page_id: stringSchema("Optional Notion page ID override."),
      since: stringSchema("Optional ISO datetime. Only comments after this instant are returned."),
      limit: integerSchema("Maximum number of comments to fetch.", { minimum: 1, maximum: 100 }),
    }),
  },
  {
    name: "umbral_notion_upsert_task",
    task: "notion.upsert_task",
    description: "Create or update a task in the Notion task database used by the stack.",
    resultTitle: "Notion task upsert result",
    parameters: taskToolSchema(
      {
        task_id: stringSchema("Stable task identifier."),
        status: enumStringSchema(
          ["queued", "running", "done", "failed", "blocked"],
          "Task status to persist in Notion.",
        ),
        team: stringSchema("Owning team or agent for the task record."),
        task: stringSchema("Human-readable task name."),
        input_summary: stringSchema("Optional summary of the task input."),
        error: stringSchema("Optional error summary if the task failed."),
        result_summary: stringSchema("Optional result summary if the task completed."),
      },
      ["task_id", "status", "team", "task"],
    ),
  },
  {
    name: "umbral_notion_update_dashboard",
    task: "notion.update_dashboard",
    description: "Update the Rick dashboard page in Notion with a metrics map.",
    resultTitle: "Notion dashboard result",
    parameters: taskToolSchema(
      {
        metrics: objectSchema("Metrics map such as {\"Active tasks\": \"12\", \"VM\": \"OK\"}."),
        page_id: stringSchema("Optional Notion dashboard page ID override."),
      },
      ["metrics"],
    ),
  },
  {
    name: "umbral_notion_create_report_page",
    task: "notion.create_report_page",
    description: "Create a structured markdown report page in Notion with optional sources and metadata.",
    resultTitle: "Notion report page result",
    parameters: taskToolSchema(
      {
        parent_page_id: stringSchema("Optional parent page ID. Defaults to the Control Room page."),
        title: stringSchema("Report title."),
        content: stringSchema("Report content in markdown."),
        sources: arraySchema(objectSchema("Source object with url/title fields."), "Optional source entries."),
        metadata: objectSchema("Optional metadata map for the report."),
        queries: arraySchema(stringSchema("Query"), "Optional research queries used to build the report."),
      },
      ["title", "content"],
    ),
  },
  {
    name: "umbral_notion_enrich_bitacora_page",
    task: "notion.enrich_bitacora_page",
    description: "Append structured sections or raw blocks to an existing Bitacora page in Notion.",
    resultTitle: "Notion Bitacora enrichment result",
    parameters: taskToolSchema(
      {
        page_id: stringSchema("Target Notion page ID."),
        sections: arraySchema(objectSchema("High-level section object."), "Optional section list."),
        blocks: arraySchema(objectSchema("Simplified raw block object."), "Optional block list."),
      },
      ["page_id"],
    ),
  },

  // Research and LLM
  {
    name: "umbral_research_web",
    task: "research.web",
    description: "Run a Tavily-backed web search through the Worker.",
    resultTitle: "Research web result",
    parameters: taskToolSchema(
      {
        query: stringSchema("Search query or question."),
        count: integerSchema("Maximum number of results.", { minimum: 1, maximum: 20 }),
        search_depth: enumStringSchema(["basic", "advanced"], "Tavily search depth."),
      },
      ["query"],
    ),
  },
  {
    name: "umbral_composite_research_report",
    task: "composite.research_report",
    description: "Generate a full research report by combining Tavily searches and the Worker LLM router.",
    resultTitle: "Composite research report result",
    parameters: taskToolSchema(
      {
        topic: stringSchema("Main topic to research."),
        queries: arraySchema(stringSchema("Query"), "Optional explicit search queries."),
        depth: enumStringSchema(["quick", "standard", "deep"], "Research depth preset."),
        language: stringSchema("Output language, for example es or en."),
      },
      ["topic"],
    ),
  },
  {
    name: "umbral_llm_generate",
    task: "llm.generate",
    description: "Generate text via the Worker multi-provider router, including Gemini, Vertex, Azure and Claude proxy routes.",
    resultTitle: "LLM generation result",
    parameters: taskToolSchema(
      {
        prompt: stringSchema("Prompt to send to the model."),
        model: stringSchema("Optional model or router alias, for example gemini_flash or gemini_vertex."),
        selected_model: stringSchema("Backward-compatible Dispatcher alias for the model."),
        max_tokens: integerSchema("Maximum tokens for the response.", { minimum: 1, maximum: 8192 }),
        temperature: numberSchema("Sampling temperature.", { minimum: 0, maximum: 2 }),
        system: stringSchema("Optional system prompt."),
      },
      ["prompt"],
    ),
  },

  // Linear
  {
    name: "umbral_linear_create_issue",
    task: "linear.create_issue",
    description: "Create a Linear issue with optional team routing and labels.",
    resultTitle: "Linear issue result",
    parameters: taskToolSchema(
      {
        title: stringSchema("Issue title."),
        description: stringSchema("Optional issue description."),
        team_key: stringSchema("Optional Umbral team key such as marketing."),
        team_id: stringSchema("Optional Linear team UUID."),
        team_name: stringSchema("Optional Linear team name, defaulting to Umbral."),
        priority: integerSchema("Linear priority: 0 none, 1 urgent, 2 high, 3 medium, 4 low.", {
          minimum: 0,
          maximum: 4,
        }),
        add_team_labels: booleanSchema("Whether to auto-apply routed team labels."),
      },
      ["title"],
    ),
  },
  {
    name: "umbral_linear_list_teams",
    task: "linear.list_teams",
    description: "List available Linear teams for the configured workspace.",
    resultTitle: "Linear teams result",
    parameters: taskToolSchema({}),
  },
  {
    name: "umbral_linear_update_issue_status",
    task: "linear.update_issue_status",
    description: "Update the workflow state of a Linear issue and optionally add a comment.",
    resultTitle: "Linear issue status result",
    parameters: taskToolSchema(
      {
        issue_id: stringSchema("Linear issue UUID."),
        state_name: stringSchema("Optional workflow state name such as Done or Cancelled."),
        comment: stringSchema("Optional comment to add to the issue."),
        team_id: stringSchema("Linear team UUID required when resolving a state name."),
      },
      ["issue_id"],
    ),
  },

  // Google and Gmail
  {
    name: "umbral_google_calendar_create_event",
    task: "google.calendar.create_event",
    description: "Create a Google Calendar event using the configured calendar token or service account.",
    resultTitle: "Google Calendar create event result",
    parameters: taskToolSchema(
      {
        title: stringSchema("Event title."),
        description: stringSchema("Optional event description."),
        start: stringSchema("Event start datetime in ISO 8601 format."),
        end: stringSchema("Optional event end datetime in ISO 8601 format."),
        timezone: stringSchema("IANA timezone, default America/Santiago."),
        attendees: arraySchema(stringSchema("Email"), "Optional attendee email addresses."),
        calendar_id: stringSchema("Optional Google Calendar ID, default primary."),
      },
      ["title", "start"],
    ),
  },
  {
    name: "umbral_google_calendar_list_events",
    task: "google.calendar.list_events",
    description: "List upcoming Google Calendar events.",
    resultTitle: "Google Calendar events result",
    parameters: taskToolSchema({
      calendar_id: stringSchema("Optional Google Calendar ID, default primary."),
      time_min: stringSchema("Optional RFC 3339 lower bound."),
      time_max: stringSchema("Optional RFC 3339 upper bound."),
      max_results: integerSchema("Maximum number of events to return.", {
        minimum: 1,
        maximum: 100,
      }),
    }),
  },
  {
    name: "umbral_gmail_create_draft",
    task: "gmail.create_draft",
    description: "Create a Gmail draft using OAuth or service-account credentials.",
    resultTitle: "Gmail draft result",
    parameters: taskToolSchema(
      {
        to: stringSchema("Primary recipient email address."),
        subject: stringSchema("Subject line."),
        body: stringSchema("Email body."),
        body_type: enumStringSchema(["plain", "html"], "Body format."),
        cc: arraySchema(stringSchema("Email"), "Optional CC recipients."),
        reply_to: stringSchema("Optional Reply-To address."),
      },
      ["to", "subject", "body"],
    ),
  },
  {
    name: "umbral_gmail_list_drafts",
    task: "gmail.list_drafts",
    description: "List Gmail drafts for the authenticated account.",
    resultTitle: "Gmail drafts result",
    parameters: taskToolSchema({
      max_results: integerSchema("Maximum drafts to return.", { minimum: 1, maximum: 100 }),
      q: stringSchema("Optional Gmail search query."),
    }),
  },

  // Figma
  {
    name: "umbral_figma_get_file",
    task: "figma.get_file",
    description: "Fetch Figma file metadata and page structure.",
    resultTitle: "Figma file result",
    parameters: taskToolSchema(
      {
        file_key: stringSchema("Figma file key from the design URL."),
        depth: integerSchema("Traversal depth for the returned structure.", { minimum: 1, maximum: 4 }),
      },
      ["file_key"],
    ),
  },
  {
    name: "umbral_figma_get_node",
    task: "figma.get_node",
    description: "Fetch one or more nodes from a Figma file.",
    resultTitle: "Figma node result",
    parameters: taskToolSchema(
      {
        file_key: stringSchema("Figma file key."),
        node_ids: stringOrStringArraySchema("Single node ID or list of node IDs."),
        depth: integerSchema("Traversal depth for node lookup.", { minimum: 1, maximum: 4 }),
      },
      ["file_key", "node_ids"],
    ),
  },
  {
    name: "umbral_figma_export_image",
    task: "figma.export_image",
    description: "Export one or more Figma nodes as PNG, SVG, JPG or PDF.",
    resultTitle: "Figma export result",
    parameters: taskToolSchema(
      {
        file_key: stringSchema("Figma file key."),
        node_ids: stringOrStringArraySchema("Single node ID or list of node IDs."),
        format: enumStringSchema(["png", "svg", "jpg", "pdf"], "Export format."),
        scale: numberSchema("Optional export scale between 0.01 and 4.", { minimum: 0.01, maximum: 4 }),
      },
      ["file_key", "node_ids"],
    ),
  },
  {
    name: "umbral_figma_add_comment",
    task: "figma.add_comment",
    description: "Add a comment to a Figma file, optionally anchored to a node.",
    resultTitle: "Figma comment result",
    parameters: taskToolSchema(
      {
        file_key: stringSchema("Figma file key."),
        message: stringSchema("Comment message."),
        node_id: stringSchema("Optional node ID to anchor the comment."),
        client_meta: objectSchema("Optional client_meta payload for comment placement."),
      },
      ["file_key", "message"],
    ),
  },
  {
    name: "umbral_figma_list_comments",
    task: "figma.list_comments",
    description: "List comments for a Figma file.",
    resultTitle: "Figma comments result",
    parameters: taskToolSchema(
      {
        file_key: stringSchema("Figma file key."),
      },
      ["file_key"],
    ),
  },

  // Document generation
  {
    name: "umbral_document_create_word",
    task: "document.create_word",
    description: "Generate a Word document from a template or from scratch.",
    resultTitle: "Word document result",
    parameters: taskToolSchema({
      template_path: stringSchema("Optional .docx template path."),
      data: objectSchema("Template variables for docxtpl mode."),
      output_path: stringSchema("Optional output path. Omit to receive base64."),
      title: stringSchema("Document title for scratch mode."),
      content: stringSchema("Document body for scratch mode."),
    }),
  },
  {
    name: "umbral_document_create_pdf",
    task: "document.create_pdf",
    description: "Generate a PDF from HTML or plain text.",
    resultTitle: "PDF document result",
    parameters: taskToolSchema({
      html_content: stringSchema("HTML content for WeasyPrint mode."),
      text_content: stringSchema("Plain text content for FPDF mode."),
      title: stringSchema("Optional PDF title for text mode."),
      output_path: stringSchema("Optional output path. Omit to receive base64."),
    }),
  },
  {
    name: "umbral_document_create_presentation",
    task: "document.create_presentation",
    description: "Generate a PowerPoint presentation from a slide list.",
    resultTitle: "Presentation result",
    parameters: taskToolSchema(
      {
        slides: arraySchema(objectSchema("Slide object with title, content and optional notes."), "Slides to render."),
        output_path: stringSchema("Optional output path. Omit to receive base64."),
      },
      ["slides"],
    ),
  },

  // Granola
  {
    name: "umbral_granola_process_transcript",
    task: "granola.process_transcript",
    description: "Process a Granola transcript into Notion and optional follow-up task creation.",
    resultTitle: "Granola transcript result",
    parameters: taskToolSchema(
      {
        title: stringSchema("Meeting title."),
        content: stringSchema("Transcript content in markdown."),
        date: stringSchema("Optional ISO meeting date."),
        attendees: arraySchema(stringSchema("Attendee"), "Optional attendee list."),
        action_items: arraySchema(objectSchema("Action item object."), "Optional explicit action items."),
        source: stringSchema("Optional source label."),
        notify_enlace: booleanSchema("Whether to notify Enlace after processing."),
      },
      ["title", "content"],
    ),
  },
  {
    name: "umbral_granola_create_followup",
    task: "granola.create_followup",
    description: "Create a reminder, email draft, proposal or calendar event from a Granola transcript.",
    resultTitle: "Granola follow-up result",
    parameters: taskToolSchema(
      {
        transcript_page_id: stringSchema("Transcript page ID in Notion."),
        followup_type: enumStringSchema(
          ["reminder", "email_draft", "proposal", "calendar_event"],
          "Type of follow-up to create.",
        ),
        title: stringSchema("Optional meeting title."),
        date: stringSchema("Optional meeting date."),
        attendees: arraySchema(stringSchema("Attendee"), "Optional attendee list."),
        action_items: arraySchema(objectSchema("Action item object."), "Optional action items."),
        due_date: stringSchema("Optional due date for reminder follow-ups."),
        notes: stringSchema("Optional extra notes for the follow-up."),
        start: stringSchema("Optional start datetime for calendar event follow-ups."),
        end: stringSchema("Optional end datetime for calendar event follow-ups."),
        timezone: stringSchema("Optional timezone for calendar event follow-ups."),
      },
      ["transcript_page_id", "followup_type"],
    ),
  },

  // Azure / Make / Observability
  {
    name: "umbral_azure_audio_generate",
    task: "azure.audio.generate",
    description: "Generate TTS audio through the Azure realtime deployment configured in the Worker.",
    resultTitle: "Azure audio result",
    parameters: taskToolSchema(
      {
        text: stringSchema("Text to convert to audio."),
        voice: enumStringSchema(
          ["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"],
          "Voice preset for the realtime deployment.",
        ),
        instructions: stringSchema("Optional instructions for the realtime model."),
        deployment: stringSchema("Optional Azure deployment name."),
        output_path: stringSchema("Optional path where the WAV should be saved."),
      },
      ["text"],
    ),
  },
  {
    name: "umbral_google_audio_generate",
    task: "google.audio.generate",
    description: "Generate TTS audio through the Gemini preview TTS model configured in the Worker.",
    resultTitle: "Google audio result",
    parameters: taskToolSchema(
      {
        text: stringSchema("Text to convert to audio."),
        voice: stringSchema("Optional Google prebuilt voice name, for example Kore or Puck."),
        model: stringSchema("Optional Gemini TTS model, default gemini-2.5-flash-preview-tts."),
        instructions: stringSchema("Optional style or delivery instructions for the voice."),
        output_path: stringSchema("Optional path where the WAV should be saved."),
      },
      ["text"],
    ),
  },
  {
    name: "umbral_make_post_webhook",
    task: "make.post_webhook",
    description: "POST a JSON payload to an allowlisted Make.com webhook URL.",
    resultTitle: "Make webhook result",
    parameters: taskToolSchema(
      {
        webhook_url: stringSchema("Make.com webhook URL."),
        payload: objectSchema("JSON payload to send."),
        timeout: integerSchema("Timeout in seconds.", { minimum: 1, maximum: 120 }),
      },
      ["webhook_url", "payload"],
    ),
  },
  {
    name: "umbral_system_ooda_report",
    task: "system.ooda_report",
    description: "Generate a Redis-backed OODA report from the Worker observability scripts.",
    resultTitle: "OODA report result",
    parameters: taskToolSchema({
      week_ago: integerSchema("Week offset. Zero means the current week.", { minimum: 0, maximum: 52 }),
      format: enumStringSchema(["markdown", "json"], "Output format."),
    }),
  },
  {
    name: "umbral_system_self_eval",
    task: "system.self_eval",
    description: "Run the Worker self-evaluation report over recent completed tasks.",
    resultTitle: "Self-evaluation result",
    parameters: taskToolSchema({
      limit: integerSchema("Maximum number of tasks to evaluate.", { minimum: 1, maximum: 100 }),
      format: enumStringSchema(["markdown", "json"], "Output format."),
    }),
  },

  // Windows / VM
  {
    name: "umbral_windows_pad_run_flow",
    task: "windows.pad.run_flow",
    description: "Run an allowlisted Power Automate Desktop flow on the Windows execution node.",
    resultTitle: "Windows PAD flow result",
    parameters: taskToolSchema(
      {
        flow_name: stringSchema("Power Automate Desktop flow name."),
        params: objectSchema("Optional flow parameters payload."),
      },
      ["flow_name"],
    ),
  },
  {
    name: "umbral_windows_open_notepad",
    task: "windows.open_notepad",
    description: "Open Notepad on the interactive Windows session to verify connectivity and GUI control.",
    resultTitle: "Windows Notepad result",
    parameters: taskToolSchema({
      text: stringSchema("Optional text to open in Notepad."),
      run_now: booleanSchema("Run the scheduled task immediately when not in an interactive session."),
      run_as_user: stringSchema("Optional Windows username for the scheduled task."),
    }),
  },
  {
    name: "umbral_windows_write_worker_token",
    task: "windows.write_worker_token",
    description: "Write the Worker token to C:\\openclaw-worker\\worker_token on the Windows node.",
    resultTitle: "Windows worker token result",
    parameters: taskToolSchema({}),
  },
  {
    name: "umbral_windows_firewall_allow_port",
    task: "windows.firewall_allow_port",
    description: "Create or refresh a Windows firewall rule allowing inbound TCP access on a port.",
    resultTitle: "Windows firewall result",
    parameters: taskToolSchema({
      port: integerSchema("TCP port to allow.", { minimum: 1, maximum: 65535 }),
      name: stringSchema("Optional firewall rule name."),
    }),
  },
  {
    name: "umbral_windows_start_interactive_worker",
    task: "windows.start_interactive_worker",
    description: "Start the interactive Worker process on the Windows node.",
    resultTitle: "Windows interactive Worker result",
    parameters: taskToolSchema({}),
  },
  {
    name: "umbral_windows_add_interactive_worker_to_startup",
    task: "windows.add_interactive_worker_to_startup",
    description: "Install the interactive Worker startup shortcut in the Windows Startup folder.",
    resultTitle: "Windows startup shortcut result",
    parameters: taskToolSchema({
      username: stringSchema("Windows username, default Rick."),
    }),
  },
  {
    name: "umbral_windows_fs_ensure_dirs",
    task: "windows.fs.ensure_dirs",
    description: "Create a directory tree on the Windows node within the allowlisted base paths.",
    resultTitle: "Windows ensure dirs result",
    parameters: taskToolSchema(
      {
        path: stringSchema("Directory path to create."),
      },
      ["path"],
    ),
  },
  {
    name: "umbral_windows_fs_list",
    task: "windows.fs.list",
    description: "List directory contents on the Windows node within the allowlisted base paths.",
    resultTitle: "Windows directory list result",
    parameters: taskToolSchema(
      {
        path: stringSchema("Directory path to inspect."),
        limit: integerSchema("Maximum entries to return.", { minimum: 1, maximum: 1000 }),
      },
      ["path"],
    ),
  },
  {
    name: "umbral_windows_fs_read_text",
    task: "windows.fs.read_text",
    description: "Read a UTF-8 text file on the Windows node.",
    resultTitle: "Windows read text result",
    parameters: taskToolSchema(
      {
        path: stringSchema("File path to read."),
        max_chars: integerSchema("Maximum number of characters to return.", {
          minimum: 1,
          maximum: 1_000_000,
        }),
      },
      ["path"],
    ),
  },
  {
    name: "umbral_windows_fs_write_text",
    task: "windows.fs.write_text",
    description: "Write a UTF-8 text file on the Windows node within the allowlisted base paths.",
    resultTitle: "Windows write text result",
    parameters: taskToolSchema(
      {
        path: stringSchema("File path to write."),
        text: stringSchema("Text content to write."),
        max_chars: integerSchema("Optional maximum size validation.", {
          minimum: 1,
          maximum: 1_000_000,
        }),
      },
      ["path", "text"],
    ),
  },
  {
    name: "umbral_windows_fs_write_bytes_b64",
    task: "windows.fs.write_bytes_b64",
    description: "Write binary data to the Windows node from a base64 payload.",
    resultTitle: "Windows write bytes result",
    parameters: taskToolSchema(
      {
        path: stringSchema("File path to write."),
        b64: stringSchema("Base64 payload to decode and write."),
      },
      ["path", "b64"],
    ),
  },
];

const plugin = {
  id: "umbral-worker",
  name: "Umbral Worker",
  description: "Bridge OpenClaw tools to the Umbral Worker HTTP API.",
  register(api: OpenClawPluginApi) {
    api.registerTool(
      {
        name: "umbral_worker_run",
        description:
          "Run a Worker task immediately through POST /run. Use for short synchronous tasks or as a fallback when a typed Umbral tool does not exist yet.",
        parameters: {
          type: "object",
          additionalProperties: false,
          required: ["task"],
          properties: {
            task: stringSchema("Worker task name, for example notion.add_comment."),
            input: objectSchema("Task input payload."),
            team: stringSchema("Optional Worker team override."),
            taskType: stringSchema("Optional Worker task_type override."),
          },
        },
        async execute(_id: string, params: JsonObject) {
          const payload = buildRunEnvelope(api, params);
          const result = await workerRequest(api, "POST", "/run", { body: payload });
          const task = typeof params.task === "string" ? params.task.trim() : "";
          return renderResult("Worker run result", sanitizeWorkerResult(task, result));
        },
      },
      { optional: true },
    );

    api.registerTool(
      {
        name: "umbral_worker_enqueue",
        description:
          "Queue a Worker task through POST /enqueue. Use for async or longer-running work.",
        parameters: {
          type: "object",
          additionalProperties: false,
          required: ["task"],
          properties: {
            task: stringSchema("Worker task name."),
            input: objectSchema("Task input payload."),
            team: stringSchema("Optional Worker team override."),
            taskType: stringSchema("Optional Worker task_type override."),
            callbackUrl: stringSchema("Optional callback URL for completion or failure."),
          },
        },
        async execute(_id: string, params: JsonObject) {
          const cfg = getPluginConfig(api);
          const task = typeof params.task === "string" ? params.task.trim() : "";
          if (!task) {
            throw new Error("task is required.");
          }
          const body = {
            task,
            input: requireObject(params.input, "input"),
            team:
              (typeof params.team === "string" && params.team.trim()) ||
              cfg.defaultTeam ||
              "system",
            task_type:
              (typeof params.taskType === "string" && params.taskType.trim()) ||
              cfg.defaultTaskType ||
              "general",
            callback_url:
              typeof params.callbackUrl === "string" && params.callbackUrl.trim()
                ? params.callbackUrl.trim()
                : undefined,
          };
          const result = await workerRequest(api, "POST", "/enqueue", { body });
          return renderResult("Worker enqueue result", result);
        },
      },
      { optional: true },
    );

    api.registerTool(
      {
        name: "umbral_worker_task_status",
        description: "Read the Redis-backed status for a queued Worker task.",
        parameters: {
          type: "object",
          additionalProperties: false,
          required: ["taskId"],
          properties: {
            taskId: stringSchema("Worker task_id to inspect."),
          },
        },
        async execute(_id: string, params: JsonObject) {
          const taskId = typeof params.taskId === "string" ? params.taskId.trim() : "";
          if (!taskId) {
            throw new Error("taskId is required.");
          }
          const result = await workerRequest(
            api,
            "GET",
            `/task/${encodeURIComponent(taskId)}/status`,
          );
          return renderResult("Worker task status", result);
        },
      },
      { optional: true },
    );

    api.registerTool(
      {
        name: "umbral_worker_tools_inventory",
        description: "List the task inventory and installed skills exposed by the Umbral Worker.",
        parameters: {
          type: "object",
          additionalProperties: false,
          properties: {},
        },
        async execute() {
          const result = await workerRequest(api, "GET", "/tools/inventory");
          return renderResult("Worker tools inventory", result);
        },
      },
      { optional: true },
    );

    api.registerTool(
      {
        name: "umbral_provider_status",
        description:
          "Inspect configured LLM providers, routing preferences, and quota state from the Worker.",
        parameters: {
          type: "object",
          additionalProperties: false,
          properties: {},
        },
        async execute() {
          const result = await workerRequest(api, "GET", "/providers/status");
          return renderResult("Worker provider status", result);
        },
      },
      { optional: true },
    );

    for (const definition of TASK_TOOLS) {
      registerTaskTool(api, definition);
    }
  },
};

export default plugin;
