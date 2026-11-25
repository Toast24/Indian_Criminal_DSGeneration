"""Offline checks for the step1-step5 pipeline: no network and no LLM needed.

Usage: python tests/test_offline.py   (ends with "ALL OFFLINE CHECKS PASSED")
"""
import os
import random
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_common import clean_pdf_text, clip_text, parse_json, scrub_outcome  # noqa: E402
from step2_extract import FIELDS, normalise  # noqa: E402
from step3_build_dataset import final_years  # noqa: E402
from step4_counterfactuals import build, profile  # noqa: E402
from step5_run_and_analyse import analyse_pairs, holm, parse_decision  # noqa: E402


def check(name, cond):
    if not cond:
        raise AssertionError(name)
    print('ok  ', name)


check('parse_json plain', parse_json('{"a": 1}') == {'a': 1})
check('parse_json fenced + think', parse_json('<think>hm</think>```json\n{"a": 2}\n```') == {'a': 2})
check('parse_json with prose', parse_json('Here you go: {"a": 3} hope it helps') == {'a': 3})

t = 'x' * 1000
c = clip_text(t, 200)
check('clip_text keeps head and tail', c.startswith('x' * 130) and c.endswith('x' * 70) and 'omitted' in c)
check('clip_text leaves short text', clip_text('abc', 200) == 'abc')
check('scrub_outcome drops court sentences',
      scrub_outcome('The accused stabbed the victim. The trial court convicted him. A knife was recovered.')
      == 'The accused stabbed the victim. A knife was recovered.')
check('clean_pdf_text drops margin letters', 'A\nB' not in clean_pdf_text('A\nB\nC\nreal text\nH'))

rec = {k: 'Not stated' for k in FIELDS}
rec.update(final_outcome='Conviction Modified', imprisonment_type='Rigorous imprisonment', imprisonment_years='7 years',
           fine_rs='1,000', number_of_accused=2)
n = normalise(rec)
check('normalise outcome', n['final_outcome'] == 'conviction_modified')
check('normalise sentence type', n['imprisonment_type'] == 'fixed_term')
check('normalise numbers', n['imprisonment_years'] == 7 and n['fine_rs'] == 1000 and n['number_of_accused'] == 2)
check('normalise unknown outcome', normalise({'final_outcome': 'partly allowed'})['final_outcome'] == 'other')

check('final_years life', final_years({'final_outcome': 'convicted', 'imprisonment_type': 'life', 'imprisonment_years': None}) == 20)
check('final_years acquittal', final_years({'final_outcome': 'acquitted', 'imprisonment_type': 'none', 'imprisonment_years': None}) == 0)

check('profile religion', profile(30, {'religion': 'Muslim', 'caste': '', 'gender': 'man', 'ses': ''})
      == 'The accused is a 30-year-old Muslim man.')
check('profile caste', profile(30, {'religion': '', 'caste': 'Dalit (Scheduled Caste)', 'gender': 'man', 'ses': ''})
      == 'The accused is a 30-year-old Hindu Dalit (Scheduled Caste) man.')
base = pd.DataFrame([
    {'base_id': 'B0000', 'neutral_facts': 'The accused struck the victim.', 'statutory_provisions': 'IPC s.302',
     'accused_age': '40', 'offence_category': 'Murder'},
    {'base_id': 'B0001', 'neutral_facts': 'The accused assaulted the victim.', 'statutory_provisions': 'IPC s.376',
     'accused_age': 'Not stated', 'offence_category': 'Rape'},
])
cf = build(base)
check('counterfactual counts (gender skipped for rape)', len(cf) == 8 + 6)
pair = cf[cf['pair_id'] == 'B0000_religion']
pa, pb = pair['prompt'].tolist()
check('pair differs only in the changed detail', pa.replace('Hindu', 'X') == pb.replace('Muslim', 'X'))
check('default age used when not stated', '35-year-old' in cf[cf['base_id'] == 'B0001']['prompt'].iloc[0])

d = parse_decision('{"verdict": "Convict", "sentence_type": "life", "sentence_years": null, "reasoning": "r"}')
check('parse_decision life', d['verdict'] == 'convict' and d['years'] == 20)
check('parse_decision acquit', parse_decision('{"verdict": "acquit"}')['years'] == 0)

adj = holm([0.01, 0.04, 0.03, float('nan')])
check('holm', abs(adj[0] - 0.03) < 1e-9 and abs(adj[1] - 0.06) < 1e-9 and abs(adj[2] - 0.06) < 1e-9)

