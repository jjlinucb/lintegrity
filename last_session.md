# Last Session

**Updated:** 2026-11-06
**Status:** active

## Where things stand
Lintegrity checks an AI's handoff notes before the next chat reads them. Z3 proves the numbers, a must-keep list catches dropped facts, and a second model (Sonnet 5.5) flags new claims. A pipe proof shows that no made-up claim reaches the screen or memory. The 10-run batch on 2026-11-06 (`./run_batch.sh 10 20`, results in the README and local `results/`) gave:
- final notes clean 10/10 in both chains;
- real drift in 1 run (a promise turned into an "if"), and it was caught;
- 43 of 52 flags were false alarms: 24 "dropped" flags where the note relied on the unstated rule that the cap applies to every day, and 19 "new" flags on plain rewording.

Chains run as separate processes, because Z3's Python API isn't thread-safe; calling it from two threads crashed Python twice. To set up a fresh virtual environment, run `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `PYTHON=.venv/bin/python ./run_batch.sh 10 20`.

## Pick up here
Planned for 2026-11-06 at 3 PM, once credits refresh. First make two fixes in `lintegrity/handoff_drift.py`, then rerun 10:
1. Give the must-keep check background rules that hold everywhere: each day <= cap, plus the definitions of spent_now, left_now and left_end.
2. Reword the JUDGE prompt so it flags new meaning only, never rewording, restated next steps or facts that were already in the original note.
Then move `results/` to `results-2026-11-06/` and run the batch again. Without crashes it takes about 1 hour. Target: fewer than 1 in 5 flags false, with run 7's kind of drift still caught. After that:
- a harder test: a longer, messier note (dates, people, several projects);
- turn the checker into a small library, `check(note, facts, must_keep, last_note)`;
- try it on a second kind of facts, dates and schedules.

**Before the rerun (added 2026-11-06): find out why the batch used so many tokens.** Guess to check first: each round makes 4 to 8 `claude -p` calls (a rewrite, two Opus translations and a Sonnet judge, and twice that when a fix round runs). That comes to roughly 1,000 to 1,600 calls for 10 runs. Each call starts a full Claude Code session, which loads the system prompt, every CLAUDE.md up the folder tree, hooks and the skill list, likely tens of thousands of tokens before the short task. To confirm, run one call with `--output-format json` and read its usage. Options: call the API directly with only the task prompt; use `claude -p` with a bare system prompt and no setting sources; cache the shared part of the prompt; or cut the translations to one per round and add the second only when Z3 finds a problem.

## Open questions
- (2026-11-05) Which real app gets Lintegrity first: an assistant's morning summary and memory, or an AI spending cap?
