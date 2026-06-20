# QAgent

QAgent is a local, no-API assistant for generating theorem-level mathematical research questions from papers.

Given paper titles, arXiv/CVGMT/open-PDF URLs, DOI-style metadata, or local PDF paths, QAgent tries to fetch and read the paper evidence, asks a logged-in Codex CLI backend to generate candidate questions, validates candidate structure, runs novelty/direct-corollary hard review, and exports QED-style final question folders.

QAgent is a research assistant, not an oracle. It does not guarantee novelty, correctness, publishability, or journal acceptance. A human mathematician should review every generated question before using it.

## Features

- Streamlit UI for batch paper input.
- No OpenAI API key required in the default mode.
- Uses Codex CLI from the user's logged-in local account/config.
- Prioritizes open full-text sources such as arXiv, CVGMT, direct PDFs, and local PDFs.
- Generates theorem-level candidate questions before final selection.
- Runs local candidate validation for structure, theorem form, direct-corollary risk, transfer evidence, and metadata consistency.
- Runs candidate-level novelty/search review when available.
- Exports final selected question folders with problem statements, proof guidance, verification notes, survey traces, feasibility analysis, and metadata.
- Marks weak evidence as low confidence instead of silently presenting it as certain.

## What QAgent Does Not Do

- It does not automatically control or scrape the GPT Pro web UI.
- It does not guarantee that Codex/GPT search found every related paper.
- It does not replace expert mathematical judgment.
- It does not guarantee identical outputs across machines, accounts, model versions, or dates.
- It does not include private run outputs, downloaded PDFs, or paper text in the public repository.

## Requirements

- Python 3.10 or newer.
- A working Codex CLI installation.
- A logged-in Codex CLI account.
- Internet access if you want online paper fetching/search.

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python -m streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Recommended Input

Use English field names. For each paper, provide title, authors, and an open URL when possible:

```markdown
## Exact paper title
Authors: First Author; Second Author
URL: https://arxiv.org/abs/2501.01234

---

Title: Exact paper title from CVGMT or another open repository
Authors: First Author; Second Author
URL: https://cvgmt.sns.it/paper/1234/
PDF URL: optional direct PDF URL if available

---

Title: Local PDF example
Authors: First Author
PDF Path: C:\Users\you\Desktop\papers\paper.pdf
```

Strongly recommended sources:

- arXiv abstract links or PDF links;
- CVGMT paper pages;
- direct PDF URLs;
- local PDFs.

DOI-only or journal-page-only input is less reliable because full text is often harder to fetch.

## Main Workflow

1. Resolve paper entries and fetch metadata/PDF/full text when possible.
2. Run evidence preflight and mark low-confidence papers when full text is incomplete.
3. Run paper-level literature survey.
4. Generate candidate questions.
5. Validate candidate schema and theorem form.
6. Repair candidates when validation fails.
7. Run candidate-level novelty/direct-corollary review.
8. Run hard review and candidate replacement when useful.
9. Run final selection from the hard-review allowlist.
10. Write final outputs and quality guidance.

See [docs/architecture.md](docs/architecture.md) for a stage-by-stage diagram.

## UI Parameters

- `Deep Mode`: higher-quality mode for smaller batches.
- `Batch Mode`: rough screening mode for larger batches.
- `n`: number of input papers expected by the UI.
- `a`: candidate width parameter. Initial candidates per paper are `(a + 1) * b`.
- `b`: final questions requested per paper.
- `Question style`: general research style or specialized transfer-pattern style.
- `Model override`: optional Codex CLI model override. Leave blank to use the local Codex CLI default.

## Model Backend

The default backend is:

```text
Codex CLI logged-in account, no API key
```

If no model override is supplied, QAgent uses the local Codex CLI default from the user's account/config. If a model override is entered, QAgent records it and calls Codex CLI with that model when supported.

Every run writes backend metadata, including:

- backend type;
- model;
- model source;
- Codex CLI version;
- whether model override appears supported.

## Optional GPT Pro Web Handoff

QAgent can write manual GPT Pro handoff prompts under:

```text
outputs/{batch_id}/gpt_pro_handoff/
```

This is a manual workflow. The user copies prompts into GPT Pro web sessions and saves JSON replies back into the expected result files. QAgent does not log in to or control the GPT Pro website.

## Output Structure

Final selected questions are written as:

```text
outputs/{batch_id}/{paper_id}/selected/{question_id}/problem_statement.tex
outputs/{batch_id}/{paper_id}/selected/{question_id}/additional_prove_human_help_global.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/additional_verify_rule_global.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/survey_queries.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/feasibility_analysis.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/metadata.json
```

Candidate and diagnostic artifacts are also written under `outputs/{batch_id}/`.

The public repository intentionally ignores `outputs/`, generated batch inputs, downloaded PDFs, and extracted paper text.

## Documentation

- [User manual](docs/user_manual.md)
- [Architecture](docs/architecture.md)
- [Reproducibility notes](docs/reproducibility.md)

## Development Checks

Run the test suite:

```powershell
python -m unittest discover -s tests
```

Compile the main files:

```powershell
python -m py_compile app.py src\qagent\candidate_validator.py src\qagent\runner.py src\qagent\hard_review.py
```

## Publishing Safety

Before pushing to GitHub, make sure these are not committed:

- `outputs/`
- `data/batch_*.md`
- `data/pdfs/`
- `data/paper_text/`
- `.codex/`
- `.agents/`
- private logs or paper PDFs

## Authors

- Haotong Fu <2301110012@pku.edu.cn>
- Wei Wang <wwmath166@outlook.com>

## Acknowledgements

The authors thank the following people for helpful discussions, feedback, and support:

- Zeyu Jin <jinzy@pku.edu.cn>
- Wentao Long
- Ziyu Wang <wangziyu-edu@stu.pku.edu.cn>
- Shengquan Xiang <2301110012@pku.edu.cn>
- Zhifei Zhang <zfzhang@math.pku.edu.cn>

## License

MIT License. See [LICENSE](LICENSE).
