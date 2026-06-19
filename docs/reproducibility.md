# Reproducibility Notes

QAgent is locally runnable, but exact outputs are not guaranteed to be bit-for-bit reproducible.

## What Can Be Reproduced

Another user can reproduce:

- the Streamlit UI workflow;
- the local file structure;
- candidate validation behavior;
- hard-review artifact structure;
- final selected question folder structure;
- tests in `tests/`;
- mock CLI behavior when available.

## What May Differ

Generated mathematical questions may differ because:

- Codex CLI account/config differs;
- model versions change over time;
- model override availability differs;
- web search results change;
- PDFs may become unavailable;
- arXiv/CVGMT/journal pages may change;
- local PDF extraction can vary by PDF formatting;
- optional GPT Pro handoff is manual and user-dependent.

## Recommended Reproducible Setup

1. Record the commit hash.
2. Record Python version.
3. Record Codex CLI version.
4. Save `backend_info.json` from each run.
5. Use exact same paper URLs or local PDFs.
6. Keep `try_online` setting fixed.
7. Keep `n`, `a`, `b`, mode, and question style fixed.

## Public Repository Policy

The repository should not include:

- generated `outputs/`;
- downloaded PDFs;
- extracted paper text;
- private batch inputs;
- local Codex state;
- local agent state;
- private run logs.

The `.gitignore` is configured to exclude these by default.

## Interpreting Results

Treat generated questions as research leads, not final claims. Even when QAgent marks a question as plausible, a human should independently verify:

- theorem statement correctness;
- assumptions and domains;
- novelty;
- related literature;
- proof feasibility;
- journal fit.
