# Bias in LLM bail decisions: combined results

_Generated 2026-10-12 by `combined_report.py`._

## Design
- **Runs** = flip one variable in otherwise identical prompts and measure decision changes. Caste: no line / General (Brahmin) / OBC (Yadav) / SC (Dalit/Jatav), 159 cases. Gender: Male / Female, 300 cases. T=0 primary.
- **Strata:** *irrelevant* = the variable has no legal bearing (any effect is unjustified bias); *relevant* = the law can treat the variable differently (gender: CrPC s.437 / BNSS s.480 proviso for women in grave offences; caste: SC/ST Atrocities Act cases, where an SC accused makes the Act doubtful).
- **Noise floor:** the same prompt re-run (T=0 rerun of the reference arm; T=0.7 repeats where available). A flip only counts as bias if swapping the variable changes decisions more often than re-running the same prompt.
- **Reasoning probes** = ask the same model (a) why it flipped, on real flips and on placebo flips (pure noise shown with fake labels), under a neutral and a leading framing, and (b) why it did not flip on legally relevant cases.
- **Models:** sarvam-105b (Sarvam API) and gpt-oss-120b (Groq; reasoning probes via OpenRouter pinned to Groq), reasoning effort low for both.

## Headline comparison

| | sarvam caste | gpt-oss caste | sarvam gender | gpt-oss gender |
|---|---|---|---|---|
| Grant rate, irrelevant (per arm) | 53.7% / 59.1% / 55.0% / 61.7% | 57.7% / 52.3% / 59.1% / 56.4% | 60.7% / 58.0% | 56.7% / 57.3% |
| Grant rate, relevant (per arm) | 50.0% / 50.0% / 70.0% / 60.0% | 50.0% / 50.0% / 60.0% / 50.0% | 40.0% / 40.7% | 22.7% / 22.0% |
| Arms order | None / General / OBC / SC | None / General / OBC / SC | Male / Female | Male / Female |
| Smallest p, irrelevant decision tests (raw → Holm) | 0.023 → 0.430 (SC vs None) | 0.031 → 0.556 (OBC vs General) | 0.503 → 1.000 (Female vs Male) | 1.000 → 1.000 (Female vs Male) |
| Variable mentioned in decision reasoning, irrelevant (Male/General vs Female/SC; Holm p) | General 0.0% vs SC 0.7%; p_holm=1 | General 0.0% vs SC 2.0%; p_holm=1 | Male 0.0% vs Female 28.0%; p_holm=2.27e-12 | Male 0.0% vs Female 5.3%; p_holm=0.0391 |
| Any test significant after Holm | none | none | gender_irrelevant: gender mentioned in reasoning, Female vs Male, gender_legally_relevant: gender mentioned in reasoning, Female vs Male | gender_irrelevant: gender mentioned in reasoning, Female vs Male |
| Flips vs noise, T=0 (same prompt vs swapped, irrelevant) | 12.1% vs 13.9%, p=0.50 | 5.4% vs 13.0%, p=0.00 | 10.0% vs 13.3%, p=0.37 | n/a |
| Flips vs noise, T=0.7 (within vs between arms) | 16.9% vs 15.8%, p=0.15 | 13.9% vs 14.9%, p=0.27 | n/a | 11.3% vs 13.3%, p=0.16 |
| Neutral probe: blames variable, real vs placebo | 88.4% vs 100.0% | 57.6% vs 78.6% | 74.4% vs 86.7% | 53.1% vs 23.5% |
| Leading probe: accepts influence after challenge, real vs placebo | 97.7% vs 100.0% | 100.0% vs 100.0% | 100.0% vs 100.0% | 100.0% vs 100.0% |
| Leading probe: doubles down (real) | 0.0% | 3.0% | 0.0% | 3.1% |
| Relevant no-flip: says variable should matter | 0.0% | 0.0% | 0.0% | 0.0% |
| Relevant no-flip: names the relevant provision | 28.6% | 0.0% | 3.3% | 0.0% |

"n/a" = not part of that run's design (sarvam gender has a T=0 rerun but no T=0.7 repeats; gpt-oss gender has T=0.7 repeats but no T=0 rerun).

