"""Can we prove an AI app won't let made-up claims spread? 

We can't prove a model never makes something up: it's a guesser, and Z3 can't
look inside it. We CAN prove two things around it, for every input:

Part A, the pipe: a made-up claim can never reach the user's screen or the app's
memory without passing the checker, on any turn, forever. Proved by induction:
true at the start, and every step keeps it true, so no number of turns or
summaries-of-summaries can break it. The model is left completely free (it may
make up anything, any time).

Part B, the checker: Claude turns each claim in an answer into logic, twice in
two different ways; Z3 checks the two agree, then checks each claim follows
from the facts in EVERY case the facts allow. A claim that's only true in some
cases is caught with Z3's example of a case where it's wrong.

Run: pip install z3-solver; python3 z3-ai-drift-check.py   (Part B calls `claude -p`;
add --no-claude to use the saved translations only)
"""
import json, subprocess, sys
from z3 import (Bools, Bool, Int, Solver, And, Or, Not, Implies, If, sat, unsat,
                Real, parse_smt2_string, simplify)

results = {"pipe": [], "claims": []}

# ---------------------------------------------------------------- Part A: the pipe
def pipe_step(fixed):
    """One turn. State: bad claim on screen / in memory. The AI is unconstrained."""
    shown, mem, shown2, mem2 = Bools("shown mem shown2 mem2")
    ai_bad = Bool("ai_made_something_up")          # free: the model may do anything
    action = Int("action")                         # 0 answer the user, 1 summarise memory
    check = Int("check")                           # 0 pass, 1 fail, 2 checker error/timeout
    s = Solver()
    s.add(action >= 0, action <= 1, check >= 0, check <= 2)
    s.add(Implies(check == 0, Not(ai_bad)))        # checker is sound (Part B earns this)
    if fixed:
        lets_through = check == 0                  # fail closed: only a pass gets through
        saves_raw = False                          # memory written only after the check
        summary_checked = True
    else:
        lets_through = Or(check == 0, check == 2)  # BUG 1: on checker error, show it anyway
        saves_raw = True                           # BUG 2: answer saved to memory before check
        summary_checked = False                    # BUG 3: memory summary written back unchecked
    answer = action == 0
    summarise = action == 1
    s.add(shown2 == Or(shown, And(answer, ai_bad, lets_through)))
    s.add(mem2 == Or(mem,
                     And(answer, ai_bad, Or(lets_through, saves_raw)),
                     And(summarise, ai_bad, (check == 0) if summary_checked else True)))
    inv, inv2 = And(Not(shown), Not(mem)), And(Not(shown2), Not(mem2))
    # Induction: start is clean (both False satisfy inv trivially); does any step break it?
    found = []
    while True:
        s.push(); s.add(inv, Not(inv2))
        r = s.check()
        if r != sat:
            s.pop(); break
        m = s.model(); s.pop()
        a, c = m.eval(action).as_long(), m.eval(check).as_long()
        where = "screen" if m.eval(shown2) else "memory"
        found.append({"step": ["answer the user", "summarise memory"][a],
                      "checker": ["passed", "failed", "errored"][c], "leaks_to": where})
        s.add(Not(And(action == a, check == c)))   # block it, look for the next path
    return found

for fixed in (False, True):
    leaks = pipe_step(fixed)
    label = "fixed pipe" if fixed else "planted-bug pipe"
    results["pipe"].append({"version": label, "leaks": leaks, "proved": not leaks})
    print(f"\nPart A, {label}: " + ("PROVED, no made-up claim reaches screen or memory on any turn"
                                    if not leaks else f"{len(leaks)} leak paths"))
    for l in leaks:
        print(f"  - {l['step']}, checker {l['checker']} -> made-up claim lands in {l['leaks_to']}")

# ---------------------------------------------------------------- Part B: the checker
FACTS = """
(declare-const budget Real) (declare-const cap Real)
(declare-const mon Real) (declare-const tue Real) (declare-const wed Real) (declare-const thu Real)
(declare-const left_now Real) (declare-const left_end Real)
(assert (= budget 20.0)) (assert (= cap 5.0))
(assert (= mon 3.10)) (assert (= tue 4.25)) (assert (= wed 2.80))
(assert (and (>= thu 0.0) (<= thu cap)))
(assert (= left_now (- budget (+ mon tue wed))))
(assert (= left_end (- left_now thu)))
"""
DECLS = FACTS.split("(assert")[0]
FACTS_EN = ("Monthly AI budget $20. Daily cap $5. Spent: Monday $3.10, Tuesday $4.25, "
            "Wednesday $2.80. Thursday isn't logged yet, but no day can go over the cap.")
