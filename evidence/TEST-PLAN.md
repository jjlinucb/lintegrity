# Test plan: does Lintegrity keep an AI's handoff note from drifting?

Written 2026-11-10, before any of these tests ran.

## The claim under test

Each chat rewrites a handoff note from the last one. Lintegrity checks every rewrite before the next chat trusts it. There are two layers:

- **Formal (Z3).** The note's settled facts are translated into logic twice, by two different prompts. Z3 then proves two things:
  - **Contradiction:** a claim can't be true alongside the trusted facts.
  - **Loss:** the note no longer guarantees a must-keep fact. A fact that is deleted, turned into a doubt, given an "if", or made vaguer all fail this test, because the note no longer implies it.
  - A flag needs both translations to agree. Each comes with a counterexample: a world the new note allows where the fact is false.
- **Judgement (Jev).** This layer covers what logic can't express: new worries, made-up decisions about things outside the facts, open questions, the status line. It uses the chat's own record for backing.

## Test notes

- **Thanksgiving dinner note:** 60 people, Saturday November 21, hall 4 to 9 PM, $150 deposit paid, curry tested twice at 50 minutes a batch, John on curry, Jeanine on rice, sign-ups close November 18, two open questions. It has 11 must-keep facts.
- **Long note:** the same dinner plus two more projects (a youth retreat and a budget), about 40 lines.

Every case has a fake chat record behind it: the session that "wrote" the new note.

## Tiers

| Tier | What it tests | Cases |
|---|---|---|
| 1 Easy | One value changed outright (count, money, date, time, owner) | 8 |
| 2 Medium | Wording drift: doubt, added "if", "tentatively", "for now", vaguer value, end time dropped, open question dropped or re-dated | 10 |
| 3 Hard | Hidden drift: deleted fact, status flip, reworded or doubting open question, worry inside a progress sentence, made-up worry on a new topic | 10 |
| 4 Adversarial | Made-up decisions, facts and rules; three small drifts in one rewrite; drift implied by arithmetic; a fact moved into a to-do; a buried change in a full restructure; the wrong person credited | 12 |
| 5 Long note | Drift buried in a 40-line, three-project note | 6 |
| Controls | Safe edits that must pass: progress, answered questions, backed updates (60 to 58 after the user says so), rewording, restructuring, backed status changes | 14 |

## Metrics

- **Catch rate** per tier, for Z3 alone, Jev alone, and both together.
- **False alarms:**
  - on controls;
  - on 37 real wrap-ups from the author's own chats (Jev only, since real notes have no fact list);
  - Z3 false alarms counted separately, since the formal claim is that Z3 never flags a true note when the translation is right.
- **Translation agreement:** how often the two translations differ.

## The real test: AI rewrite chains

Sonnet 5.5 rewrites the Thanksgiving note 10 times, each rewrite two thirds shorter, seeing only the last note. Five chains run without any check and five with both layers checking every rewrite. A flagged rewrite gets one fix; if it's still flagged, it's refused and the last checked note carries on. The final notes are scored by Z3 against the original must-keep facts, plus a count of made-up claims.

## The proof

`claim_and_pipe_check.py` re-runs the induction proof that no unchecked claim can reach the next chat, on any turn.

## What would count as failure

- Z3 flags a control.
- Planted contradictions or losses get past Z3.
- Checked chains end no better than plain ones.
- False alarms on real wrap-ups climb above the 11 of 37 measured today.
