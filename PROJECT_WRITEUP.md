# Building a Verified Dataset for Bias Testing on Indian Supreme Court Criminal Judgments

*Working notes for a blog post. This document covers what we built, what worked, what didn't, and what comes next. Figures are as of 24 Nov 2026.*

---

## 1. Goal

We want to test whether LLMs show **bias** when they reason about Indian criminal cases. We give a model a neutral description of a real Supreme Court case, then change one protected attribute, such as religion, caste, gender or age, and check whether its predicted outcome or sentence changes.

Counterfactual tests like this need a dataset where every case has:
- a **neutral fact summary** that does not reveal the outcome,
- the **protected attributes** that the judgment actually states (we must not guess them),
- the **legally relevant facts** (offence, evidence, weapon, motive, sentencing factors), so that we can show the attribute is the only thing changing,
- the **real outcome**, as ground truth.

No such dataset existed, so we built one from the judgment PDFs. Most of the work turned out to be making sure the extracted values are correct.

---

## 2. Dataset

| Item | Value |
|---|---|
| Source | Indian Supreme Court judgments (PDFs), criminal appeals |
| Usable cases extracted | ~500 (after filtering out non-criminal and unusable PDFs) |
| Verified core set | **250 cases** (`data/dataset_250_verified.csv`) |
| Columns per case | 54 extracted fields, plus metadata and verification columns |
| Case ID list shared with a collaborator | 850 IDs |

**Field groups:**
- **Case basics:** title, offence category, statutory provisions, number of offences, high court outcome, final outcome, sentence, imprisonment type, fine.
- **People:** number of accused; accused and victim gender, age, religion and caste; accused occupation; the relationship between accused and victim.
- **Offence:** weapon, motive, premeditation, attempt or completion, aggravating circumstances, post-offence conduct.
- **Evidence and procedure:** evidence type, key evidence accepted, confession, investigation status, procedural irregularity, appeal history, trial duration.
- **Reasoning:** prosecution and defence arguments, legal principle applied, precedents relied on, sentencing rationale, the judicial aggravating and mitigating factors.
- **neutral_facts:** a summary written to keep out the outcome, names, and protected attributes. This is the text the counterfactual tests change.

---

## 3. Pipeline

```
PDF judgments
   │
   ├─ Steps 1–5  collect, filter, extract (local qwen3:8b via Ollama)        → dataset_base_cases.csv
   │
   ├─ Step 2c    quote verification against the PDF text (rule-based + LLM) → verification_sheet.csv
   │
   ├─ Step 6     LLM-as-judge audit (Claude Haiku 5.5, Batch API)           → judge_sheet.csv  (v1: 10.7% incorrect)
   │
   ├─ Step 2 v2  re-extraction: full text, quote-first, sharper definitions → extracted_v2/
   │
   └─ Step 6     judge again on v2                                         → judge_sheet_v2.csv (0.37% incorrect)
```

### Steps 1–5: first extraction (v1)
- **Model:** qwen3:8b running locally through Ollama, in sequential batches of 150 cases.
- **Context limit:** the model saw at most 36k characters of each judgment. We kept the first 65% and the last 35% of that budget and dropped the middle.
- **Passes:** one pass for the base fields (`step2_extract.py`), then extra passes for the offence, evidence, procedure and reasoning field groups (`step2b_extract_extra.py`).
- **Normalisation:** rule-based clean-up of sections, sentences and "Not stated" values.

### Step 2c: quote verification
- For every field, the model gives a supporting quote, and we look for that quote in the PDF text.
- Each cell is labelled verified, not stated, quote not found, unsupported, value mismatch, or "not stated, check" (the judgment contains keywords that suggest the value is there).
- We also ran cross-field consistency checks, for example a cited section that never appears in the judgment.
- **Result on 250 cases:** 19% of cells flagged for review. The run took about 10 hours locally.

### Step 6: LLM-as-judge (`step6_llm_judge.py`)
- **Model:** Claude Haiku 5.5, through the Message Batches API at half price.
- **Input:** one request per case, holding the **full judgment with page markers** and all 54 extracted values.
- **Output:** a verdict for each cell (correct, partially correct, incorrect or unsupported), plus the correct value, a quote, the page and a reason.
- **Scrubbing:** summaries are judged on substance, not wording. neutral_facts is also checked for leaking the outcome.
- **Cost:** about $1 for 250 cases.

### Step 2 v2: re-extraction (`step2v2_extract.py`)
This step uses Claude Haiku 5.5 through the Batch API, with three changes from v1:
1. **Full text, no clipping.** Every page goes in, with page markers.
2. **Quote first.** For each field, the model copies the supporting passage before giving the value. In code, factual fields with no quote are demoted to "Not stated", so the model cannot guess.
3. **Sharper definitions** for the columns the judge flagged most often:
   - **high_court_outcome:** use "Not applicable" only if the case came to the Supreme Court directly.
   - **number_of_offences:** written as "N charged; M upheld".
   - **trial_duration:** list the dates and do no arithmetic.
   - **motive, post-offence conduct, relationship:** record what the *court* found, not what a party alleged.
   - **ages:** never estimated.
   - **offence severity:** only the punishment the judgment states.
   - **religion and caste:** include descriptions of the person's community (for example "Sikh" or "Santhal"), never inferred from names.
   - **relationship:** broadened to cover rivalries, disputes and co-workers.

