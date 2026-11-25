"""Shared helpers for the step1-step5 judgment pipeline.

LLM config comes from environment variables:
- LLM_BASE_URL unset  -> local Ollama (native /api/chat, thinking off), model LLM_MODEL (default qwen3:8b)
- LLM_BASE_URL set    -> any OpenAI-compatible endpoint (Groq, OpenRouter, ...), with LLM_MODEL and LLM_API_KEY
Each can be overridden per role with an EXTRACT_ or TEST_ prefix (e.g. TEST_LLM_MODEL), so run_batches.py can
extract with one model while testing another.
"""
import json
import os
import re

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data')
PDF_DIR = os.path.join(DATA, 'pdf')
TEXT_DIR = os.path.join(DATA, 'text')
EXTRACT_DIR = os.path.join(DATA, 'extracted')
S3 = 'https://indian-supreme-court-judgments.s3.amazonaws.com'

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
NUM_CTX = int(os.environ.get('OLLAMA_NUM_CTX', '16384'))


def _env(role, name):
    return os.environ.get(f'{role.upper()}_{name}') if role else None


def llm_config(role=None):
    """role: None, 'extract' or 'test'. Role-prefixed variables win over the plain LLM_* ones."""
    base = (_env(role, 'LLM_BASE_URL') or os.environ.get('LLM_BASE_URL', '')).rstrip('/')
    model = _env(role, 'LLM_MODEL') or os.environ.get('LLM_MODEL') or ('qwen3:8b' if not base else '')
    if base and not model:
        raise RuntimeError('LLM_BASE_URL is set, so LLM_MODEL must be set too')
    return base, model, _env(role, 'LLM_API_KEY') or os.environ.get('LLM_API_KEY', '')


def chat(messages, temperature=0.0, max_tokens=4000, json_mode=True, timeout=900, role=None):
    """Returns the model's text reply."""
    base, model, key = llm_config(role)
    if not base:
        body = {'model': model, 'messages': messages, 'stream': False, 'think': False,
                'options': {'temperature': temperature, 'num_ctx': NUM_CTX, 'num_predict': max_tokens}}
        if json_mode:
            body['format'] = 'json'
        r = requests.post(OLLAMA_URL + '/api/chat', json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()['message']['content']
    body = {'model': model, 'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens}
    if json_mode:
        body['response_format'] = {'type': 'json_object'}
    headers = {'Authorization': 'Bearer ' + key} if key else {}
    r = requests.post(base + '/chat/completions', json=body, headers=headers, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f'{r.status_code} {r.text[:300]}')
    return r.json()['choices'][0]['message']['content']


def parse_json(text):
    """Parses a JSON object from a model reply, tolerating code fences, <think> blocks and surrounding prose."""
    if text is None:
        raise ValueError('empty reply')
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find('{'), text.rfind('}')
        if i < 0 or j <= i:
            raise
        return json.loads(text[i:j + 1])


def clip_text(text, max_chars):
    """Keeps the head (facts, charges) and tail (findings, order) of a long judgment."""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.65)
    tail = max_chars - head
    return text[:head] + '\n\n[... middle of judgment omitted ...]\n\n' + text[-tail:]


COURT_RE = re.compile(r'\b(trial court|sessions (?:court|judge)|high court|supreme court|this court|appeal|appellant|'
                      r'convict\w*|acquit\w*|sentenc\w*|remand\w*|upheld|set aside)\b', re.I)


def scrub_outcome(facts):
    """Drops sentences that reveal how any court decided, so the tested model only sees the incident and evidence."""
    sentences = re.split(r'(?<=[.!?])\s+', str(facts or '').strip())
    return ' '.join(s for s in sentences if s and not COURT_RE.search(s))


def clean_pdf_text(text):
    """Drops the A-H margin letters and page headers that SCR PDFs carry."""
    lines = [l for l in text.splitlines() if not re.fullmatch(r'\s*[A-H]\s*', l)]
    text = '\n'.join(lines)
    text = re.sub(r'\d+\s+SUPREME COURT REPORTS\s+\[\d{4}\]\s+\d+\s+S\.C\.R\.', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()
