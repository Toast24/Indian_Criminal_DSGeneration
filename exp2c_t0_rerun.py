"""Exp 2c: re-run the no-caste arm once more at temperature 0 on all 159 cases.

Gives the temperature-0 within-arm flip rate (same prompt twice), to compare with the between-arm flip rates
(no caste line vs each caste label) from the primary run. Reuses the notebook's prompt, client and validation
code by executing its setup cells, so the prompt is byte-identical to the primary run.
"""
import os, json, time, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import nbformat

os.environ['EXP2_SCOPE'] = 'full'
ns = {}
nb = nbformat.read('exp2_caste_bail.ipynb', as_version=4)
for c in nb.cells:
    if c.cell_type != 'code': continue
    if 'jobs = []' in c.source: break           # stop before the notebook's own call loop
    exec(c.source, ns)

sample, build_prompt, llm, validate = ns['sample'], ns['build_prompt'], ns['llm'], ns['validate']
OUT = os.path.join(ns['OUTPUT_DIR'], 'calls_t0_rerun_None.jsonl')
done = set()
if os.path.exists(OUT):
    done = {json.loads(l)['case_id'] for l in open(OUT, encoding='utf-8') if json.loads(l)['status'] == 'ok'}
rows = sample.set_index('case_id')
todo = [c for c in sample['case_id'] if c not in done]
print(f'Cases: {len(sample)} | done: {len(done)} | to run: {len(todo)}', flush=True)
lock = threading.Lock()

def run(cid):
    prompt = build_prompt(rows.loc[cid].to_dict() | {'case_id': cid}, 'None')
    parsed, err, out, cost = None, None, {}, 0.0
    for attempt in range(3):
        try:
            out = llm(prompt, 0.0, cid, 'None')
            cost += out['cost_inr'] if 'cost_inr' in out else \
                (out['prompt_tokens'] or 0) * ns['PRICE_IN'] + (out['completion_tokens'] or 0) * ns['PRICE_OUT']
            if out['finish_reason'] == 'length' or not out['content']:
                err = 'truncated'; continue
            parsed, err = validate(out['content'], cid)
            if parsed: break
        except Exception as e:
            err = f'api_error: {e}'; time.sleep(5 * 2 ** attempt)
    rec = {'case_id': cid, 'arm': 'None', 'temperature': 0.0, 'repeat': 'rerun',
           'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'ok' if parsed else 'failed',
           'error': err if not parsed else None, 'cost_inr': round(cost, 4),
           'bail_granted': parsed['bail_granted'] if parsed else None,
           'reasoning': parsed['reasoning'] if parsed else None,
           'relevant_acts': parsed['relevant_acts'] if parsed else None,
           'completion_tokens': out.get('completion_tokens'), 'reasoning_trace': out.get('reasoning_trace')}
    with lock, open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return rec['status']

with ThreadPoolExecutor(ns['MAX_WORKERS']) as ex:
    for i, f in enumerate(as_completed([ex.submit(run, c) for c in todo]), 1):
        f.result()
        if i % 25 == 0 or i == len(todo): print(f'{i}/{len(todo)}', flush=True)
