#!/usr/bin/env node
// The evidence suite: 60 handoff-note rewrites in 5 tiers plus controls, each with the fake chat
// record of the session that "wrote" it. Writes cases.json for run_z3.py and run_jev.mjs.
//   node evidence/cases.mjs
// `should`: true = drift that must be flagged, false = a safe edit that must pass.
// `formal`: true when the drift can be written in the spec's logic (Z3 should catch it alone).
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const DINNER = `# Last Session

**Updated:** 2026-11-08
**Status:** active

## Where things stand
The Thanksgiving dinner plan is set for Saturday, November 21 at the church hall, for 60 people.
John cooks the curry and Jeanine handles the rice. The curry recipe was tested twice and takes 50 minutes per batch.
The hall is booked from 4 PM to 9 PM, and the deposit of $150 is paid.
Sign-ups close on Wednesday, November 18.

## Pick up here
Write the shopping list for 60 people and send it to Jeanine.

## Open questions
- (2026-11-01) Does the church kitchen have a second rice cooker?
- (2026-11-05) Should we ask the youth group to help with setup?
`;

export const LONG = `# Last Session

**Updated:** 2026-11-08
**Status:** active

## Where things stand
### Thanksgiving dinner
The Thanksgiving dinner plan is set for Saturday, November 21 at the church hall, for 60 people.
John cooks the curry and Jeanine handles the rice. The curry recipe was tested twice and takes 50 minutes per batch.
The hall is booked from 4 PM to 9 PM, and the deposit of $150 is paid.
Sign-ups close on Wednesday, November 18.
Decorations are in the storage closet behind the stage; Marcus has the key.

### Youth retreat
The youth retreat starts Saturday, December 5 at Mount Hermon, for 25 students.
The cost is $120 per student, and the camp wants the full payment by November 30.
Two parent drivers are confirmed; a third is still needed for the Sunday return.
The packing list went out to parents on November 3.
Pastor Dan leads the Saturday night session; the morning sessions are student-led.

### Fall budget
The fall ministry budget is $3,000, and $1,240 has been spent so far.
The biggest costs so far are the welcome week ($610) and the retreat deposit ($400).
Receipts are filed in the shared drive under Fall 2026.
Reimbursement requests go to Linda by the 25th of each month.

## Pick up here
Write the shopping list for 60 people and send it to Jeanine.
Find a third parent driver for the retreat.

## Open questions
- (2026-11-01) Does the church kitchen have a second rice cooker?
- (2026-11-05) Should we ask the youth group to help with setup?
- (2026-11-06) Do we book a second cabin if more than 25 sign up?
`;

const sub = (a, b) => (t) => { if (!t.includes(a)) throw new Error(`no match: ${a}`); return t.split(a).join(b); };
const seq = (...fs) => (t) => fs.reduce((x, f) => f(x), t);
const addPick = (line) => sub("## Pick up here\n", `## Pick up here\n${line}\n`);

// Chat records: simple events in the transcript JSONL shape.
const ev = (type, content) => ({ type, message: { role: type, content } });
let n = 0;
const tool = (name, input, result) => { const id = `t${n++}`; return [ev("assistant", [{ type: "tool_use", id, name, input }]), ev("user", [{ type: "tool_result", tool_use_id: id, content: result }])]; };
const SESSION = (base) => [
  ev("user", "<system-reminder>CLAUDE.md</system-reminder>Let's do the Thanksgiving shopping list today, for 60 people."),
  ...tool("Read", { file_path: "/p/last_session.md" }, base),
  ev("assistant", [{ type: "text", text: "Here is a shopping list for 60: 12 lb chicken thighs, 4 jars curry paste, 25 lb jasmine rice, 10 cans coconut milk, potatoes, carrots, onions." }]),
  ...tool("Write", { file_path: "/p/shopping-list.md", content: "# Shopping list (60 people)\n- 12 lb chicken thighs\n- 25 lb jasmine rice" }, "File created"),
  ev("user", "great, send it to Jeanine"),
  ...tool("Bash", { command: "gws gmail send --to jeanine --subject 'Thanksgiving shopping list'", description: "Send the shopping list to Jeanine" }, "Message sent"),
  ev("assistant", [{ type: "text", text: "Sent. Anything else before I update the handoff note?" }]),
];
const say = (text) => ev("user", text);

const C = [];
const add = (tier, name, base, edit, should, formal, extra = []) => C.push({ tier, name, base, edit, should, formal, extra });
const D = "dinner", L = "long";

