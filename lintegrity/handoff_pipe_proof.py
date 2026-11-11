"""Proof by induction: can a flagged handoff note ever become the trusted note?

Each turn, the AI writes a note that may drift, in any way, on every turn. The checker reads it.
The proof assumes the checker flags every drifted note it actually judges; the evidence suite
measures how close the real checker comes to that. What the proof adds is the plumbing: given
that, does any path let a drifted note become the note the next chat trusts?

  gate: Lintegrity's handoff gate. A flagged note gets one fix; if the fix is flagged, it is
        refused and the last trusted note carries on. A checker error counts as a flag.
  hook-old: the Claude Code hook before 2026-11-10. It never blocked twice in a row (the second
        write was accepted unchecked, because Claude may know better), and it failed open when
        Jev errored or timed out.
  hook: the Claude Code hook since 2026-11-10, rebuilt as the gate. It checks the write before it
        lands (PreToolUse), denies the first flagged write for a fix, refuses the next, and
        counts a Jev error as a flag. A refused note goes through only if the user says
        "accept the note"; that is the user's call, not drift, so it is modeled as its own choice.

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
    approved = Bool("user_said_accept_the_note")
    trusted_before = Bool("trusted_clean_before")
    # The checker's verdict: it flags every drifted note it judges (the measured assumption).
    flag1 = drift
    if design == "gate":
        rejected1 = Or(flag1, err1)                      # an error counts as a flag
        rejected2 = Or(fix_drift, err2)
        new_clean = If(Not(rejected1), Not(drift),       # passed: becomes trusted
                    If(Not(rejected2), Not(fix_drift),   # fixed: the fix becomes trusted
                       trusted_before))                  # refused: last trusted note carries on
    elif design == "hook":
        rejected = Or(flag1, err1)
        new_clean = If(Not(rejected), Not(drift),
                    If(And(told, approved), Not(drift),  # refused, but the user let it through
                       trusted_before))                  # denied or refused: nothing lands
        return trusted_before, new_clean, [drift, fix_drift, err1, err2, told, approved]
    else:  # hook-old
        accepted_unchecked = Or(told, err1)              # second write, or Jev error: no verdict
        new_clean = If(accepted_unchecked, Not(drift),
                    If(Not(flag1), Not(drift),           # passed
                       trusted_before))                  # blocked this time; nothing trusted yet
    return trusted_before, new_clean, [drift, fix_drift, err1, err2, told]


for design in ("gate", "hook-old", "hook"):
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
        ways = sorted({" + ".join(w for w, on in [("the user said accept the note", v.get("user_said_accept_the_note") is not None and str(v.get("user_said_accept_the_note")) == "True"),
                                                    ("second write accepted", str(v["already_flagged_once"]) == "True" and "user_said_accept_the_note" not in v),
                                                    ("checker error", str(v["checker_error_on_write"]) == "True" and "user_said_accept_the_note" not in v)] if on) for v in paths})
        print(f"      ways in: {', '.join(w or '?' for w in ways)}")

# The rebuilt hook, minus the user's own override: the same guarantee as the gate.
before, after, choices = turn("hook")
s = Solver()
s.add(before, Not(after), Not(Bool("user_said_accept_the_note")))
print("hook, unless the user says \"accept the note\": " + ("PROVED. No drifted note becomes trusted, on any turn, even when Jev errors or Claude writes it again." if s.check() == unsat else f"LEAK: {s.model()}"))
