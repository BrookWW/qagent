# QAgent User Manual

This manual explains how to run QAgent locally and how to interpret its outputs.

## 1. Purpose

QAgent helps a researcher turn mathematical papers into theorem-level research-question candidates. It is designed for exploratory work: finding plausible short research directions, not certifying final mathematical novelty.

Use QAgent when you want:

- candidate theorem statements inspired by one or more papers;
- survey-guided checks against obvious duplicates;
- direct-corollary and known-result risk notes;
- proof-route and feasibility guidance;
- QED-style output folders for later human review.

## 2. Installation

Install dependencies:

```powershell
pip install -r requirements.txt
```

Make sure Codex CLI is installed and logged in.

Run the UI:

```powershell
python -m streamlit run app.py
```

## 3. Input Format

The best input gives an exact title, authors, and an open-access source.

Recommended:

```markdown
## Paper title
Authors: Author One; Author Two
URL: https://arxiv.org/abs/2501.01234
```

Also supported:

```markdown
Title: Paper title
Authors: Author One
URL: https://cvgmt.sns.it/paper/1234/
PDF URL: https://example.org/paper.pdf
DOI: optional
```

Local PDF:

```markdown
Title: Paper title
Authors: Author One
PDF Path: C:\Users\you\Desktop\papers\paper.pdf
```

Prefer arXiv, CVGMT, direct PDF URLs, and local PDFs. Journal landing pages and DOI-only input may fail to provide full text.

## 4. UI Settings

### Mode

`Deep Mode` is the recommended mode for serious question generation. It spends more time on evidence, survey, candidate validation, hard review, and final selection.

`Batch Mode` is for rough screening. Treat its outputs as low confidence.

### Question Style

`General research style` uses theorem skeletons, proof pressure points, adjacent-model transfer, and research-direction gates.

`Specialized transfer-pattern style` uses curated transfer-pattern prompts and is better when you want the system to stay close to established pattern libraries.

### n

The number of papers you are giving in the input box. The UI checks that the parsed paper count matches `n`.

### a

Candidate width parameter. QAgent asks for `(a + 1) * b` initial candidates per paper.

### b

Requested final questions per paper.

## 5. Run Workflow

1. Paste paper entries.
2. Choose mode, question style, `n`, `a`, and `b`.
3. Choose whether to try online fetching/search.
4. Optionally enter a Codex model override.
5. Click `Run Agent`.
6. Wait for the stages to complete.
7. Open the results browser in the UI.
8. Review final selected questions and all guidance files.

## 6. Main Output Files

For each final selected question:

- `problem_statement.tex`: theorem-style question statement.
- `additional_prove_human_help_global.md`: proof guidance and quality notes.
- `additional_verify_rule_global.md`: verification checklist.
- `survey_queries.md`: search queries and novelty-survey notes.
- `feasibility_analysis.md`: proof route, obstacles, and score discussion.
- `metadata.json`: backend, score, confidence, and selection metadata.

Important batch-level files:

- `batch_report.md`: summary of selected questions.
- `evidence_preflight.json`: whether PDFs/full text were found.
- `candidate_validation.json`: candidate structure and theorem-form issues.
- `hard_review.json`: candidate novelty/direct-corollary review.
- `quality_audit.json`: post-output quality guidance.

## 7. Confidence Labels

Low confidence means the output may still be useful, but one or more important checks were incomplete.

Common reasons:

- full PDF text was not completely read;
- novelty search found medium duplicate risk;
- final selected candidate came from fallback;
- proof route needs human confirmation;
- candidate statement was repaired from a weaker form.

Low-confidence output should not be treated as final research advice.

## 8. Manual GPT Pro Handoff

QAgent can create handoff prompts for GPT Pro web use. This is manual:

1. QAgent writes prompts under `outputs/{batch_id}/gpt_pro_handoff/`.
2. You copy a prompt into GPT Pro.
3. You save the JSON response into the expected result path.
4. You rerun or continue QAgent.

QAgent does not automate, scrape, or control the GPT Pro web page.

## 9. Recommended Human Review

Before using a generated problem:

1. Read the original paper.
2. Check the final theorem statement for correctness.
3. Verify the novelty survey manually.
4. Search arXiv, MathSciNet, zbMATH, Google Scholar, and journal databases yourself.
5. Try the first proof lemma.
6. Remove or rewrite any vague assumption.

QAgent is most useful when treated as a strong brainstorming and screening assistant.