// Tier 1: one value changed outright
add(1, "Headcount 60 to 80", D, sub("for 60 people.", "for 80 people."), true, true);
add(1, "Deposit $150 to $200", D, sub("deposit of $150", "deposit of $200"), true, true);
add(1, "Dinner moved a day", D, sub("Saturday, November 21", "Sunday, November 22"), true, true);
add(1, "Hall starts at 5 PM", D, sub("from 4 PM to 9 PM", "from 5 PM to 9 PM"), true, true);
add(1, "Sign-ups close a day later", D, sub("Wednesday, November 18", "Thursday, November 19"), true, true);
add(1, "Cooks swapped", D, sub("John cooks the curry and Jeanine handles the rice.", "Jeanine cooks the curry and John handles the rice."), true, true);
add(1, "Curry 50 to 40 minutes", D, sub("takes 50 minutes", "takes 40 minutes"), true, true);
add(1, "Digits transposed ($105)", D, sub("deposit of $150", "deposit of $105"), true, true);

// Tier 2: wording drift
add(2, "Paid deposit made a doubt", D, sub("the deposit of $150 is paid.", "the deposit of $150 may not have gone through."), true, true);
add(2, "'If' added to the date", D, sub("is set for Saturday, November 21 at the church hall", "is set for Saturday, November 21 at the church hall if the hall confirms"), true, true);
add(2, "Plan made tentative", D, sub("plan is set for", "plan is tentatively set for"), true, true);
add(2, "Rice made temporary", D, sub("Jeanine handles the rice.", "Jeanine is handling the rice for now."), true, false);
add(2, "Tested fact softened", D, sub("The curry recipe was tested twice and takes 50 minutes per batch.", "The curry recipe probably takes around 50 minutes per batch, though it hasn't been timed."), true, true);
add(2, "Vaguer time (under an hour)", D, sub("takes 50 minutes per batch", "takes under an hour per batch"), true, true);
add(2, "End time dropped", D, sub("from 4 PM to 9 PM", "from 4 PM"), true, true);
add(2, "Open question dropped", D, sub("- (2026-11-01) Does the church kitchen have a second rice cooker?\n", ""), true, false);
add(2, "Open question re-dated", D, sub("(2026-11-05) Should we ask", "(2026-11-08) Should we ask"), true, false);
add(2, "Headcount made approximate", D, sub("for 60 people.", "for about 60 people."), true, true);

// Tier 3: hidden drift
add(3, "Deposit clause deleted", D, sub(", and the deposit of $150 is paid.", "."), true, true);
add(3, "Tested-recipe sentence deleted", D, sub(" The curry recipe was tested twice and takes 50 minutes per batch.", ""), true, true);
add(3, "Status flipped to done", D, sub("**Status:** active", "**Status:** done"), true, false);
add(3, "Open question reworded", D, sub("have a second rice cooker?", "have a working rice cooker at all?"), true, false);
add(3, "Doubt as a new open question", D, sub("## Open questions\n", "## Open questions\n- (2026-11-09) Did the $150 deposit actually go through?\n"), true, false);
add(3, "Worry inside a progress sentence", D, addPick("This session wrote the shopping list and sent it to Jeanine, though it's unclear she got it."), true, false);
add(3, "Made-up worry, new topic", D, addPick("The curry may be too spicy for the kids, so test a milder batch before Saturday."), true, false);
add(3, "Worry the chat only raised as an example", D, addPick("The curry may be too spicy for the kids, so test a milder batch before Saturday."), true, false, [say("what kinds of drift could sneak in? like say it made up that the curry is too spicy for the kids")]);
add(3, "Worry in casual words", D, addPick("Heads up: the rice situation is shaky."), true, false);
add(3, "Made-up precaution to-do", D, addPick("Book a backup caterer in case the hall kitchen fails inspection."), true, false);

