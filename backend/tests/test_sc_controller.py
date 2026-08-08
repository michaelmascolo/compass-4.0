"""Deterministic unit tests for the Sentence Craft controller (no LLM). Covers spec §14."""
import sys; sys.path.insert(0, "/app/backend")
import functional_v3 as sc

def A(**k):  # active-sentence analysis helper
    d = {"importance_to_whole": "supporting", "teaching_priority": "teach_now",
         "observed_sentence_patterns": []}
    d.update(k); return d

fails = []
def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond: fails.append(name)

# domain mapping
check("map assumes-knowledge -> orient_reader", sc.sc_domain_for_pattern("assumes knowledge the reader lacks") == "orient_reader")
check("map run-on -> organize_sentence", sc.sc_domain_for_pattern("this is a run-on sentence") == "organize_sentence")
check("map vague -> make_precise", sc.sc_domain_for_pattern("vague pronoun") == "make_precise")
check("map transition -> connect_thought", sc.sc_domain_for_pattern("missing transition") == "connect_thought")

# single occurrence != stable pattern; repeated evidence -> confidence
p1 = sc.sc_update_patterns([], ["make_precise"])
check("single occurrence not a pattern", p1[0]["status"] == "occurrence" and p1[0]["confidence"] == "tentative")
p2 = sc.sc_update_patterns(p1, ["make_precise"])
check("2nd instance -> pattern/moderate", p2[0]["status"] == "pattern" and p2[0]["confidence"] == "moderate")
p3 = sc.sc_update_patterns(p2, ["make_precise"])
check("3rd instance -> high confidence", p3[0]["confidence"] == "high")

# no false pattern: unrelated domains stay separate, none promoted
pmix = sc.sc_update_patterns([], ["make_precise", "connect_thought", "orient_reader"])
check("no false pattern collapse", all(x["status"] == "occurrence" for x in pmix) and len(pmix) == 3)

# relevance before improvement -> route upward (even with a nice grammatical issue present)
r = sc.sc_select_operation(A(importance_to_whole="distracting", observed_sentence_patterns=["passive construction"]), [])
check("distracting sentence routes upward", r["decision"] == "route_upward")

# sufficiency before excellence -> advance
r = sc.sc_select_operation(A(teaching_priority="no_instruction_needed", observed_sentence_patterns=[]), [])
check("sufficient sentence advances", r["decision"] == "advance")

# recurrence influences selection: recurring make_precise (2 instances) beats an isolated strengthen issue
patt = sc.sc_update_patterns(sc.sc_update_patterns([], ["make_precise"]), ["make_precise"])  # 2 instances
r = sc.sc_select_operation(A(observed_sentence_patterns=["vague reference", "passive construction"]), patt)
check("recurring pattern selected", r["decision"] == "operate" and r["operation"] == "make_precise" and r["pattern_recurrent"])

# higher leverage can win when NOT overridden by a recurring pattern:
# organize_sentence (overload) present with an isolated make_precise -> organize wins on leverage
r = sc.sc_select_operation(A(observed_sentence_patterns=["run-on sentence", "vague word"]), [])
check("higher-leverage organize_sentence wins", r["operation"] == "organize_sentence")

# fading: scaffold decreases with evidence of control
base = sc.sc_update_patterns([], ["connect_thought"])  # more_support
after1 = sc.sc_record_performance(base, "connect_thought", independent=False)
check("scaffold fades after supported success", sc.sc_scaffold_for_pattern(sc._sc_find_pattern(after1, "connect_thought")) == "guided_attention")
after2 = sc.sc_record_performance(after1, "connect_thought", independent=True)
check("scaffold fades to independent_check after independent", sc.sc_scaffold_for_pattern(sc._sc_find_pattern(after2, "connect_thought")) == "independent_check")
after3 = sc.sc_record_performance(after2, "connect_thought", independent=True, recognized=True)
p = sc._sc_find_pattern(after3, "connect_thought")
check("independent recognition -> controlled + independent scaffold", p["status"] == "controlled" and sc.sc_scaffold_for_pattern(p) == "independent")

# controlled pattern no longer counted as recurrent-for-selection
r = sc.sc_select_operation(A(observed_sentence_patterns=["missing transition", "vague word"]), after3)
check("controlled pattern not force-selected", not (r["operation"] == "connect_thought" and r["pattern_recurrent"]))

# focus labels exist for every operation, none expose internal names
check("focus label for every op", all(op in sc.SC_FOCUS_LABEL for op in sc.SC_OPERATIONS))

# ---- surfaced payload architecture (must leave room for pattern-focused SC behavior) ----
# simulate an 'operate' turn diagnostics with an established recurring pattern
_patt = sc.sc_update_patterns(sc.sc_update_patterns([], ["make_precise"]), ["make_precise"])  # 2 instances
_sel = sc.sc_select_operation(A(observed_sentence_patterns=["vague reference"]), _patt)
_diag = {"sentence_count": 4, "thesis": "Homework harms rest.", "active_sentence_index": 1,
         "active_sentence_text": "It is bad.", "communicative_function": "supporting",
         "decision": "operate", "selection": _sel,
         "patterns_after": [dict(p) for p in _patt]}
pay = sc._sc_payload_from_diag(_diag, sc.SC_FOCUS_LABEL.get(_sel["operation"], ""))
_req = ["active", "decision", "active_sentence_index", "active_sentence_text", "focus_label",
        "operation", "scaffold_level", "pattern", "pattern_influenced_operation", "evidence_of_control"]
check("payload has all architecture fields", all(k in pay for k in _req))
check("payload active + text surfaced (index-robust)", pay["active"] and pay["active_sentence_text"] == "It is bad.")
check("payload focus_label is learner-facing (no internal op name)", pay["focus_label"] and pay["focus_label"] not in sc.SC_OPERATIONS)
check("payload pattern hypothesis present", isinstance(pay["pattern"], dict) and pay["pattern"]["domain"] == "make_precise")
check("payload records pattern influence", pay["pattern_influenced_operation"] is True)
check("payload carries control evidence object", isinstance(pay["evidence_of_control"], dict))

# completion diagnostics -> graceful payload (no selection / no pattern)
_cdiag = {"sentence_count": 4, "thesis": "", "active_sentence_index": None, "decision": "complete"}
cpay = sc._sc_payload_from_diag(_cdiag, "Reviewing the whole paragraph")
check("completion payload graceful", cpay["decision"] == "complete" and cpay["pattern"] is None and cpay["active_sentence_text"] == "")

print("\nRESULT:", "PASS" if not fails else f"FAIL ({len(fails)})")
