#!/usr/bin/env node
// The judgement layer as a command, for the rewrite chains: reads {before, after, record} as JSON
// on stdin and prints the problems the session-check hook would name, as a JSON list.
import { readFileSync } from "node:fs";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DIR = process.env.SESSION_CHECK_DIR ?? resolve(HERE, "../../TYPESAFE/hooks/session-check");
const { findChanges, buildQuestions, stateFor, decide, MODEL } = await import(join(DIR, "check.mjs"));
const { ask, loadKey } = await import(join(DIR, "../../lib/jev.mjs"));
const { loadTerms } = await import(join(DIR, "../../lib/gate.mjs"));

const { before, after, record = "", anchor = null } = JSON.parse(readFileSync(0, "utf8"));
const found = findChanges(before, after, anchor);
let problems = [];
if (found.changed.length || found.removed.length || found.lostSinceAnchor.length || found.dropped.length || found.status) {
  for (let i = 0; i < 3; i++) {
    try {
      const r = await ask(loadKey(), { model: MODEL, state: stateFor(before, after, found, record), questions: buildQuestions(found, { record: !!record }), budgetMs: 20000, terms: loadTerms() });
      problems = decide(found, r.answers ?? {}, { support: record ? record + "\n" + before : "" });
      break;
    } catch (e) { if (i === 2) { process.stdout.write(JSON.stringify({ error: String(e.message ?? e) })); process.exit(0); } }
  }
} else problems = decide(found, {});
process.stdout.write(JSON.stringify(problems));
