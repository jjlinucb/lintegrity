"""Score a batch of drift runs: how often the plain chain drifted, what the checked chain did.

Reads results/batch-*/results.json, prints one line per run and a total, and writes
results/summary.json plus results/flags.json (every flag raised, for hand-labelling
false alarms).
"""
import glob, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
BAD = ("false", "not proved", "unchecked number", "dropped", "new")


def issues(rows):
    return [r for r in rows if r["verdict"] in BAD]


runs, flags = [], []
for path in sorted(glob.glob(os.path.join(ROOT, "batch-*", "results.json")),
                   key=lambda p: int(p.split("batch-")[1].split(os.sep)[0])):
    run = path.split(os.sep)[-2]
    d = json.load(open(path))
    row = {"run": run}
    for c in d["chains"]:
        name = c["chain"]
        final = issues(c["audit_vs_start"])
        drifted = [e["round"] for e in c["rounds"] if issues(e["rows"]) or e.get("first_try_bad")]
        acts = [e["action"] for e in c["rounds"]]
        row[name] = {
            "final_issues": [f"{r['verdict']}: {r['claim']}" for r in final],
            "first_drift_round": drifted[0] if drifted else None,
            "rounds_with_flags": len(drifted),
            "fixed": sum(a.startswith("fixed") for a in acts),
            "refused": sum(a.startswith("refused") for a in acts),
        }
        for e in c["rounds"]:
            for r in e.get("first_try_bad", []) + issues(e["rows"]):
                flags.append({"run": run, "chain": name, "round": e["round"], **r})
    runs.append(row)

json.dump(runs, open(os.path.join(ROOT, "summary.json"), "w"), indent=1)
json.dump(flags, open(os.path.join(ROOT, "flags.json"), "w"), indent=1)

print(f"{'run':10} {'plain: final issues':>20} {'first drift':>12} | {'checked: final issues':>22} {'fixed':>6} {'refused':>8}")
for r in runs:
    p, g = r["plain"], r["gated"]
    print(f"{r['run']:10} {len(p['final_issues']):>20} {str(p['first_drift_round']):>12} | "
          f"{len(g['final_issues']):>22} {g['fixed']:>6} {g['refused']:>8}")
n = len(runs)
if n:
    pd = sum(bool(r["plain"]["final_issues"]) for r in runs)
    gd = sum(bool(r["gated"]["final_issues"]) for r in runs)
    print(f"\n{n} runs. Plain final note had an issue in {pd}; checked final note in {gd}.")
    print(f"Flags raised in all: {len(flags)} (label them in results/flags.json for false alarms).")
