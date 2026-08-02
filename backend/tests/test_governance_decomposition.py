"""Unit tests for the Compass Governance v1 Stage-2 decomposition
(triage_experiment.ROUTE_LENS_MAP + resolvers + directive builder).
Pure/synchronous — no LLM calls. Run: python -m pytest tests/test_governance_decomposition.py
or: python tests/test_governance_decomposition.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import triage_experiment as TX


def _act(route, dim="", prev="none", prior=False, ios=None):
    return TX.resolve_route_activation(
        {"instructional_route": route, "highest_leverage_dimension": dim,
         "prev_target_status": prev, "relevant_instructional_objects": ios or []}, prior)


def test_every_route_mapped():
    for r in ("stall_support", "inside_out_clarification", "outside_in_reader_task",
              "convention_instruction", "transfer_test", "support_fading"):
        assert r in TX.ROUTE_LENS_MAP


def test_stall_runs_core_only_no_new_target():
    a = _act("stall_support", prev="unchanged")
    assert a["active_lenses"] == []
    assert a["may_select_new_target"] is False


def test_inside_out_activates_purpose_and_io():
    a = _act("inside_out_clarification", dim="central claim")
    assert "M6" in a["active_lenses"] and "IO" in a["active_lenses"]
    assert "M8" in a["dormant_lenses"] and "M9" in a["dormant_lenses"]


def test_outside_in_reader_plus_dimension_lens():
    assert _act("outside_in_reader_task", dim="evidence-interpretation gap")["active_lenses"] == ["M12", "M8"]
    assert _act("outside_in_reader_task", dim="paragraph-to-paragraph coherence")["active_lenses"] == ["M12", "M9"]
    assert _act("outside_in_reader_task", dim="the ending merely stops")["active_lenses"] == ["M12", "M10"]
    # reader-only when no content keyword matches
    assert _act("outside_in_reader_task", dim="clarity for a lay reader")["active_lenses"] == ["M12"]


def test_convention_runs_conv_only():
    a = _act("convention_instruction", dim="parallel structure")
    assert a["active_lenses"] == ["CONV"]
    for c in ("M7", "M8", "M9", "M10", "M12", "IO"):
        assert c in a["dormant_lenses"]


def test_transfer_and_fading_allow_consolidation_no_new_target():
    for r in ("transfer_test", "support_fading"):
        a = _act(r, prev="resolved", prior=True)
        assert a["active_lenses"] == ["M13"]
        assert a["may_select_new_target"] is False
        assert a["consolidation_allowed"] is True and a["fading_allowed"] is True


def test_revision_lens_added_on_prior_draft():
    a = _act("outside_in_reader_task", dim="evidence", prior=True)
    assert "M13" in a["active_lenses"]
    b = _act("outside_in_reader_task", dim="evidence", prior=False)
    assert "M13" not in b["active_lenses"]


def test_prev_unchanged_forbids_new_target():
    assert _act("outside_in_reader_task", dim="evidence", prev="unchanged")["may_select_new_target"] is False


def test_prev_resolved_enables_consolidation():
    assert _act("outside_in_reader_task", dim="evidence", prev="resolved")["consolidation_allowed"] is True


def test_empty_route_defaults_safely():
    assert _act("")["route"] == TX._DEFAULT_ROUTE


def test_all_lenses_partitioned_active_or_dormant():
    a = _act("outside_in_reader_task", dim="evidence", prior=True)
    universe = set(TX.ALL_CONTENT_LENSES + ["M13"])
    assert set(a["active_lenses"]) | set(a["dormant_lenses"]) == universe
    assert set(a["active_lenses"]).isdisjoint(a["dormant_lenses"])


def test_directive_does_not_create_competing_constitution():
    ov = TX.build_focused_override(
        {"instructional_route": "outside_in_reader_task", "inside_or_outside": "outside_in",
         "prev_target_status": "none", "learner_state": "engaged",
         "highest_leverage_dimension": "evidence", "route_confidence": 0.8, "rationale": "x"}, False)
    assert "does not replace, revise, weaken, or supersede" in ov
    assert "authoritative" in ov.lower()
    assert "route_fallback_required" in ov
    assert "EXACTLY TWO internal candidate" in ov


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            passed += 1
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
