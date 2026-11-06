"""Does a handoff note drift when Claude rewrites it chat after chat?

A long chat can restart from a short handoff note instead of carrying its whole history. Each restart, Claude rewrites
the note shorter for the next chat, and it only sees the last note, not the original
facts. That's where drift lives: a summary of a summary of a summary.

Two chains, same start, same number of rewrites:
  plain:  each rewrite goes straight into the next chat.
  gated:  each rewrite's claims are checked by Z3 against the SOURCE facts (not the last
          note). A wrong claim goes back to Claude once, named, to fix; if it is still
          wrong, the rewrite is refused and the last checked note carries on.
Claims Z3 can't express (plans, names, feelings) are marked "can't check", never "true".

Run: pip install z3-solver; python3 z3-handoff-drift.py [rounds]   (calls `claude -p`)
"""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from z3 import Solver, And, Not, Real, parse_smt2_string, unsat

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
MODEL = "claude-opus-5-5"

FACTS = """
(declare-const budget Real) (declare-const cap Real) (declare-const refund Real)
(declare-const mon Real) (declare-const tue Real) (declare-const wed Real)
(declare-const thu Real) (declare-const fri Real)
(declare-const spent_now Real) (declare-const left_now Real) (declare-const left_end Real)
(assert (= budget 50.0)) (assert (= cap 8.0)) (assert (= refund 2.0))
(assert (= mon 6.40)) (assert (= tue 7.95)) (assert (= wed 0.0)) (assert (= thu 5.10))
(assert (and (>= fri 0.0) (<= fri cap)))
(assert (= spent_now (- (+ mon tue wed thu) refund)))
(assert (= left_now (- budget spent_now)))
(assert (= left_end (- left_now fri)))
"""
DECLS = FACTS.split("(assert")[0]
VOCAB = ("budget cap refund mon tue wed thu fri spent_now left_now left_end "
         "(dollars; spent_now = Mon-Thu spend minus the refund; left_now = budget - spent_now; "
         "left_end = left_now - fri)")

START = """Handoff note, AI budget project, week of Nov 2.
- Weekly AI budget is $50; no single day may go over the $8 daily cap.
- Spend so far: Monday $6.40, Tuesday $7.95 (closest to the cap), Wednesday $0 (the API was down all day), Thursday $5.10.
- Anthropic refunded $2.00 for Wednesday's failed calls, so net spend Mon-Thu is $17.45 and $32.55 is left right now.
- Friday isn't logged yet. Because of the cap, at least $24.55 will be left at the end of the week.
- No day has gone over the cap.
- Next step: the team lead wants a chart of daily spend for Sunday's review."""

# Facts every handoff must still carry (the note's own claims must imply each one).
MUST_KEEP = {
    "budget is $50": "(assert (= budget 50.0))",
    "daily cap is $8": "(assert (= cap 8.0))",
    "Mon-Thu amounts": "(assert (and (= mon 6.40) (= tue 7.95) (= wed 0.0) (= thu 5.10)))",
    "$2 refund": "(assert (= refund 2.0))",
    "$32.55 left now": "(assert (= left_now 32.55))",
    "at least $24.55 left after Friday": "(assert (>= left_end 24.55))",
    "no day over the cap": "(assert (and (<= mon cap) (<= tue cap) (<= wed cap) (<= thu cap)))",
}

REWRITE = ("You are handing this project to a fresh chat that will see ONLY your note. "
           "Rewrite the handoff note below to about two thirds of its length. Keep what the next "
           "chat needs. Reply with the note only.\n\nNOTE:\n")

TRANSLATE = [
    ("Translate each factual claim in the NOTE into one SMT-LIB2 assertion using only these Real "
     f"variables: {VOCAB}. Write 'about X' as exactly X. 'No day over the cap' means every day <= cap. "
     'If a claim cannot be written with those variables, give "smt": "". If a claim mixes an amount '
     "with a reason or context (\"Wednesday was $0 because the API was down\"), give the smt for the "
     "amount part. "
     'Reply with JSON only: [{"claim": "<plain words>", "smt": "(assert ...)"}].\n\nNOTE:\n'),
    ("You are a logician. List every checkable statement in the NOTE as an SMT-LIB2 (assert ...) "
     f"over Real constants {VOCAB}. Treat approximate amounts as exact. For statements outside "
     'that vocabulary use an empty smt string; when a statement pairs an amount with a reason, encode the amount. Output a JSON array of {"claim", "smt"} objects, '
     "nothing else.\n\nNOTE:\n"),
]


JUDGE_MODEL = "claude-sonnet-5-5"   # a second, different model for the "is this new?" check
JUDGE = ("REFERENCE is the last trusted handoff note. For each numbered STATEMENT, decide if the "
         "REFERENCE says it or directly implies it (rewording is fine; a new worry, doubt, plan, "
         "condition, reason or changed meaning is NOT fine). Reply with JSON only: a list of the "
         "numbers of statements that are NOT supported, e.g. [2, 5], or [] if all are supported.\n\n")


def claude(prompt, model=MODEL):
    out = subprocess.run(["claude", "-p", "--model", model, prompt],
                         capture_output=True, text=True, timeout=300)
    return out.stdout.strip()


def parse(txt):
    return json.loads(txt[txt.find("["): txt.rfind("]") + 1])


def to_z3(smt):
    return And(*parse_smt2_string(DECLS + smt))


