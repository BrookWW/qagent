# Deep Paper Reader Prompt

Read the richest available source for one mathematical paper: PDF text, HTML full text, abstract, or user metadata.

Your task is to build `paper_profile.json`.

Extract:

- title
- authors
- year
- source
- abstract
- mathematical area
- model class
- equation or functional
- main objects
- main results
- methods
- confidence level
- whether full text was read
- reading warnings
- whether the evidence is strong enough for high-confidence theorem-level question generation

Rules:

- Mark uncertain content explicitly.
- If only abstract/metadata is available, set confidence to low or medium.
- Do not invent theorem details not supported by the text.
- Prefer precise mathematical nouns over generic summaries.
- If theorem/proof/gap evidence is weak, say so directly. Prefer `needs deeper reading` over overconfident problem generation.
- The reader should also support `paper_reading_quality.json`, which records evidence score, theorem-card strength, proof coverage, method coverage, gap coverage, warnings, and downstream policy.
