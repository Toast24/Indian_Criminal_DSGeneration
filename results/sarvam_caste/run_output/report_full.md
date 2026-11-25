# Experiment 2 (caste) report: sarvam-105b, scope=full, 2026-10-10
- Sampled: 159 | analysed (all 4 arms valid): 159 | failed calls: 1 | spend ₹474

## Grant rates (primary, T=0)
- caste_irrelevant / None: 53.7% [45.7%, 61.5%], accuracy 76.5%
- caste_irrelevant / General: 59.1% [51.0%, 66.6%], accuracy 76.5%
- caste_irrelevant / OBC: 55.0% [47.0%, 62.8%], accuracy 76.5%
- caste_irrelevant / SC: 61.7% [53.7%, 69.2%], accuracy 73.8%
- caste_relevant / None: 50.0% [23.7%, 76.3%], accuracy 70.0%
- caste_relevant / General: 50.0% [23.7%, 76.3%], accuracy 70.0%
- caste_relevant / OBC: 70.0% [39.7%, 89.2%], accuracy 90.0%
- caste_relevant / SC: 60.0% [31.3%, 83.2%], accuracy 80.0%

## Tests
- caste_irrelevant: Cochran Q (4 arms): p=0.0341, p_holm=0.6132
- caste_irrelevant: SC vs General: n=149.0, 59.1% → 61.7%, diff +2.7% [-3.4%, +9.4%], flips=16.1%, p=0.5413, p_holm=1.0000
- caste_irrelevant: OBC vs General: n=149.0, 59.1% → 55.0%, diff -4.0% [-10.1%, +2.0%], flips=13.4%, p=0.2632, p_holm=1.0000
- caste_irrelevant: SC vs None: n=149.0, 53.7% → 61.7%, diff +8.1% [+2.0%, +14.1%], flips=16.1%, p=0.0227, p_holm=0.4305
- caste_irrelevant: OBC vs None: n=149.0, 53.7% → 55.0%, diff +1.3% [-4.0%, +6.7%], flips=10.7%, p=0.8036, p_holm=1.0000
- caste_irrelevant: General vs None: n=149.0, 53.7% → 59.1%, diff +5.4% [-0.7%, +12.1%], flips=14.8%, p=0.1338, p_holm=1.0000
- caste_relevant: Cochran Q (4 arms): p=0.3916, p_holm=1.0000
- caste_relevant: SC vs General: n=10.0, 50.0% → 60.0%, diff +10.0% [-20.2%, +40.2%], flips=30.0%, p=1.0000, p_holm=1.0000
- caste_relevant: OBC vs General: n=10.0, 50.0% → 70.0%, diff +20.0% [+0.0%, +50.0%], flips=20.0%, p=0.5000, p_holm=1.0000
- caste_relevant: SC vs None: n=10.0, 50.0% → 60.0%, diff +10.0% [-20.2%, +40.2%], flips=30.0%, p=1.0000, p_holm=1.0000
- caste_relevant: OBC vs None: n=10.0, 50.0% → 70.0%, diff +20.0% [+0.0%, +50.0%], flips=20.0%, p=0.5000, p_holm=1.0000
- caste_relevant: General vs None: n=10.0, 50.0% → 50.0%, diff +0.0% [+0.0%, +0.0%], flips=0.0%, p=1.0000, p_holm=1.0000
- caste_irrelevant: any caste (pooled) vs None: n=149.0, 53.7% → 58.6%, diff +4.9% [-0.0%, +9.6%], flips=26.8%, p=0.0513, p_holm=0.8504
- caste_relevant: any caste (pooled) vs None: n=10.0, 50.0% → 60.0%, diff +10.0% [-6.7%, +30.1%], flips=30.0%, p=0.4935, p_holm=1.0000
- caste_irrelevant: noise floor between vs within caste arms: p=0.7790, p_holm=1.0000
- caste_relevant: noise floor between vs within caste arms: p=1.0000, p_holm=1.0000
- caste_irrelevant: GEE SC vs None: p=0.0500, p_holm=0.8504
- caste_irrelevant: caste mention SC vs General: p=1.0000, p_holm=1.0000
- caste_relevant: caste mention SC vs General: p=1.0000, p_holm=1.0000