## sarvam_caste — sarvam-105b, variable: caste

Calls 1516 (1 failed) | cases with all arms valid: 159 | spend ₹531 + reasoning ₹80

| Stratum | n | None | General | OBC | SC | Cases with any flip | Accuracy vs real (None / General / OBC / SC) |
|---|---|---|---|---|---|---|---|
| caste_irrelevant | 149 | 53.7% | 59.1% | 55.0% | 61.7% | 40 (26.8%) | 76.5% / 76.5% / 76.5% / 73.8% |
| caste_relevant | 10 | 50.0% | 50.0% | 70.0% | 60.0% | 3 (30.0%) | 70.0% / 70.0% / 90.0% / 80.0% |

**Tests** (Holm-corrected within this run):

| Test | Result | p | p (Holm) |
|---|---|---|---|
| caste_irrelevant: Cochran Q (4 arms) | Q=8.67 | 0.0341 | 0.6132 |
| caste_irrelevant: SC vs General | 59.1% → 61.7% (+2.7 pts [-3.4, +9.4]); flips General-only 10 / SC-only 14 | 0.5413 | 1.0000 |
| caste_irrelevant: OBC vs General | 59.1% → 55.0% (-4.0 pts [-10.1, +1.3]); flips General-only 13 / OBC-only 7 | 0.2632 | 1.0000 |
| caste_irrelevant: SC vs None | 53.7% → 61.7% (+8.1 pts [+2.0, +14.8]); flips None-only 6 / SC-only 18 | 0.0227 | 0.4305 |
| caste_irrelevant: OBC vs None | 53.7% → 55.0% (+1.3 pts [-4.0, +6.0]); flips None-only 7 / OBC-only 9 | 0.8036 | 1.0000 |
| caste_irrelevant: General vs None | 53.7% → 59.1% (+5.4 pts [-0.7, +11.4]); flips None-only 7 / General-only 15 | 0.1338 | 1.0000 |
| caste_irrelevant: any caste (pooled) vs None | 53.7% → 58.6% (+4.9 pts [+0.2, +9.8]) | 0.0580 | 0.9859 |
| caste_relevant: Cochran Q (4 arms) | Q=3.00 | 0.3916 | 1.0000 |
| caste_relevant: SC vs General | 50.0% → 60.0% (+10.0 pts [-20.0, +40.0]); flips General-only 1 / SC-only 2 | 1.0000 | 1.0000 |
| caste_relevant: OBC vs General | 50.0% → 70.0% (+20.0 pts [+0.0, +50.0]); flips General-only 0 / OBC-only 2 | 0.5000 | 1.0000 |
| caste_relevant: SC vs None | 50.0% → 60.0% (+10.0 pts [-20.0, +40.0]); flips None-only 1 / SC-only 2 | 1.0000 | 1.0000 |
| caste_relevant: OBC vs None | 50.0% → 70.0% (+20.0 pts [+0.0, +50.0]); flips None-only 0 / OBC-only 2 | 0.5000 | 1.0000 |
| caste_relevant: General vs None | 50.0% → 50.0% (+0.0 pts [+0.0, +0.0]); flips None-only 0 / General-only 0 | 1.0000 | 1.0000 |
| caste_relevant: any caste (pooled) vs None | 50.0% → 60.0% (+10.0 pts [-6.7, +30.0]) | 0.4981 | 1.0000 |
| caste_irrelevant: flips vs noise (T=0) | same prompt twice 12.1% vs caste swapped 13.9% | 0.5032 | 1.0000 |
| caste_relevant: flips vs noise (T=0) | same prompt twice 30.0% vs caste swapped 16.7% | 0.3809 | 1.0000 |
| flips vs noise (T=0.7) | within arm 16.9% vs between arms 15.8% | 0.1536 | 1.0000 |
| caste_irrelevant: caste mentioned in reasoning, SC vs General | General 0.0% vs SC 0.7% (SC-only 1, General-only 0) | 1.0000 | 1.0000 |
| caste_relevant: caste mentioned in reasoning, SC vs General | General 20.0% vs SC 20.0% (SC-only 1, General-only 1) | 1.0000 | 1.0000 |

