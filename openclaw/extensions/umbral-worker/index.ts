import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, join } from "node:path";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

type JsonObject = Record<string, unknown>;
type JsonSchema = Record<string, unknown>;

type PluginConfig = {
  baseUrl?: string;
  interactiveBaseUrl?: string;
  tokenFile?: string;
  defaultTeam?: string;
  defaultTaskType?: string;
  timeoutMs?: number;
};

type RequestOptions = {
  auth?: boolean;
  body?: JsonObject;
  query?: Record<string, string | number | boolean | undefined>;
  baseUrlOverride?: string;
};

type TaskToolDefinition = {
  name: string;
  task: string;
  description: string;
  resultTitle: string;
  parameters: JsonSchema;
  dispatchMode?: "run" | "enqueue";
  defaultTeam?: string;
  defaultTaskType?: string;
  baseUrlConfigKey?: keyof PluginConfig;
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
  // Keep the network target pinned to plugin config or the loopback default.
  // Reading a generic env var here enlarges the plugin attack surface and is
  // redundant for the VPS runtime, which already injects `baseUrl` explicitly.
  const raw =
    (typeof cfg.baseUrl === "string" && cfg.baseUrl.trim()) ||
    "http://127.0.0.1:8088";
  return trimTrailingSlash(raw);
}

function resolveBaseUrlOverride(
  api: OpenClawPluginApi,
  baseUrlConfigKey?: keyof PluginConfig,
): string | undefined {
  if (!baseUrlConfigKey) {
    return undefined;
  }
  const cfg = getPluginConfig(api);
  const candidate = cfg[baseUrlConfigKey];
  const raw = typeof candidate === "string" ? candidate.trim() : "";
  if (!raw) {
    return undefined;
  }
  return trimTrailingSlash(raw);
}

function resolveTimeoutMs(api: OpenClawPluginApi): number {
  const cfg = getPluginConfig(api);
  if (typeof cfg.timeoutMs === "number" && cfg.timeoutMs >= 1000) {
    return cfg.timeoutMs;
  }
  return 30000;
}

function resolvePath(value: string): string {
  if (value.startsWith("~/")) {
    return join(homedir(), value.slice(2));
  }
  if (value === "~") {
    return homedir();
  }
  return isAbsolute(value) ? value : join(homedir(), value);
}

function resolveToken(api: OpenClawPluginApi): string {
  const cfg = getPluginConfig(api);
  const tokenPath = resolvePath(cfg.tokenFile || "~/.config/openclaw/worker-token");
  const token = readFileSync(tokenPath, "utf8").trim();
  if (!token) {
    throw new Error(`Worker token file is empty: ${tokenPath}`);
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
    if (key === "b64_json" && typeof raw === "string") {
      result[key] =
        "[omitted from gateway response; use output_path or direct Worker call for binary image]";
      result.b64_json_chars = raw.length;
      continue;
    }
    if (key === "b64_png" && typeof raw === "string") {
      result[key] =
        "[omitted from gateway response; use path or direct Worker call for binary screenshot]";
      result.b64_png_chars = raw.length;
      continue;
    }
    result[key] = sanitizeBinaryPayload(raw);
  }
  return result;
}

