# Last Session

**Updated:** 2026-11-10
**Status:** active

## Where things stand
Lintegrity checks an AI's handoff notes before the next chat reads them. Z3 proves the numbers, a must-keep list (with background rules) catches dropped facts, and Sonnet 5.5 reads the note's own sentences against the original and the last note, flagging changes in meaning only. A pipe proof shows that no made-up claim reaches the screen or memory.

The afternoon batch of 2026-11-06 used the fixed check: without it, the note drifted in 10 of 10 runs; with it, the note ended clean in 10 of 10 (40 fixes, 0 refusals, no clear false alarms in 115 flags). The drift came in four kinds: an "if" added to a promise, a made-up weekend, a fact turned into a doubt, and a wrong number. The morning batch's false alarms (43 of 52) and its blindness to drift with no number in it are both fixed.

All calls are lean (`LEAN` flags in `handoff_drift.py`: about 1,000 tokens of setup instead of 48,000), so a batch costs roughly 1/15 of the morning's. Results are in local `results/` (afternoon) and `results-2026-11-06-v2/` (morning); both are ignored by git. Run `lintegrity/selftest.py` before any batch. Z3 runs in processes, not threads (it isn't thread-safe). To set up: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then run with `PYTHON=.venv/bin/python`.

A Jev version of the meaning check now runs on every last_session.md write, as a private Claude Code hook (`session-check` in the john-jev-lab repo): about 0.5 s and $0.00004 per check; 2 of 31 real wrap-ups fired, 6 of 6 planted drifts caught. The README has a public summary.

On 2026-11-10 the hook learned to read the chat's own transcript, to catch a made-up worry about a topic the last note never covered (the one blind spot in planted testing). It asks only about worries, risks and precautions: asking whether every new sentence was backed fired on 7 of 26 real wrap-ups. Now 16 of 16 planted cases are right and 0 of 26 real wrap-ups fire on it. Then a sneakier planted set (deleted facts, status flips, open-question tricks, made-up decisions with no worry words) broke it at 9 of 18; each hole now has its own check, and it's 20 of 20, with 11 of 37 real wrap-ups firing (4 before, about half the new ones worth a look). Details in TYPESAFE `hooks/session-check/runs.md`.

On 2026-11-10 a planned evidence run (`evidence/`, write-up in `evidence/EVIDENCE.md`) put both layers through 68 cases in six tiers, rewrite chains, and a new handoff pipe proof. Both layers: 47 of 47 drifts caught, 0 false alarms on 21 safe edits. Z3 caught 31 of 31 formal drifts, with no false alarm. Haiku chains lost a must-keep fact in 2 of 5 plain chains and 0 of 5 checked. The new `lintegrity/note_check.py` is the general Z3 fact check (two translations plus a tie-break reading).

## Pick up here
Gaps the evidence run found:
1. Done 2026-11-10: the session-check hook was rebuilt as the gate (PreToolUse; deny once, then refuse; an error counts as a flag; the user overrides with "accept the note"). `handoff_pipe_proof.py` proves it leak-free apart from that override.
2. Chains drop the dates on open questions; the hook flags re-dated questions but not dropped dates.
3. Jev compares each rewrite only with the last trusted note, so a detail can slip out one step at a time (the packing-list case). Also compare with the original, or the note from N rounds back.

Earlier plan, still open: Make the check notice when the same drift keeps coming back (the weekend question returned 11 times in a row in two runs), and report "the source note is unclear here" instead of fixing it every round. Then test on a longer, messier note (dates, people, several projects), and turn the checker into a small library: `check(note, facts, must_keep, last_note)`.

Use cases are listed in `USE-CASES.md`. The first candidates in John's own apps are kept outside this public repo, in the vault ideas list (item 14).

## Open questions
- (2026-11-05) Which real app gets Lintegrity first: an assistant's morning summary and memory, or an AI spending cap? Waiting, by choice (2026-11-06).
