"""Step 6: an LLM judge (Claude Haiku 5.5 through the Message Batches API) checks every extracted cell
against the full judgment. One request per case judges all columns, so each judgment is sent once.

Usage:
  python step6_llm_judge.py submit [N] [--all]   build and submit the batch (default: the 250 cases in
                                                 data/dataset_250_verified.csv; --all = data/dataset_base_cases.csv)
  python step6_llm_judge.py status               show progress of the submitted batch
  python step6_llm_judge.py collect              download results -> data/judge/raw/, data/judge_sheet.csv,
                                                 data/judge_report.txt
  python step6_llm_judge.py dry [N]              write the requests to data/judge/requests_preview.jsonl, no API call

Needs ANTHROPIC_API_KEY in the environment (or in .env). JUDGE_MODEL overrides the model.
Batches cost half the normal price and usually finish within an hour (24 h at most).
"""
import json
import os
import sys

import pandas as pd
from dotenv import load_dotenv

from pipeline_common import DATA, parse_json, scrub_outcome
from step2_extract import FIELDS
from step2b_extract_extra import EXTRA_FIELDS
from step2c_verify import JudgmentText, load_values

load_dotenv()
MODEL = os.environ.get('JUDGE_MODEL', 'claude-haiku-5-5')
# JUDGE_TAG keeps separate runs apart (e.g. "v1s" = v1 values re-judged, "v2" = step2v2 values)
TAG = os.environ.get('JUDGE_TAG', '')
SFX = f'_{TAG}' if TAG else ''
JUDGE_DIR = os.path.join(DATA, 'judge' + SFX)
RAW_DIR = os.path.join(JUDGE_DIR, 'raw')
BATCH_FILE = os.path.join(JUDGE_DIR, 'batch_id.txt')
SHEET = os.path.join(DATA, f'judge_sheet{SFX}.csv')
REPORT = os.path.join(DATA, f'judge_report{SFX}.txt')


def get_values(path):
    """Values to judge. Tagged runs judge neutral_facts after scrub_outcome, as the dataset uses it."""
    if TAG.startswith('v2'):
        from step2v2_extract import load_values_v2
        rec = load_values_v2(path)
    else:
        rec = load_values(path)
    if TAG and isinstance(rec.get('neutral_facts'), str):
        rec['neutral_facts'] = scrub_outcome(rec['neutral_facts'])
    return rec
COLUMNS = list(dict.fromkeys(list(FIELDS) + list(EXTRA_FIELDS)))
VERDICTS = ['correct', 'partially_correct', 'incorrect', 'unsupported']

SYSTEM = (
    'You are a careful legal research assistant auditing a dataset built from Indian Supreme Court judgments. '
    'Another model extracted values from a judgment; you check each value against the judgment text only, '
    'using no outside knowledge.\n\n'
    'Verdicts:\n'
    '- correct: the judgment supports the value (for a "Not stated"-style value: the judgment really does not '
    'state it).\n'
    '- partially_correct: right in substance but incomplete or slightly off (e.g. one of two weapons, '
    'sections missing).\n'
    '- incorrect: the judgment contradicts the value, or the value is "Not stated" but the judgment does state '
    'it.\n'
    '- unsupported: the value is given but nothing in the judgment backs it (e.g. a guessed age).\n'
    'Summaries (facts, arguments, rationale) are judged on accuracy, not wording: paraphrase is fine, invented '
    'or wrong details are not. neutral_facts must also not reveal the court outcome.\n'
    'For every verdict other than correct, give the value the judgment supports in "correct_value" '
    '("Not stated" if none) and a short quote with its page. Keep each reason under 25 words.'
)


def case_paths(all_cases=False, limit=None):
    src = 'dataset_base_cases.csv' if all_cases else 'dataset_250_verified.csv'
    paths = pd.read_csv(os.path.join(DATA, src))['path'].tolist()
    return paths[:limit] if limit else paths


def judgment_with_pages(path):
    doc = JudgmentText.from_pdf(path)
    return '\n\n'.join(f'[page {i}]\n{p}' for i, p in enumerate(doc.pages, 1))


def user_prompt(path):
    values = get_values(path)
    spec = '\n'.join(f'- {c}: {json.dumps(values.get(c), ensure_ascii=False)}' for c in COLUMNS)
    defs = ''
    if TAG.startswith('v2'):  # judge each column by the definition the extractor was given
        from step2v2_extract import DEFS
        defs = ('COLUMN DEFINITIONS (judge each value against its definition):\n'
                + '\n'.join(f'- {c}: {DEFS.get(c, "")}' for c in COLUMNS) + '\n\n')
    return (f'JUDGMENT ({path}):\n"""\n{judgment_with_pages(path)}\n"""\n\n{defs}'
            f'EXTRACTED VALUES ({len(COLUMNS)} columns):\n{spec}\n\n'
            'Judge every column listed. Reply with only a JSON object keyed by column name, each entry:\n'
            '{"verdict": "correct|partially_correct|incorrect|unsupported", "correct_value": "... or null", '
            '"quote": "... or null", "page": number or null, "reason": "..."}')


def request(path):
    return {
        'custom_id': path,  # paths look like 2010_13_203_206, valid custom_ids
        'params': {
            'model': MODEL,
            # thinking counts toward this; most cases need ~10k, long judgments more (JUDGE_MAX_TOKENS to raise)
            'max_tokens': int(os.environ.get('JUDGE_MAX_TOKENS', '16000')),
            'system': SYSTEM,
            'messages': [{'role': 'user', 'content': user_prompt(path)}],
        },
    }


