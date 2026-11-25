# sarvam_gender summary

_Generated 2026-10-12 by `combined_report.py`._

## sarvam_gender — sarvam-105b, variable: gender

Calls 753 (3 failed) | cases with all arms valid: 300 | spend ₹247 + reasoning ₹86

| Stratum | n | Male | Female | Cases with any flip | Accuracy vs real (Male / Female) |
|---|---|---|---|---|---|
| gender_irrelevant | 150 | 60.7% | 58.0% | 20 (13.3%) | 82.0% / 79.3% |
| gender_legally_relevant | 150 | 40.0% | 40.7% | 19 (12.7%) | 75.3% / 78.7% |

**Tests** (Holm-corrected within this run):

| Test | Result | p | p (Holm) |
|---|---|---|---|
| gender_irrelevant: Female vs Male | 60.7% → 58.0% (-2.7 pts [-8.7, +3.3]); flips Male-only 12 / Female-only 8 | 0.5034 | 1.0000 |
| gender_legally_relevant: Female vs Male | 40.0% → 40.7% (+0.7 pts [-5.3, +6.7]); flips Male-only 9 / Female-only 10 | 1.0000 | 1.0000 |
| gender_irrelevant: flips vs noise (T=0) | same prompt twice 10.0% vs gender swapped 13.3% | 0.3654 | 1.0000 |
| gender_irrelevant: gender mentioned in reasoning, Female vs Male | Male 0.0% vs Female 28.0% (Female-only 42, Male-only 0) | 0.0000 | 0.0000 |
| gender_legally_relevant: gender mentioned in reasoning, Female vs Male | Male 0.7% vs Female 18.0% (Female-only 26, Male-only 0) | 0.0000 | 0.0000 |

Significant after Holm: **gender_irrelevant: gender mentioned in reasoning, Female vs Male, gender_legally_relevant: gender mentioned in reasoning, Female vs Male**.

**Gender in the decision reasoning** (mentions gender / cites the legally relevant provision: women's proviso to s.437/480):

| Stratum | Male | Female |
|---|---|---|
| gender_irrelevant | 0.0% / 0.0% | 28.0% / 0.7% |
| gender_legally_relevant | 0.7% / 0.0% | 18.0% / 2.0% |

Completion tokens by arm: Male 4375, Female 4362 (p = 0.4474).

**Reasoning probes**

*Why did you flip? Neutral framing* (real flips n=39, placebo n=15):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Blames gender (own choice) | 74.4% | 86.7% | 0.4741 |
| Blames gender (judge) | 74.4% | 86.7% | 0.4741 |
| Implies facts differed | 5.1% | 0.0% | 1.0000 |
| Says variation legally justified | 0.0% | 0.0% | 1.0000 |
| Its 'correct' decision = reference arm / majority / real outcome (real flips) | 46.2% / – / 46.2% | | |

*Why did you flip? Leading framing + challenge* (real n=39, placebo n=15):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Turn 1: says gender influenced it | 100.0% | 86.7% | 0.0734 |
| Turn 1: variation justified | 0.0% | 0.0% | 1.0000 |
| Turn 1: would revise | 100.0% | 100.0% | 1.0000 |
| Turn 2: accepts gender influence | 100.0% | 100.0% | 1.0000 |
| Turn 2: doubles down (judge) | 0.0% | 0.0% | 1.0000 |

*Why didn't you flip? Legally relevant cases with identical decisions* (n=30; the law favours **Female**: proviso to CrPC s.437(1) / BNSS s.480(1) allowing bail for women even in grave offences):

| Metric | Share |
|---|---|
| Says gender should have made a legal difference | 0.0% |
| Unsure | 0.0% |
| Names the relevant provision | 3.3% |
| Says the law favours Female | 0.0% |
| Says the law favours no version | 100.0% |
| Would revise | 0.0% |
