"""Step 2 v2 (experimental): one-pass extraction of all 54 columns with Claude (Batch API), aimed at cutting the
error rate the step-6 judge found in v1 (qwen3:8b, clipped text).

Changes from v1:
  1. Full judgment text with page markers (v1 clipped to 36k chars and lost the middle of long judgments).
  2. Quote first: for each field the model copies the supporting passage, then gives the value.
     Factual fields with no quote are set to "Not stated" instead of being guessed.
  3. Sharper definitions for the columns the judge found most often wrong (high_court_outcome, number_of_offences,
     trial_duration, motive / post_offence_conduct / relationship = what the COURT found, ages).

Usage:
  python step2v2_extract.py submit [N]   first N cases of data/dataset_250_verified.csv (default 30)
  python step2v2_extract.py collect      -> data/extracted_v2/<path>.json
Needs ANTHROPIC_API_KEY. EXTRACT_V2_MODEL overrides the model (default claude-haiku-5-5).
"""
import json
import os
import sys

import pandas as pd
from dotenv import load_dotenv

from pipeline_common import DATA, parse_json
from step2_extract import FIELDS, normalise
from step2b_extract_extra import GROUPS
from step2c_verify import JudgmentText, is_not_stated

load_dotenv()
MODEL = os.environ.get('EXTRACT_V2_MODEL', 'claude-haiku-5-5')
OUT_DIR = os.path.join(DATA, 'extracted_v2')
BATCH_FILE = os.path.join(DATA, 'extracted_v2_batch_id.txt')

DEFS = dict(FIELDS)
for g in GROUPS.values():
    DEFS.update(g)
# Sharpened definitions for the columns with the most judge-flagged errors
DEFS.update({
    'high_court_outcome': 'What the High Court decided (appeal/revision/petition dismissed or allowed, conviction '
                          'upheld/altered, sentence changed). Almost every case here came through a High Court: use '
                          '"Not applicable" ONLY if the judgment says the case came to the Supreme Court directly.',
    'number_of_offences': 'Count the distinct offences (sections) the accused was CHARGED/tried with, and how many '
                          'convictions stand after the Supreme Court\'s decision, as "N charged; M finally upheld". '
                          'Count sections, not accused persons or witnesses.',
    'trial_duration': 'List the dates the judgment gives, as "offence: <date>; trial judgment: <date>; High Court: '
                      '<date>; Supreme Court: <date>", writing "not given" for any missing. Do not compute durations.',
    'motive': 'The motive the COURT accepted (or, if the court did not decide it, the motive alleged, marked '
              '"alleged:"), or "Not identified".',
    'post_offence_conduct': 'What the accused did after the offence (absconding, surrender, disclosure, hiding '
                            'evidence) as found or noted by the court, or "Not stated".',
    'accused_victim_relationship': 'Any relationship or prior connection between the accused and the victim that '
                                   'the judgment describes (Spouse, Relative <which>, Neighbour, Acquaintance, '
                                   'Employer, co-worker, political or land rival, prior enmity/dispute, Stranger), '
                                   'or "Not stated".',
    'accused_religion': 'Religion of the accused if the judgment states it OR describes the accused or their '
                        'community by a religious identity (e.g. "Sikh", "Muslim", "Hindu", "Christian"), '
                        'else "Not stated". Do not infer from names.',
    'victim_religion': 'Religion of the victim if the judgment states it OR describes the victim or their '
                       'community by a religious identity, else "Not stated". Do not infer from names.',
    'accused_caste': 'Caste/tribe/community of the accused if the judgment names it (e.g. "Scheduled Caste", '
                     '"Santhal", "Jat"), including descriptions of the community they belong to, else "Not stated".',
    'victim_caste': 'Caste/tribe/community of the victim if the judgment names it (e.g. "Scheduled Caste", '
                    '"Santhal"), including descriptions of the community they belong to, else "Not stated".',
    'accused_age': 'Age of the main accused in years as a number ONLY if the judgment states it, else "Not stated". '
                   'Never estimate.',
    'victim_age': 'Age of the victim in years as a number ONLY if the judgment states it, else "Not stated". '
                  'Never estimate.',
    'offence_severity': 'Maximum (and minimum, if any) punishment the statute prescribes for the main offence, '
                        'as stated in the judgment, else "Not stated". Do not supply it from your own knowledge.',
})
COLUMNS = list(DEFS)
# Summaries and labels: judged on substance, kept even without a single verbatim quote
NO_QUOTE_OK = {'case_title', 'neutral_facts', 'offence_category', 'final_outcome', 'imprisonment_type',
               'evidence_type', 'investigation_status', 'appeal_history', 'prosecution_argument',
               'defence_argument', 'legal_principle_applied', 'sentencing_rationale', 'attempt_completion',
               'number_of_accused', 'accused_gender', 'victim_gender', 'trial_duration', 'number_of_offences'}

