# Experiment 1 report — openai/gpt-oss-120b (groq), 2026-10-07
- Eligible cases: 1032 | sampled: 300 | analysed (both genders valid): 300
- Failed calls: 0 | over-length reasoning: 0.0%

## Paired tests
- overall: n=300.0, Male 39.7% vs Female 39.7%, diff +0.0% [-3.7%, +3.7%], h=0.00, flips=10.7%, p_holm=1.0000
- gender_irrelevant: n=150.0, Male 56.7% vs Female 57.3%, diff +0.7% [-5.3%, +6.7%], h=0.01, flips=12.7%, p_holm=1.0000
- gender_legally_relevant: n=150.0, Male 22.7% vs Female 22.0%, diff -0.7% [-5.3%, +4.0%], h=-0.02, flips=8.7%, p_holm=1.0000

## Noise floor
- Within 11.3% vs between 13.3%, p_holm=0.3995

## Power
- Discordant rate 0.107; cases needed for a 5-point effect: 333

## Reading the results
- gender_irrelevant: a significant effect beyond the noise floor is unjustified bias.
- gender_legally_relevant: a higher female grant rate may reflect the CrPC s.437 / BNSS s.480 proviso.
- Strata are not pooled for conclusions.

## Caveats
- Strata and sex-offence exclusions use keyword rules on the facts; spot-check them.
- Accuracy is against real outcomes, which are not a neutral gold standard.