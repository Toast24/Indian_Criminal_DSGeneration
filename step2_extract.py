"""Step 2: extract structured fields from each downloaded judgment with an LLM (local Ollama by default).

Usage: python step2_extract.py [limit]      e.g. `python step2_extract.py 10` to try 10 first
Writes data/text/<path>.txt (PDF text) and data/extracted/<path>.json. Resumes: judgments already extracted are skipped.
Env: [EXTRACT_]LLM_BASE_URL / LLM_MODEL / LLM_API_KEY (see pipeline_common.py), MAX_CHARS (text sent, default 36000).
"""
import json
import os
import sys
import time
import traceback

import pandas as pd
from pypdf import PdfReader

from pipeline_common import DATA, EXTRACT_DIR, PDF_DIR, TEXT_DIR, chat, clean_pdf_text, clip_text, llm_config, parse_json

MAX_CHARS = int(os.environ.get('MAX_CHARS', '36000'))

OUTCOMES = ['convicted', 'acquitted', 'conviction_modified', 'remanded', 'other']
IMPRISONMENT_TYPES = ['none', 'fixed_term', 'life', 'death', 'not_stated']

# field -> instruction. Order is the order the model is asked to fill them in.
FIELDS = {
    'case_title': 'Short case title, e.g. "X v. State of Y"',
    'number_of_accused': 'Integer number of accused/appellants whose criminal liability the Court decides',
    'accused_gender': 'Male / Female / Mixed / Not stated',
    'accused_age': 'Age in years of the (main) accused at the time of offence as a number, or "Not stated"',
    'accused_religion': 'Only if explicitly stated in the judgment, else "Not stated"',
    'accused_caste': 'Caste/community only if explicitly stated (e.g. "Scheduled Caste"), else "Not stated"',
    'accused_occupation': 'Occupation if stated, else "Not stated"',
    'accused_socioeconomic_status': 'Any statement on wealth/poverty/class, else "Not stated"',
    'previous_criminal_record': 'Yes / No / Not stated, with a few words if Yes',
    'victim_gender': 'Male / Female / Mixed / None (victimless) / Not stated',
    'victim_age': 'Age in years as a number, or "Not stated"',
    'victim_caste': 'Only if explicitly stated, else "Not stated"',
    'victim_religion': 'Only if explicitly stated, else "Not stated"',
    'accused_victim_relationship': 'e.g. Spouse, Relative, Neighbour, Acquaintance, Stranger, Not stated',
    'offence_category': 'One of: Murder, Culpable homicide, Attempt to murder, Dowry death, Cruelty, Rape, '
                        'Sexual assault, Kidnapping, Robbery/Dacoity, Hurt, Cheating/Fraud, Forgery, '
                        'Criminal breach of trust, Narcotics, Corruption, Other',
    'statutory_provisions': 'Sections charged, e.g. "IPC s.302, s.34; Arms Act s.27"',
    'weapon': 'Weapon used, or "None mentioned"',
    'evidence_type': 'Main kinds of evidence: eyewitness, circumstantial, medical, recovery, dying declaration, etc.',
    'confession': 'Any confession/admission and whether relied on, else "None"',
    'aggravating_circumstances': 'Aggravating facts noted, else "None noted"',
    'mitigating_circumstances': 'Mitigating facts noted, else "None noted"',
    'trial_court_outcome': 'What the trial court decided, in a few words (verdict and sentence)',
    'high_court_outcome': 'What the High Court decided, in a few words, or "Not applicable"',
    'final_outcome': 'The Supreme Court\'s final result for the accused, exactly one of: ' + ', '.join(OUTCOMES) +
                     '. convicted = conviction upheld or restored; acquitted = accused acquitted/discharged; '
                     'conviction_modified = convicted of a lesser/different offence or sentence changed; '
                     'remanded = sent back for fresh trial/hearing',
    'offence_finally_established': 'Offence(s) the accused finally stands convicted of, or "None"',
    'imprisonment_type': 'Final sentence type, exactly one of: ' + ', '.join(IMPRISONMENT_TYPES),
    'imprisonment_years': 'Final fixed-term sentence in years as a number (e.g. 7, 2.5); null if not a fixed term',
    'fine_rs': 'Final fine in rupees as a number, or null',
    'neutral_facts': 'A 150-300 word neutral summary of the prosecution case and the evidence as presented at trial, '
                     'written so a judge could decide guilt from it. Refer only to "the accused" and "the victim" '
                     '(and roles like "the victim\'s brother"); NO names, NO religion, caste, gender pronouns, '
                     'nationality or wealth of the accused. Describe only the incident, the investigation and the '
                     'evidence; stop before any court proceedings. NEVER mention the trial court, High Court, Supreme '
                     'Court, appeals, convictions, acquittals or sentences.',
}

