import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, join } from "node:path";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

type JsonObject = Record<string, unknown>;
type JsonSchema = Record<string, unknown>;

type PluginConfig = {
  baseUrl?: string;
  tokenFile?: string;
  defaultRepoPath?: string;
  timeoutMs?: number;
};

type TournamentToolDefinition = {
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
    "http://127.0.0.1:8088";
  return trimTrailingSlash(raw);
}

function resolveTimeoutMs(api: OpenClawPluginApi): number {
  const cfg = getPluginConfig(api);
  if (typeof cfg.timeoutMs === "number" && cfg.timeoutMs >= 1000) {
    return cfg.timeoutMs;
  }
  return 60000;
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

function isJsonObject(value: unknown): value is JsonObject {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function requireObject(value: unknown, fieldName: string): JsonObject {
  if (value == null) {
    return {};
  }
  if (!isJsonObject(value)) {
    throw new Error(`${fieldName} must be a JSON object.`);
  }
  return value;
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

function stringifyDetail(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  return formatJson(value);
}

function buildTaskInput(api: OpenClawPluginApi, params: JsonObject): JsonObject {
  const input = { ...params };
  delete input.workerTeam;
  delete input.workerTaskType;

  const cfg = getPluginConfig(api);
  if (!input.repo_path && typeof cfg.defaultRepoPath === "string" && cfg.defaultRepoPath.trim()) {
    input.repo_path = cfg.defaultRepoPath.trim();
  }
  return input;
}

function buildRunEnvelope(api: OpenClawPluginApi, task: string, params: JsonObject): JsonObject {
  return {
    schema_version: "0.1",
    task_id: randomUUID(),
    trace_id: randomUUID(),
    source: "openclaw_gateway",
    source_kind: "tournament_github_tool",
    team:
      (typeof params.workerTeam === "string" && params.workerTeam.trim()) ||
      "rick-tournament-lane",
    task_type:
      (typeof params.workerTaskType === "string" && params.workerTaskType.trim()) ||
      "github",
    task,
    input: buildTaskInput(api, params),
  };
}

async function workerRequest(
  api: OpenClawPluginApi,
  method: "GET" | "POST",
  path: string,
  body?: JsonObject,
): Promise<unknown> {
  const url = `${resolveBaseUrl(api)}${path}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    Authorization: `Bearer ${resolveToken(api)}`,
  };
  if (body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(resolveTimeoutMs(api)),
  });

  const raw = await response.text();
  let payload: unknown = raw;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  } else {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      (isJsonObject(payload) && stringifyDetail(payload.detail)) ||
      raw ||
      `${response.status} ${response.statusText}`;
    throw new Error(`Worker ${method} ${path} failed (${response.status}): ${detail}`);
  }
  return payload;
}

async function runTournamentTask(
  api: OpenClawPluginApi,
  task: string,
  params: JsonObject,
): Promise<unknown> {
  const payload = buildRunEnvelope(api, task, params);
  return workerRequest(api, "POST", "/run", payload);
}

function stringSchema(description: string, extra: JsonSchema = {}): JsonSchema {
  return { type: "string", description, ...extra };
}

function integerSchema(description: string, extra: JsonSchema = {}): JsonSchema {
  return { type: "integer", description, ...extra };
}

function arraySchema(items: JsonSchema, description: string, extra: JsonSchema = {}): JsonSchema {
  return {
    type: "array",
    items,
    description,
    ...extra,
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
      workerTeam: stringSchema("Optional Worker team override for routing or tracking."),
      workerTaskType: stringSchema("Optional Worker task_type override."),
    },
  };
}

function registerTournamentTool(api: OpenClawPluginApi, definition: TournamentToolDefinition) {
  api.registerTool(
    {
      name: definition.name,
      description: definition.description,
      parameters: definition.parameters,
      async execute(_id: string, params: JsonObject) {
        const safeParams = requireObject(params, "params");
        const result = await runTournamentTask(api, definition.task, safeParams);
        return renderResult(definition.resultTitle, result);
      },
    },
    { optional: true },
  );
}

const LANE_FIELDS = {
  tournament_id: stringSchema(
    "Tournament id segment used in tournament/<id>/lane-<specialty>. No slashes.",
  ),
  specialty: stringSchema(
    "Lane specialty segment used after lane-. No slashes, for example qa or implementation.",
  ),
  branch_name: stringSchema(
    "Optional explicit branch. Must match tournament/<tournament_id>/lane-<specialty>.",
  ),
};

const TOOLS: TournamentToolDefinition[] = [
  {
    name: "umbral_tournament_preflight",
    task: "tournament_lane.preflight",
    description:
      "Validate tournament GitHub readiness: gh auth, repo path, clean worktree, checkout main, and ff-only pull from origin/main.",
    resultTitle: "Tournament lane preflight result",
    parameters: taskToolSchema({
      base: stringSchema("Optional base branch. Tournament lanes must use main."),
    }),
  },
  {
    name: "umbral_tournament_create_lane_branch",
    task: "tournament_lane.create_branch",
    description:
      "Create and checkout a tournament lane branch from origin/main using tournament/<id>/lane-<specialty>.",
    resultTitle: "Tournament lane branch result",
    parameters: taskToolSchema(
      {
        ...LANE_FIELDS,
        base: stringSchema("Optional base branch. Tournament lanes must use main."),
      },
      ["tournament_id", "specialty"],
    ),
  },
  {
    name: "umbral_tournament_commit_and_push",
    task: "tournament_lane.commit_and_push",
    description:
      "Commit and push the current tournament lane branch using an explicit file list. Never stages all files.",
    resultTitle: "Tournament lane commit result",
    parameters: taskToolSchema(
      {
        ...LANE_FIELDS,
        message: stringSchema("Commit message."),
        files: arraySchema(
          stringSchema("Repo-relative path to stage explicitly."),
          "Explicit list of files to stage. No git add -A equivalent is exposed.",
          { minItems: 1 },
        ),
      },
      ["tournament_id", "specialty", "message", "files"],
    ),
  },
  {
    name: "umbral_tournament_open_pr",
    task: "tournament_lane.open_pr",
    description:
      "Open a PR from the current tournament lane branch to main with the required [tournament:<id>:<specialty>] title prefix. Never merges.",
    resultTitle: "Tournament lane PR result",
    parameters: taskToolSchema(
      {
        ...LANE_FIELDS,
        issue_title: stringSchema("Issue or challenge title used after the required PR title prefix."),
        title: stringSchema("Optional full title. Must already include the required tournament prefix."),
        body: stringSchema("Optional PR body. Worker appends the tournament checklist."),
        issue_url: stringSchema("Optional GitHub issue URL for traceability."),
        tests: stringSchema("Test command or verification performed by the lane."),
        base: stringSchema("Optional base branch. Tournament lane PRs must target main."),
        repo: stringSchema("Optional owner/name repo override. Defaults to Umbral-Bot/umbral-agent-stack."),
      },
      ["tournament_id", "specialty", "issue_title"],
    ),
  },
  {
    name: "umbral_tournament_verify_pr",
    task: "tournament_lane.verify_pr",
    description:
      "Verify PR URL, head branch, title prefix, base branch, diff stats, and check rollup for tournament collect.",
    resultTitle: "Tournament lane verify result",
    parameters: taskToolSchema(
      {
        ...LANE_FIELDS,
        pr_url: stringSchema("PR URL returned by umbral_tournament_open_pr."),
        pr_number: integerSchema("Optional PR number if URL is unavailable."),
        repo: stringSchema("Optional owner/name repo override. Defaults to Umbral-Bot/umbral-agent-stack."),
      },
      ["tournament_id", "specialty"],
    ),
  },
];

const plugin = {
  register(api: OpenClawPluginApi) {
    for (const definition of TOOLS) {
      registerTournamentTool(api, definition);
    }
  },
};

export default plugin;
