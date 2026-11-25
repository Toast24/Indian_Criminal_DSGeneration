"""Step 2c: make every extracted value one small step from verification.

For each usable case and each extracted column:
- stated values: the LLM must copy exact supporting quote(s) from the judgment (or say it cannot); a script then finds
  each quote in the PDF text (fuzzy, to survive PDF spacing glitches) and records the page. A quote that is not in the
  judgment, or a number that is not in its quote, is flagged - that is the hallucination signal.
- "Not stated" values: no quote is possible, so the judgment is searched for keywords that would mean the field IS
  stated (e.g. religion words for accused_religion). Hits are flagged as a possible miss.
- whole-case consistency checks (acquitted but sentenced, sentence above 20 years, implausible ages, ...).

Usage:
  python step2c_verify.py usable [limit]   verify every usable case (resumes: finished groups are skipped)
  python step2c_verify.py report           -> data/verification_sheet.csv (one row per case x column) + per-column summary
Writes data/verified/<path>.json.
"""
import glob
import json
import os
import re
import sys
import time
import traceback

import pandas as pd
from pypdf import PdfReader
from rapidfuzz import fuzz

from pipeline_common import DATA, EXTRACT_DIR, PDF_DIR, chat, clean_pdf_text, clip_text, llm_config, parse_json
from step2_extract import FIELDS, pdf_to_text
from step2b_extract_extra import EXTRA_DIR, GROUPS as EXTRA_GROUPS

VERIFY_DIR = os.path.join(DATA, 'verified')
MAX_CHARS = int(os.environ.get('MAX_CHARS', '36000'))
FUZZY_MIN = 90          # rapidfuzz partial_ratio needed to accept a quote that is not an exact (normalised) match

_main = list(FIELDS)
# One LLM call per group; the judgment text comes first in every prompt so Ollama can reuse its cache across calls
VERIFY_GROUPS = {
    'main_people': _main[:_main.index('offence_category')],
    'main_case': _main[_main.index('offence_category'):],
    'offence_evidence': list(EXTRA_GROUPS['offence']) + list(EXTRA_GROUPS['evidence']),
    'procedure_reasoning': list(EXTRA_GROUPS['procedure']) + list(EXTRA_GROUPS['reasoning']),
}
NUMERIC_FIELDS = {'accused_age', 'victim_age', 'imprisonment_years', 'fine_rs'}

NOT_STATED_RE = re.compile(r'^(?:not[ _]stated|not mentioned|none|none noted|none mentioned|not applicable|'
                           r'not identified|n/?a|null|nil|unknown)?$', re.I)
# Fields whose "Not stated" can be checked by searching for words that would mean the judgment does state it
NOT_STATED_KEYWORDS = {
    'accused_religion': r'\b(?:hindu|muslim|mohammedan|christian|sikh|jain|buddhist|parsi|religio\w*)\b',
    'victim_religion': r'\b(?:hindu|muslim|mohammedan|christian|sikh|jain|buddhist|parsi|religio\w*)\b',
    'accused_caste': r'\b(?:caste|scheduled|dalit|tribe|backward class|brahmin|harijan)\b',
    'victim_caste': r'\b(?:caste|scheduled|dalit|tribe|backward class|brahmin|harijan)\b',
    'accused_age': r'\b(?:aged|age of|years old|\d{1,2} years of age)\b',
    'victim_age': r'\b(?:aged|age of|years old|\d{1,2} years of age|minor)\b',
    'previous_criminal_record': r'\b(?:antecedents?|previous(?:ly)? convicted|history.sheeter|criminal record|habitual)\b',
    'weapon': r'\b(?:knife|axe|gun|pistol|revolver|rifle|sword|lathi|stick|rod|dagger|gandasa|spear|weapon)\b',
    'confession': r'\b(?:confess\w*|extra.judicial)\b',
    'custody_duration': r'\b(?:in custody|undergone|incarcerat\w*|in jail)\b',
    'bail_history': r'\b(?:bail)\b',
    'motive': r'\b(?:motive)\b',
}

NUM_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
             'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']

SYSTEM = ('You check data extracted from an Indian Supreme Court judgment against the judgment itself. For every field, '
          'copy word-for-word from the judgment the passage that supports the given value. Never paraphrase, never '
          'repeat the extracted value as a quote, never invent text. Reply with one JSON object.')