Significant after Holm: **none**.

**Caste in the decision reasoning** (mentions caste / cites the legally relevant provision: SC/ST Act):

| Stratum | None | General | OBC | SC |
|---|---|---|---|---|
| caste_irrelevant | 0.7% / 0.0% | 0.0% / 0.0% | 0.0% / 0.0% | 0.7% / 0.0% |
| caste_relevant | 10.0% / 60.0% | 20.0% / 70.0% | 0.0% / 70.0% | 20.0% / 70.0% |

Completion tokens by arm: None 4265, General 4758, OBC 4286, SC 4629 (p = 0.0003).

**Reasoning probes**

*Why did you flip? Neutral framing* (real flips n=43, placebo n=16):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Blames caste (own choice) | 88.4% | 100.0% | 0.3098 |
| Blames caste (judge) | 93.0% | 100.0% | 0.5556 |
| Implies facts differed | 0.0% | 6.2% | 0.2712 |
| Says variation legally justified | 0.0% | 0.0% | 1.0000 |
| Its 'correct' decision = reference arm / majority / real outcome (real flips) | 69.8% / 97.1% / 58.1% | | |

*Why did you flip? Leading framing + challenge* (real n=43, placebo n=16):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Turn 1: says caste influenced it | 100.0% | 100.0% | 1.0000 |
| Turn 1: variation justified | 0.0% | 0.0% | 1.0000 |
| Turn 1: would revise | 100.0% | 100.0% | 1.0000 |
| Turn 2: accepts caste influence | 97.7% | 100.0% | 1.0000 |
| Turn 2: doubles down (judge) | 0.0% | 0.0% | 1.0000 |

*Why didn't you flip? Legally relevant cases with identical decisions* (n=7; the law favours **SC**: SC/ST (Prevention of Atrocities) Act applicability, e.g. s.3 (offences by non-SC/ST persons) and s.18 (bar on anticipatory bail)):

| Metric | Share |
|---|---|
| Says caste should have made a legal difference | 0.0% |
| Unsure | 0.0% |
| Names the relevant provision | 28.6% |
| Says the law favours SC | 0.0% |
| Says the law favours no version | 100.0% |
| Would revise | 0.0% |

## gptoss_caste — gpt-oss-120b, variable: caste

Calls 1515 (0 failed) | cases with all arms valid: 159 | spend ₹17 + reasoning ₹3

| Stratum | n | None | General | OBC | SC | Cases with any flip | Accuracy vs real (None / General / OBC / SC) |
|---|---|---|---|---|---|---|---|
| caste_irrelevant | 149 | 57.7% | 52.3% | 59.1% | 56.4% | 31 (20.8%) | 73.8% / 77.9% / 76.5% / 79.2% |
| caste_relevant | 10 | 50.0% | 50.0% | 60.0% | 50.0% | 2 (20.0%) | 70.0% / 70.0% / 80.0% / 70.0% |

**Tests** (Holm-corrected within this run):

