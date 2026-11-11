"""Formal check of a handoff note's settled facts, with Z3.

A note is translated into SMT-LIB assertions twice, by two different prompts. Only what the note
states as settled goes in: a doubted fact ("may not have gone through") gives no assertion, a
conditional one is guarded by `pending` ("if the hall confirms"), and a vague one becomes the
range it states ("under an hour" is < 60). Then Z3 proves, for each translation:

  contradiction: a claim can't hold together with the trusted facts (facts AND claim is unsat);
  loss:          the note no longer guarantees a must-keep fact (rules AND note AND NOT fact is
                 sat). The satisfying model is the counterexample: a world the note allows where
                 the fact is false.

A finding counts only when both translations show it, so one bad translation can't raise a flag.
Facts outside the vocabulary are left to the judgement layer (Jev).

    from note_check import Spec, check_note
    findings = check_note(spec, note_text)
"""
import hashlib, json, os, re, subprocess, threading
from dataclasses import dataclass, field
from z3 import (And, Not, Solver, Bool, Int, BoolRef, parse_smt2_string, sat, unsat, is_true)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "evidence", "translation-cache.json")
TRANSLATE_MODEL = os.environ.get("LINTEGRITY_TRANSLATE_MODEL", "claude-sonnet-5-5")
LEAN = ["--system-prompt", "You are a careful assistant. Follow the instructions exactly.",
        "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--exclude-dynamic-system-prompt-sections", "--no-session-persistence"]


@dataclass
class Spec:
    ints: dict          # name -> meaning
    bools: dict         # name -> meaning
    facts: str          # SMT asserts: the trusted note's facts
    rules: str          # SMT asserts that hold everywhere (a note may lean on them unsaid)
    must_keep: dict     # label -> SMT assert
    calls: list = field(default_factory=list)

    def decls(self):
        d = [f"(declare-const {n} Int)" for n in self.ints] + [f"(declare-const {n} Bool)" for n in self.bools]
        return "\n".join(d + ["(declare-const pending Bool)"]) + "\n"

    def vocab(self):
        lines = [f"- {n} (Int): {m}" for n, m in self.ints.items()] + [f"- {n} (Bool): {m}" for n, m in self.bools.items()]
        return "\n".join(lines + ["- pending (Bool): an unresolved condition; guard any conditional claim with it"])

    def z3(self, smt):
        return And(*parse_smt2_string(self.decls() + smt)) if smt.strip() else And(True)


PROMPTS = [
    "Translate the settled facts in the NOTE into SMT-LIB2 assertions, one per claim, using only these "
    "variables:\n{vocab}\n\nRules: assert only what the note states as settled. A claim stated with doubt "
    "('may', 'might', 'probably', 'unverified', 'not sure', 'unclear', 'confirm whether') gets smt \"\". A claim "
    "that depends on a condition ('if', 'assuming', 'unless', 'once') is written (assert (=> pending CLAIM)). A "
    "vague value is written as the range it states: 'under an hour' is (< x 60), 'about 60' is (and (>= x 55) "
    "(<= x 65)), 'from 4 PM' with no end gives only the start. Times are 24-hour (4 PM is 16). Anything that "
    "can't be written with these variables gets smt \"\". Reply with JSON only: "
    '[{{"claim": "<plain words>", "smt": "(assert ...)"}}].\n\nNOTE:\n',
    "You are a logician formalizing a handoff note. For every statement in the NOTE, give an SMT-LIB2 (assert ...) "
    "over these constants, or an empty string when the statement is outside them:\n{vocab}\n\nEncode only firm "
    "statements. Hedged statements (doubt, 'probably', 'may not', 'hasn't been checked') are encoded as \"\". "
    "Conditional statements are encoded as (assert (=> pending STATEMENT)). Approximate or bounded values become "
    "the bound they give ('around 50' -> between 45 and 55; 'less than an hour' -> < 60), never an exact value. "
    "Use 24-hour clock hours. Output a JSON array of {{\"claim\", \"smt\"}} objects and nothing else.\n\nNOTE:\n",
    # Third reading, used only to break a tie when the first two disagree.
    "Read the NOTE sentence by sentence. For each sentence that states something as settled, write it as SMT-LIB2 "
    "(assert ...) over these constants, including totals and durations implied by its numbers (for example "
    "'two batches take 100 minutes' is (assert (= (* 2 curry_minutes) 100))):\n{vocab}\n\nA hedged sentence gives "
    "\"\"; a conditional one is (assert (=> pending ...)); a vague amount is the bound it states; times are 24-hour. "
    "Sentences outside these constants give \"\". Reply with a JSON array of {{\"claim\", \"smt\"}} only.\n\nNOTE:\n",
]

