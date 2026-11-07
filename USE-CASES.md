# Where Lintegrity fits

Lintegrity fits anywhere an AI writes notes for later and works from those notes instead of the original. It is strongest where the facts can be written as rules: money, counts, dates, times, quantities. A case is worth trying when it has three things:

1. **A source of truth** the note can be checked against: a ledger, a calendar, a database, a log.
2. **Rewriting over time:** summaries of summaries, memory files, handoffs between chats, agents or people.
3. **A real cost when a fact slips:** a wrong balance, a missed time, a promise that quietly turned into an "if".

## Personal assistants and memory
- **Morning briefings:** check meeting times, counts and deadlines against the calendar and inbox before the briefing is saved or read aloud.
- **Long-running memory:** check every write to an assistant's memory file, so a guess never becomes a remembered fact.
- **Chat handoffs:** check a restart note against the project's state, such as which tests pass, what got merged and what's still open, before a fresh chat trusts it.

## Money
- **AI spending caps and budgets:** prove that balances and limits stated in a summary match the ledger. This is the demo in this repo.
- **Small-business reports:** check sales, stock and prices in weekly summaries against the shop's records.
- **Expense and invoice summaries:** check totals, due dates and paid or unpaid status.

## Schedules and logistics
- **Shared to-do and calendar apps:** check that a summary of who does what, and when, still matches the app's data after several AI passes.
- **Event run-sheets:** check times, headcounts and quantities as a plan is rewritten.
- **Recipes scaled for a crowd:** check quantities and cook times after an AI rescales or summarises a recipe.

## Teams and agents
- **Multi-agent pipelines:** check every note one agent hands the next, so one agent's guess can't become the next agent's fact.
- **Coding agents' status reports:** check "done", "tests pass" and "merged" claims against git and CI before the next session builds on them.
- **Meeting notes:** check dates, owners and decisions against the transcript when the notes are summarised again later.

## High-stakes handoffs (with care)
- **Shift handoffs** in care, support and operations, where drift is a known risk. A checker can catch changed numbers and times, but people decide.
- **Policy and contract summaries:** check limits, dates and amounts against the source text.

## Not a fit
- Opinions, advice and open questions with no source to check against.
- One-shot answers that are never rewritten or reused, where a plain claim check is enough.