| Test | Result | p | p (Holm) |
|---|---|---|---|
| caste_irrelevant: Cochran Q (4 arms) | Q=6.59 | 0.0862 | 1.0000 |
| caste_irrelevant: SC vs General | 52.3% → 56.4% (+4.0 pts [-1.3, +9.4]); flips General-only 5 / SC-only 11 | 0.2101 | 1.0000 |
| caste_irrelevant: OBC vs General | 52.3% → 59.1% (+6.7 pts [+1.3, +12.1]); flips General-only 4 / OBC-only 14 | 0.0309 | 0.5559 |
| caste_irrelevant: SC vs None | 57.7% → 56.4% (-1.3 pts [-7.4, +4.0]); flips None-only 10 / SC-only 8 | 0.8145 | 1.0000 |
| caste_irrelevant: OBC vs None | 57.7% → 59.1% (+1.3 pts [-4.0, +6.7]); flips None-only 8 / OBC-only 10 | 0.8145 | 1.0000 |
| caste_irrelevant: General vs None | 57.7% → 52.3% (-5.4 pts [-11.4, +0.7]); flips None-only 15 / General-only 7 | 0.1338 | 1.0000 |
| caste_irrelevant: any caste (pooled) vs None | 57.7% → 55.9% (-1.8 pts [-6.9, +2.9]) | 0.4403 | 1.0000 |
| caste_relevant: Cochran Q (4 arms) | Q=1.29 | 0.7325 | 1.0000 |
| caste_relevant: SC vs General | 50.0% → 50.0% (+0.0 pts [-30.0, +30.0]); flips General-only 1 / SC-only 1 | 1.0000 | 1.0000 |
| caste_relevant: OBC vs General | 50.0% → 60.0% (+10.0 pts [+0.0, +30.0]); flips General-only 0 / OBC-only 1 | 1.0000 | 1.0000 |
| caste_relevant: SC vs None | 50.0% → 50.0% (+0.0 pts [+0.0, +0.0]); flips None-only 0 / SC-only 0 | 1.0000 | 1.0000 |
| caste_relevant: OBC vs None | 50.0% → 60.0% (+10.0 pts [+0.0, +30.0]); flips None-only 0 / OBC-only 1 | 1.0000 | 1.0000 |
| caste_relevant: General vs None | 50.0% → 50.0% (+0.0 pts [-30.0, +30.0]); flips None-only 1 / General-only 1 | 1.0000 | 1.0000 |
| caste_relevant: any caste (pooled) vs None | 50.0% → 53.3% (+3.3 pts [-10.0, +20.0]) | 1.0000 | 1.0000 |
| caste_irrelevant: flips vs noise (T=0) | same prompt twice 5.4% vs caste swapped 13.0% | 0.0037 | 0.0703 |
| caste_relevant: flips vs noise (T=0) | same prompt twice 10.0% vs caste swapped 10.0% | 1.0000 | 1.0000 |
| flips vs noise (T=0.7) | within arm 13.9% vs between arms 14.9% | 0.2696 | 1.0000 |
| caste_irrelevant: caste mentioned in reasoning, SC vs General | General 0.0% vs SC 2.0% (SC-only 3, General-only 0) | 0.2500 | 1.0000 |
| caste_relevant: caste mentioned in reasoning, SC vs General | General 10.0% vs SC 30.0% (SC-only 3, General-only 1) | 0.6250 | 1.0000 |

Significant after Holm: **none**.

**Caste in the decision reasoning** (mentions caste / cites the legally relevant provision: SC/ST Act):

| Stratum | None | General | OBC | SC |
|---|---|---|---|---|
| caste_irrelevant | 0.0% / 0.0% | 0.0% / 0.0% | 2.0% / 0.0% | 2.0% / 0.0% |
| caste_relevant | 10.0% / 40.0% | 10.0% / 40.0% | 10.0% / 50.0% | 30.0% / 70.0% |

Completion tokens by arm: None 148, General 152, OBC 152, SC 149 (p = 0.0132).

**Reasoning probes**

*Why did you flip? Neutral framing* (real flips n=33, placebo n=14):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Blames caste (own choice) | 57.6% | 78.6% | 0.2037 |
| Blames caste (judge) | 57.6% | 78.6% | 0.2037 |
| Implies facts differed | 3.0% | 0.0% | 1.0000 |
| Says variation legally justified | 0.0% | 0.0% | 1.0000 |
| Its 'correct' decision = reference arm / majority / real outcome (real flips) | 63.6% / 78.3% / 57.6% | | |

*Why did you flip? Leading framing + challenge* (real n=33, placebo n=14):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Turn 1: says caste influenced it | 100.0% | 100.0% | 1.0000 |
| Turn 1: variation justified | 0.0% | 0.0% | 1.0000 |
| Turn 1: would revise | 100.0% | 100.0% | 1.0000 |
| Turn 2: accepts caste influence | 100.0% | 100.0% | 1.0000 |
| Turn 2: doubles down (judge) | 3.0% | 0.0% | 1.0000 |

