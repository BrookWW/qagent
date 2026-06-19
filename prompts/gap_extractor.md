# Gap Extractor Prompt

Generate possible research gaps from theorem_cards, proof_cards, method_cards, and limitation_cards.

Each gap card must include:

- gap_title
- gap_type
- known_result_from_input
- missing_case
- why_not_direct_restatement
- expected_tools
- possible_obstacles
- duplicate_risk_queries
- qed_gpt_attackability_guess
- sci_publishable_potential_guess
- nontriviality_guess

Rules:

- A gap must be based on a specific theorem, method, limitation, or fragile proof step.
- Do not merely restate a theorem from the paper.
- Prefer narrowed, theorem-level gaps that are nontrivial but attackable.
- Mark duplicate risk queries for a future survey agent.
- If only abstract/metadata is available, state that confidence is lower.
