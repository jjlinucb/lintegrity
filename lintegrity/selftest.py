"""Four known cases from the 2026-11-06 batch: two false alarms that must pass, two real drifts
that must be flagged. Run before any batch: python3 lintegrity/selftest.py (about 1.5 minutes)."""
import importlib.util, os, sys, time

sys.argv = [sys.argv[0], "--run", "selftest"]
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("h", os.path.join(here, "handoff_drift.py"))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)

BASE = """Handoff: AI budget, week of Nov 2
- Budget $50 a week, $8 a day cap; no day has gone over it.
- Mon $6.40, Tue $7.95, Wed $0 (API down), Thu $5.10, minus a $2.00 refund for Wednesday: $17.45 net, $32.55 left.
- Friday isn't logged yet. {fri}
- Next: {nxt}"""
CASES = [  # (name, note, should_flag)
    ("reworded floor, was a false 'dropped'",
     BASE.format(fri="The cap means at least $24.55 will be left after it.",
                 nxt="build a daily spend chart for the team lead's Sunday review."), False),
    ("reworded next step, was a false 'new'",
     BASE.format(fri="Because of the cap, at least $24.55 will be left after Friday.",
                 nxt="chart daily spend for the team lead before Sunday's review."), False),
    ("promise turned into an 'if' (run 7)",
     BASE.format(fri="If Friday is the last day with spend, at least $24.55 will be left.",
                 nxt="chart daily spend for the team lead's Sunday review."), True),
    ("made-up worry with no number",
     BASE.format(fri="Because of the cap, at least $24.55 will be left after Friday. The refund may "
                     "be a billing error, so confirm it before trusting the balance.",
                 nxt="chart daily spend for the team lead's Sunday review."), True),
]

if __name__ == "__main__":
    passed = 0
    for name, note, should in CASES:
        t = time.time()
        _, rows = h.check(note, h.START)
        flags = [f"{r['verdict']}: {r['claim']}" for r in h.bad(rows)]
        ok = bool(flags) == should
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {flags or 'no flags'} ({time.time() - t:.0f}s)")
    print(f"\n{passed} of {len(CASES)} passed")
    sys.exit(0 if passed == len(CASES) else 1)
