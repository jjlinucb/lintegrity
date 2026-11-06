# Lintegrity

**Keep an AI's memory from drifting, and prove it.**

AI agents in long chats keep notes for themselves: summaries, memory files, handoffs to a fresh chat. Each note is written from the last one, never from the original. Over many rounds, small changes pile up. A fact falls out. A "what if" loses its "if". A guess gets repeated until it reads like a fact.

Lintegrity checks every note before the next chat reads it.

- **Numbers are proved.** Claude translates each claim into logic twice, in two different ways. The [Z3](https://github.com/Z3Prover/z3) solver checks that the two translations agree, then accepts a claim only if it is true in every case the source facts allow. When a claim is wrong, Z3 gives a case where it fails.
- **Dropped facts are caught.** A must-keep list names the facts every note has to carry. Z3 checks that the note still implies each one.
- **New claims are flagged.** For anything that can't be written as a rule, a second, different model checks whether the last trusted note said it.
- **The pipe is proved.** A model of the app's flow shows that no made-up claim can reach the screen or the memory without passing the check, on any turn, even if the AI makes things up every time. The proof is by induction, so it covers every turn, not just a sample.

A note that fails gets one try at a fix, with the problems named. If it still fails, it is refused, and the last checked note carries on.

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

Drift varies a lot from run to run, so one run proves little about how often it happens. The next step is many runs per setting, with false alarms counted alongside catches.

## What it can't do

- **It can't make a model stop guessing.** It only stops guesses from being saved or shown.
- **Z3 only proves what can be written as rules:** money, counts, dates, schedules. Plans, reasons and wording go to the second model, which is a judgement, not a proof.
- **The facts and must-keep list are written by hand for now.**

## Run it

```bash
pip install -r requirements.txt
python3 lintegrity/claim_and_pipe_check.py      # pipe proof + one-answer check (about 40 s)
python3 lintegrity/handoff_drift.py 20          # plain vs checked handoffs (about 30 min)
```

The claim checks call the [Claude Code](https://claude.com/claude-code) CLI (`claude -p`), so you need it installed and signed in. Add `--no-claude` to the first script to reuse saved translations.

## Status

This is an early prototype, started November 2026. Next: turn the checker into a small library an app calls before it saves memory, and try it on dates and schedules.

MIT licensed.
