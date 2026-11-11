# Evidence: does Lintegrity keep an AI's handoff notes from drifting?

November 10, 2026. The plan was written before the tests ran: [TEST-PLAN.md](TEST-PLAN.md). Everything below can be re-run from this folder.

## The short answer

- **Proved:** a drifted note can never become the note the next chat trusts, as long as the checker flags it. Z3 proves this by induction over every turn ([handoff_pipe_proof.py](../lintegrity/handoff_pipe_proof.py)).
- **Proved, for each note:** when a note contradicts a trusted fact, or stops guaranteeing one, Z3 shows it with a counterexample. This works for anything the facts can express as logic: counts, money, dates, times, owners, durations, per-person amounts. It held on every such drift in the suite (31 of 31), including 4 held-out ones written after the last change to the checker.
- **In real AI rewrite chains:** Haiku 5.5, rewriting a long note 10 times with no check, lost a must-keep fact in 2 of 5 chains. With the check, it lost none (0 of 5), after 21 fixes and 0 refusals.
- **Measured, not proved:** the judgement layer (Jev) covers what logic can't express, like made-up worries, made-up decisions, status changes and open questions. Both layers together caught 47 of 47 planted drifts, with 0 false alarms on 21 safe edits (4 of them true arithmetic statements).
- **Two honest limits:**
  - **The proof is only as good as the translation into logic.** One case slipped through until a third reading was added to break ties between the two translations.
  - **The proof covers the design, not the checker's accuracy.** It assumes the checker flags every drifted note it judges; section 1 measures how close it comes.

## 1. The test suite: 68 cases in 6 tiers

Each case starts from a trusted note: a Thanksgiving dinner plan with 11 must-keep facts, or a 40-line note on three projects with 16. Each case rewrites that note and includes a fake record of the chat that "wrote" it. The safe edits include changes the chat backs up, such as the user saying 58 people signed up.

- **Z3** translates the note into logic twice and flags only what both translations show. On a disagreement, a third reading decides.
- **Jev** is the session-check hook, run exactly as Claude Code runs it, chat record included.
- **Both:** a Z3 finding stands unless the chat record shows the fact really changed (the 60 to 58 update). A Jev flag always stands.

| Tier | Drifts | Z3 alone | Jev alone | Both |
|---|---|---|---|---|
| 1 Easy: one value changed | 8 | 8/8 | 8/8 | 8/8 |
| 2 Medium: doubt, "if", vaguer, end time dropped, questions | 10 | 7/10 | 10/10 | 10/10 |
| 3 Hard: deleted facts, status flip, worries on new topics | 10 | 3/10 | 10/10 | 10/10 |
| 4 Adversarial: made-up decisions and rules, compound, arithmetic | 12 | 7/12 | 10/12 | 12/12 |
| 5 Long note: drift buried in 40 lines | 3 | 3/3 | 3/3 | 3/3 |
| 6 Held-out arithmetic | 4 | 4/4 | 0/4 | 4/4 |
| **All drifts** | **47** | 32/47 | 41/47 | **47/47** |
| Drifts Z3 can express | 31 | **31/31** | 25/31 | 31/31 |
| **False alarms on safe edits** | **21** | **0** | **0** | **0** |

**What the table shows.** Each layer catches what the other can't:

