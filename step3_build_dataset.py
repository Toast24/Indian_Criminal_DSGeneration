"""Step 3: merge extracted JSONs with the selection metadata into data/dataset_base_cases.csv.

A case is kept as a base case when it has usable neutral facts and a clear convicted / acquitted / modified outcome.
Usage: python step3_build_dataset.py
"""
import glob
import json
import os
import re

import pandas as pd

from pipeline_common import DATA, EXTRACT_DIR, scrub_outcome

USABLE_OUTCOMES = {'convicted', 'acquitted', 'conviction_modified'}
# Names leaking into the "neutral" facts would let the tested model infer religion/caste, so such cases are flagged
LEAK_RE = re.compile(r'\b(?:hindu|muslim|christian|sikh|dalit|brahmin|scheduled caste|scheduled tribe|caste)\b', re.I)


def final_years(r):
    """Sentence on one numeric scale for analysis: death=99, life=20 (the usual remission floor is 14), acquittal=0."""
    if r['final_outcome'] == 'acquitted':
        return 0.0
    return {'death': 99.0, 'life': 20.0}.get(r['imprisonment_type'], r['imprisonment_years'])


def load_extra():
    """Second-pass fields (step2b), one row per judgment; columns are absent until any were extracted."""
    from step2b_extract_extra import EXTRA_DIR, EXTRA_FIELDS
    rows = []
    for fp in glob.glob(os.path.join(EXTRA_DIR, '*.json')):
        with open(fp, encoding='utf-8') as f:
            r = json.load(f)
        rows.append({'path': r['_path'], **{k: r.get(k) for k in EXTRA_FIELDS},
                     'extra_groups': ','.join(r.get('_groups', []))})
    return pd.DataFrame(rows, columns=['path'] + EXTRA_FIELDS + ['extra_groups'])


def build_base(paths=None, verbose=True):
    """Base-case table from the extracted JSONs (only those in `paths`, if given). base_id is the judgment path."""
    sel = pd.read_csv(os.path.join(DATA, 'selected_cases.csv'))
    if paths is not None:
        sel = sel[sel['path'].isin(paths)]
    recs = []
    for fp in glob.glob(os.path.join(EXTRACT_DIR, '*.json')):
        with open(fp, encoding='utf-8') as f:
            r = json.load(f)
        r['_warnings'] = '; '.join(r.get('_warnings') or [])
        recs.append(r)
    ext = pd.DataFrame(recs)
    df = sel.merge(ext, left_on='path', right_on='_path', how='inner')
    df = df.merge(load_extra(), on='path', how='left')
    from step2c_verify import case_summary
    df = df.merge(case_summary(), on='path', how='left')
    if verbose:
        print(f'{len(df)} extracted judgments')
    df['neutral_facts_raw'] = df['neutral_facts']
    df['neutral_facts'] = df['neutral_facts'].map(scrub_outcome)
    facts = df['neutral_facts']
    df['facts_words'] = facts.str.split().str.len()
    df['facts_leak'] = facts.str.contains(LEAK_RE)
    df['convicted_final'] = df['final_outcome'].isin({'convicted', 'conviction_modified'}).astype(int)
    df['sentence_years_final'] = df.apply(final_years, axis=1)

    keep = df['final_outcome'].isin(USABLE_OUTCOMES) & (df['facts_words'] >= 80) & ~df['facts_leak']
    if verbose:
        print('dropped:', (~df['final_outcome'].isin(USABLE_OUTCOMES)).sum(), 'unclear outcome,',
              (df['facts_words'] < 80).sum(), 'short facts,', df['facts_leak'].sum(), 'facts mentioning religion/caste')
    base = df[keep].drop(columns=['_path']).reset_index(drop=True)
    base.insert(0, 'base_id', base['path'])
    return base


def main():
    base = build_base()
    out = os.path.join(DATA, 'dataset_base_cases.csv')
    base.to_csv(out, index=False)
    print(f'{len(base)} base cases -> {out}')
    print(base['final_outcome'].value_counts().to_string())
    print(base['offence_category'].value_counts().head(10).to_string())


if __name__ == '__main__':
    main()
