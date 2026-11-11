#!/usr/bin/env node
// Both layers together, per case, and the scorecard by tier.
//   node evidence/combine.mjs      (after run_z3.py and run_jev.mjs)
// A Z3 finding is a proof that the note contradicts or no longer carries a trusted fact. That is
// still right when the session really changed the fact (the user said 58 people, not 60), so each
// Z3 finding gets one question: does the chat record show this fact being changed? Backed
// findings are dropped; the rest stand.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DIR = process.env.SESSION_CHECK_DIR ?? resolve(HERE, "../../TYPESAFE/hooks/session-check");
const { recordFromEvents } = await import(join(DIR, "record.mjs"));
const { MODEL } = await import(join(DIR, "check.mjs"));
const { ask, loadKey } = await import(join(DIR, "../../lib/jev.mjs"));
const { loadTerms } = await import(join(DIR, "../../lib/gate.mjs"));
const BACKED = 0.6;

const cases = JSON.parse(readFileSync(join(HERE, "cases.json"), "utf8"));
const z3 = JSON.parse(readFileSync(join(HERE, "results-z3.json"), "utf8"));
const jev = JSON.parse(readFileSync(join(HERE, "results-jev.json"), "utf8"));

const rows = [];
for (const c of cases) {
  const zr = z3[`case:${c.id}`];
  const findings = zr.problems.map((p) => (p.kind === "loss" ? `The note no longer says: ${p.fact}.` : `The note says something that contradicts the trusted facts: ${p.claim}.`));
  let standing = findings, backedP = [];
  if (findings.length) {
    const record = recordFromEvents(c.events);
    const questions = Object.fromEntries(findings.map((f, i) => [`changed_${i}`, {
      type: "noul",
      instructions: `A handoff note was rewritten at the end of a work session. \`chat_record\` is that session. \`finding\` ${i} is a proved difference between the new note and the trusted facts: \`findings[${i}]\`. Does \`chat_record\` show the user or the session's work really changing that fact?`,
      criteria: { true: "Yes: the chat shows the user stating the new value or decision, or work in the session that changed it.", false: "No: nothing in the chat changes this fact." },
    }]));
    const r = await ask(loadKey(), { model: MODEL, state: { chat_record: record, previous_note: c.before, new_note: c.after, findings }, questions, budgetMs: 20000, terms: loadTerms() });
    backedP = findings.map((_, i) => r.answers?.[`changed_${i}`]?.noul ?? 0);
    standing = findings.filter((_, i) => backedP[i] < BACKED);
  }
  const z = standing.length > 0, j = jev[c.id].flagged;
  rows.push({ id: c.id, tier: c.tier, name: c.name, should: c.should, formal: c.formal, z3_raw: findings.length > 0, z3: z, jev: j, both: z || j, backed: backedP.map((x) => +x.toFixed(2)) });
}

const T = { 1: "1 Easy", 2: "2 Medium", 3: "3 Hard", 4: "4 Adversarial", 5: "5 Long note", 6: "6 Held-out arithmetic" };
const pct = (a, b) => `${a}/${b}`;
const lines = ["| Tier | Drifts | Z3 alone | Jev alone | Both |", "|---|---|---|---|---|"];
for (const t of [1, 2, 3, 4, 5, 6]) {
  const d = rows.filter((r) => r.tier === t && r.should);
  lines.push(`| ${T[t]} | ${d.length} | ${pct(d.filter((r) => r.z3).length, d.length)} | ${pct(d.filter((r) => r.jev).length, d.length)} | ${pct(d.filter((r) => r.both).length, d.length)} |`);
}
const drifts = rows.filter((r) => r.should), ctl = rows.filter((r) => !r.should), formal = drifts.filter((r) => r.formal);
lines.push(`| **All drifts** | ${drifts.length} | ${pct(drifts.filter((r) => r.z3).length, drifts.length)} | ${pct(drifts.filter((r) => r.jev).length, drifts.length)} | ${pct(drifts.filter((r) => r.both).length, drifts.length)} |`);
lines.push(`| Drifts Z3 can express | ${formal.length} | ${pct(formal.filter((r) => r.z3).length, formal.length)} | ${pct(formal.filter((r) => r.jev).length, formal.length)} | ${pct(formal.filter((r) => r.both).length, formal.length)} |`);
lines.push(`| **False alarms on safe edits** | ${ctl.length} | ${ctl.filter((r) => r.z3).length} | ${ctl.filter((r) => r.jev).length} | ${ctl.filter((r) => r.both).length} |`);
const held = rows.filter((r) => r.tier === 6 && !r.should);
lines.push(`| Held-out true statements (must pass) | ${held.length} | ${held.filter((r) => r.z3).length} flagged | ${held.filter((r) => r.jev).length} flagged | ${held.filter((r) => r.both).length} flagged |`);
const table = lines.join("\n");
console.log(table);
console.log("\nMissed by both:", drifts.filter((r) => !r.both).map((r) => `#${r.id} ${r.name}`).join("; ") || "none");
console.log("False alarms (both):", ctl.filter((r) => r.both).map((r) => `#${r.id} ${r.name}`).join("; ") || "none");
console.log("Z3 findings cleared as backed by the chat:", rows.filter((r) => r.z3_raw && !r.z3).map((r) => `#${r.id} ${r.name} ${r.backed}`).join("; ") || "none");
console.log("Planted Z3 findings wrongly cleared:", rows.filter((r) => r.should && r.z3_raw && !r.z3).map((r) => `#${r.id} ${r.backed}`).join("; ") || "none");
writeFileSync(join(HERE, "results-combined.json"), JSON.stringify({ rows, table }, null, 1));