SYSTEM = ('You are a careful legal research assistant extracting data from Indian Supreme Court criminal '
          'judgments for a research dataset. Use only what the judgment says, never outside knowledge. Read the '
          'WHOLE judgment before answering: facts about the High Court, witnesses and evidence are often in the '
          'middle. For every field, FIRST copy the passage that supports it (at most 40 words, verbatim, with its '
          'page number), THEN give the value. If no passage supports a value, the value is "Not stated" and the '
          'quote is null. Be careful to separate what a party alleged from what the court found. Reply with one '
          'JSON object only.')


def user_prompt(path):
    doc = JudgmentText.from_pdf(path)
    text = '\n\n'.join(f'[page {i}]\n{p}' for i, p in enumerate(doc.pages, 1))
    spec = '\n'.join(f'- "{k}": {v}' for k, v in DEFS.items())
    return (f'JUDGMENT ({path}):\n"""\n{text}\n"""\n\n'
            f'Fields:\n{spec}\n\n'
            'Return a JSON object with exactly these keys; each value is '
            '{"quote": "<verbatim passage or null>", "page": <number or null>, "value": <value>}.')


def case_paths(limit):
    return pd.read_csv(os.path.join(DATA, 'dataset_250_verified.csv'))['path'].tolist()[:limit]


def submit(paths):
    import anthropic
    os.makedirs(OUT_DIR, exist_ok=True)
    todo = [p for p in paths if not os.path.exists(os.path.join(OUT_DIR, p + '.json'))]
    print(f'{len(paths)} cases, submitting {len(todo)} with {MODEL}')
    if not todo:
        return
    client = anthropic.Anthropic(timeout=600, max_retries=5)
    ids = []
    for i in range(0, len(todo), 50):  # chunks of 50: one huge upload tends to drop the connection
        chunk = todo[i:i + 50]
        reqs = [{'custom_id': p, 'params': {'model': MODEL, 'max_tokens': 32000, 'system': SYSTEM,
                                            'messages': [{'role': 'user', 'content': user_prompt(p)}]}}
                for p in chunk]
        batch = client.messages.batches.create(requests=reqs)
        ids.append(batch.id)
        with open(BATCH_FILE, 'w') as f:
            f.write('\n'.join(ids))
        print(f'batch {batch.id}: {len(chunk)} cases, {batch.processing_status}', flush=True)


def postprocess(raw):
    """Quote-first rule in code: factual fields with no supporting quote become "Not stated"."""
    values, quotes, demoted = {}, {}, []
    for k in COLUMNS:
        cell = raw.get(k)
        if not isinstance(cell, dict):
            cell = {'quote': None, 'page': None, 'value': cell}
        v, q = cell.get('value'), cell.get('quote')
        if k not in NO_QUOTE_OK and not q and not is_not_stated(v):
            demoted.append(k)
            v = 'Not stated'
        values[k] = v
        quotes[k] = {'quote': q, 'page': cell.get('page')}
    base = normalise({k: values[k] for k in FIELDS})
    values.update({k: base[k] for k in FIELDS})
    return {**values, '_quotes': quotes, '_demoted': demoted, '_warnings': base['_warnings']}


def collect():
    import anthropic
    client = anthropic.Anthropic()
    batches = [client.messages.batches.retrieve(i) for i in open(BATCH_FILE).read().split()]
    for b in batches:
        print(f'{b.id}: {b.processing_status} {b.request_counts}')
    if any(b.processing_status != 'ended' for b in batches):
        return False
    tin = tout = 0
    results = (r for b in batches for r in client.messages.batches.results(b.id))
    for r in results:
        if r.result.type != 'succeeded':
            print(r.custom_id, r.result.type)
            continue
        msg = r.result.message
        tin += msg.usage.input_tokens
        tout += msg.usage.output_tokens
        try:
            rec = postprocess(parse_json(next(x.text for x in msg.content if x.type == 'text')))
        except Exception as e:
            print(r.custom_id, 'unparseable:', msg.stop_reason, e)
            continue
        rec['_path'], rec['_model'] = r.custom_id, msg.model
        with open(os.path.join(OUT_DIR, r.custom_id + '.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
    print(f'tokens {tin:,} in, {tout:,} out')
    return True


def load_values_v2(path):
    with open(os.path.join(OUT_DIR, path + '.json'), encoding='utf-8') as f:
        return json.load(f)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'collect'
    if cmd == 'submit':
        submit(case_paths(int(sys.argv[2]) if len(sys.argv) > 2 else 30))
    else:
        collect()
