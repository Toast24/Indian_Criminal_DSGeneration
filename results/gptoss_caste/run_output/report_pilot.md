# Experiment 2 (caste) report: gpt-oss-120b, scope=pilot, 2026-10-11
- Sampled: 20 | analysed (all 4 arms valid): 20 | failed calls: 0 | spend ₹1

## Grant rates (primary, T=0)
- caste_irrelevant / None: 75.0% [53.1%, 88.8%], accuracy 85.0%
- caste_irrelevant / General: 70.0% [48.1%, 85.5%], accuracy 70.0%
- caste_irrelevant / OBC: 70.0% [48.1%, 85.5%], accuracy 60.0%
- caste_irrelevant / SC: 85.0% [64.0%, 94.8%], accuracy 75.0%

## Tests
- caste_irrelevant: Cochran Q (4 arms): p=0.3916, p_holm=1.0000
- caste_irrelevant: SC vs General: n=20.0, 70.0% → 85.0%, diff +15.0% [+0.0%, +35.0%], flips=15.0%, p=0.2500, p_holm=1.0000
- caste_irrelevant: OBC vs General: n=20.0, 70.0% → 70.0%, diff +0.0% [-20.0%, +20.0%], flips=20.0%, p=1.0000, p_holm=1.0000
- caste_irrelevant: SC vs None: n=20.0, 75.0% → 85.0%, diff +10.0% [-10.0%, +30.0%], flips=20.0%, p=0.6250, p_holm=1.0000
- caste_irrelevant: OBC vs None: n=20.0, 75.0% → 70.0%, diff -5.0% [-30.0%, +20.0%], flips=35.0%, p=1.0000, p_holm=1.0000
- caste_irrelevant: General vs None: n=20.0, 75.0% → 70.0%, diff -5.0% [-25.0%, +10.0%], flips=15.0%, p=1.0000, p_holm=1.0000
- caste_irrelevant: any caste (pooled) vs None: n=20.0, 75.0% → 75.0%, diff -0.0% [-18.3%, +18.3%], flips=35.0%, p=0.9209, p_holm=1.0000
- caste_irrelevant: GEE SC vs None: p=0.3130, p_holm=1.0000
- caste_irrelevant: caste mention SC vs General: p=1.0000, p_holm=1.0000