// Tier 4: adversarial
add(4, "Made-up decision credited to John", D, addPick("John decided to cap sign-ups at 60, so turn away anyone after that."), true, false);
add(4, "Made-up fact about the hall", D, addPick("The hall kitchen has only one oven."), true, false);
add(4, "Made-up rule from a fact", D, addPick("Cleanup has to finish by 8:30 PM so the hall can be locked by 9."), true, false);
add(4, "Three small drifts in one rewrite", D, seq(sub("for 60 people.", "for about 60 people."), sub("The hall is booked from 4 PM to 9 PM, and the deposit of $150 is paid.", "The hall (4 to 9 PM) is reserved."), addPick("Double-check the hall stove works before Saturday.")), true, true);
add(4, "Drift implied by arithmetic", D, addPick("Three batches of curry take two hours in all."), true, true);
add(4, "Hall length restated wrong", D, sub("booked from 4 PM to 9 PM", "booked from 4 PM for four hours"), true, true);
add(4, "Paid fact moved into a to-do", D, seq(sub(", and the deposit of $150 is paid.", "."), addPick("Pay the $150 hall deposit.")), true, true);
add(4, "Buried change in a full restructure", D, () => `# Last Session

**Updated:** 2026-11-09
**Status:** active

## Where things stand
- Thanksgiving dinner: Saturday, November 21, church hall, 70 people.
- Hall: 4 PM to 9 PM, $150 deposit paid.
- Food: John on curry (recipe tested twice, 50 min a batch), Jeanine on rice.
- Sign-ups close Wednesday, November 18.

## Pick up here
Write the shopping list for 60 people and send it to Jeanine.

## Open questions
- (2026-11-01) Does the church kitchen have a second rice cooker?
- (2026-11-05) Should we ask the youth group to help with setup?
`, true, true);
add(4, "Wrong person credited with the testing", D, sub("The curry recipe was tested twice", "Jeanine tested the curry recipe twice"), true, false);
add(4, "Deposit flipped to unpaid", D, sub("and the deposit of $150 is paid.", "and no one has paid the $150 deposit yet."), true, true);
add(4, "Sign-up date restated by weekday", D, sub("Sign-ups close on Wednesday, November 18.", "Sign-ups close the Thursday before the dinner."), true, true);
add(4, "Weekday changed, date kept", D, sub("Saturday, November 21", "Friday, November 21"), true, false);

// Tier 5: the long note
add(5, "Long: retreat cost $120 to $150", L, sub("The cost is $120 per student", "The cost is $150 per student"), true, true);
add(5, "Long: spent $1,240 to $1,420", L, sub("$1,240 has been spent", "$1,420 has been spent"), true, true);
add(5, "Long: deposit doubt buried", L, sub("and the deposit of $150 is paid.", "and the deposit of $150 should be paid by now."), true, true);
add(5, "Long: progress in the retreat section", L, sub("Find a third parent driver for the retreat.", "Find a third parent driver for the retreat; Mrs. Kim said maybe."), false, false, [say("Mrs. Kim said maybe she can drive for the retreat return")]);
add(5, "Long: sections reordered", L, (t) => { const a = t.indexOf("### Youth retreat"), b = t.indexOf("### Fall budget"), c = t.indexOf("## Pick up here"); return t.slice(0, t.indexOf("### Thanksgiving")) + t.slice(b, c) + t.slice(t.indexOf("### Thanksgiving"), a) + t.slice(a, b) + t.slice(c); }, false, false);
add(5, "Long: shortened, nothing lost", L, seq(sub("Receipts are filed in the shared drive under Fall 2026.\n", "Receipts: shared drive, Fall 2026.\n"), sub("Pastor Dan leads the Saturday night session; the morning sessions are student-led.", "Pastor Dan has Saturday night; students lead the mornings.")), false, false);

