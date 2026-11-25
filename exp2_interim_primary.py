"""Interim analysis of the Exp 2 primary run (temperature 0) while the noise repeats continue."""
import re, math
import numpy as np, pandas as pd
from scipy import stats

ARMS = ['None', 'General', 'OBC', 'SC']
PAIRS = [('General', 'SC'), ('General', 'OBC'), ('None', 'SC'), ('None', 'OBC'), ('None', 'General')]

d = pd.read_json('exp2_output/calls_full_sarvam_sarvam-105b.jsonl', lines=True)
d = d[(d.temperature == 0) & (d.status == 'ok')].drop_duplicates(['case_id', 'arm'], keep='last')
src = pd.read_csv('anonymised_bail_dataset.csv')
src['case_id'] = [f'CASE_{i:04d}' for i in range(1, len(src) + 1)]
CASTE_RE = re.compile(r'SC/ST|SC\s*&\s*ST|Scheduled Castes?|Scheduled Tribes?|Atrocit\w*|\bcaste\w*', re.I)
src['stratum'] = np.where(src.facts.str.contains(CASTE_RE), 'caste_relevant', 'caste_irrelevant')
src['real'] = src.bail_outcome.str.lower().eq('granted')
d = d.merge(src[['case_id', 'stratum', 'real', 'bail_type']], on='case_id')

prim = d.pivot(index='case_id', columns='arm', values='bail_granted').reindex(columns=ARMS).dropna()
prim = prim.astype(bool).join(src.set_index('case_id')[['stratum', 'real', 'bail_type']])
print(f'Calls ok: {len(d)} | cases with all 4 arms: {len(prim)}')

def mcn(a, b):
    n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
    return (stats.binomtest(n10, n10 + n01).pvalue if n10 + n01 else 1.0), n10, n01

def cochran(X):
    X = np.asarray(X, int); k = X.shape[1]; col, row, N = X.sum(0), X.sum(1), X.sum()
    den = k * N - (row ** 2).sum()
    Q = (k - 1) * (k * (col ** 2).sum() - N ** 2) / den if den else 0
    return Q, stats.chi2.sf(Q, k - 1)

def boot(a, b, n=2000):
    idx = np.random.default_rng(42).integers(0, len(a), (n, len(a)))
    return np.percentile(b[idx].mean(1) - a[idx].mean(1), [2.5, 97.5])

def holm(p):
    p = np.asarray(p); o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for r, i in enumerate(o): run = max(run, min(1, (m - r) * p[i])); adj[i] = run
    return adj

rows = []
for s, sub in prim.groupby('stratum'):
    print(f'\n=== {s} (n={len(sub)}) ===')
    for a in ARMS:
        print(f'  {a:8} grant {sub[a].mean():.1%} | accuracy vs real {np.mean(sub[a] == sub.real):.1%}')
    Q, p = cochran(sub[ARMS].values)
    rows.append({'test': f'{s}: Cochran Q', 'p': p, 'detail': f'Q={Q:.2f}'})
    for ref, arm in PAIRS:
        a, b = sub[ref].values, sub[arm].values
        p, n10, n01 = mcn(a, b); lo, hi = boot(a, b)
        rows.append({'test': f'{s}: {arm} vs {ref}', 'p': p,
                     'detail': f'{a.mean():.1%} -> {b.mean():.1%} ({b.mean() - a.mean():+.1%} [{lo:+.1%}, {hi:+.1%}]), '
                               f'flips: {ref}-only granted {n10}, {arm}-only granted {n01}'})
    anyc = sub[['General', 'OBC', 'SC']].mean(axis=1)
    print(f'  caste arms that granted, among cases None granted: {anyc[sub["None"]].mean():.1%}; '
          f'among cases None denied: {anyc[~sub["None"]].mean():.1%}')
    for bt, g in sub.groupby('bail_type'):
        print(f'  {bt:12} n={len(g)}: ' + ', '.join(f'{a} {g[a].mean():.0%}' for a in ARMS))

res = pd.DataFrame(rows); res['p_holm'] = holm(res.p)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120)
print('\n', res[['test', 'detail', 'p', 'p_holm']].round(4).to_string(index=False))

MENT = re.compile(r'\b(caste\w*|dalit|jatav|brahmin|yadav|obc|backward|scheduled|community|marginali[sz]ed|social(ly)? (status|background))\b', re.I)
SCST = re.compile(r'SC/ST|SC\s*&\s*ST|Atrocit|PoA Act', re.I)
d['mentions_caste'] = d.reasoning.str.contains(MENT)
d['cites_scst'] = (d.reasoning + ' ' + d.relevant_acts.astype(str)).str.contains(SCST)
print('\nReasoning mentions / SC-ST Act citations by arm:')
print(d.groupby(['stratum', 'arm'])[['mentions_caste', 'cites_scst']].mean().round(3).to_string())
print('\nMean completion tokens by arm:', d.groupby('arm').completion_tokens.mean().round(0).to_dict())
for _, r in d[d.mentions_caste].iterrows():
    print(f'\n[{r.case_id} {r.arm} granted={r.bail_granted}] {r.reasoning}')
prim.to_csv('exp2_output/interim_primary_pairs.csv')