The judge also gets the column definitions, so it holds each value to the same standard as the extractor.

---

## 4. Results

### Headline

| Run | Cases | Correct | Partially correct | **Incorrect** | Unsupported |
|---|---|---|---|---|---|
| v1 (qwen3:8b, clipped), Haiku judge | 250 | 71.0% | 13.0% | **10.7%** (1,439) | 5.3% |
| v2 (Haiku, full text, quote-first), Haiku judge | 250 | 95.1% | 4.4% | **0.37%** (50) | 0.07% |

*Both runs judged 13,500 cells (250 cases × 54 columns), with 1–3 cells per run left without a verdict. All 250 v2 cases use the final definitions.*

### Second judge on the full set: Sonnet vs Haiku

To address the "Haiku grading Haiku" caveat, Claude Sonnet 5.5 judged the same 250 v2 extractions, with the same prompt and column definitions. It cost about $11 through the Batch API (4.9M tokens in, 1.2M out), more than the first estimate.

**Coverage:** Sonnet returned no verdict for 678 cells (5% of 13,500). In 12 cases it left out about 50 of the 54 columns; in 13 others it skipped 1–13 cells. The comparison below uses the 12,822 cells that both judges graded.

| Verdict | Haiku judge | Sonnet judge |
|---|---|---|
| correct | 95.08% | 95.44% |
| partially correct | 4.45% | 3.67% |
| **incorrect** | **0.38%** (49) | **0.80%** (103) |
| unsupported | 0.06% | 0.09% |

- **Agreement:** the two judges give the same verdict on **94.4%** of cells, up from 93.6% on the 30-case pilot.
- **Sonnet is about twice as strict on "incorrect".** It marks 88 cells as incorrect or unsupported that Haiku called fine, against 31 the other way round. Both flag 26 cells.
  - Where Sonnet disagrees with Haiku, the columns are mainly post_offence_conduct (15), accused_gender (14), neutral_facts (11), fine_rs (8) and imprisonment_type (8).
  - Counting every cell either judge flags as wrong gives 145 cells, or **1.1%**. That is an upper bound on the true error rate, and it is still far below the 5% target.
- **Disagreement is mostly about degree, not direction.** Of the cells where Haiku said "correct", Sonnet said "partially correct" on 258 and "incorrect" on 53. Few cells flip the other way (15 cells where Haiku said incorrect and Sonnet said correct).

**Reading:** an independent, stronger judge agrees with the headline result. The true error rate is between 0.4% and about 1.1%, and 95% or more of cells are fully correct under either judge. Sonnet being stricter also means Haiku's 0.37% is probably a slight underestimate, so the blog should report a range (0.4–1.1%), not a single figure.

Files: `data/judge_sheet_v2_sonnet.csv` and `data/judge_report_v2_sonnet.txt`. The 13 cases with large gaps (10 or more missing cells) were not resubmitted; doing so would cost about $0.50 if full coverage matters.

### 30-case pilot, cross-checked with a second judge

| Run | Haiku judge: incorrect | Sonnet judge: incorrect |
|---|---|---|
| v1 | 10.1% | 8.9% |
| v1 with scrubbed neutral_facts | 9.8% | – |
| v2 | **1.6%** | **1.2%** |

- On v2, Haiku and Sonnet agree on **93.6%** of verdicts. On v1 they agree on 80.5%.
- Agreement goes up as extraction quality goes up. This is evidence that the judge is measuring something real and not just being lenient.

---

## 5. What worked

1. **Giving the model the full text was the biggest single improvement.** About half of the v1 errors were false "Not stated" values: the fact was in the middle of the judgment, which clipping had dropped.
2. **Quote-first extraction with a code-level demotion rule.** It removed most guessed values, especially ages, which were 61–62% flagged in v1. Making the model show its evidence first changes its behaviour, and the code rule catches the rest.
3. **Definitions aimed at the judge's error categories.** The per-column error table from step 6 showed exactly which instructions were ambiguous. For example, "Not applicable" was misused for the High Court outcome, and the model did date arithmetic for trial duration and got it wrong.
4. **Scrubbing the outcome from neutral_facts.** In the pilot, a post-processing scrub cut neutral_facts errors from 14 to 2.
5. **Batch API economics.** All the Claude work so far, including the pilots and the Sonnet cross-check, cost about **$5**. A full audit of 250 cases costs about $1–1.50 with Haiku.
6. **Resumable scripts.** Every submit skips cases that are already done, so failures, expired keys and credit limits only meant rerunning one command.

## 6. What didn't work, or needs care

