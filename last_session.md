# Last Session

**Updated:** 2026-11-06
**Status:** active

## Where things stand
Lintegrity checks an AI's handoff notes before the next chat reads them. Z3 proves the numbers, a must-keep list (with background rules) catches dropped facts, and Sonnet 5.5 reads the note's own sentences against the original and the last note, flagging changes in meaning only. A pipe proof shows that no made-up claim reaches the screen or memory.

The afternoon batch of 2026-11-06 used the fixed check: without it, the note drifted in 10 of 10 runs; with it, the note ended clean in 10 of 10 (40 fixes, 0 refusals, no clear false alarms in 115 flags). The drift came in four kinds: an "if" added to a promise, a made-up weekend, a fact turned into a doubt, and a wrong number. The morning batch's false alarms (43 of 52) and its blindness to drift with no number in it are both fixed.

All calls are lean (`LEAN` flags in `handoff_drift.py`: about 1,000 tokens of setup instead of 48,000), so a batch costs roughly 1/15 of the morning's. Results are in local `results/` (afternoon) and `results-2026-11-06-v2/` (morning); both are ignored by git. Run `lintegrity/selftest.py` before any batch. Z3 runs in processes, not threads (it isn't thread-safe). To set up: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then run with `PYTHON=.venv/bin/python`.

## Pick up here
Make the check notice when the same drift keeps coming back (the weekend question returned 11 times in a row in two runs), and report "the source note is unclear here" instead of fixing it every round. Then test on a longer, messier note (dates, people, several projects), and turn the checker into a small library: `check(note, facts, must_keep, last_note)`.

Use cases are listed in `USE-CASES.md`. The first candidates in John's own apps are kept outside this public repo, in the vault ideas list (item 14).

## Open questions
- (2026-11-05) Which real app gets Lintegrity first: an assistant's morning summary and memory, or an AI spending cap? Waiting, by choice (2026-11-06).
