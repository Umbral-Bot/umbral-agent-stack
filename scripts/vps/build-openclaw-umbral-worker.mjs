#!/usr/bin/env node
// Build the umbral-worker OpenClaw plugin: strip TypeScript types from
// index.ts into dist/index.js so the gateway can load it (the gateway
// runtime requires a compiled JS entry; TS source is only resolved by
// CLI/dev flows). Uses Node's built-in stripTypeScriptTypes — no deps.
import { stripTypeScriptTypes } from "node:module";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const pluginDir = process.argv[2]
  ? process.argv[2]
  : join(dirname(fileURLToPath(import.meta.url)), "..", "..", "openclaw", "extensions", "umbral-worker");

const src = readFileSync(join(pluginDir, "index.ts"), "utf8");
const out = stripTypeScriptTypes(src, { mode: "strip" });
mkdirSync(join(pluginDir, "dist"), { recursive: true });
writeFileSync(join(pluginDir, "dist", "index.js"), out);
console.log(`built ${join(pluginDir, "dist", "index.js")} (${out.length} bytes)`);
