"""Step 1: pick ~650 Supreme Court criminal-appeal judgments at random and download their English PDFs.

Source: the public AWS Open Data bucket s3://indian-supreme-court-judgments (per-year metadata parquet + per-judgment PDFs).
Usage: python step1_select_and_download.py [n_cases] [first_year] [last_year]
       python step1_select_and_download.py --add N     top up: append N judgments not already selected
       python step1_select_and_download.py --from-list selected_cases_850.txt
                                                        exactly the judgments listed (one case path per line), in order
Writes data/selected_cases.csv and data/pdf/<path>.pdf. Re-running skips PDFs already downloaded.
"""
import io
import os
import re
import sys
import time

import pandas as pd
import requests

from pipeline_common import DATA, PDF_DIR, S3

ADD = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == '--add' else 0
FROM_LIST = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--from-list' else None
ARGS = [] if ADD or FROM_LIST else sys.argv[1:]
N_CASES = int(ARGS[0]) if ARGS else 650
FIRST_YEAR = int(ARGS[1]) if len(ARGS) > 1 else 2010
LAST_YEAR = int(ARGS[2]) if len(ARGS) > 2 else 2024
SEED = 42

# Substantive offences, so the sample is mostly trials on merits rather than bail or quashing petitions
OFFENCE_RE = re.compile(r'\b(?:30[2-7]|304-?B|376|36[3-6]|39[2-7]|498-?A|NDPS|324|326|354|420|409|467|468|471)\b', re.I)


def load_metadata(year):
    r = requests.get(f'{S3}/metadata/parquet/year={year}/metadata.parquet', timeout=120)
    r.raise_for_status()
    df = pd.read_parquet(io.BytesIO(r.content))
    df['year'] = year
    return df


def html_text(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html or ''))


def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    frames = []
    for y in range(FIRST_YEAR, LAST_YEAR + 1):
        try:
            frames.append(load_metadata(y))
            print(f'metadata {y}: {len(frames[-1])} judgments')
        except Exception as e:
            print(f'metadata {y}: skipped ({e})')
    meta = pd.concat(frames, ignore_index=True)
    meta['meta_text'] = meta['raw_html'].map(html_text)
    is_crl = meta['meta_text'].str.contains(r'Case No\s*:\s*CRIMINAL APPEAL', case=False, regex=True)
    has_offence = (meta['meta_text'] + ' ' + meta['description'].fillna('')).str.contains(OFFENCE_RE)
    pool = meta[is_crl & has_offence & meta['available_languages'].fillna('').str.contains('ENG')]
    pool = pool.drop_duplicates('path')
    print(f'criminal appeals with substantive offences: {len(pool)} of {len(meta)}')

    sel_path = os.path.join(DATA, 'selected_cases.csv')
    existing = pd.read_csv(sel_path) if ADD else None
    if FROM_LIST:
        # Exactly the listed judgments, in the listed order - no filtering or sampling
        with open(FROM_LIST, encoding='utf-8') as f:
            wanted = [l.strip() for l in f if l.strip()]
        picked = meta.drop_duplicates('path').set_index('path').reindex(wanted)
        missing = picked.index[picked['title'].isna()].tolist()
        if missing:
            print(f'WARNING: {len(missing)} listed cases not found in the archive metadata: {missing[:10]}')
        picked = picked.dropna(subset=['title']).reset_index().copy()
    elif ADD:
        # A different seed and the already-selected cases excluded, so the original sample stays as it was
        pool = pool[~pool['path'].isin(existing['path'])]
        picked = pool.sample(n=min(ADD, len(pool)), random_state=SEED + 1).copy()
    else:
        picked = pool.sample(n=min(N_CASES, len(pool)), random_state=SEED).copy()
    picked['pdf_url'] = [f'{S3}/data/pdf/year={y}/english/{p}_EN.pdf' for y, p in zip(picked['year'], picked['path'])]
    picked['case_no'] = picked['meta_text'].str.extract(r'Case No\s*:\s*(CRIMINAL APPEAL[^|]*)', flags=re.I)[0].str.strip()
    cols = ['path', 'year', 'title', 'petitioner', 'respondent', 'case_id', 'citation', 'decision_date',
            'disposal_nature', 'judge', 'case_no', 'description', 'pdf_url']
    out = pd.concat([existing, picked[cols]], ignore_index=True) if ADD else picked[cols]
    out.to_csv(sel_path, index=False)
    print(f'{len(picked)} newly selected; {len(out)} in {sel_path}')

    ok = 0
    for i, (path, url) in enumerate(zip(picked['path'], picked['pdf_url']), 1):
        out = os.path.join(PDF_DIR, path + '.pdf')
        if os.path.exists(out) and os.path.getsize(out) > 0:
            ok += 1
            continue
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=120)
                r.raise_for_status()
                with open(out, 'wb') as f:
                    f.write(r.content)
                ok += 1
                break
            except Exception as e:
                if attempt == 2:
                    print(f'  failed {path}: {e}')
                time.sleep(2)
        if i % 50 == 0:
            print(f'  downloaded {i}/{len(picked)}')
    print(f'done: {ok}/{len(picked)} PDFs in {PDF_DIR}')


if __name__ == '__main__':
    main()
