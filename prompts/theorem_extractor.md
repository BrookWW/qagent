# Theorem Extractor Prompt

Extract theorem, proposition, lemma, and corollary cards from the available paper text.

Each theorem card must include:

- theorem_label
- theorem_type
- assumptions
- conclusion
- domain
- dimension
- boundary condition
- regularity class
- parameter range
- dependencies
- source excerpt or source summary
- confidence: high/medium/low

Rules:

- Preserve the distinction between exact excerpts and summaries.
- If a statement is incomplete due to extraction quality, mark confidence low.
- Do not turn motivational prose into a theorem card unless it clearly states a result.
