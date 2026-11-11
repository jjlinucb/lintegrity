#!/usr/bin/env node
// Run every evidence case through the judgement layer: the session-check hook (Jev, with the
// chat's own record), exactly as Claude Code calls it. Saves results-jev.json.
//   node evidence/run_jev.mjs
// The hook lives in a private repo; point SESSION_CHECK_HOOK at it if it isn't the sibling folder.
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const HOOK = process.env.SESSION_CHECK_HOOK ?? resolve(HERE, "../../TYPESAFE/hooks/session-check/session-check.mjs");
const root = mkdtempSync(join(tmpdir(), "lintegrity-evidence-"));
process.env.SESSION_CHECK_DATA = join(root, "data");
const { run } = await import(HOOK);

const cases = JSON.parse(readFileSync(join(HERE, "cases.json"), "utf8"));
const out = {};
for (const c of cases) {
  const dir = join(root, `case${c.id}`); mkdirSync(dir);
  const path = join(dir, "last_session.md");
  // The wrap-up's own write of the note comes last, as in a real chat; the hook must skip it.
  const events = [...c.events, { type: "assistant", message: { content: [{ type: "tool_use", id: "own", name: "Write", input: { file_path: path, content: c.after } }] } }];
  const transcript = join(dir, "t.jsonl");
  writeFileSync(transcript, events.map((e) => JSON.stringify(e)).join("\n") + "\n");
  writeFileSync(path, c.before); await run({ tool_input: { file_path: path } });   // trusted base
  writeFileSync(path, c.after);
  const t = Date.now();
  const r = await run({ tool_name: "Write", tool_input: { file_path: path }, transcript_path: transcript });
  const reasons = r ? r.reason.split("\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2)) : [];
  out[c.id] = { flagged: !!r, reasons, ms: Date.now() - t };
  const mark = !!r === c.should ? "RIGHT" : c.should ? "miss " : "FALSE";
  console.log(`${mark} t${c.tier} #${String(c.id).padStart(2)} ${c.name}${reasons.length ? "\n        " + reasons.join("\n        ") : ""}`);
}
writeFileSync(join(HERE, "results-jev.json"), JSON.stringify(out, null, 1));
const usage = readFileSync(join(root, "data", "usage.jsonl"), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)).filter((u) => u.input_tokens);
console.log(`\nJev calls: ${usage.length}, input tokens ${usage.reduce((a, u) => a + u.input_tokens, 0)}, median ${usage.map((u) => u.ms).sort((a, b) => a - b)[usage.length >> 1]} ms`);
