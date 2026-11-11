"""Proof by induction: can a flagged handoff note ever become the trusted note?

Each turn, the AI writes a note that may drift, in any way, on every turn. The checker reads it.
The proof assumes the checker flags every drifted note it actually judges; the evidence suite
measures how close the real checker comes to that. What the proof adds is the plumbing: given
that, does any path let a drifted note become the note the next chat trusts?

  gate: Lintegrity's handoff gate. A flagged note gets one fix; if the fix is flagged, it is
        refused and the last trusted note carries on. A checker error counts as a flag.
  hook: the Claude Code hook as built. It never blocks twice in a row (the second write is
        accepted unchecked, because Claude may know better), and it fails open when Jev errors
        or times out.

Invariant: the trusted note is clean. Base case: the starting note is clean. Step: if the trusted
note is clean before a turn, it is clean after, for every write, check result and error. Z3 proves
the step, or returns the turn that breaks it.

    python3 lintegrity/handoff_pipe_proof.py
"""
from z3 import Bool, And, Or, Not, If, Implies, Solver, sat, unsat


def turn(design):
    # Free choices each turn: the AI's write, its fix, whether the checker errors, and whether
    # the last write was already flagged (the hook's "told once" marker).
    drift, fix_drift = Bool("write_drifted"), Bool("fix_drifted")
    err1, err2 = Bool("checker_error_on_write"), Bool("checker_error_on_fix")
    told = Bool("already_flagged_once")
    trusted_before = Bool("trusted_clean_before")
    # The checker's verdict: it flags every drifted note it judges (the measured assumption).
    flag1 = drift
    if design == "gate":
        rejected1 = Or(flag1, err1)                      # an error counts as a flag
        rejected2 = Or(fix_drift, err2)
        new_clean = If(Not(rejected1), Not(drift),       # passed: becomes trusted
                    If(Not(rejected2), Not(fix_drift),   # fixed: the fix becomes trusted
                       trusted_before))                  # refused: last trusted note carries on
    else:  # hook
        accepted_unchecked = Or(told, err1)              # second write, or Jev error: no verdict
        new_clean = If(accepted_unchecked, Not(drift),
                    If(Not(flag1), Not(drift),           # passed
                       trusted_before))                  # blocked this time; nothing trusted yet
    return trusted_before, new_clean, [drift, fix_drift, err1, err2, told]


for design in ("gate", "hook"):
    before, after, choices = turn(design)
    s = Solver()
    s.add(before, Not(after))                            # clean before, drifted after: a leak
    if s.check() == unsat:
        print(f"{design}: PROVED. A drifted note never becomes the trusted note, on any turn (base: the first note is clean; step: unsat).")
    else:
        m = s.model()
        why = ", ".join(f"{c}={m.eval(c, model_completion=True)}" for c in choices)
        print(f"{design}: LEAK. A drifted note becomes trusted when: {why}")
        # list every distinct way in
        paths = []
        while s.check() == sat:
            m = s.model()
            vals = {str(c): m.eval(c, model_completion=True) for c in choices}
            paths.append(vals)
            s.add(Or(*[c != m.eval(c, model_completion=True) for c in choices]))
        ways = sorted({("second write accepted" if v["already_flagged_once"] else "") + ("checker error" if v["checker_error_on_write"] else "") for v in paths})
        print(f"      ways in: {', '.join(w or '?' for w in ways)}")
