"""Step 2b: extract the remaining gold-schema columns (offence details, evidence, procedure, reasoning) in a second
pass, one LLM call per group so a small model is not overloaded. Only the gold court/parties columns are left out.

Usage:
  python step2b_extract_extra.py usable        every usable case already extracted (as step 3 would select them)
  python step2b_extract_extra.py all [limit]   every extracted judgment
Writes data/extracted_extra/<path>.json; groups already present in a file are skipped, so it resumes.
"""
import json
import os
import sys
import time
import traceback

import pandas as pd

from pipeline_common import DATA, EXTRACT_DIR, TEXT_DIR, chat, clip_text, llm_config, parse_json

EXTRA_DIR = os.path.join(DATA, 'extracted_extra')
MAX_CHARS = int(os.environ.get('MAX_CHARS', '36000'))

# group -> {field: instruction}; field names follow the gold dataset's columns
GROUPS = {
    'offence': {
        'offence_severity': 'Statutory punishment range for the main offence (minimum/maximum)',
        'attempt_completion': 'Completed / Attempt',
        'physical_harm': 'Injuries or death caused, briefly',
        'number_of_offences': 'Number of offences/counts charged and how many were finally upheld',
        'financial_property_loss': 'Money or property lost, or "Not applicable"',
        'premeditation_planning': 'Whether the court found premeditation/planning, briefly',
        'motive': 'Motive found or alleged, or "Not identified"',
    },
    'evidence': {
        'key_evidence_accepted': 'Evidence the Supreme Court accepted or relied on',
        'witness_credibility': 'How the court assessed the main witnesses',
        'post_offence_conduct': 'Conduct of the accused after the offence (absconding, surrender, etc.), or "Not stated"',
    },
    'procedure': {
        'custody_duration': 'Time the accused spent in custody, or "Not stated"',
        'bail_history': 'Bail granted/refused at any stage, or "Not stated"',
        'trial_duration': 'Dates of offence, trial judgment, High Court and Supreme Court decisions where given',
        'legal_representation': 'Counsel for the accused and the State in the Supreme Court',
        'investigation_status': 'e.g. FIR registered, charge sheet filed, trial completed',
        'procedural_irregularity': 'Any procedural lapse the court noted, or "None noted"',
        'appeal_history': 'Outcome at each level: trial court, High Court, Supreme Court',
    },
    'reasoning': {
        'prosecution_argument': 'Main arguments of the prosecution/State in the Supreme Court',
        'defence_argument': 'Main arguments of the accused in the Supreme Court',
        'legal_principle_applied': 'Legal principle or test the Supreme Court applied',
        'precedent_relied_upon': 'Main precedents relied on (case names with citations)',
        'sentencing_rationale': 'Why the final sentence was imposed, or "Not applicable"',
        'judicial_mitigating_factors': 'Mitigating factors the court itself weighed, or "None"',
        'judicial_aggravating_factors': 'Aggravating factors the court itself weighed, or "None"',
        'other_sentence_order': 'Any other order: compensation, directions, guidelines, etc., or "None"',
    },
}
ALL_GROUPS = list(GROUPS)
EXTRA_FIELDS = [f for g in GROUPS.values() for f in g]

SYSTEM = ('You are a careful legal research assistant extracting data from Indian Supreme Court criminal judgments. '
          'Use only what the judgment says, in a sentence or two per field. If something is not stated, write '
          '"Not stated". Reply with one JSON object.')


def build_prompt(group, text):
    spec = '\n'.join(f'- "{k}": {v}' for k, v in GROUPS[group].items())
    return (f'Extract these fields from the judgment below and return a JSON object with exactly these keys:\n{spec}\n\n'
            f'JUDGMENT TEXT:\n"""\n{text}\n"""')


def extract_extra(path, groups, label=''):
    """Adds the missing groups to data/extracted_extra/<path>.json. Returns the groups that failed."""
    out = os.path.join(EXTRA_DIR, path + '.json')
    rec = {}
    if os.path.exists(out):
        with open(out, encoding='utf-8') as f:
            rec = json.load(f)
    todo = [g for g in groups if g not in rec.get('_groups', [])]
    if not todo:
        return []
    with open(os.path.join(TEXT_DIR, path + '.txt'), encoding='utf-8') as f:
        text = clip_text(f.read(), MAX_CHARS)
    failed = []
    for g in todo:
        msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': build_prompt(g, text)}]
        for attempt in range(2):
            try:
                got = parse_json(chat(msgs, max_tokens=2000, role='extract'))
                rec.update({k: got.get(k) for k in GROUPS[g]})
                rec['_groups'] = sorted(set(rec.get('_groups', [])) | {g})
                break
            except Exception as e:
                if attempt == 1:
                    failed.append(g)
                    with open(os.path.join(DATA, 'extract_errors.log'), 'a', encoding='utf-8') as f:
                        f.write(f'{path} [extra:{g}]\t{e!r}\n{traceback.format_exc()}\n')
    rec['_path'], rec['_model'] = path, llm_config('extract')[1]
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return failed


def extract_extra_paths(paths, groups, label=''):
    os.makedirs(EXTRA_DIR, exist_ok=True)
    paths = [p for p in paths if os.path.exists(os.path.join(EXTRACT_DIR, p + '.json'))]
    print(f'{label}extra fields ({", ".join(groups)}) for {len(paths)} judgments', flush=True)
    t0 = time.time()
    for i, p in enumerate(paths, 1):
        t = time.time()
        failed = extract_extra(p, groups)
        el = time.time() - t0
        print(f'{label}extra [{i}/{len(paths)}] {p} ({time.time() - t:.0f}s)'
              f'{" failed: " + ",".join(failed) if failed else ""} | eta {el / i * (len(paths) - i) / 60:.0f} min',
              flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'usable':
        from step3_build_dataset import build_base
        extract_extra_paths(build_base(verbose=False)['path'].tolist(), ALL_GROUPS)
    elif mode == 'all':
        sel = pd.read_csv(os.path.join(DATA, 'selected_cases.csv'))
        paths = sel['path'].tolist()
        extract_extra_paths(paths[:int(sys.argv[2])] if len(sys.argv) > 2 else paths, ALL_GROUPS)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