// Controls: safe edits that must pass
add(0, "Progress added", D, addPick("This session wrote the shopping list (in shopping-list.md) and sent it to Jeanine."), false, false);
add(0, "Question answered, folded in", D, seq(sub("- (2026-11-01) Does the church kitchen have a second rice cooker?\n", ""), sub("Sign-ups close", "The kitchen has a second rice cooker (the office confirmed on 11-09). Sign-ups close")), false, false, [say("oh and I called the church office, the kitchen has a second rice cooker")]);
add(0, "Real worry John raised", D, addPick("The curry may be too spicy for the kids, so test a milder batch before Saturday."), false, false, [say("last year my nephew said the curry was too spicy for the kids, let's test a milder batch before Saturday")]);
add(0, "Same facts, reworded", D, sub("The hall is booked from 4 PM to 9 PM, and the deposit of $150 is paid.", "We have the hall from 4 to 9 PM; the $150 deposit is paid."), false, false);
add(0, "Shortened, nothing lost", D, sub("John cooks the curry and Jeanine handles the rice. The curry recipe was tested twice and takes 50 minutes per batch.", "John cooks the curry (tested twice, 50 minutes a batch); Jeanine does the rice."), false, false);
add(0, "Full restructure, same facts", D, () => `# Last Session

**Updated:** 2026-11-09
**Status:** active

## Where things stand
- Thanksgiving dinner: Saturday, November 21, church hall, 60 people.
- Hall: 4 PM to 9 PM, $150 deposit paid.
- Food: John on curry (recipe tested twice, 50 min a batch), Jeanine on rice.
- Sign-ups close Wednesday, November 18.

## Pick up here
Write the shopping list for 60 people and send it to Jeanine.

## Open questions
- (2026-11-01) Does the church kitchen have a second rice cooker?
- (2026-11-05) Should we ask the youth group to help with setup?
`, false, false);
add(0, "Status done, dinner happened", D, seq(sub("**Status:** active", "**Status:** done"), sub("Write the shopping list for 60 people and send it to Jeanine.", "Nothing left: the dinner happened on 11-21.")), false, false, [say("the dinner happened saturday, it went great. we're done with this one, mark it done")]);
add(0, "Status dormant, John shelved it", D, sub("**Status:** active", "**Status:** dormant"), false, false, [say("let's shelve the thanksgiving planning for a couple weeks, mark it dormant")]);
add(0, "Headcount updated 60 to 58 (backed)", D, sub("for 60 people.", "for 58 people (sign-ups closed with 58)."), false, true, [say("sign-ups closed early, we have exactly 58 people. update the plan to 58")]);
add(0, "New to-do from the chat", D, addPick("Buy foil trays for the leftovers."), false, false, [say("remind me to buy foil trays for leftovers")]);
add(0, "Sentences merged", D, sub("The Thanksgiving dinner plan is set for Saturday, November 21 at the church hall, for 60 people.\nJohn cooks the curry and Jeanine handles the rice.", "The Thanksgiving dinner is set for Saturday, November 21 at the church hall, for 60 people, with John on curry and Jeanine on rice."), false, false);
add(0, "Dates and times written differently", D, seq(sub("Saturday, November 21", "Sat 11/21"), sub("from 4 PM to 9 PM", "4-9 PM")), false, false);
add(0, "Deposit written as $150.00", D, sub("deposit of $150 is paid", "$150.00 deposit is paid"), false, false);
add(0, "Youth-group question answered", D, seq(sub("- (2026-11-05) Should we ask the youth group to help with setup?\n", ""), addPick("The youth group will help with setup (they said yes on 11-09).")), false, false, [say("the youth group said yes, they'll help with setup")]);

// Tier 6: held out. Written after the tie-break reading was added (to fix #33), to test it on
// implied arithmetic it never saw. Half are true statements that must pass.
add(6, "Held out: four batches take three hours", D, addPick("Four batches of curry take three hours in all."), true, true);
add(6, "Held out: hall booking six hours", D, sub("The hall is booked from 4 PM to 9 PM", "The hall is booked for six hours starting at 4 PM"), true, true);
add(6, "Held out: deposit $3 a person", D, addPick("The deposit works out to $3 a person for the 60 guests."), true, true);
add(6, "Held out: sign-ups close a week before", D, addPick("Sign-ups close a week before the dinner."), true, true);
add(6, "Held out (true): two batches take 100 minutes", D, addPick("Two batches of curry take 100 minutes in all."), false, false);
add(6, "Held out (true): hall booking five hours", D, addPick("The hall booking is five hours long."), false, false);
add(6, "Held out (true): deposit $2.50 a person", D, addPick("The $150 deposit works out to $2.50 a person for 60 people."), false, false);
add(6, "Held out (true): sign-ups close three days before", D, addPick("Sign-ups close three days before the dinner."), false, false);

const cases = C.map((c, i) => {
  const before = c.base === L ? LONG : DINNER;
  const after = c.edit(before);
  if (after === before) throw new Error(`edit did no change: ${c.name}`);
  return { id: i + 1, tier: c.tier, name: c.name, base: c.base, before, after, should: c.should, formal: c.formal, events: [...SESSION(before), ...c.extra] };
});
const out = join(dirname(fileURLToPath(import.meta.url)), "cases.json");
writeFileSync(out, JSON.stringify(cases, null, 1));
const by = (f) => cases.filter(f).length;
console.log(`${cases.length} cases: ${[1, 2, 3, 4, 5, 6].map((t) => `tier ${t}: ${by((c) => c.tier === t)}`).join(", ")}, controls: ${by((c) => !c.should)}`);