_lock = threading.Lock()


def _cache():
    if os.environ.get("LINTEGRITY_NO_CACHE") == "1":
        return {}
    try:
        with open(CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(key, value):
    if os.environ.get("LINTEGRITY_NO_CACHE") == "1":
        return
    with _lock:
        c = _cache()
        c[key] = value
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump(c, f, indent=0)


def claude(prompt, model=TRANSLATE_MODEL):
    out = subprocess.run(["claude", "-p", "--model", model, *LEAN, prompt],
                         capture_output=True, text=True, timeout=300, cwd="/tmp")
    return out.stdout.strip()


def translate(spec, note, which):
    prompt = PROMPTS[which].format(vocab=spec.vocab()) + note
    key = hashlib.sha1((TRANSLATE_MODEL + prompt).encode()).hexdigest()
    hit = _cache().get(key)
    if hit is not None:
        return hit
    for _ in range(3):
        raw = claude(prompt)
        spec.calls.append(1)
        try:
            rows = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
            rows = [r for r in rows if isinstance(r, dict)]
            _save(key, rows)
            return rows
        except Exception:
            continue
    return None


def _usable(spec, rows):
    """Rows whose smt parses; a row that doesn't parse is dropped (and counted)."""
    good, bad = [], 0
    for r in rows or []:
        smt = (r.get("smt") or "").strip()
        if not smt:
            continue
        try:
            good.append((r.get("claim", ""), smt, spec.z3(smt)))
        except Exception:
            bad += 1
    return good, bad


def _model_text(m):
    return ", ".join(f"{d.name()}={m[d]}" for d in sorted(m.decls(), key=lambda d: d.name()) if d.name() != "pending")


def prove(spec, rows):
    """Contradictions and losses for one translation."""
    good, bad = _usable(spec, rows)
    facts, rules = spec.z3(spec.facts), spec.z3(spec.rules)
    note = And(*[z for _, _, z in good]) if good else And(True)
    contradictions = []
    for claim, smt, z in good:
        s = Solver(); s.add(facts, rules, z)
        if s.check() == unsat:
            contradictions.append({"claim": claim, "smt": smt})
    losses = {}
    for label, k in spec.must_keep.items():
        s = Solver(); s.add(rules, note, Not(spec.z3(k)))
        if s.check() == sat:
            losses[label] = _model_text(s.model())
    s = Solver(); s.add(rules, note)
    return {"contradictions": contradictions, "losses": losses, "consistent": s.check() == sat,
            "claims": len(good), "unparsed": bad}


def _vars(smt):
    return set(re.findall(r"[a-z_][a-z0-9_]*", smt)) - {"assert", "and", "or", "not", "pending", "true", "false", "ite", "distinct"}


def check_note(spec, note):
    """Findings both translations agree on. Returns dict with problems + per-translation detail."""
    a_rows, b_rows = translate(spec, note, 0), translate(spec, note, 1)
    if a_rows is None or b_rows is None:
        return {"error": "translation failed", "problems": []}
    a, b = prove(spec, a_rows), prove(spec, b_rows)
    disagree = sorted(set(a["losses"]) ^ set(b["losses"])) + (["contradiction"] if bool(a["contradictions"]) != bool(b["contradictions"]) else [])
    readings = [a, b]
    if disagree:  # a third reading breaks the tie: a finding stands when 2 of 3 show it
        c_rows = translate(spec, note, 2)
        if c_rows is not None:
            readings.append(prove(spec, c_rows))
    need = 2
    problems = []
    for label in sorted(set().union(*[r["losses"] for r in readings])):
        have = [r for r in readings if label in r["losses"]]
        if len(have) >= need:
            problems.append({"kind": "loss", "fact": label, "counterexample": have[0]["losses"][label]})
    seen = set()
    for i, r in enumerate(readings):
        for c in r["contradictions"]:
            votes = 1 + sum(any(_vars(c["smt"]) & _vars(d["smt"]) for d in o["contradictions"]) for j, o in enumerate(readings) if j != i)
            key = frozenset(_vars(c["smt"]))
            if votes >= need and key not in seen:
                seen.add(key)
                problems.append({"kind": "contradiction", "claim": c["claim"], "smt": c["smt"]})
    return {"problems": problems, "a": a, "b": b, "c": readings[2] if len(readings) > 2 else None, "disagree": disagree}


# ---- The Thanksgiving-dinner spec used by the evidence tests ------------------------------------
DINNER = Spec(
    ints={
        "people": "how many people the dinner is planned for",
        "deposit": "the hall deposit in dollars",
        "hall_start": "hour the hall booking starts (24h)", "hall_end": "hour the hall booking ends (24h)",
        "dinner_month": "month of the dinner (1-12)", "dinner_day": "day of month of the dinner",
        "signup_month": "month sign-ups close", "signup_day": "day of month sign-ups close",
        "curry_minutes": "minutes one batch of curry takes", "curry_tests": "times the curry recipe was tested",
        "retreat_people": "youth retreat headcount", "retreat_cost": "youth retreat cost per person in dollars",
        "retreat_month": "month of the youth retreat", "retreat_day": "day of month the youth retreat starts",
        "budget_total": "ministry fall budget in dollars", "budget_spent": "fall budget spent so far in dollars",
    },
    bools={
        "deposit_paid": "the hall deposit is paid",
        "john_curry": "John cooks the curry", "jeanine_curry": "Jeanine cooks the curry",
        "john_rice": "John handles the rice", "jeanine_rice": "Jeanine handles the rice",
        "second_rice_cooker": "the church kitchen has a second rice cooker",
    },
    facts="""
(assert (= people 60)) (assert (= deposit 150)) (assert deposit_paid)
(assert (= hall_start 16)) (assert (= hall_end 21))
(assert (= dinner_month 11)) (assert (= dinner_day 21)) (assert (= signup_month 11)) (assert (= signup_day 18))
(assert (= curry_minutes 50)) (assert (= curry_tests 2))
(assert john_curry) (assert jeanine_rice) (assert (not jeanine_curry)) (assert (not john_rice))
(assert (= retreat_people 25)) (assert (= retreat_cost 120)) (assert (= retreat_month 12)) (assert (= retreat_day 5))
(assert (= budget_total 3000)) (assert (= budget_spent 1240))
""",
    rules="""
(assert (< hall_start hall_end))
(assert (not (and john_curry jeanine_curry))) (assert (not (and john_rice jeanine_rice)))
""",
    must_keep={
        "60 people": "(assert (= people 60))",
        "Saturday, November 21": "(assert (and (= dinner_month 11) (= dinner_day 21)))",
        "hall from 4 PM": "(assert (= hall_start 16))",
        "hall until 9 PM": "(assert (= hall_end 21))",
        "$150 deposit": "(assert (= deposit 150))",
        "deposit is paid": "(assert deposit_paid)",
        "curry takes 50 minutes a batch": "(assert (= curry_minutes 50))",
        "curry tested twice": "(assert (= curry_tests 2))",
        "John cooks the curry": "(assert john_curry)",
        "Jeanine handles the rice": "(assert jeanine_rice)",
        "sign-ups close November 18": "(assert (and (= signup_month 11) (= signup_day 18)))",
    },
)

LONG_MUST_KEEP = {
    **DINNER.must_keep,
    "retreat: 25 people": "(assert (= retreat_people 25))",
    "retreat: $120 each": "(assert (= retreat_cost 120))",
    "retreat: December 5": "(assert (and (= retreat_month 12) (= retreat_day 5)))",
    "budget: $3,000": "(assert (= budget_total 3000))",
    "budget: $1,240 spent": "(assert (= budget_spent 1240))",
}


def spec_for(base):
    if base == "long":
        return Spec(DINNER.ints, DINNER.bools, DINNER.facts, DINNER.rules, LONG_MUST_KEEP)
    return DINNER


def with_update(spec, smt):
    """A spec whose trusted facts were updated by the session (a backed change, e.g. 60 -> 58)."""
    facts = spec.facts
    for m in re.finditer(r"\(= (\w+) [^)]+\)", smt):
        facts = re.sub(rf"\(assert \(= {m.group(1)} [^)]+\)\)", "", facts)
    return Spec(spec.ints, spec.bools, facts + smt, spec.rules, spec.must_keep)