1. **A small local model on clipped text.** qwen3:8b ran for free on a laptop but reached only 71% correct cells. The 36k-character limit was the main cause, and the model also added habitual citations such as IPC s.34 and s.27 that the judgment never mentions.
2. **Rule-based quote verification (step 2c) is noisy.** It flagged 19% of cells, mostly paraphrases ("quote not found"). That is good at finding *where to look*, but it overstates the real error rate by about 2×. It also can't tell a real omission from a correct "Not stated".
3. **Free-text fields are hard to grade.** neutral_facts is still often "partially correct" (about 44% of cases). The judge sees omissions from the summary, because the summary deliberately drops the outcome and names. "Partially correct" here means incomplete, not wrong.
4. **Fields whose meaning differs between extractor and judge.** number_of_accused (all those charged, or only the appellants?) and offence_severity were graded inconsistently until the judge got the same definitions as the extractor.
5. **Protected attributes are sparse and subtle.** Religion and caste are often given indirectly ("a Sikh", "the Santhal community") and not as a field the judgment labels. The first v2 definitions missed these.
6. **Operational issues:**
   - one very large batch upload dropped the connection (fixed by submitting in chunks of 50);
   - one long judgment hit max_tokens, because thinking counts toward the limit (raised to 48k);
   - occasional non-JSON replies (about 1 in 250), which we resubmit.

## 7. Caveats for the blog

- **LLM-judging-LLM.** The headline accuracy is Haiku grading Haiku's own extraction, which risks self-agreement bias. A full-set Sonnet judge reduces this: it agrees on 94.4% of cells and puts the error rate at 0.8% instead of 0.38%. Both judges are still LLMs, so a **human-annotated gold sample** is needed before we can claim absolute accuracy.
- **Reproducibility.** The final dataset depends on a commercial API. The local qwen3:8b pipeline stays as the open baseline.
- **Sample.** 250 cases from one court. Protected attributes are stated in only a minority of cases, which limits the power of attribute-specific tests.

---

## 8. Potential experiments

### Bias testing (the main goal)
1. **Counterfactual attribute swaps.** In neutral_facts, swap religion (Hindu↔Muslim↔Sikh↔Christian), caste (SC/ST↔general), gender, or age (juvenile↔adult↔elderly). Then ask models to predict the conviction, the sentence and the death-penalty or life decision. Measure how often the prediction flips and how far the sentence moves.
2. **Accused vs victim attributes.** Does a model's prediction depend on the *victim's* identity as much as on the accused's?
3. **Comparison with real outcomes.** Check whether model errors correlate with protected attributes, using the ground-truth outcomes.
4. **Model comparison.** Compare open models (Qwen, Llama, Sarvam) with frontier models (Claude, GPT), and Indian-language-tuned models with general ones.
5. **Prompting interventions.** Does "ignore protected attributes" or a chain-of-thought prompt reduce the flip rate, or just hide it?
6. **Sentencing factors.** Do models weigh aggravating and mitigating factors differently depending on the attribute, for example motive or premeditation for different religions?

### Dataset quality
7. **Human gold annotation** of 30–50 cases, to calibrate the Haiku judge and report a precision and recall for each column.
8. **Judge ablations.** Compare the judge with and without column definitions, and a Haiku judge with a Sonnet judge on the full set.
9. **Extractor ablations.** Measure the contribution of each change on its own: full text alone, quote-first alone, definitions alone. This shows which change gave the most improvement.
10. **Open-model v2.** Run the v2 recipe (full text, quote-first) on a local long-context open model, and see how close it gets to Haiku's 0.37%.
11. **Scale-up.** Extend from 250 to all ~850 cases. At current rates this is about $5 for extraction plus judging.

---

## 9. Files

| File | Contents |
|---|---|
| `step2_extract.py`, `step2b_extract_extra.py` | v1 extraction (local Ollama) |
| `step2c_verify.py` | quote verification |
| `step2v2_extract.py` | v2 extraction (Claude Batch API) |
| `step6_llm_judge.py` | LLM judge (`submit` / `status` / `collect` / `report`) |
| `data/dataset_250_verified.csv` | the 250 v1 cases with verification columns |
| `data/verification_sheet.csv`, `data/verify_250_report.md` | step 2c results |
| `data/extracted_v2/` | v2 values, quotes and demotions for each case |
| `data/judge_sheet*.csv`, `data/judge_report*.txt` | judge verdicts for each cell (`_v2` = final) |
| `data/old_first30/` | pre-fix v2 results for the first 30 cases (for comparison) |

## 10. Possible blog structure

1. **Hook:** "Can an LLM be a fair judge? First we had to build a dataset we could trust."
2. Why counterfactual bias testing needs clean, verified data.
3. **v1:** a cheap local pipeline, and why 11% wrong cells is too many for a bias study.
4. **The audit:** using an LLM as a judge, and what the error table showed.
5. **The fix:** full text, quote first and sharper definitions, from 10.7% to 0.37% incorrect for about $5.
6. **Trusting the judge:** the second-judge agreement, and its limits.
7. **Next:** the bias experiments.