def submit(paths):
    import anthropic
    os.makedirs(JUDGE_DIR, exist_ok=True)
    done = {f[:-5] for f in os.listdir(RAW_DIR)} if os.path.isdir(RAW_DIR) else set()
    todo = [p for p in paths if p not in done]
    print(f'{len(paths)} cases, {len(paths) - len(todo)} already judged, submitting {len(todo)} with {MODEL}')
    if not todo:
        return
    reqs = []
    for i, p in enumerate(todo, 1):
        reqs.append(request(p))
        print(f'\rbuilt {i}/{len(todo)}', end='', flush=True)
    print()
    batch = anthropic.Anthropic().messages.batches.create(requests=reqs)
    with open(BATCH_FILE, 'w') as f:
        f.write(batch.id)
    print(f'batch {batch.id}: {batch.processing_status}. Check with: python step6_llm_judge.py status')


def status():
    import anthropic
    b = anthropic.Anthropic().messages.batches.retrieve(open(BATCH_FILE).read().strip())
    c = b.request_counts
    print(f'{b.id}: {b.processing_status} | processing {c.processing}, succeeded {c.succeeded}, '
          f'errored {c.errored}, expired {c.expired}, canceled {c.canceled}')
    return b


def collect():
    import anthropic
    client = anthropic.Anthropic()
    b = status()
    if b.processing_status != 'ended':
        print('not finished yet')
        return
    os.makedirs(RAW_DIR, exist_ok=True)
    tokens_in = tokens_out = failed = 0
    for r in client.messages.batches.results(b.id):
        if r.result.type != 'succeeded':
            print(f'{r.custom_id}: {r.result.type} (resubmit with: python step6_llm_judge.py submit)')
            failed += 1
            continue
        msg = r.result.message
        tokens_in += msg.usage.input_tokens
        tokens_out += msg.usage.output_tokens
        text = next((x.text for x in msg.content if x.type == 'text'), '')
        try:
            verdicts = parse_json(text)
        except Exception:
            print(f'{r.custom_id}: reply was not JSON (stop_reason {msg.stop_reason}); will be resubmitted')
            failed += 1
            continue
        with open(os.path.join(RAW_DIR, r.custom_id + '.json'), 'w', encoding='utf-8') as f:
            json.dump({'model': msg.model, 'stop_reason': msg.stop_reason, 'verdicts': verdicts}, f,
                      ensure_ascii=False, indent=1)
    print(f'tokens: {tokens_in:,} in, {tokens_out:,} out; {failed} failed')
    report()


def sheet():
    rows = []
    for fn in sorted(os.listdir(RAW_DIR)):
        path = fn[:-5]
        with open(os.path.join(RAW_DIR, fn), encoding='utf-8') as f:
            verdicts = json.load(f)['verdicts']
        values = get_values(path)
        for c in COLUMNS:
            v = verdicts.get(c) or {}
            verdict = v.get('verdict') if v.get('verdict') in VERDICTS else 'missing'
            rows.append({'path': path, 'column': c, 'value': values.get(c), 'verdict': verdict,
                         'correct_value': v.get('correct_value'), 'quote': v.get('quote'), 'page': v.get('page'),
                         'reason': v.get('reason')})
    df = pd.DataFrame(rows)
    ver = os.path.join(DATA, 'verification_sheet.csv')
    if os.path.exists(ver):  # put the step 2c status alongside, to compare the two checks
        v2 = pd.read_csv(ver)[['path', 'column', 'status']].rename(columns={'status': 'step2c_status'})
        df = df.merge(v2, on=['path', 'column'], how='left')
    return df


def report():
    df = sheet()
    df.to_csv(SHEET, index=False)
    lines = [f'{df["path"].nunique()} cases, {len(df)} cells judged by {MODEL}', '',
             'Overall verdicts:', df['verdict'].value_counts().to_string(), '']
    t = pd.crosstab(df['column'], df['verdict'])
    t['wrong_%'] = (100 * (1 - t.get('correct', 0) / t.sum(axis=1))).round(1)
    lines += ['Per column (sorted by % not fully correct):', t.sort_values('wrong_%', ascending=False).to_string(), '']
    if 'step2c_status' in df:
        lines += ['Judge verdict vs step 2c status:', pd.crosstab(df['step2c_status'], df['verdict']).to_string()]
    txt = '\n'.join(lines)
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)
    print(f'-> {SHEET}, {REPORT}')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    cmd = args[0] if args else 'status'
    limit = int(args[1]) if len(args) > 1 else None
    if cmd == 'submit':
        submit(case_paths('--all' in sys.argv, limit))
    elif cmd == 'dry':
        os.makedirs(JUDGE_DIR, exist_ok=True)
        out = os.path.join(JUDGE_DIR, 'requests_preview.jsonl')
        paths = case_paths('--all' in sys.argv, limit or 2)
        with open(out, 'w', encoding='utf-8') as f:
            for p in paths:
                f.write(json.dumps(request(p), ensure_ascii=False) + '\n')
        chars = os.path.getsize(out)
        print(f'{len(paths)} requests -> {out} (~{chars / 4 / len(paths):,.0f} input tokens per case)')
    elif cmd == 'status':
        status()
    elif cmd == 'collect':
        collect()
    elif cmd == 'report':
        report()
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
