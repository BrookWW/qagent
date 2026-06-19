from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_gpt_pro_handoff(output_dir: str | Path, batch_id: str, n: int, a: int, b: int) -> dict[str, Any]:
    """Create per-paper GPT Pro web prompts for manual parallel expert review.

    This does not automate the ChatGPT/GPT Pro web UI. It creates a safe handoff
    package that can be pasted into GPT Pro sessions and later imported by Codex.
    """
    output_path = Path(output_dir)
    handoff_dir = output_path / "gpt_pro_handoff"
    prompts_dir = handoff_dir / "prompts"
    results_dir = handoff_dir / "results"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    prompts: list[dict[str, str]] = []
    initial = (a + 1) * b
    for i in range(1, n + 1):
        paper_id = f"paper_{i:03d}"
        paper_dir = output_path / paper_id
        prompt_path = prompts_dir / f"{paper_id}_gpt_pro_prompt.md"
        result_path = results_dir / f"{paper_id}.json"
        prompt_path.write_text(
            _build_prompt(batch_id, paper_id, paper_dir, initial),
            encoding="utf-8",
        )
        prompts.append(
            {
                "paper_id": paper_id,
                "prompt_path": prompt_path.as_posix(),
                "expected_result_path": result_path.as_posix(),
            }
        )

    manifest = {
        "backend": "gpt_pro_web_handoff",
        "mode": "manual_parallel_web",
        "direct_web_automation": False,
        "batch_id": batch_id,
        "n": n,
        "a": a,
        "b": b,
        "initial_candidates_per_paper": initial,
        "note": "QAgent does not automate the GPT Pro web UI. Copy prompts into GPT Pro in parallel and save JSON replies in results/.",
        "prompts": prompts,
    }
    (handoff_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (handoff_dir / "README.md").write_text(
        "# GPT Pro Parallel Handoff\n\n"
        "This directory contains one prompt per paper for external GPT Pro web use.\n\n"
        "1. Copy prompts from `prompts/` into GPT Pro web sessions.\n"
        "2. Save each JSON reply as `results/paper_###.json`.\n"
        "3. Continue QAgent; Codex prompts are instructed to use those results when present.\n\n"
        "QAgent does not automate the GPT Pro web UI or scrape ChatGPT pages.\n",
        encoding="utf-8",
    )
    return manifest


def write_gpt_pro_final_selection_handoff(output_dir: str | Path, batch_id: str, n: int, b: int) -> dict[str, Any]:
    """Create a GPT Pro web prompt for final candidate selection."""
    output_path = Path(output_dir)
    handoff_dir = output_path / "gpt_pro_handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    result_path = handoff_dir / "final_selection_result.json"
    prompt_path = handoff_dir / "final_selection_prompt.md"
    prompt_path.write_text(_build_final_selection_prompt(batch_id, output_path, n, b), encoding="utf-8")
    manifest_path = handoff_dir / "final_selection_manifest.json"
    manifest = {
        "backend": "gpt_pro_web_handoff",
        "mode": "manual_parallel_web_final_selection",
        "direct_web_automation": False,
        "batch_id": batch_id,
        "n": n,
        "b": b,
        "prompt_path": prompt_path.as_posix(),
        "expected_result_path": result_path.as_posix(),
        "note": "Copy this prompt into GPT Pro after candidate generation and hard review. Save the JSON reply to final_selection_result.json.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_prompt(batch_id: str, paper_id: str, paper_dir: Path, initial: int) -> str:
    profile = _read_json(paper_dir / "paper_profile.json") or {}
    theorem_cards = _read_json(paper_dir / "theorem_cards.json") or []
    proof_cards = _read_json(paper_dir / "proof_cards.json") or []
    limitation_cards = _read_json(paper_dir / "limitation_cards.json") or []
    gap_cards = _read_json(paper_dir / "gap_cards.json") or []
    paper_survey = _read_json(paper_dir / "paper_literature_survey.json") or {}
    title = profile.get("title") or profile.get("paper_title") or paper_id
    return f"""You are an external GPT Pro mathematical expert for QAgent.

Batch: {batch_id}
Paper ID: {paper_id}
Paper title: {title}

Generate exactly {initial} theorem-level candidate research questions and survey each one.

Hard rules:
- Follow clean theorem-level problem rules.
- Do not reproduce the input paper's main theorem.
- Use the paper_literature_survey evidence as a hard negative map before proposing candidates.
- Do not generate directions listed under do_not_generate or likely_known_directions unless you explicitly mark them as rejected.
- Prefer small but real SCI-level theorem targets.
- Do not put metadata/confidence/novelty/proof-agent prose inside q environments.
- Do not scrape Google Scholar.

Return JSON only:
{{
  "paper_id": "{paper_id}",
  "paper_title": "{title}",
  "candidate_questions": [],
  "ranked_questions": [],
  "survey_notes": [],
  "expert_summary": ""
}}

Paper profile:
```json
{json.dumps(profile, ensure_ascii=False, indent=2)}
```

Theorem cards:
```json
{json.dumps(theorem_cards, ensure_ascii=False, indent=2)}
```

Proof cards:
```json
{json.dumps(proof_cards, ensure_ascii=False, indent=2)}
```

Limitation cards:
```json
{json.dumps(limitation_cards, ensure_ascii=False, indent=2)}
```

Gap cards:
```json
{json.dumps(gap_cards, ensure_ascii=False, indent=2)}
```

Paper-level literature survey:
```json
{json.dumps(paper_survey, ensure_ascii=False, indent=2)}
```
"""


def _build_final_selection_prompt(batch_id: str, output_dir: Path, n: int, b: int) -> str:
    summaries: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        paper_id = f"paper_{i:03d}"
        paper_dir = output_dir / paper_id
        summaries.append(
            {
                "paper_id": paper_id,
                "paper_profile": _read_json(paper_dir / "paper_profile.json"),
                "candidate_questions": _read_json(paper_dir / "candidate_questions.json"),
                "ranked_questions": _read_json(paper_dir / "ranked_questions.json"),
                "candidate_quality_flags": _read_json(paper_dir / "candidate_quality_flags.json"),
            }
        )
    return f"""You are an external GPT Pro mathematical critic for QAgent final selection.

Batch: {batch_id}

Task:
- For each paper, choose exactly {b} final selected questions from the existing candidates.
- Reject direct reproductions, likely known theorems, template/generic problems, weak theorem forms, and candidates without a plausible proof sprint.
- Prefer clean theorem-level transfer/sharpness/quantitative/boundary/endpoint problems with small SCI-level potential.
- Do not invent new candidate IDs.
- If fewer than {b} candidates are acceptable for a paper, mark the shortage honestly and explain why.

Return JSON only:
{{
  "batch_id": "{batch_id}",
  "final_selection": [
    {{
      "paper_id": "paper_001",
      "selected_question_ids": [],
      "selection_rationales": {{}},
      "rejected_question_ids": [],
      "warnings": []
    }}
  ]
}}

Candidate evidence:
```json
{json.dumps(summaries, ensure_ascii=False, indent=2)}
```
"""