SYSTEM = ('You are a careful legal research assistant extracting data from Indian Supreme Court criminal judgments. '
          'Use only what the judgment says. If something is not stated, write "Not stated". Reply with one JSON object.')


def build_prompt(text):
    spec = '\n'.join(f'- "{k}": {v}' for k, v in FIELDS.items())
    return (f'Extract these fields from the judgment below and return a JSON object with exactly these keys:\n{spec}\n\n'
            f'JUDGMENT TEXT:\n"""\n{text}\n"""')


def normalise(rec):
    """Coerces the model's output onto the schema; records problems in `_warnings`."""
    out, warn = {}, []
    for k in FIELDS:
        if k not in rec:
            warn.append(f'missing {k}')
        out[k] = rec.get(k)
    fo = str(out.get('final_outcome') or '').strip().lower().replace(' ', '_')
    if fo not in OUTCOMES:
        fo = next((o for o in OUTCOMES if o in fo), 'other')
        warn.append(f'final_outcome coerced from {rec.get("final_outcome")!r}')
    out['final_outcome'] = fo
    it = str(out.get('imprisonment_type') or '').strip().lower().replace(' ', '_').replace('-', '_')
    if it not in IMPRISONMENT_TYPES:
        it = ('life' if 'life' in it else 'death' if 'death' in it else 'fixed_term' if 'year' in it or 'rigorous' in it
              else 'not_stated')
        warn.append(f'imprisonment_type coerced from {rec.get("imprisonment_type")!r}')
    out['imprisonment_type'] = it
    for k in ('imprisonment_years', 'fine_rs', 'number_of_accused'):
        v = out.get(k)
        try:
            out[k] = float(str(v).replace(',', '').split()[0]) if v not in (None, '', 'null') else None
        except (ValueError, IndexError):
            out[k] = None
    out['_warnings'] = warn
    return out


def pdf_to_text(path):
    txt_path = os.path.join(TEXT_DIR, path + '.txt')
    if os.path.exists(txt_path):
        with open(txt_path, encoding='utf-8') as f:
            return f.read()
    reader = PdfReader(os.path.join(PDF_DIR, path + '.pdf'))
    text = clean_pdf_text('\n'.join((p.extract_text() or '') for p in reader.pages))
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def extract_one(path):
    text = pdf_to_text(path)
    if len(text) < 1500:
        raise ValueError(f'too little text in PDF ({len(text)} chars); probably scanned')
    msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': build_prompt(clip_text(text, MAX_CHARS))}]
    last = None
    for attempt in range(2):
        try:
            rec = normalise(parse_json(chat(msgs, max_tokens=3000, role='extract')))
            rec['_text_chars'] = len(text)
            return rec
        except Exception as e:
            last = e
    raise last


def extract_paths(paths, label=''):
    """Extracts every judgment in `paths` that has a PDF and no JSON yet; returns the number attempted."""
    os.makedirs(TEXT_DIR, exist_ok=True)
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    todo = [p for p in paths if os.path.exists(os.path.join(PDF_DIR, p + '.pdf'))
            and not os.path.exists(os.path.join(EXTRACT_DIR, p + '.json'))]
    model = llm_config('extract')[1]
    print(f'{label}model {model}: {len(todo)} to extract', flush=True)
    t0 = time.time()
    for i, path in enumerate(todo, 1):
        t = time.time()
        try:
            rec = extract_one(path)
            rec['_path'], rec['_model'] = path, model
            with open(os.path.join(EXTRACT_DIR, path + '.json'), 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
            status = f"{rec['final_outcome']}, {rec['offence_category']}"
        except Exception as e:
            with open(os.path.join(DATA, 'extract_errors.log'), 'a', encoding='utf-8') as f:
                f.write(f'{path}\t{e!r}\n{traceback.format_exc()}\n')
            status = f'ERROR {e!r}'[:150]
        el = time.time() - t0
        print(f'{label}[{i}/{len(todo)}] {path} ({time.time() - t:.0f}s) {status} | eta {el / i * (len(todo) - i) / 60:.0f} min',
              flush=True)
    return len(todo)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sel = pd.read_csv(os.path.join(DATA, 'selected_cases.csv'))
    paths = [p for p in sel['path'] if os.path.exists(os.path.join(PDF_DIR, p + '.pdf'))
             and not os.path.exists(os.path.join(EXTRACT_DIR, p + '.json'))]
    print(f'{len(sel) - len(paths)} already done or missing a PDF')
    extract_paths(paths[:limit] if limit else paths)


if __name__ == '__main__':
    main()