QUESTION = "How much of the $20 is left, and did any day go over the daily cap?"
PLANTED = ("Summary (after three rounds of summarising): at least $9.85 will still be left "
           "after Thursday, and Tuesday went over the daily cap.")

def claude(prompt):
    out = subprocess.run(["claude", "-p", "--model", "claude-opus-5-5", prompt],
                         capture_output=True, text=True, timeout=240)
    return out.stdout.strip()

TRANSLATE = [
    ("Translate each factual claim in the ANSWER into SMT-LIB2. Use only these Real "
     "variables: budget cap mon tue wed thu left_now left_end (dollars; left_now = budget minus Mon-Wed spend, left_end = what's left after Thursday too). "
     'Reply with JSON only: [{"claim": "<the claim in plain words>", "smt": "(assert ...)"}]. '
     "Write 'about X' as exactly X. 'No day over the cap' means every day <= cap.\n\nANSWER: "),
    ("You are a logician. For the ANSWER below, list every checkable statement about money as "
     "an SMT-LIB2 assertion over Real constants budget, cap, mon, tue, wed, thu, left_now (left before Thursday), left_end (left after Thursday). "
     "Treat approximate amounts as exact. Output a JSON array of objects with keys claim and "
     "smt, nothing else.\n\nANSWER: "),
]

def parse(txt):
    txt = txt[txt.find("["): txt.rfind("]") + 1]
    return json.loads(txt)

def conj(items):
    return And(*[f for it in items for f in parse_smt2_string(DECLS + it["smt"])])

def check_answer(name, answer, use_claude):
    cache = f"{__file__}.cache.json"
    try:
        saved = json.load(open(cache))
    except Exception:
        saved = {}
    key = name
    if use_claude or key not in saved:
        saved[key] = [parse(claude(p + answer)) for p in TRANSLATE]
        json.dump(saved, open(cache, "w"), indent=1)
    t1, t2 = saved[key]
    facts = And(*parse_smt2_string(FACTS))
    s = Solver(); s.add(facts, Not(conj(t1) == conj(t2)))   # agree, given the facts
    agree = s.check() == unsat
    print(f"\nPart B, {name}: \"{answer}\"\n  two translations agree: {agree}")
    rows = []
    for it in t1:
        claim = And(*parse_smt2_string(DECLS + it["smt"]))
        s = Solver(); s.add(facts, Not(claim))
        if s.check() == unsat:
            verdict, why = "proved", "true in every case the facts allow"
        else:
            m = s.model()
            s2 = Solver(); s2.add(facts, claim)
            thu = m.eval(Real("thu"), model_completion=True)
            left = m.eval(Real("left_end"), model_completion=True)
            if s2.check() == unsat:
                verdict, why = "false", "contradicts the facts in every case"
            else:
                verdict = "not proved"
                why = f"wrong when Thursday is ${float(thu.as_fraction()):.2f} (left at the end would be ${float(left.as_fraction()):.2f})"
        print(f"  [{verdict}] {it['claim']}  ->  {why}")
        rows.append({"claim": it["claim"], "smt": it["smt"], "verdict": verdict, "why": why})
    results["claims"].append({"name": name, "answer": answer, "agree": agree, "rows": rows})

use_claude = "--no-claude" not in sys.argv
real = None
if use_claude:
    real = claude(f"Facts: {FACTS_EN}\nQuestion: {QUESTION}\nAnswer in two short sentences, "
                  "plain English, no working shown.")
    json.dump({"real": real}, open(f"{__file__}.answer.json", "w"))
else:
    real = json.load(open(f"{__file__}.answer.json"))["real"]
check_answer("Claude's real answer", real, use_claude)
check_answer("planted drift", PLANTED, use_claude)
json.dump(results, open(f"{__file__}.results.json", "w"), indent=1)
