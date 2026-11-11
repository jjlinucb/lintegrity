# Lintegrity

**Keep an AI's memory from drifting, and prove it.**

AI agents in long chats keep notes for themselves: summaries, memory files, handoffs to a fresh chat. Each note is written from the last one, never from the original. Over many rounds, small changes pile up. A fact falls out. A "what if" loses its "if". A guess gets repeated until it reads like a fact.

Lintegrity checks every note before the next chat reads it.

- **Numbers are proved.** Claude translates each claim into logic twice, in two different ways. The [Z3](https://github.com/Z3Prover/z3) solver checks that the two translations agree, then accepts a claim only if it is true in every case the source facts allow. When a claim is wrong, Z3 gives a case where it fails.
- **Dropped facts are caught.** A must-keep list names the facts every note has to carry. Z3 checks that the note still implies each one.
- **New claims are flagged.** For anything that can't be written as a rule, a second, different model checks whether the last trusted note said it.
- **The pipe is proved.** A model of the app's flow shows that no made-up claim can reach the screen or the memory without passing the check, on any turn, even if the AI makes things up every time. The proof is by induction, so it covers every turn, not just a sample.

A note that fails gets one try at a fix, with the problems named. If it still fails, it is refused, and the last checked note carries on.

## Evidence (November 10)

A planned test of the whole idea, with 68 cases in six tiers, rewrite chains, and a proof. The full write-up is in [evidence/EVIDENCE.md](evidence/EVIDENCE.md).

- **Both layers together** caught 47 of 47 planted drifts, with 0 false alarms on 21 safe edits.
- **Z3 alone** caught 31 of 31 drifts that can be written as logic, each with a counterexample, and never flagged a true note. That includes 4 held-out arithmetic drifts that the judgement model missed every time.
- **Proof by induction:** the gate never lets a flagged note become the trusted note, on any turn. The same proof shows how a fail-open design (accept on a checker error, or on a second write) leaks.
- **Rewrite chains:** Haiku 5.5 rewrote a long note 10 times. Without the check, it lost a must-keep fact in 2 of 5 chains. With the check, it lost none, after 21 fixes and 0 refusals. Sonnet 5.5 didn't drift at all on the shorter note, and the check raised 0 false alarms across those 50 rewrites.

## What it found

**One answer.** Claude Opus 5.5 answered a budget question, and all 8 of its claims were proved. A drifted summary planted for the test was caught twice: "Tuesday went over the cap" is false, and "at least $9.85 left after Thursday" is wrong if Thursday costs $0.50.

**The pipe.** A version with three planted bugs leaked in 4 ways. It showed a made-up answer when the checker errored, saved the answer to memory before checking it, and wrote the memory summary back unchecked. The fixed version is proved: there is no leak path.

**Twenty handoffs.** Claude Opus 5.5 rewrote a budget handoff note 20 times, two thirds shorter each time, seeing only the last note.

| | Plain chain | Checked chain |
|---|---|---|
| Key fact "at least $24.55 left after Friday" | Dropped at rewrite 1, never came back | Kept |
| Made-up worry "the refund may be counted twice" | Appeared at rewrite 3; by rewrite 20 it was the headline, "Check first", with a made-up $30.55 | Never got in |
| Numbers in the final note | Right, but framed around the made-up worry | All proved |

The drift wasn't wrong arithmetic. It was something lost, and something new.

**A second 20-handoff run** used version 2 of the check. That version proves the number inside a reason ("Wednesday was $0 because the API was down") and asks a second model whether each claim was in the last trusted note.

- **Plain chain:** it drifted less. It made up no worry this time, but the guaranteed floor softened from "at least $24.55 will be left" to "even at the cap, $24.55 would be left". It stayed that way from rewrite 6 to the end.
- **Checked chain:** it fixed 6 rewrites after one nudge and refused 1. Its final note passed the audit against the original note.
- **False alarms:** the second model flagged an unchanged line twice, which cost one refusal. The must-keep check counted the softened floor as dropped, because the note no longer said Friday is under the cap.

Drift varies a lot from run to run, so one run proves little about how often it happens.

**Ten runs, first version of the check** (November 6, morning; Opus 5.5 writing and translating, Sonnet 5.5 judging; `./run_batch.sh 10 20`, scored by `lintegrity/score_batch.py`):

- **Final notes:** clean in all 10 runs, in both chains. On a short note full of numbers, Opus 5.5 wobbles mid-chain in most runs but corrects itself.
- **Real drift:** one run. A firm promise ("at least $24.55 will be left") became a condition ("if Friday is the last day with spend") from rewrite 1 to 18. The check flagged it every round.
- **False alarms:** 43 of the 52 flags, sorted by hand. Both causes were fixed for the afternoon runs:
  - **24 "dropped" flags on a fact that was still there.** The note didn't say the cap applies to Friday, and the check assumed nothing.
  - **19 "new" flags on rewording.** The second model treated a reworded next step as new.

**Ten runs with the fixed check** (November 6, afternoon). This version gives the must-keep check the background rules, so a cap binds every day. The second model reads the note's own sentences against both the original and the last note, and flags only changes in meaning. Every call runs lean. `lintegrity/selftest.py` passed all 4 known cases before the batch.

- **Without the check:** the note drifted in all 10 runs. Across the runs, four kinds of drift showed up:
  - a firm promise grew an "if" ("at least $24.55, if Friday is the last day");
  - a weekend got made up ("$8.55 left after Sunday");
  - a sure fact became a doubt ("possible $2 refund, not yet verified");
  - in 2 runs a number went wrong ("$30.55 left", when $32.55 is left).
- **With the check:** the note ended clean in all 10 runs, after 40 fixes and 0 refusals.
- **Flags:** 115 in all. Reading them by hand, I found no clear false alarms; each one was a real change in meaning. Many are the same drift coming back round after round.

The morning's "10 of 10 clean" was the old check missing drift that had no number in it.

**Drift that keeps coming back points at a gap in the source.** The original note says "at the end of the week" but counts only Friday, so whether the weekend counts is open. Claude raised the weekend in every run, and in two runs it raised it 11 times in a row. Next: when the same drift returns again and again, report "the source note is unclear here" instead of fixing it every round.

**Cost:** a plain `claude -p` call loads the whole Claude Code setup, about 48,000 tokens, before a short task: $0.19 per call at API prices. Lean flags cut that to about 1,000 tokens, or $0.008 per call. Together with fewer calls (one reading of each note, a second only when the first flags something, and the plain chain checked every 5th rewrite), this batch cost roughly 1/15 of the morning's.

**Next:** report a gap in the source instead of fixing the same drift every round; test on longer, messier notes; and turn the checker into a small library an app calls before it saves memory.

## In daily use: checking an AI's own handoff notes

The same check runs as a Claude Code hook on every write of a project's `last_session.md`, the note each chat leaves for the next. It uses [Jev](https://docs.typesafe.ai), a fast model that returns probabilities instead of text. One batched request asks whether each changed sentence alters what the last trusted note said, and whether an open question that vanished was settled. Code catches a question re-dated to look new. New progress passes. A flagged note goes back to Claude once, with the problems named.

- **Speed and cost:** about 0.5 s and 900 input tokens per check, roughly $0.00004. The `claude -p` version took about 20 s and $0.05.
- **Accuracy:** on 31 real wrap-ups from four projects it fired twice, and both were real changes in fact worth a second look. It caught 6 of 6 planted drifts: a fact made a doubt, an added condition, two made-up worries, a dropped open question, and it let legit progress pass.
- **Made-up concerns:** comparing notes alone can't tell a made-up worry about a new topic ("the curry may be too spicy for the kids") from a real one. So the hook also sends the end of the chat's own transcript and asks whether a new worry, risk or precaution was raised anywhere in the chat. Planted ones are caught (0.82), the same worry passes when the user raised it in the chat, and none of 26 real wrap-ups fired (highest 0.22). Asking whether *every* new sentence was backed by the chat fired on 7 of those 26, because the record is cut at the start and real work happened earlier, so the check is held to concerns only. With the record, a check is about 6,000 tokens and 0.3 s, roughly $0.00025.
- **Sneakier drift:** a second planted set went after what the check didn't look at. Version one caught 9 of 18: deleted facts, a status flipped to "done", reworded or newly doubting open questions, and made-up decisions or facts with no worry words all got through. Each now has its own question. For a made-up decision or fact, code also searches the whole chat for the claim's names and numbers, because Jev reads only the end of the chat and real work from earlier would otherwise look made up. Now 20 of 20 are right. On 37 real wrap-ups it fires on 11 (4 before), and about half of those new flags are worth a second look.
- **Not a proof:** no Z3 here. Handoff notes are mostly words, so this half of Lintegrity is the meaning check.

## What it can't do

- **It can't make a model stop guessing.** It only stops guesses from being saved or shown.
- **Z3 only proves what can be written as rules:** money, counts, dates, schedules. Plans, reasons and wording go to the second model, which is a judgement, not a proof.
- **The facts and must-keep list are written by hand for now.**

## Run it

```bash
pip install -r requirements.txt
python3 lintegrity/claim_and_pipe_check.py      # pipe proof + one-answer check (about 40 s)
python3 lintegrity/selftest.py                  # 4 known cases, about 1.5 min
python3 lintegrity/handoff_drift.py 20          # one plain vs checked run (about 15 min)
./run_batch.sh 10 20                            # 10 runs, two at a time, then scored (about 75 min)
```

The claim checks call the [Claude Code](https://claude.com/claude-code) CLI (`claude -p`), so you need it installed and signed in. Add `--no-claude` to the first script to reuse saved translations.

## Status

This is an early prototype, started November 2026.

Where else it fits: [USE-CASES.md](USE-CASES.md).

MIT licensed.
