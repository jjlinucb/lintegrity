"""Run every evidence case through the formal layer (note_check.py) and save the findings.

    .venv/bin/python evidence/run_z3.py            # all cases (translations are cached)
    .venv/bin/python evidence/run_z3.py --bases    # only the two untouched base notes (must be clean)

Translations run in threads (they are `claude -p` calls); Z3 runs in the main thread only, since
it isn't thread-safe.
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lintegrity"))
from note_check import spec_for, translate, prove, check_note, DINNER  # noqa: E402

cases = json.load(open(os.path.join(HERE, "cases.json")))
notes = {}
if "--bases" in sys.argv:
    for c in cases:
        notes.setdefault(("base", c["base"]), c["before"])
else:
    for c in cases:
        notes[("case", c["id"])] = c["after"]
        notes.setdefault(("base", c["base"]), c["before"])
base_of = {("base", "dinner"): "dinner", ("base", "long"): "long"}
base_of.update({("case", c["id"]): c["base"] for c in cases})

t0 = time.time()
jobs = [(k, w) for k in notes for w in (0, 1)]
with ThreadPoolExecutor(8) as ex:
    list(ex.map(lambda j: translate(spec_for(base_of[j[0]]), notes[j[0]], j[1]), jobs))
print(f"translations ready in {time.time() - t0:.0f} s ({len(DINNER.calls)} new calls)")

results = {}
for k, note in notes.items():
    r = check_note(spec_for(base_of[k]), note)
    results[f"{k[0]}:{k[1]}"] = r

for b in ("dinner", "long"):
    r = results.get(f"base:{b}")
    if r:
        print(f"base {b}: {len(r['problems'])} problems {r['problems']}  (claims a={r['a']['claims']} b={r['b']['claims']}, unparsed a={r['a']['unparsed']} b={r['b']['unparsed']})")
if "--bases" not in sys.argv:
    for c in cases:
        r = results[f"case:{c['id']}"]
        flag = bool(r["problems"])
        mark = "RIGHT" if flag == c["should"] else ("miss " if c["should"] else "FALSE")
        kinds = "; ".join(p.get("fact") or p.get("claim", "") for p in r["problems"])
        print(f"{mark} t{c['tier']} #{c['id']:>2} {'F' if c['formal'] else ' '} {c['name']}: {kinds}  {('disagree ' + ','.join(r['disagree'])) if r['disagree'] else ''}")
json.dump(results, open(os.path.join(HERE, "results-z3.json"), "w"), indent=1)