def check(note, reference):
    """Check a note's claims against the source facts, what it dropped, and what it added
    that the reference (the last trusted note) never said. Returns (agree, rows)."""
    with ThreadPoolExecutor(2) as ex:
        t1, t2 = ex.map(lambda p: parse(claude(p + note)), TRANSLATE)
    facts = to_z3(FACTS.split(DECLS, 1)[1])
    c1 = And(*[to_z3(i["smt"]) for i in t1 if i["smt"].strip()] or [True])
    c2 = And(*[to_z3(i["smt"]) for i in t2 if i["smt"].strip()] or [True])
    s = Solver(); s.add(facts, Not(c1 == c2))
    agree = s.check() == unsat
    rows = []
    for it in t1:
        if not it["smt"].strip():
            rows.append({"claim": it["claim"], "verdict": "can't check", "why": "outside the rules"})
            continue
        try:
            claim = to_z3(it["smt"])
        except Exception as e:
            rows.append({"claim": it["claim"], "verdict": "can't check", "why": f"bad translation: {e}"})
            continue
        s = Solver(); s.add(facts, Not(claim))
        if s.check() == unsat:
            rows.append({"claim": it["claim"], "verdict": "proved", "why": "true in every case"})
            continue
        m = s.model()
        s2 = Solver(); s2.add(facts, claim)
        if s2.check() == unsat:
            why, v = "contradicts the facts", "false"
        else:
            fri = m.eval(Real("fri"), model_completion=True)
            why, v = f"wrong if Friday is ${float(fri.as_fraction()):.2f}", "not proved"
        rows.append({"claim": it["claim"], "verdict": v, "why": why})
    # A new number Z3 can't check is where drift hides: flag it.
    for row in rows:
        if row["verdict"] == "can't check" and "$" in row["claim"]:
            row["verdict"], row["why"] = "unchecked number", "has a number the rules can't check"
    # What did the note drop? Its own claims (without the source facts) must imply each must-keep.
    said = And(*[to_z3(i["smt"]) for i in t1 if i["smt"].strip() and _ok(i["smt"])] or [True])
    for name, smt in MUST_KEEP.items():
        s = Solver(); s.add(said, Not(to_z3(smt)))
        if s.check() != unsat:
            rows.append({"claim": f"(dropped) {name}", "verdict": "dropped", "why": "the note no longer says this"})
    # Words Z3 can't check: ask a second model whether the last trusted note said them.
    loose = [r for r in rows if r["verdict"] == "can't check"]
    if loose:
        listing = "\n".join(f"{i + 1}. {r['claim']}" for i, r in enumerate(loose))
        try:
            new_ones = parse(claude(JUDGE + "REFERENCE:\n" + reference + "\n\nSTATEMENTS:\n" + listing,
                                    model=JUDGE_MODEL))
        except Exception:
            new_ones = []
        for n in new_ones:
            if isinstance(n, int) and 1 <= n <= len(loose):
                loose[n - 1]["verdict"] = "new"
                loose[n - 1]["why"] = "not in the last trusted note"
    return agree, rows


def _ok(smt):
    try:
        to_z3(smt); return True
    except Exception:
        return False


def bad(rows):
    return [r for r in rows if r["verdict"] in ("false", "not proved", "unchecked number", "dropped", "new")]


def run_chain(gated):
    name = "gated" if gated else "plain"
    note, log = START, []
    for r in range(1, ROUNDS + 1):
        new = claude(REWRITE + note)
        agree, rows = check(new, note)
        entry = {"round": r, "note": new, "agree": agree, "rows": rows, "action": "kept"}
        if gated and (bad(rows) or not agree):
            fix = ("A checker found problems with your note (wrong, unsupported, a number it can't check, a key fact you dropped, or something new the last note never said):\n"
                   + "\n".join(f"- {b['claim']} ({b['why']})" for b in bad(rows))
                   + ("\n- (two independent readings of the note disagreed; make the numbers unambiguous)"
                      if not agree else "")
                   + "\nRewrite the note with those fixed: correct or remove wrong or new ones, put dropped facts back from the last checked note. Add nothing the last checked note doesn't say. Reply with the new note only.\n\n"
                   + "LAST CHECKED NOTE:\n" + note + "\n\nYOUR NOTE:\n" + new)
            new2 = claude(fix)
            agree2, rows2 = check(new2, note)
            entry.update(first_try_bad=bad(rows), note=new2, agree=agree2, rows=rows2)
            if bad(rows2) or not agree2:
                entry["action"] = "refused, kept last checked note"
                new = note
            else:
                entry["action"] = "fixed after one round of feedback"
                new = new2
        log.append(entry)
        note = new
        nb = len(bad(entry["rows"]))
        json.dump(log, open(__file__.replace(".py", f".{name}.partial.json"), "w"), indent=1)
        print(f"[{name}] round {r}: {nb} bad, agree={entry['agree']}, {entry['action']}", flush=True)
    return {"chain": name, "rounds": log, "final_note": note}


if __name__ == "__main__":
    with ThreadPoolExecutor(2) as ex:
        results = list(ex.map(run_chain, (False, True)))
    # Final audit of both end notes against the ORIGINAL note, the real source of truth.
    for c in results:
        c["audit_vs_start"] = check(c["final_note"], START)[1]
    json.dump({"start": START, "chains": results},
              open(__file__.replace(".py", ".results.json"), "w"), indent=1)
    for c in results:
        print(f"\n=== {c['chain']} chain, final note ===\n{c['final_note']}")
        for row in c["audit_vs_start"]:
            print(f"  [{row['verdict']}] {row['claim']}  ({row['why']})")
