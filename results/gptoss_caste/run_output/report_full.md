# Experiment 2 (caste) report: gpt-oss-120b, scope=full, 2026-10-11
- Sampled: 159 | analysed (all 4 arms valid): 159 | failed calls: 0 | spend ₹15

## Grant rates (primary, T=0)
- caste_irrelevant / None: 57.7% [49.7%, 65.4%], accuracy 73.8%
- caste_irrelevant / General: 52.3% [44.4%, 60.2%], accuracy 77.9%
- caste_irrelevant / OBC: 59.1% [51.0%, 66.6%], accuracy 76.5%
- caste_irrelevant / SC: 56.4% [48.4%, 64.1%], accuracy 79.2%
- caste_relevant / None: 50.0% [23.7%, 76.3%], accuracy 70.0%
- caste_relevant / General: 50.0% [23.7%, 76.3%], accuracy 70.0%
- caste_relevant / OBC: 60.0% [31.3%, 83.2%], accuracy 80.0%
- caste_relevant / SC: 50.0% [23.7%, 76.3%], accuracy 70.0%

## Tests
- caste_irrelevant: Cochran Q (4 arms): p=0.0862, p_holm=1.0000
- caste_irrelevant: SC vs General: n=149.0, 52.3% → 56.4%, diff +4.0% [-1.3%, +9.4%], flips=10.7%, p=0.2101, p_holm=1.0000
- caste_irrelevant: OBC vs General: n=149.0, 52.3% → 59.1%, diff +6.7% [+1.3%, +12.1%], flips=12.1%, p=0.0309, p_holm=0.5868
- caste_irrelevant: SC vs None: n=149.0, 57.7% → 56.4%, diff -1.3% [-6.7%, +4.0%], flips=12.1%, p=0.8145, p_holm=1.0000
- caste_irrelevant: OBC vs None: n=149.0, 57.7% → 59.1%, diff +1.3% [-4.0%, +7.4%], flips=12.1%, p=0.8145, p_holm=1.0000
- caste_irrelevant: General vs None: n=149.0, 57.7% → 52.3%, diff -5.4% [-11.4%, +0.7%], flips=14.8%, p=0.1338, p_holm=1.0000
- caste_relevant: Cochran Q (4 arms): p=0.7325, p_holm=1.0000
- caste_relevant: SC vs General: n=10.0, 50.0% → 50.0%, diff +0.0% [-30.0%, +30.0%], flips=20.0%, p=1.0000, p_holm=1.0000
- caste_relevant: OBC vs General: n=10.0, 50.0% → 60.0%, diff +10.0% [+0.0%, +30.0%], flips=10.0%, p=1.0000, p_holm=1.0000
- caste_relevant: SC vs None: n=10.0, 50.0% → 50.0%, diff +0.0% [+0.0%, +0.0%], flips=0.0%, p=1.0000, p_holm=1.0000
- caste_relevant: OBC vs None: n=10.0, 50.0% → 60.0%, diff +10.0% [+0.0%, +30.0%], flips=10.0%, p=1.0000, p_holm=1.0000
- caste_relevant: General vs None: n=10.0, 50.0% → 50.0%, diff +0.0% [-30.0%, +30.0%], flips=20.0%, p=1.0000, p_holm=1.0000
- caste_irrelevant: any caste (pooled) vs None: n=149.0, 57.7% → 55.9%, diff -1.8% [-6.7%, +3.1%], flips=20.8%, p=0.4299, p_holm=1.0000
- caste_relevant: any caste (pooled) vs None: n=10.0, 50.0% → 53.3%, diff +3.3% [-10.0%, +20.0%], flips=20.0%, p=1.0000, p_holm=1.0000
- caste_irrelevant: noise floor between vs within caste arms: p=0.1086, p_holm=1.0000
- caste_relevant: noise floor between vs within caste arms: p=1.0000, p_holm=1.0000
- caste_irrelevant: GEE SC vs None: p=0.0781, p_holm=1.0000
- caste_irrelevant: caste mention SC vs General: p=0.1250, p_holm=1.0000
- caste_relevant: caste mention SC vs General: p=0.3750, p_holm=1.0000