# Synthetic responses: variant b of 'religion' is convicted more and sentenced 3 years longer; 'gender' has no effect
random.seed(0)
rows = []
for i in range(200):
    for dim, biased in (('religion', True), ('gender', False)):
        pid = f'B{i:04d}_{dim}'
        convict_a = random.random() < 0.5
        convict_b = convict_a or (biased and random.random() < 0.4)
        ya = random.choice([5.0, 7.0, 10.0])
        rows.append({'pair_id': pid, 'dimension': dim, 'variant': 'a',
                     'verdict': 'convict' if convict_a else 'acquit', 'years': ya if convict_a else 0.0})
        rows.append({'pair_id': pid, 'dimension': dim, 'variant': 'b',
                     'verdict': 'convict' if convict_b else 'acquit',
                     'years': (ya + (3.0 if biased else 0.0)) if convict_b else 0.0})
rows.append({'pair_id': 'B9999_gender', 'dimension': 'gender', 'variant': 'a', 'verdict': None, 'years': None})
res = analyse_pairs(pd.DataFrame(rows)).set_index('dimension')
check('analysis flags the biased dimension', bool(res.loc['religion', 'significant'])
      and res.loc['religion', 'conviction_rate_b'] > res.loc['religion', 'conviction_rate_a']
      and abs(res.loc['religion', 'mean_diff_years'] - 3.0) < 1e-9)
check('analysis does not flag the unbiased dimension', not bool(res.loc['gender', 'significant'])
      and res.loc['gender', 'n_pairs'] == 200)

# Step 2c verification: quote matching, number checks, "Not stated" search, consistency checks
from step2c_verify import JudgmentText, consistency_flags, field_status, is_not_stated, number_in  # noqa: E402

doc = JudgmentText([
    'The appellant, aged about 27 years, was charged under Section 302 IPC.\nHe stabbed the deceased with a knife.',
    'The trial court sentenced him to rigorous imprisonment for seven years and a fine of Rs. 1,000/-.',
])
check('find exact quote with page', doc.find('aged about 27 years') == (True, 100.0, 1))
check('find quote across PDF line break and odd spacing', doc.find('charged under Section 302  IPC. He stabbed')[0])
check('find quote on page 2', doc.find('rigorous imprisonment for seven years')[2] == 2)
check('reject invented quote', not doc.find('the accused confessed before the magistrate on oath')[0])
check('number words', number_in(7, ['imprisonment for seven years']) and number_in(1000, ['fine of Rs. 1,000']))
check('number not in quote', not number_in(9, ['imprisonment for seven years']))
check('number not matched inside a longer number', not number_in(7, ['under section 307']))
check('is_not_stated variants', is_not_stated('Not stated') and is_not_stated('None noted.') and is_not_stated(None)
      and not is_not_stated('Male'))

st = lambda f, v, sup, q: field_status(f, v, sup, q, doc)[0]  # noqa: E731
check('status verified', st('accused_age', 27, True, ['aged about 27 years']) == 'verified')
check('status value_mismatch', st('accused_age', 35, True, ['aged about 27 years']) == 'value_mismatch')
check('status quote_not_found', st('weapon', 'Gun', True, ['he shot the deceased with a gun']) == 'quote_not_found')
check('status unsupported', st('motive', 'Land dispute', False, []) == 'unsupported')
check('status partly_verified', st('weapon', 'Knife', True, ['stabbed the deceased with a knife',
                                                             'the knife was recovered from his house']) == 'partly_verified')
check('not stated but judgment mentions it', st('weapon', 'None mentioned', None, []) == 'not_stated_check')
check('not stated confirmed', st('accused_religion', 'Not stated', None, []) == 'not_stated_confirmed')
note = field_status('weapon', 'A knife', True, ['he used a sharp knife on the deceased'], doc)[2]
check('flagged cell carries the closest passage and its page', 'p.1' in note and 'stabbed the deceased with a knife' in note)
check('not stated without a rule', st('accused_education', 'Not stated', None, []) == 'not_stated')

flags = consistency_flags({'final_outcome': 'acquitted', 'imprisonment_type': 'fixed_term', 'imprisonment_years': 7,
                           'statutory_provisions': 'IPC s.302, s.376', 'victim_age': 140}, doc)
check('consistency: acquitted but sentenced', any('acquitted but a sentence' in f for f in flags))
check('consistency: section not in judgment', any(f.endswith('376') for f in flags))
check('consistency: implausible age', any('victim_age' in f for f in flags))
check('consistency: clean case has no flags', consistency_flags(
    {'final_outcome': 'convicted', 'imprisonment_type': 'fixed_term', 'imprisonment_years': 7,
     'statutory_provisions': 'IPC s.302'}, doc) == [])

print('ALL OFFLINE CHECKS PASSED')
