# Lintegrity

Proof-checked AI memory. An AI that hands notes to itself across long chats (summaries, memory, handoffs) slowly drifts: facts drop out, guesses turn into facts. Lintegrity checks every note before the next chat reads it. Z3 proves each number against the source facts, a must-keep list catches what was dropped, and a second model flags anything the last trusted note never said.

## Read first
1. `last_session.md`: where work stopped and what's next.
2. `README.md`: what it does and the results so far.
3. `lintegrity/handoff_drift.py`: the drift test (plain chain vs checked chain).
4. `lintegrity/claim_and_pipe_check.py`: the pipe proof (no made-up claim reaches the screen or memory on any turn) and the single-answer claim check.

## Rules
- **This repo is public.** No personal names, private app names, emails, keys or paths from anyone's machine. Example data stays made up.
- Run with `pip install -r requirements.txt`. The drift test calls the `claude` CLI, so it needs Claude Code signed in. Results JSON files stay out of git.
- A check counts only once it has been shown to fail on a planted bug. Plant the bug, show red, fix it, show green.
- Say plainly what is proved and what isn't. Z3 proves claims that can be written as rules (money, dates, counts). Everything else is a second model's judgement, and the README must say so.
- Commit as `johnlinsv@gmail.com`.
