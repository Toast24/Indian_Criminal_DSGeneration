# Indian Criminal Judgments: a Verified Dataset for Counterfactual Bias Testing

A pipeline that turns Indian Supreme Court criminal judgments into a structured, audited dataset, built to test whether LLMs change their predictions when a protected attribute (religion, caste, gender, age) is swapped in an otherwise identical case.

**Headline result:** extraction quality went from **10.7% incorrect cells (v1)** to **0.37% (v2)** under a Haiku judge, and **0.8%** under an independent Sonnet judge. The full story, with what worked and what didn't, is in [PROJECT_WRITEUP.md](PROJECT_WRITEUP.md).

## Dataset

| File | What it is |
|---|---|
| [`data/dataset_v2_250.csv`](data/dataset_v2_250.csv) | **The final dataset.** 250 cases x 54 columns, from the v2 extraction (Claude Haiku, full text, quote-first). Use this one. |
| `data/extracted_v2/<case>.json` | The same values, plus the supporting quote and page for every field, and any fields demoted to "Not stated". |
| `data/dataset_250_verified.csv` | The v1 extraction (local qwen3:8b) with step 2c verification flags. Kept as the baseline. |
| `data/dataset_base_cases.csv` | All ~500 usable v1 cases. |
| `selected_cases_850.txt` | The 850 case IDs selected from the court corpus. |
| `data/judge_sheet*.csv`, `data/judge_report*.txt` | Judge verdicts for every cell. `_v2` = Haiku judging v2, `_v2_sonnet` = Sonnet judging v2. |
| `data/counterfactual_prompts.csv` | Prompts for the bias experiments. |

Columns: case basics (offence, statutes, outcomes, sentence), people (gender, age, religion, caste, occupation, accused-victim relationship), offence (weapon, motive, premeditation, post-offence conduct), evidence and procedure, reasoning (arguments, precedents, sentencing factors), and `neutral_facts`, an outcome-free case summary for the counterfactual tests.

**Not included:** the 850 source judgment PDFs (405 MB) and the extracted text cache. Judgments are public records and can be re-downloaded; case IDs are in `selected_cases_850.txt`.

## Pipeline

```
PDF judgments
  -> step1-5   collect, filter, extract (local qwen3:8b, Ollama)         v1 dataset
  -> step2c    quote verification against the PDF text                   19% of cells flagged
  -> step6     LLM-as-judge audit (Claude, Batch API)                    10.7% incorrect
  -> step2v2   re-extract: full text, quote-first, sharper definitions   v2 dataset
  -> step6     judge again (Haiku and Sonnet)                            0.37% / 0.8% incorrect
```

| Script | Purpose |
|---|---|
| `step1_*.py` ... `step5_*.py` | Case selection, text extraction, batch building, v1 runs |
| `step2_extract.py`, `step2b_extract_extra.py` | v1 field extraction (`FIELDS`, `GROUPS`, prompts) |
| `step2c_verify.py` | Quote verification and consistency checks |
| `step2v2_extract.py` | v2 extraction through the Claude Batch API |
| `step6_llm_judge.py` | LLM judge: `submit`, `status`, `collect`, `report`, `dry` |
| `exp*.py`, `reasoning_probe.py`, `llm_clients.py` | Counterfactual bias experiments |

Prompts: each extractor and the judge send **one prompt per case** covering all columns (v1 sends one per field group). See `SYSTEM`, `DEFS` and `user_prompt()` in the step scripts. `python step6_llm_judge.py dry 1` writes the exact request without calling the API.

## Reproducing

```powershell
pip install anthropic pandas python-dotenv pdfplumber
$env:ANTHROPIC_API_KEY = "<your key>"           # never commit keys

python step2v2_extract.py submit 250            # v2 extraction (Batch API, ~$2)
python step2v2_extract.py collect
$env:JUDGE_TAG = "v2"
python step6_llm_judge.py submit                # Haiku judge, ~$1.30
python step6_llm_judge.py collect
# Sonnet judge: also set JUDGE_TAG=v2_sonnet and JUDGE_MODEL=claude-sonnet-5-5  (~$11)
```

The v1 steps need [Ollama](https://ollama.com) with `qwen3:8b`. Batches are resumable: submit skips cases that already have results.

## Caveats

- The headline accuracy comes from LLM judges, not human annotators. A human-checked sample is still needed for an absolute accuracy figure.
- v2 depends on a commercial API; v1 (local qwen3:8b) is the open baseline.
- 250 cases from one court; protected attributes are stated in only a minority of judgments.
- Sonnet returned no verdict for 678 of 13,500 cells (5%), concentrated in 13 cases.

## Security

API keys live in `.env` and `*_key.txt`, which are git-ignored. Do not commit them.