- **Jev misses all 6 drifts that need arithmetic:**
  - "three batches take two hours" (it's 150 minutes);
  - "booked from 4 PM for four hours" (the hall is booked until 9 PM);
  - "the deposit works out to $3 a person" ($150 for 60 people is $2.50);
  - "sign-ups close a week before the dinner" (it's 3 days);
  - two more like them.
- **Z3 misses everything outside the facts:**
  - a made-up worry about the curry being too spicy;
  - "John decided to cap sign-ups at 60";
  - a status flipped to "done";
  - a dropped open question.

Together they cover both.

**Z3 never raised a false alarm.** That includes 4 held-out arithmetic statements that are true ("the $150 deposit works out to $2.50 a person"), which it proved and let through. Its only flag on a safe edit was the backed change from 60 to 58 people, which is correct: the note does contradict the old facts. The chat record then cleared it (0.86), and no planted drift was cleared that way.

**The fix made after looking.** The first run missed one case, #33: "three batches of curry take two hours". One translation wrote it as logic and the other didn't, and a flag needs agreement. I added a third reading that is used only when the first two disagree. That fix was made after seeing the miss, so on its own #33 proves nothing. Tier 6 was written afterwards to test the fix fairly: 4 new arithmetic drifts and 4 true statements. Z3 got all 8 right, and the third reading decided 3 of them.

## 2. The proof: no unchecked note becomes trusted

[handoff_pipe_proof.py](../lintegrity/handoff_pipe_proof.py) models one turn of the handoff:
- the AI writes a note that may drift in any way, on every turn;
- the checker judges it;
- the note is accepted, fixed or refused;
- the checker itself may error.

The invariant is "the trusted note is clean". Z3 checks whether any turn can break it.

| Design | Result |
|---|---|
| Lintegrity's gate: one fix, then refuse; a checker error counts as a flag | **Proved.** No path lets a drifted note become trusted, on any turn. |
| The Claude Code hook before November 10 | **Leak, 3 ways in:** Jev errors or times out (the hook failed open), Claude writes the same note a second time (it never blocked twice in a row), or both. |
| The Claude Code hook since November 10, rebuilt as the gate: it checks before the write lands, denies once, then refuses, and treats an error as a flag | **Proved**, except for one way in: the user saying "accept the note" in the chat. That's the user's own call, not drift. |

The proof's one assumption is that the checker flags every drifted note it judges. Section 1 measures how close the real checker comes. So the guarantee is: **every drift the checker can see is kept out of the next chat, on every turn, with no exceptions in the plumbing.**

## 3. Real AI rewrite chains

The setup: an AI rewrites the note again and again, each time about two thirds shorter, seeing only the last note. In the plain chains every rewrite passes straight on. In the checked chains, both layers check every rewrite; a flagged rewrite gets one fix, then is refused.

**Sonnet 5.5, dinner note, 5 chains per arm, 10 rewrites each:**

- **Plain:** no drift at all. Every chain kept all 11 facts. The note shrank to about 460 characters and stopped changing. A final note, read by hand, is fully correct.
- **Checked:** 50 of 50 rewrites passed on the first try, so the check raised **0 false alarms on 50 real AI rewrites.**
- **What this shows:** on a short, dense note, Sonnet 5.5 doesn't drift, so this run can't show prevention. It shows the check is quiet when nothing is wrong.

**Haiku 5.5, long three-project note (16 must-keep facts), 5 chains per arm, 10 rewrites each:**

| | Plain | Checked |
|---|---|---|
| Lost a must-keep fact (proved by Z3) | **2 of 5 chains** ("curry tested twice" dropped at rewrite 5 and at rewrite 7, and never came back) | **0 of 5** |
| Final note flagged against the original by either layer | **4 of 5** | **1 of 5** |
| Rewrites passed / fixed / refused | n/a | 29 / 21 / 0 |

- **What the check caught:** the 21 fixes were mostly detail dropped without a word (20 Jev flags, such as "Pastor Dan leads Saturday night" or "the packing list went out November 3"). The other 4 were Z3 proofs that a must-keep fact was no longer guaranteed. Each Z3 finding came with a counterexample, for example a world the note allows where the curry was tested 3 times. Every fix was accepted on the second try; nothing had to be refused.
- **What got past it:** in one checked chain, "the packing list went out to parents on November 3" was dropped at rewrite 7. The fix was accepted because Jev compares each rewrite with the *last trusted* note, and the loss slipped by one step at a time. It isn't a must-keep fact, so Z3 never saw it. This is the judgement layer's limit in practice. Comparing each rewrite with the original note as well would close it.
- **A gap found by reading the notes:** both arms dropped the dates on open questions ("(2026-11-01) Does the church kitchen…" became "Second rice cooker at the church kitchen?"). The hook flags a re-dated question but not a dropped date, so the next chat loses when each question was raised.

**From November 6 (budget note, Opus 5.5, 20 rewrites, 10 runs each):** without the check, the note drifted in 10 of 10 runs. With the check, it ended clean in 10 of 10, after 40 fixes and 0 refusals. The drift seen: a promise grew an "if", a weekend was made up, a fact became a doubt, and a number went wrong.

## 4. Real wrap-ups: the cost in false alarms

Real notes have no hand-written fact list, so only the judgement layer runs on them. On 37 real wrap-ups from the author's own chats (counts only; no note text is published here), the hook fired on 11.

- **4 fired before this week's checks:** dropped open questions that were hard-wrapped across lines.
- **7 are new, from the deleted-fact and made-up-claim checks.** Read by hand:
  - **about 3 are worth a second look:** a list of unresolved risks dropped twice, and a set of decisions cut;
  - **4 are false alarms:** trimmed detail about finished work, work done in another chat, and a flagged line being removed.

A false alarm costs one rewrite. Writing a fact list for real projects, so Z3 can run on them too, is the main open step.

## What this does and doesn't prove

- **It does:**
  - drift that Z3 can express is caught with a proof and a counterexample, never by a guess, and no safe edit was flagged (0 of 21);
  - the gate's plumbing provably lets no flagged note through.
- **It doesn't:**
  - prove the translation into logic is right. Two independent readings plus a tie-break are the safeguard; one of 47 drifts needed the tie-break.
  - make the judgement layer a proof. Jev is a strong measured check (41 of 47 alone, 0 false alarms here), not a guarantee.
  - cover real projects formally yet, since that needs a fact list per project.
  - cover a crash in the hook itself (Node missing, a bug). That lets the write through, so Claude never gets stuck.

## Cost

- **Jev:** 66 checks, 134,682 input tokens (about $0.006 in all), median 144 ms each.
- **Z3 layer:** two Sonnet 5.5 translations per note, about $0.02, plus under a second of Z3.
- **Rewrite chains:** about 500 Sonnet and Haiku calls.

## Re-run it

```bash
node evidence/cases.mjs                 # writes cases.json (68 cases)
.venv/bin/python evidence/run_z3.py     # formal layer (translations cached in evidence/)
node evidence/run_jev.mjs               # judgement layer: needs the session-check hook and a TypeSafe key
node evidence/combine.mjs               # both layers, the table above
.venv/bin/python lintegrity/handoff_pipe_proof.py
.venv/bin/python evidence/chains.py 10 5   # LINTEGRITY_BASE=long LINTEGRITY_WRITER=claude-haiku-5-5 for the long run
```
