# Last Session

**Updated:** 2026-11-05
**Status:** active

## Where things stand
Started 2026-11-05 from a prototype in an ideas chat. Two checks work: the pipe proof (Z3 induction; with planted bugs it finds 4 leak paths, and the fixed version is proved) and the handoff drift test. On 20 rewrites of a budget handoff, the plain chain dropped a key fact at rewrite 1 and turned a made-up worry into its headline by rewrite 20, while the checked chain stayed clean. Version 2 adds the second-model "was this in the last note?" check and lets proved numbers inside a reason through.

## Pick up here
1. Read the version 2 20-rewrite results and put them in the README.
2. Make the checker a small library: `check(note, facts, must_keep, last_note)` returning a verdict per claim, so any app can call it before saving memory.
3. Try it on a second kind of facts (dates and schedules) so it isn't only money.

## Open questions
- 2026-11-05: which real app gets it first? Candidates: an assistant's morning summary and memory, or an AI spending cap. Not decided.