function sanitizeWorkerResult(task: string, value: unknown): unknown {
  if (
    !task.endsWith(".audio.generate") &&
    !task.endsWith(".image.generate") &&
    task !== "browser.screenshot" &&
    task !== "gui.screenshot"
  ) {
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
  const baseUrl = options.baseUrlOverride || resolveBaseUrl(api);
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
    headers.Authorization = `Bearer ${resolveToken(api)}`;
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
    source: "openclaw_gateway",
    source_kind: "tool_run",
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

function buildEnqueueBody(
  api: OpenClawPluginApi,
  task: string,
  params: JsonObject,
  overrides: { defaultTeam?: string; defaultTaskType?: string } = {},
): JsonObject {
  const cfg = getPluginConfig(api);
  return {
    task,
    input: buildTaskInput(params),
    team:
      (typeof params.workerTeam === "string" && params.workerTeam.trim()) ||
      overrides.defaultTeam ||
      cfg.defaultTeam ||
      "system",
    task_type:
      (typeof params.workerTaskType === "string" && params.workerTaskType.trim()) ||
      overrides.defaultTaskType ||
      cfg.defaultTaskType ||
      "general",
    source: "openclaw_gateway",
    source_kind: "tool_enqueue",
    notion_track: Boolean(params.notionTrack),
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
  options: { baseUrlOverride?: string } = {},
): Promise<unknown> {
  const payload = buildRunEnvelope(api, {
    task,
    input: buildTaskInput(params),
    team: params.workerTeam,
    taskType: params.workerTaskType,
  });
  return workerRequest(api, "POST", "/run", {
    body: payload,
    baseUrlOverride: options.baseUrlOverride,
  });
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function enqueueNamedTaskAndWait(
  api: OpenClawPluginApi,
  task: string,
  params: JsonObject,
  overrides: { defaultTeam?: string; defaultTaskType?: string } = {},
): Promise<unknown> {
  const body = buildEnqueueBody(api, task, params, overrides);
  const queued = await workerRequest(api, "POST", "/enqueue", { body });
  if (!isJsonObject(queued)) {
    throw new Error("Worker enqueue returned a non-JSON response.");
  }

  const taskId =
    typeof queued.task_id === "string" && queued.task_id.trim() ? queued.task_id.trim() : "";
  if (!taskId) {
    throw new Error(`Worker enqueue did not return a task_id: ${formatJson(queued)}`);
  }

  const startedAt = Date.now();
  const timeoutMs = resolveTimeoutMs(api);
  while (Date.now() - startedAt < timeoutMs) {
    const status = await workerRequest(
      api,
      "GET",
      `/task/${encodeURIComponent(taskId)}/status`,
    );
    if (!isJsonObject(status)) {
      throw new Error("Worker task status returned a non-JSON response.");
    }

    const state = typeof status.status === "string" ? status.status.toLowerCase() : "";
    if (state === "done") {
      return {
        ok: true,
        task_id: taskId,
        task: status.task ?? task,
        team: status.team ?? body.team,
        task_type: status.task_type ?? body.task_type,
        result: status.result,
      };
    }
    if (state === "failed" || state === "blocked") {
      const error =
        typeof status.error === "string" && status.error.trim()
          ? status.error.trim()
          : formatJson(status);
      throw new Error(`Queued Worker task ${taskId} ${state}: ${error}`);
    }

    await sleep(1000);
  }

  throw new Error(`Timed out waiting for queued Worker task ${taskId} (${task}).`);
}

function registerTaskTool(api: OpenClawPluginApi, definition: TaskToolDefinition) {
  api.registerTool(
    {
      name: definition.name,
      description: definition.description,
      parameters: definition.parameters,
      async execute(_id: string, params: JsonObject) {
        const baseUrlOverride = resolveBaseUrlOverride(api, definition.baseUrlConfigKey);
        const result =
          definition.dispatchMode === "enqueue"
            ? await enqueueNamedTaskAndWait(api, definition.task, params, {
                defaultTeam: definition.defaultTeam,
                defaultTaskType: definition.defaultTaskType,
              })
            : await runNamedTask(api, definition.task, params, {
                baseUrlOverride,
              });
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
    name: "umbral_notion_read_page",
    task: "notion.read_page",
    description: "Read a Notion page by URL or page ID and return metadata plus a plain-text snapshot of its blocks.",
    resultTitle: "Notion page read result",
    parameters: taskToolSchema(
      {
        page_id_or_url: stringSchema("Notion page UUID or full page URL."),
        max_blocks: integerSchema("Maximum number of top-level blocks to read.", {
          minimum: 1,
          maximum: 100,
        }),
      },
      ["page_id_or_url"],
    ),
  },
  {
    name: "umbral_notion_read_database",
    task: "notion.read_database",
    description: "Read a Notion database by URL or database ID and return flattened rows plus schema metadata.",
    resultTitle: "Notion database read result",
    parameters: taskToolSchema(
      {
        database_id_or_url: stringSchema("Notion database UUID or full database URL."),
        max_items: integerSchema("Maximum number of rows to read.", {
          minimum: 1,
          maximum: 100,
        }),
        filter: objectSchema("Optional Notion database filter object."),
      },
      ["database_id_or_url"],
    ),
  },
  {
    name: "umbral_notion_search_databases",
    task: "notion.search_databases",
    description: "Search Notion databases by title and return matching database IDs and URLs.",
    resultTitle: "Notion database search result",
    parameters: taskToolSchema(
      {
        query: stringSchema("Database title or search query."),
        max_results: integerSchema("Maximum number of database matches to return.", {
          minimum: 1,
          maximum: 20,
        }),
      },
      ["query"],
    ),
  },
  {
    name: "umbral_notion_create_database_page",
    task: "notion.create_database_page",
    description: "Create a page inside a Notion database using raw Notion API properties and optional child blocks.",
    resultTitle: "Notion database page create result",
    parameters: taskToolSchema(
      {
        database_id_or_url: stringSchema("Notion database UUID or full database URL."),
        properties: objectSchema("Raw Notion page properties payload."),
        children: arraySchema(objectSchema("Optional raw Notion block object."), "Optional child blocks."),
        icon: stringSchema("Optional page icon as emoji or external image URL."),
      },
      ["database_id_or_url", "properties"],
    ),
  },
  {
    name: "umbral_notion_update_page_properties",
    task: "notion.update_page_properties",
    description: "Update raw Notion page properties for an existing page.",
    resultTitle: "Notion page properties update result",
    parameters: taskToolSchema(
      {
        page_id_or_url: stringSchema("Notion page UUID or full page URL."),
        properties: objectSchema("Raw Notion page properties payload."),
        icon: stringSchema("Optional page icon as emoji or external image URL."),
        archived: booleanSchema("Optional page archive toggle. Use true to archive a loose page after it was regularized elsewhere."),
      },
      ["page_id_or_url"],
    ),
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
        project_name: stringSchema("Optional exact project name from the Projects registry."),
        project_page_id: stringSchema("Optional Notion page ID of the related project."),
        deliverable_name: stringSchema("Optional exact deliverable name from the deliverables registry."),
        deliverable_page_id: stringSchema("Optional Notion page ID of the related deliverable."),
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
        icon: stringSchema("Optional page icon as emoji or external image URL."),
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
  {
    name: "umbral_notion_upsert_project",
    task: "notion.upsert_project",
    description: "Create or update a project entry in the 📁 Proyectos — Umbral Notion database. Use to register a project, backfill metadata, or update status, sprint, open issues, blockers, and next action.",
    resultTitle: "Notion project upsert result",
    parameters: taskToolSchema(
      {
        name: stringSchema("Project name (used as lookup key)."),
        estado: enumStringSchema(["Activo", "En pausa", "Completado", "Archivado"], "Project status."),
        linear_project_url: stringSchema("URL of the associated Linear project."),
        shared_path: stringSchema("Windows shared path such as G:\\\\Mi unidad\\\\Project\\\\."),
        responsable: stringSchema("Name of the human responsible for the project."),
        agentes: stringSchema("Comma-separated agent names: Rick, Claude, Codex, Cursor, Antigravity."),
        sprint: stringSchema("Current sprint label such as R21."),
        start_date: stringSchema("Project start date (YYYY-MM-DD)."),
        target_date: stringSchema("Project target date (YYYY-MM-DD)."),
        open_issues: integerSchema("Number of open Linear issues."),
        bloqueos: stringSchema("Current blockers for the project."),
        next_action: stringSchema("Next concrete action to move the project forward."),
        last_update_date: stringSchema("Date of last project update (YYYY-MM-DD)."),
        icon: stringSchema("Optional page icon as emoji or external image URL."),
      },
      ["name"],
    ),
  },

  {
    name: "umbral_notion_upsert_deliverable",
    task: "notion.upsert_deliverable",
    description: "Create or update a reviewable deliverable in the Notion deliverables registry. Use this for benchmarks, reports, drafts, editorial pieces, and knowledge assets that David must review.",
    resultTitle: "Notion deliverable upsert result",
    parameters: taskToolSchema(
      {
        name: stringSchema("Deliverable title in natural Spanish. Make it descriptive and do not include dates in the title."),
        project_name: stringSchema("Exact project name in the projects registry."),
        project_page_id: stringSchema("Optional project page ID if already resolved."),
        deliverable_type: enumStringSchema(
          [
            "Benchmark",
            "Reporte",
            "Borrador",
            "Pieza editorial",
            "Criterio / base de conocimiento",
            "Plan",
            "Auditoria",
          ],
          "Deliverable type.",
        ),
        review_status: enumStringSchema(
          [
            "Pendiente revision",
            "Aprobado",
            "Aprobado con ajustes",
            "Rechazado",
            "Archivado",
          ],
          "Human review state.",
        ),
        date: stringSchema("Deliverable date (YYYY-MM-DD)."),
        suggested_due_date: stringSchema("Optional suggested review deadline (YYYY-MM-DD). Omit to let the Worker infer it."),
        agent: enumStringSchema(["Rick", "Claude", "Codex", "Cursor", "Antigravity"], "Agent that produced the deliverable."),
        summary: stringSchema("Short summary of the deliverable."),
        artifact_url: stringSchema("Canonical URL to the artifact."),
        artifact_path: stringSchema("Canonical shared path such as G:\\\\Mi unidad\\\\..."),
        notes: stringSchema("Review notes or context."),
        next_action: stringSchema("Next concrete action after review."),
        linear_issue_url: stringSchema("Related Linear issue URL."),
        source_task_id: stringSchema("Origin task id if applicable."),
        last_update_date: stringSchema("Date of last update (YYYY-MM-DD)."),
        icon: stringSchema("Optional page icon as emoji or external image URL."),
      },
      ["name"],
    ),
  },

  // Research and LLM
  {
    name: "umbral_research_web",
    task: "research.web",
    description: "Run a web search through the Worker (Tavily primario con fallback Gemini grounded search).",
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
    description: "Create a Linear issue with optional team routing, labels, and project association.",
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
        project_id: stringSchema("Optional Linear project UUID to associate after creation."),
        project_name: stringSchema("Optional Linear project name to resolve or create."),
        create_project_if_missing: booleanSchema("Create the Linear project automatically when project_name does not exist."),
        project_description: stringSchema("Optional short Linear project description if the project must be created."),
        project_content: stringSchema("Optional long-form Linear project content if the project must be created."),
        project_start_date: stringSchema("Optional Linear project start date (YYYY-MM-DD)."),
        project_target_date: stringSchema("Optional Linear project target date (YYYY-MM-DD)."),
        project_priority: integerSchema("Optional Linear project priority.", {
          minimum: 0,
          maximum: 4,
        }),
        project_icon: stringSchema("Optional emoji/icon for a newly created Linear project."),
        project_color: stringSchema("Optional hex color for a newly created Linear project."),
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
  {
    name: "umbral_linear_list_projects",
    task: "linear.list_projects",
    description: "List Linear projects, optionally filtered by a case-insensitive name query.",
    resultTitle: "Linear projects result",
    parameters: taskToolSchema({
      query: stringSchema("Optional case-insensitive substring filter on project name."),
      limit: integerSchema("Maximum number of projects to return.", {
        minimum: 1,
        maximum: 250,
      }),
    }),
  },
  {
    name: "umbral_linear_create_project",
    task: "linear.create_project",
    description: "Create a Linear project, or return the existing one when the same name already exists.",
    resultTitle: "Linear project result",
    parameters: taskToolSchema(
      {
        name: stringSchema("Linear project name."),
        team_id: stringSchema("Optional Linear team UUID."),
        team_name: stringSchema("Optional Linear team name, defaulting to Umbral."),
        if_exists_return: booleanSchema("Return an existing project with the same name instead of creating a duplicate."),
        description: stringSchema("Optional short project description."),
        content: stringSchema("Optional long-form project content/spec."),
        lead_id: stringSchema("Optional Linear user UUID for the project lead."),
        start_date: stringSchema("Optional project start date (YYYY-MM-DD)."),
        target_date: stringSchema("Optional project target date (YYYY-MM-DD)."),
        priority: integerSchema("Optional project priority.", { minimum: 0, maximum: 4 }),
        icon: stringSchema("Optional project icon / emoji."),
        color: stringSchema("Optional project color hex."),
      },
      ["name"],
    ),
  },
  {
    name: "umbral_linear_attach_issue_to_project",
    task: "linear.attach_issue_to_project",
    description: "Attach an existing Linear issue to a project by UUID or project name.",
    resultTitle: "Linear issue-to-project result",
    parameters: taskToolSchema(
      {
        issue_id: stringSchema("Linear issue UUID."),
        project_id: stringSchema("Optional Linear project UUID."),
        project_name: stringSchema("Optional Linear project name to resolve or create."),
        create_project_if_missing: booleanSchema("Create the project automatically if project_name does not exist."),
        team_id: stringSchema("Optional Linear team UUID, used if the project needs to be created."),
        team_name: stringSchema("Optional Linear team name, defaulting to Umbral."),
        project_description: stringSchema("Optional short project description if creating the project."),
        project_content: stringSchema("Optional long-form project content/spec if creating the project."),
        project_start_date: stringSchema("Optional project start date (YYYY-MM-DD)."),
        project_target_date: stringSchema("Optional project target date (YYYY-MM-DD)."),
        project_priority: integerSchema("Optional project priority.", { minimum: 0, maximum: 4 }),
        project_icon: stringSchema("Optional project icon / emoji."),
        project_color: stringSchema("Optional project color hex."),
      },
      ["issue_id"],
    ),
  },
  {
    name: "umbral_linear_list_project_issues",
    task: "linear.list_project_issues",
    description: "List issues currently associated with a Linear project.",
    resultTitle: "Linear project issues result",
    parameters: taskToolSchema(
      {
        project_id: stringSchema("Optional Linear project UUID."),
        project_name: stringSchema("Optional Linear project name."),
        limit: integerSchema("Maximum issues to return.", { minimum: 1, maximum: 250 }),
      },
      [],
    ),
  },
  {
    name: "umbral_linear_create_project_update",
    task: "linear.create_project_update",
    description: "Post a project status update in Linear (health + body text). Use after completing a sprint milestone or when reporting blockers.",
    resultTitle: "Linear project update result",
    parameters: taskToolSchema(
      {
        body: stringSchema("Update body text (markdown supported)."),
        project_id: stringSchema("Optional Linear project UUID."),
        project_name: stringSchema("Optional Linear project name."),
        health: enumStringSchema(["onTrack", "atRisk", "offTrack"], "Project health indicator."),
      },
      ["body"],
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
    name: "umbral_google_image_generate",
    task: "google.image.generate",
    description: "Generate one or more images through Google's OpenAI-compatible Images API and save them to disk.",
    resultTitle: "Google image result",
    parameters: taskToolSchema(
      {
        prompt: stringSchema("Prompt text for image generation."),
        model: stringSchema("Optional image model, default imagen-3.0-generate-002."),
        size: stringSchema("Optional output size, for example 1024x1024 or 1536x1024."),
        n: integerSchema("Number of images to generate.", { minimum: 1, maximum: 4 }),
        output_dir: stringSchema("Optional directory where generated image files should be saved."),
        filename_prefix: stringSchema("Optional prefix for saved file names."),
        return_b64: booleanSchema("Include base64 in the Worker response. Default false."),
      },
      ["prompt"],
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
    name: "umbral_n8n_list_workflows",
    task: "n8n.list_workflows",
    description: "List workflows from the configured n8n instance.",
    resultTitle: "n8n workflows result",
    parameters: taskToolSchema({
      query: stringSchema("Optional case-insensitive substring filter on workflow name."),
      active: booleanSchema("Optional active-state filter."),
      limit: integerSchema("Maximum number of workflows to return.", { minimum: 1, maximum: 250 }),
      timeout: integerSchema("Request timeout in seconds.", { minimum: 1, maximum: 120 }),
    }),
  },
  {
    name: "umbral_n8n_get_workflow",
    task: "n8n.get_workflow",
    description: "Fetch a workflow definition from the configured n8n instance by workflow ID.",
    resultTitle: "n8n workflow result",
    parameters: taskToolSchema(
      {
        workflow_id: stringSchema("n8n workflow ID."),
        timeout: integerSchema("Request timeout in seconds.", { minimum: 1, maximum: 120 }),
      },
      ["workflow_id"],
    ),
  },
  {
    name: "umbral_n8n_create_workflow",
    task: "n8n.create_workflow",
    description: "Create a workflow in the configured n8n instance from raw workflow JSON.",
    resultTitle: "n8n create workflow result",
    parameters: taskToolSchema(
      {
        workflow: objectSchema("Raw n8n workflow payload (name, nodes, connections, settings, etc.)."),
        timeout: integerSchema("Request timeout in seconds.", { minimum: 1, maximum: 120 }),
      },
      ["workflow"],
    ),
  },
  {
    name: "umbral_n8n_update_workflow",
    task: "n8n.update_workflow",
    description: "Update an existing workflow in the configured n8n instance from raw workflow JSON.",
    resultTitle: "n8n update workflow result",
    parameters: taskToolSchema(
      {
        workflow_id: stringSchema("n8n workflow ID."),
        workflow: objectSchema("Raw n8n workflow payload."),
        timeout: integerSchema("Request timeout in seconds.", { minimum: 1, maximum: 120 }),
      },
      ["workflow_id", "workflow"],
    ),
  },
  {
    name: "umbral_n8n_post_webhook",
    task: "n8n.post_webhook",
    description: "POST a JSON payload to a webhook on the configured n8n instance.",
    resultTitle: "n8n webhook result",
    parameters: taskToolSchema(
      {
        webhook_path: stringSchema("Relative webhook path on the configured n8n instance, for example /webhook/my-flow."),
        webhook_url: stringSchema("Absolute webhook URL on the same n8n origin."),
        payload: objectSchema("JSON payload to send."),
        timeout: integerSchema("Request timeout in seconds.", { minimum: 1, maximum: 120 }),
      },
      ["payload"],
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
    parameters: taskToolSchema({
      text: stringSchema("Optional text to open in Notepad."),
      run_now: booleanSchema("Run the scheduled task immediately when not in an interactive session."),
      run_as_user: stringSchema("Optional Windows username for the scheduled task."),
    }),
  },
  {
    name: "umbral_windows_open_url",
    task: "windows.open_url",
    description: "Open a URL in the default browser of the Windows lab session.",
    resultTitle: "Windows open URL result",
    dispatchMode: "enqueue",
    defaultTeam: "lab",
    parameters: taskToolSchema(
      {
        url: stringSchema("HTTP or HTTPS URL to open in the default browser."),
      },
      ["url"],
    ),
  },
  {
    name: "umbral_windows_write_worker_token",
    task: "windows.write_worker_token",
    description: "Write the Worker token to C:\\openclaw-worker\\worker_token on the Windows node.",
    resultTitle: "Windows worker token result",
    dispatchMode: "enqueue",
    defaultTeam: "lab",
    parameters: taskToolSchema({}),
  },
  {
    name: "umbral_windows_firewall_allow_port",
    task: "windows.firewall_allow_port",
    description: "Create or refresh a Windows firewall rule allowing inbound TCP access on a port.",
    resultTitle: "Windows firewall result",
    dispatchMode: "enqueue",
    defaultTeam: "lab",
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
    parameters: taskToolSchema({}),
  },
  {
    name: "umbral_windows_add_interactive_worker_to_startup",
    task: "windows.add_interactive_worker_to_startup",
    description: "Install the interactive Worker startup shortcut in the Windows Startup folder.",
    resultTitle: "Windows startup shortcut result",
    dispatchMode: "enqueue",
    defaultTeam: "lab",
    parameters: taskToolSchema({
      username: stringSchema("Windows username, default Rick."),
    }),
  },
  {
    name: "umbral_windows_fs_ensure_dirs",
    task: "windows.fs.ensure_dirs",
    description: "Create a directory tree on the Windows node within the allowlisted base paths.",
    resultTitle: "Windows ensure dirs result",
    dispatchMode: "enqueue",
    defaultTeam: "lab",
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
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
    dispatchMode: "enqueue",
    defaultTeam: "lab",
    parameters: taskToolSchema(
      {
        path: stringSchema("File path to write."),
        b64: stringSchema("Base64 payload to decode and write."),
      },
      ["path", "b64"],
    ),
  },
  {
    name: "umbral_browser_navigate",
    task: "browser.navigate",
    description: "Navigate a persistent Playwright browser page on the Windows lab node.",
    resultTitle: "Browser navigate result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        url: stringSchema("Target URL to open."),
        page_id: stringSchema("Optional existing page ID. Omit to create or reuse the default page."),
        wait_until: enumStringSchema(
          ["commit", "domcontentloaded", "load", "networkidle"],
          "Playwright wait_until mode.",
        ),
        timeout_ms: integerSchema("Optional navigation timeout in milliseconds.", {
          minimum: 1000,
          maximum: 120000,
        }),
      },
      ["url"],
    ),
  },
  {
    name: "umbral_browser_read_page",
    task: "browser.read_page",
    description: "Read visible text from the current browser page or a selector on the Windows lab node.",
    resultTitle: "Browser read page result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema({
      page_id: stringSchema("Optional existing page ID."),
      selector: stringSchema("Optional CSS selector to narrow the read target."),
      include_html: booleanSchema("Include the page HTML snapshot in the response."),
    }),
  },
  {
    name: "umbral_browser_screenshot",
    task: "browser.screenshot",
    description: "Capture a screenshot from the Playwright browser running on the Windows lab node.",
    resultTitle: "Browser screenshot result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema({
      page_id: stringSchema("Optional existing page ID."),
      path: stringSchema("Optional absolute output path on the Windows node."),
      full_page: booleanSchema("Capture the full page instead of the viewport."),
      selector: stringSchema("Optional CSS selector to capture instead of the whole page."),
      return_b64: booleanSchema("Return a base64 PNG payload in addition to writing the file."),
    }),
  },
  {
    name: "umbral_browser_click",
    task: "browser.click",
    description: "Click a CSS selector in the Playwright browser running on the Windows lab node.",
    resultTitle: "Browser click result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        page_id: stringSchema("Optional existing page ID."),
        selector: stringSchema("CSS selector to click."),
        timeout_ms: integerSchema("Optional click timeout in milliseconds.", {
          minimum: 1000,
          maximum: 120000,
        }),
      },
      ["selector"],
    ),
  },
  {
    name: "umbral_browser_type_text",
    task: "browser.type_text",
    description: "Type text into a CSS selector in the Playwright browser running on the Windows lab node.",
    resultTitle: "Browser type text result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        page_id: stringSchema("Optional existing page ID."),
        selector: stringSchema("CSS selector to type into."),
        text: stringSchema("Text to type."),
        clear: booleanSchema("Clear the field before typing."),
        press_enter: booleanSchema("Press Enter after typing."),
        timeout_ms: integerSchema("Optional typing timeout in milliseconds.", {
          minimum: 1000,
          maximum: 120000,
        }),
      },
      ["selector", "text"],
    ),
  },
  {
    name: "umbral_browser_press_key",
    task: "browser.press_key",
    description: "Send a keyboard key to the current Playwright browser page on the Windows lab node.",
    resultTitle: "Browser press key result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        page_id: stringSchema("Optional existing page ID."),
        key: stringSchema("Key or shortcut understood by Playwright, for example Enter or Control+L."),
      },
      ["key"],
    ),
  },
  {
    name: "umbral_gui_desktop_status",
    task: "gui.desktop_status",
    description: "Inspect the current Windows desktop session on the lab node and report screen size, cursor and root control.",
    resultTitle: "GUI desktop status result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema({}),
  },
  {
    name: "umbral_gui_screenshot",
    task: "gui.screenshot",
    description: "Capture a raw desktop screenshot from the Windows GUI session on the lab node.",
    resultTitle: "GUI screenshot result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        path: stringSchema("Absolute output path on the Windows node."),
        return_b64: booleanSchema("Return a base64 PNG payload in addition to writing the file."),
      },
      [],
    ),
  },
  {
    name: "umbral_gui_click",
    task: "gui.click",
    description: "Move the mouse and click at absolute screen coordinates on the Windows lab node.",
    resultTitle: "GUI click result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        x: integerSchema("Screen X coordinate."),
        y: integerSchema("Screen Y coordinate."),
        clicks: integerSchema("Number of clicks.", { minimum: 1, maximum: 5 }),
        interval: numberSchema("Delay between clicks in seconds.", { minimum: 0 }),
        duration: numberSchema("Mouse move duration in seconds.", { minimum: 0 }),
        button: enumStringSchema(["left", "right", "middle"], "Mouse button."),
      },
      ["x", "y"],
    ),
  },
  {
    name: "umbral_gui_type_text",
    task: "gui.type_text",
    description: "Type text into the currently focused UI element on the Windows lab node.",
    resultTitle: "GUI type text result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        text: stringSchema("Text to type into the active control."),
        interval: numberSchema("Delay between keystrokes in seconds.", { minimum: 0 }),
      },
      ["text"],
    ),
  },
  {
    name: "umbral_gui_hotkey",
    task: "gui.hotkey",
    description: "Send a keyboard shortcut to the active Windows UI session on the lab node.",
    resultTitle: "GUI hotkey result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        keys: arraySchema(stringSchema("One key of the shortcut."), "Ordered key combination, for example ['ctrl','l'].", {
          minItems: 1,
        }),
      },
      ["keys"],
    ),
  },
  {
    name: "umbral_gui_list_windows",
    task: "gui.list_windows",
    description: "List top-level windows visible in the interactive Windows session on the lab node.",
    resultTitle: "GUI list windows result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema({
      visible_only: booleanSchema("Only include visible windows.", { default: true }),
    }),
  },
  {
    name: "umbral_gui_activate_window",
    task: "gui.activate_window",
    description: "Bring a matching window to the foreground in the interactive Windows session on the lab node.",
    resultTitle: "GUI activate window result",
    dispatchMode: "run",
    baseUrlConfigKey: "interactiveBaseUrl",
    parameters: taskToolSchema(
      {
        exact_title: stringSchema("Exact window title to activate."),
        title_contains: stringSchema("Substring to match against window title."),
        process_name: stringSchema("Optional process executable name, for example chrome.exe."),
      },
      [],
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
