"""R1b patcher: replace the verbose developmental_cognition schema block in functional_v3.py
with a SLIM schema (learner-critical + SC-governing + terse reasoning anchors only).
Idempotent-ish: aborts if the start/end anchors are not found exactly once."""
import io

PATH = "/app/backend/functional_v3.py"
START = "        '  \"developmental_cognition\": {'\n"
END = "        'or absent/compressed\"]}},\\n'\n"

with open(PATH) as f:
    lines = f.readlines()

si = [i for i, l in enumerate(lines) if l == START]
ei = [i for i, l in enumerate(lines) if l == END]
assert len(si) == 1, f"start anchor count={len(si)}"
assert len(ei) == 1, f"end anchor count={len(ei)}"
s, e = si[0], ei[0]
assert e > s, (s, e)

# The slim block: ONE JSON object fragment for developmental_cognition. Single-quoted Python
# string literals; no apostrophes inside (avoids escaping). Keeps commas valid. Ends '}},\n'
# (closes learner_orientation, then developmental_cognition), leaving the outer object intact.
slim = (
    '        \'  "developmental_cognition": {\'\n'
    '        \'"communicative_task": "<=25 words: what the ASSIGNMENT requires the communication to accomplish, derived from the assignment not the draft", \'\n'
    '        \'"communicative_capacity": {"writing_unit": "sentence|paragraph|multi_paragraph_response|essay|other|uncertain (a one-paragraph Teacher-Review assignment is ALWAYS paragraph)", "central_communicative_movement": "the ONE controlling movement this unit sustains", "current_communicative_load": "low|moderate|high|uncertain (from number/complexity of functions carried, not word count)", "remaining_capacity": "substantial|moderate|limited|none|uncertain", "remaining_communicative_budget": "substantial|moderate|one_high_value_move|exhausted|uncertain", "overload_risk": "low|emerging|high|uncertain", "scope_status": "underdeveloped|proportionate|approaching_capacity|overloaded|uncertain", "material_to_defer_or_exclude": ["nonessential ideas that would open a NEW line of development"]}, \'\n'
    '        \'"structural_load_analysis": {"central_communicative_movement": "the ONE controlling movement", "current_structural_work": ["the major local arguments/jobs ALREADY present, reworded from the draft, invent nothing"], "secondary_trajectories": ["lines that no longer serve the central movement -> should move/defer/condense"], "competing_structural_work": ["distinct independent trajectories competing inside this one unit"], "redundant_structural_work": ["spans repeating work already done"], "structural_load_status": "underloaded|proportionate|crowded|overloaded|uncertain", "structural_pruning_needed": "no|light|moderate|substantial|uncertain", "recommended_structural_operation": "keep|combine|condense|remove|move_elsewhere|reorganize|transition|uncertain", "confidence": "h|m|l"}, \'\n'
    '        \'"task_orientation_relation": {"value": "<=20 words: relation of the learner apparent aim to the assignment demand (directly responsive|partially responsive|related but incomplete|tangential|contradictory|unclear + basis)"}, \'\n'
    '        \'"structural_relations_and_dependencies": {"value": ["<=8 words each: the communicative organization relations the learner must construct for this task"]}, \'\n'
    '        \'"whole_communication_requirements": {"value": "<=25 words: the MINIMUM relational organization that fulfils the assignment (no prescribed sentences)"}, \'\n'
    '        \'"provisional_whole_communication": {"value": "<=25 words: the KIND of whole THIS learner can realistically construct next, within their horizon"}, \'\n'
    '        \'"instructional_center": {"value": "<=20 words: the NEXT structurally necessary coordination to develop now"}, \'\n'
    '        \'"current_instructional_sufficiency": {"value": "<=20 words: what counts as ENOUGH progress on the instructional_center this turn (not perfection)"}, \'\n'
    '        \'"instructional_horizon": "<=20 words: the upper bound of what this learner can construct successfully this interaction", \'\n'
    '        \'"developmental_constraint": {"value": "<=20 words: what currently limits this learner coordinative organization (a limit in the learner, not a flaw in the essay)"}, \'\n'
    '        \'"task_relative_adequacy": {"value": "inadequate|approaching_adequacy|adequate|uncertain — is the response self-contained and coherent for THIS task? not inadequate merely because more could be added", "material_gap": "SPECIFIC gap that PREVENTS a reasonable reader understanding the answer; empty string if none", "transition_recommendation": "stay_conceptual|transition_to_sentence_craft|uncertain"}, \'\n'
    '        \'"learner_relative_sufficiency": {"value": "not_yet_sufficient|approaching_sufficiency|sufficient|uncertain", "task_answered": "<=15 words: has THIS learner answered the assigned question adequately", "learner_accessible_target": "the highest meaningful organization THIS learner can realistically construct this episode; ONCE SET keep IDENTICAL across turns, never raise it because the learner reached it", "accessible_target_achieved": "yes|no|partial|uncertain — yes immediately once the learner performs the pinned target", "episode_target_status": "set_this_turn|kept|refined_wording|revised_wrong_diagnosis", "episode_target_revision_reason": "empty unless revised_wrong_diagnosis then one clause", "transition_recommendation": "stay_conceptual|sentence_craft|uncertain"}, \'\n'
    '        \'"timely_success_status": {"value": "not_yet_available|within_reach|achieved|missed_opportunity", "what_changed": "empty unless achieved", "how_it_improved": "empty unless achieved", "now_meets_task": "true|false"}, \'\n'
    '        \'"sentence_craft_readiness": {"value": "not_ready|nearly_ready|ready|uncertain — is the constructible whole sufficient to shift from CONSTRUCTING meaning to REFINING sentences", "developmental_work_remaining": "concise: developmental work needed before Sentence Craft; empty string if none"}, \'\n'
    '        \'"completion_readiness": {"value": "not_ready|nearly_ready|ready|uncertain — is the writing EPISODE ready to CLOSE (sufficient whole, no unresolved issue prevents fulfilling the task)"}, \'\n'
    '        \'"completion_message": {"completion_statement": "learner-facing ONE sentence that the paragraph now communicates its central idea clearly enough FOR THIS ASSIGNMENT; empty unless completion_readiness ready/nearly_ready", "achievement_statement": "learner-facing: name the ACTUAL work the learner accomplished, no generic praise; empty if not ready", "boundary_statement": "learner-facing: sufficient for the task not perfect forever; empty if not ready"}, \'\n'
    '        \'"learner_orientation": {"current_direction": "CONCISE learner-friendly no jargon: the whole the learner is building", "where_we_are": "CONCISE: what the learner has already established", "current_work": "CONCISE: what is being developed now and why it matters to the whole", "likely_next_step": "CONCISE: the likely next move if the present work becomes sufficient", "estimated_remaining_moves": "one of: probably one more step | probably one or two more steps | several steps remain | not yet estimable", "orientation_revision_reason": "empty unless the direction changed after a student revision"}},\\n\'\n'
)

new_lines = lines[:s] + [slim] + lines[e + 1:]
with open(PATH, "w") as f:
    f.writelines(new_lines)
print(f"Replaced developmental_cognition block: old lines {s}..{e} ({e-s+1} src lines) -> slim.")