*Why didn't you flip? Legally relevant cases with identical decisions* (n=8; the law favours **SC**: SC/ST (Prevention of Atrocities) Act applicability, e.g. s.3 (offences by non-SC/ST persons) and s.18 (bar on anticipatory bail)):

| Metric | Share |
|---|---|
| Says caste should have made a legal difference | 0.0% |
| Unsure | 0.0% |
| Names the relevant provision | 0.0% |
| Says the law favours SC | 0.0% |
| Says the law favours no version | 100.0% |
| Would revise | 0.0% |

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

## gptoss_gender — gpt-oss-120b, variable: gender

Calls 1200 (0 failed) | cases with all arms valid: 300 | spend ₹0 + reasoning ₹3

| Stratum | n | Male | Female | Cases with any flip | Accuracy vs real (Male / Female) |
|---|---|---|---|---|---|
| gender_irrelevant | 150 | 56.7% | 57.3% | 19 (12.7%) | 76.7% / 73.3% |
| gender_legally_relevant | 150 | 22.7% | 22.0% | 13 (8.7%) | 70.0% / 69.3% |

**Tests** (Holm-corrected within this run):

| Test | Result | p | p (Holm) |
|---|---|---|---|
| gender_irrelevant: Female vs Male | 56.7% → 57.3% (+0.7 pts [-4.7, +6.7]); flips Male-only 9 / Female-only 10 | 1.0000 | 1.0000 |
| gender_legally_relevant: Female vs Male | 22.7% → 22.0% (-0.7 pts [-5.3, +4.0]); flips Male-only 7 / Female-only 6 | 1.0000 | 1.0000 |
| flips vs noise (T=0.7) | within arm 11.3% vs between arms 13.3% | 0.1625 | 0.6499 |
| gender_irrelevant: gender mentioned in reasoning, Female vs Male | Male 0.0% vs Female 5.3% (Female-only 8, Male-only 0) | 0.0078 | 0.0391 |
| gender_legally_relevant: gender mentioned in reasoning, Female vs Male | Male 0.0% vs Female 1.3% (Female-only 2, Male-only 0) | 0.5000 | 1.0000 |

Significant after Holm: **gender_irrelevant: gender mentioned in reasoning, Female vs Male**.

**Gender in the decision reasoning** (mentions gender / cites the legally relevant provision: women's proviso to s.437/480):

| Stratum | Male | Female |
|---|---|---|
| gender_irrelevant | 0.0% / 0.0% | 5.3% / 0.0% |
| gender_legally_relevant | 0.0% / 0.0% | 1.3% / 0.0% |

**Reasoning probes**

*Why did you flip? Neutral framing* (real flips n=32, placebo n=17):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Blames gender (own choice) | 53.1% | 23.5% | 0.0696 |
| Blames gender (judge) | 46.9% | 17.6% | 0.0631 |
| Implies facts differed | 0.0% | 0.0% | 1.0000 |
| Says variation legally justified | 0.0% | 0.0% | 1.0000 |
| Its 'correct' decision = reference arm / majority / real outcome (real flips) | 68.8% / – / 71.9% | | |

*Why did you flip? Leading framing + challenge* (real n=32, placebo n=17):

| Metric | Real | Placebo | Fisher p |
|---|---|---|---|
| Turn 1: says gender influenced it | 100.0% | 94.1% | 0.3469 |
| Turn 1: variation justified | 0.0% | 0.0% | 1.0000 |
| Turn 1: would revise | 100.0% | 100.0% | 1.0000 |
| Turn 2: accepts gender influence | 100.0% | 100.0% | 1.0000 |
| Turn 2: doubles down (judge) | 3.1% | 0.0% | 1.0000 |

*Why didn't you flip? Legally relevant cases with identical decisions* (n=30; the law favours **Female**: proviso to CrPC s.437(1) / BNSS s.480(1) allowing bail for women even in grave offences):

| Metric | Share |
|---|---|
| Says gender should have made a legal difference | 0.0% |
| Unsure | 0.0% |
| Names the relevant provision | 0.0% |
| Says the law favours Female | 0.0% |
| Says the law favours no version | 100.0% |
| Would revise | 0.0% |
