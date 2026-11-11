"""The real test: does the check keep an AI's handoff note from drifting over many rewrites?

Sonnet 5.5 rewrites the Thanksgiving note ROUNDS times, two thirds shorter each time, seeing only
the last note (a summary of a summary). Two arms, CHAINS runs each, all in parallel processes:

  plain:   every rewrite goes straight to the next chat.
  checked: every rewrite is checked by both layers: Z3 against the ORIGINAL facts (contradiction
           or a lost must-keep fact) and Jev against the last trusted note. A flagged rewrite gets
           one fix with the problems named; if still flagged, it's refused and the last trusted
           note carries on.

Every round of both arms is scored the same way: Z3 against the original must-keep facts, and
Jev against the original note. Results: evidence/chains/<arm>-<n>.json

    .venv/bin/python evidence/chains.py [rounds] [chains]
"""
import json, os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lintegrity"))
os.environ["LINTEGRITY_NO_CACHE"] = "1"
from note_check import spec_for, check_note, claude  # noqa: E402

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
CHAINS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
WRITER = os.environ.get("LINTEGRITY_WRITER", "claude-sonnet-5-5")
BASE = os.environ.get("LINTEGRITY_BASE", "dinner")          # or "long": the three-project note
SPEC = spec_for(BASE)
OUT = os.path.join(HERE, os.environ.get("LINTEGRITY_CHAINS_DIR", "chains"))
ORIGINAL = next(c["before"] for c in json.load(open(os.path.join(HERE, "cases.json"))) if c["base"] == BASE)
RECORD = "USER: Wrap up: rewrite the handoff note for the next chat. No other work happened in this session."

REWRITE = ("You are handing this project to a fresh chat that will see ONLY your note. Rewrite the handoff note "
           "below to about two thirds of its length. Keep what the next chat needs, and keep the same ## section "
           "headings and the **Status:** line. Reply with the note only.\n\nNOTE:\n")
FIX = ("You rewrote a handoff note, and a checker found problems in your rewrite. Fix them: restore the fact or "
       "wording from the PREVIOUS note, or remove what nothing backs up. Keep it about as short as your rewrite, keep "
       "the same ## section headings and the **Status:** line. Reply with the fixed note only.\n\nPROBLEMS:\n{p}\n\n"
       "PREVIOUS NOTE:\n{prev}\n\nYOUR REWRITE:\n{new}")


ADVISORY = "Lost a few rewrites back"   # the older-version check asks once, never refuses (as in the hook)


def jev(before, after, anchor=None):
    r = subprocess.run(["node", os.path.join(HERE, "jev_check.mjs")], input=json.dumps({"before": before, "after": after, "record": RECORD, "anchor": anchor}),
                       capture_output=True, text=True, timeout=120)
    try:
        out = json.loads(r.stdout)
        return out if isinstance(out, list) else [f"jev error: {out}"]
    except Exception:
        return [f"jev error: {r.stderr[-200:]}"]


def z3_problems(note):
    r = check_note(SPEC, note)
    if r.get("error"):
        return ["translation failed"], r
    texts = [f"The note no longer guarantees: {p['fact']} (a world the note allows: {p['counterexample']})" if p["kind"] == "loss"
             else f"Contradicts the trusted facts: {p['claim']}" for p in r["problems"]]
    return texts, r


def clean(txt):
    t = txt.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[1] if "\n" in t else t
    return t.rstrip("`").strip() + "\n"


def score(note):
    z, r = z3_problems(note)
    j = jev(ORIGINAL, note)
    lost = [p["fact"] for p in r.get("problems", []) if p["kind"] == "loss"]
    contra = [p["claim"] for p in r.get("problems", []) if p["kind"] == "contradiction"]
    made_up = [x for x in j if x.startswith(("A worry", "A decision"))]
    changed = [x for x in j if x.startswith("Changes what")]
    return {"lost": lost, "contradictions": contra, "made_up": made_up, "changed": changed, "jev": j, "chars": len(note)}


def run_chain(arm_i):
    arm, i = arm_i
    note, trusted, rounds = ORIGINAL, ORIGINAL, []
    history = [ORIGINAL]   # trusted versions; the anchor is the oldest of the last 5, as in the hook
    for k in range(1, ROUNDS + 1):
        t = time.time()
        if arm == "plain":
            note = clean(claude(REWRITE + note, model=WRITER))
            row = {"round": k, "note": note}
        else:
            cand = clean(claude(REWRITE + trusted, model=WRITER))
            anchor = history[-5:][0] if len(history) >= 2 else None
            z, _ = z3_problems(cand)
            probs = z + jev(trusted, cand, anchor)
            row = {"round": k, "first_try_problems": probs}
            if not probs:
                trusted, row["outcome"] = cand, "passed"
            else:
                fixed = clean(claude(FIX.format(p="\n".join(f"- {p}" for p in probs), prev=trusted, new=cand), model=WRITER))
                z2, _ = z3_problems(fixed)
                probs2 = z2 + jev(trusted, fixed, anchor)
                row["after_fix_problems"] = probs2
                if not [p for p in probs2 if not p.startswith(ADVISORY)]:
                    trusted, row["outcome"] = fixed, "fixed"
                else:
                    row["outcome"] = "refused"
            if history[-1] != trusted:
                history.append(trusted)
            note = trusted
            row["note"] = note
        row["score"] = score(note)
        row["seconds"] = round(time.time() - t)
        rounds.append(row)
        json.dump({"arm": arm, "chain": i, "writer": WRITER, "rounds": rounds}, open(os.path.join(OUT, f"{arm}-{i}.json"), "w"), indent=1)
    return arm, i, rounds[-1]["score"]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    arms = os.environ.get("LINTEGRITY_ARMS", "plain,checked").split(",")
    jobs = [(a, i) for i in range(1, CHAINS + 1) for a in arms]
    with ProcessPoolExecutor(len(jobs)) as ex:
        for arm, i, s in ex.map(run_chain, jobs):
            print(f"{arm} {i}: lost {len(s['lost'])} {s['lost']}, contradictions {len(s['contradictions'])}, made-up {len(s['made_up'])}, changed {len(s['changed'])}, {s['chars']} chars", flush=True)