def is_not_stated(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return bool(NOT_STATED_RE.match(re.sub(r'[\s.]+$', '', str(value).strip())))


def norm(text):
    """Lowercase alphanumerics separated by single spaces - robust to PDF line breaks, hyphenation and odd quotes."""
    text = str(text).lower().replace('-\n', '')
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


class JudgmentText:
    """Normalised judgment text with a page index, for locating quotes."""

    def __init__(self, pages):
        self.starts, parts, pos = [], [], 0
        for p in pages:
            n = norm(p)
            self.starts.append(pos)
            parts.append(n)
            pos += len(n) + 1
        self.text = ' '.join(parts)
        self.raw = '\n'.join(pages)
        self.pages = pages

    @classmethod
    def from_pdf(cls, path):
        return cls([clean_pdf_text(p.extract_text() or '') for p in PdfReader(os.path.join(PDF_DIR, path + '.pdf')).pages])

    def closest_note(self, value):
        """Best-matching sentence in the judgment for a flagged value, so a reader can check it in one look."""
        if not hasattr(self, 'sentences'):
            self.sentences = [(i, re.sub(r'\s+', ' ', x).strip()) for i, page in enumerate(self.pages, 1)
                              for x in re.split(r'(?<=[.;])\s+', page) if len(x.split()) >= 5]
        if not self.sentences or not str(value).strip():
            return ''
        best = max(self.sentences, key=lambda s: fuzz.token_set_ratio(str(value), s[1]))
        score = fuzz.token_set_ratio(str(value), best[1])
        return f'; closest passage (p.{best[0]}, match {score:.0f}): "{best[1][:300]}"'

    def page_of(self, offset):
        page = 1
        for i, s in enumerate(self.starts, 1):
            if s <= offset:
                page = i
        return page

    def find(self, quote):
        """Returns (found, score, page) for one quote."""
        q = norm(quote)
        if len(q) < 8:
            return False, 0.0, None
        i = self.text.find(q)
        if i >= 0:
            return True, 100.0, self.page_of(i)
        al = fuzz.partial_ratio_alignment(q, self.text, score_cutoff=FUZZY_MIN)
        if al is None:
            best = fuzz.partial_ratio(q, self.text)
            return False, round(best, 1), None
        return True, round(al.score, 1), self.page_of(al.dest_start)


def number_forms(value):
    """Ways a number can appear in a judgment: 7 -> {'7', 'seven'}, 1000 -> {'1000', '1,000'}, 2.5 -> {'2.5', ...}."""
    try:
        v = float(str(value).replace(',', '').split()[0])
    except (ValueError, IndexError):
        return set()
    forms = set()
    if v == int(v):
        n = int(v)
        forms |= {str(n), f'{n:,}'}
        if n < 20:
            forms.add(NUM_WORDS[n])
        elif n < 100:
            t, u = divmod(n, 10)
            forms |= {TENS[t]} if u == 0 else {f'{TENS[t]} {NUM_WORDS[u]}', f'{TENS[t]}-{NUM_WORDS[u]}'}
        if n >= 1000 and n % 1000 == 0:
            forms |= {f'{n // 1000} thousand', f'{n // 1000}000'}
        if n >= 100000 and n % 100000 == 0:
            forms |= {f'{n // 100000} lakh', f'{n // 100000} lakhs'}
    else:
        forms.add(str(v))
        if v % 1 == 0.5:
            forms.add(f'{int(v)} and a half')
            if v < 20:
                forms.add(f'{NUM_WORDS[int(v)]} and a half')
    return forms


def number_in(value, quotes):
    joined = ' '.join(quotes).lower().replace('\n', ' ')
    return any(re.search(r'(?<![\d,.])' + re.escape(f) + r'(?![\d])', joined) for f in number_forms(value))


def field_status(field, value, supported, quotes, doc):
    """Status of one cell plus per-quote matches."""
    if is_not_stated(value):
        rx = NOT_STATED_KEYWORDS.get(field)
        if not rx:
            return 'not_stated', [], None
        hits = list(re.finditer(rx, doc.raw, re.I))
        if not hits:
            return 'not_stated_confirmed', [], None
        # Show where the words occur, so a reader can tell a real miss from e.g. a judge named Jain
        snippets = [re.sub(r'\s+', ' ', doc.raw[max(0, m.start() - 60):m.end() + 60]) for m in hits[:3]]
        return 'not_stated_check', [], f'{len(hits)} mention(s): ' + ' | '.join(f'...{x}...' for x in snippets)
    matches = [dict(zip(('text', 'found', 'score', 'page'), (q, *doc.find(q)))) for q in quotes if str(q).strip()]
    if supported is False or not matches:
        return 'unsupported', matches, 'model found no supporting passage' + doc.closest_note(value)
    found = [m for m in matches if m['found']]
    if not found:
        return 'quote_not_found', matches, 'no quote occurs in the judgment' + doc.closest_note(value)
    if field in NUMERIC_FIELDS and not number_in(value, [m['text'] for m in found]):
        return 'value_mismatch', matches, f'{value} does not appear in the quote'
    if len(found) < len(matches):
        return 'partly_verified', matches, f'{len(matches) - len(found)} of {len(matches)} quotes not found'
    return 'verified', matches, None


# partly_verified (at least one quote found, another slightly off) stays visible in the sheet but is not flagged
FLAG_STATUSES = {'unsupported', 'quote_not_found', 'value_mismatch', 'not_stated_check', 'error'}


def missing_sections(provisions, doc):
    """Section numbers in the extracted provisions that never occur in the judgment."""
    sections = set(re.findall(r'\b(\d{2,3}(?:-?[A-Z])?)\b', str(provisions or '')))
    return sorted(s for s in sections if not re.search(r'\b' + re.escape(s).replace(r'\-', '-?') + r'\b', doc.raw))


def consistency_flags(rec, doc):
    """Whole-case checks that need no quotes."""
    flags = []
    out, itype = rec.get('final_outcome'), rec.get('imprisonment_type')
    years = rec.get('imprisonment_years')
    if out == 'acquitted' and (itype in ('fixed_term', 'life', 'death') or (years or 0) > 0):
        flags.append('acquitted but a sentence is recorded')
    if out == 'acquitted' and not is_not_stated(rec.get('offence_finally_established')):
        flags.append('acquitted but an offence is recorded as finally established')
    if itype == 'fixed_term' and years is not None and years > 20:
        flags.append(f'fixed-term sentence of {years} years exceeds 20')
    if itype == 'fixed_term' and years is None:
        flags.append('fixed-term sentence without a number of years')
    for f in ('accused_age', 'victim_age'):
        try:
            a = float(rec.get(f))
            if not 0 < a <= 100:
                flags.append(f'{f} {a} implausible')
        except (TypeError, ValueError):
            pass
    if rec.get('offence_category') == 'Dowry death' and str(rec.get('victim_gender', '')).lower() == 'male':
        flags.append('dowry death with a male victim')
    missing = missing_sections(rec.get('statutory_provisions'), doc)
    if missing:
        flags.append('sections not found in judgment: ' + ', '.join(missing))
    return flags


def build_prompt(text, fields, values):
    spec = '\n'.join(f'- "{f}": {json.dumps(values.get(f), ensure_ascii=False)}' for f in fields)
    return (f'JUDGMENT TEXT:\n"""\n{text}\n"""\n\n'
            f'These values were extracted from the judgment above:\n{spec}\n\n'
            'For each field return {"supported": true/false, "quotes": [exact passages copied from the judgment]}. '
            'Give ONE quote of at most 30 words; give two only for long summaries or arguments. A quote must be text '
            'that appears in the judgment, not a restatement of the value. For category labels (e.g. offence category, '
            'outcome, sentence type, completed/attempt) quote the passage that justifies the label. Use false and [] '
            'only if nothing in the judgment supports the value. Return a JSON object keyed by field name.')


def load_values(path):
    with open(os.path.join(EXTRACT_DIR, path + '.json'), encoding='utf-8') as f:
        rec = json.load(f)
    extra_fp = os.path.join(EXTRA_DIR, path + '.json')
    if os.path.exists(extra_fp):
        with open(extra_fp, encoding='utf-8') as f:
            rec.update({k: v for k, v in json.load(f).items() if not k.startswith('_')})
    return rec


def verify_case(path):
    """Fills data/verified/<path>.json group by group. Returns the groups that failed."""
    out = os.path.join(VERIFY_DIR, path + '.json')
    res = {'fields': {}, '_groups': []}
    if os.path.exists(out):
        with open(out, encoding='utf-8') as f:
            res = json.load(f)
    values = load_values(path)
    doc = JudgmentText.from_pdf(path)
    text = clip_text(pdf_to_text(path), MAX_CHARS)
    failed = []
    for group, fields in VERIFY_GROUPS.items():
        if group in res['_groups']:
            continue
        fields = [f for f in fields if f in values]
        stated = [f for f in fields if not is_not_stated(values.get(f))]
        got = {}
        if stated:
            msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': build_prompt(text, stated, values)}]
            for attempt in range(2):
                try:
                    got = parse_json(chat(msgs, max_tokens=3000, role='extract'))
                    break
                except Exception as e:
                    if attempt == 1:
                        failed.append(group)
                        with open(os.path.join(DATA, 'extract_errors.log'), 'a', encoding='utf-8') as f:
                            f.write(f'{path} [verify:{group}]\t{e!r}\n{traceback.format_exc()}\n')
            if group in failed:
                continue
        for fld in fields:
            ans = got.get(fld) if isinstance(got.get(fld), dict) else {}
            quotes = ans.get('quotes') or []
            quotes = [quotes] if isinstance(quotes, str) else [q for q in quotes if isinstance(q, str)]
            status, matches, note = field_status(fld, values.get(fld), ans.get('supported'), quotes, doc)
            res['fields'][fld] = {'value': values.get(fld), 'status': status, 'quotes': matches, 'note': note}
        res['_groups'] = sorted(set(res['_groups']) | {group})
    res['case_flags'] = consistency_flags(values, doc)
    sp = res['fields'].get('statutory_provisions')
    missing = missing_sections(values.get('statutory_provisions'), doc)
    if sp and missing and sp['status'] not in FLAG_STATUSES:
        # A quote can support one section while another was invented, so the cell itself is flagged too
        sp['status'], sp['note'] = 'value_mismatch', 'sections not found in judgment: ' + ', '.join(missing)
    res['_path'], res['_model'] = path, llm_config('extract')[1]
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return failed


def verify_paths(paths, label=''):
    os.makedirs(VERIFY_DIR, exist_ok=True)
    print(f'{label}verifying {len(paths)} cases', flush=True)
    t0 = time.time()
    for i, p in enumerate(paths, 1):
        t = time.time()
        try:
            failed = verify_case(p)
        except Exception as e:
            failed = [repr(e)[:100]]
        el = time.time() - t0
        print(f'{label}verify [{i}/{len(paths)}] {p} ({time.time() - t:.0f}s)'
              f'{" failed: " + ",".join(failed) if failed else ""} | eta {el / i * (len(paths) - i) / 60:.0f} min',
              flush=True)


def load_verification():
    """One row per case x column."""
    rows = []
    for fp in glob.glob(os.path.join(VERIFY_DIR, '*.json')):
        with open(fp, encoding='utf-8') as f:
            r = json.load(f)
        for fld, c in r['fields'].items():
            q = c['quotes']
            rows.append({'path': r['_path'], 'column': fld, 'value': c['value'], 'status': c['status'],
                         'flagged': c['status'] in FLAG_STATUSES, 'note': c['note'],
                         'quote': ' || '.join(m['text'] for m in q), 'pages': ','.join(str(m['page']) for m in q if m['page']),
                         'quote_scores': ','.join(str(m['score']) for m in q)})
        rows.append({'path': r['_path'], 'column': '_case_consistency', 'value': None,
                     'status': 'flagged' if r.get('case_flags') else 'ok', 'flagged': bool(r.get('case_flags')),
                     'note': '; '.join(r.get('case_flags') or []), 'quote': '', 'pages': '', 'quote_scores': ''})
    return pd.DataFrame(rows)


def case_summary():
    """Per-case columns for the dataset: how many cells verified / flagged, and which."""
    v = load_verification()
    if v.empty:
        return pd.DataFrame(columns=['path', 'verify_verified', 'verify_flagged', 'verify_flags'])
    g = v.groupby('path')
    return pd.DataFrame({
        'verify_verified': g['status'].apply(lambda s: int(s.isin(['verified', 'not_stated_confirmed']).sum())),
        'verify_flagged': g['flagged'].sum().astype(int),
        'verify_flags': g.apply(lambda d: '; '.join(f"{c}:{s}" for c, s, fl in zip(d['column'], d['status'], d['flagged']) if fl),
                                include_groups=False),
    }).reset_index()


def report():
    v = load_verification()
    if v.empty:
        print('nothing verified yet')
        return
    out = os.path.join(DATA, 'verification_sheet.csv')
    v.sort_values(['path', 'column']).to_csv(out, index=False)
    print(f'{v["path"].nunique()} cases, {len(v)} cells -> {out}')
    summ = pd.crosstab(v['column'], v['status'])
    summ['flagged_%'] = (v.groupby('column')['flagged'].mean() * 100).round(1)
    with pd.option_context('display.width', 250, 'display.max_rows', 100):
        print(summ.sort_values('flagged_%', ascending=False).to_string())
    print(f'overall: {v["flagged"].mean() * 100:.1f}% of cells flagged')


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'usable':
        from step3_build_dataset import build_base
        paths = build_base(verbose=False)['path'].tolist()
        verify_paths(paths[:int(sys.argv[2])] if len(sys.argv) > 2 else paths)
    elif mode == 'report':
        report()
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
