"""Shared model clients. Each call returns a dict with content, reasoning_trace, finish_reason, token counts and cost.

- sarvam:     sarvam-105b via the Sarvam SDK (cost from token counts, INR)
- openrouter: openai/gpt-oss-120b via OpenRouter, pinned to the Groq provider with no fallback, so results are
              comparable with the Exp 1 run made directly on Groq (cost reported by OpenRouter in USD)
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

USD_TO_INR = 88.0                                   # approximate, for a single spend column across providers
SARVAM_PRICE_IN, SARVAM_PRICE_OUT = 29.28 / 1e6, 73.20 / 1e6
MODEL_NAMES = {'sarvam': 'sarvam-105b', 'openrouter': 'gpt-oss-120b'}

_sarvam = None
_http = httpx.Client(timeout=180)

def chat(provider, messages, temperature=0.0, max_tokens=12000, json_mode=True):
    global _sarvam
    if provider == 'sarvam':
        if _sarvam is None:
            from sarvamai import SarvamAI
            _sarvam = SarvamAI(api_subscription_key=os.environ['SARVAM_API_KEY'])
        kw = {'response_format': {'type': 'json_object'}} if json_mode else {}
        r = _sarvam.chat.completions(model='sarvam-105b', temperature=temperature, reasoning_effort='low',
                                     max_tokens=max_tokens, messages=messages, **kw)
        ch, u = r.choices[0], r.usage
        pt, ct = (u.prompt_tokens, u.completion_tokens) if u else (0, 0)
        return {'content': ch.message.content, 'reasoning_trace': getattr(ch.message, 'reasoning_content', None),
                'finish_reason': ch.finish_reason, 'prompt_tokens': pt, 'completion_tokens': ct,
                'cost_inr': pt * SARVAM_PRICE_IN + ct * SARVAM_PRICE_OUT, 'served_by': 'sarvam'}
    if provider == 'openrouter':
        body = {'model': 'openai/gpt-oss-120b', 'temperature': temperature, 'max_tokens': max_tokens,
                'reasoning': {'effort': 'low'}, 'provider': {'order': ['groq'], 'allow_fallbacks': False},
                'messages': messages}
        if json_mode: body['response_format'] = {'type': 'json_object'}
        r = _http.post('https://openrouter.ai/api/v1/chat/completions', json=body,
                       headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY']})
        if r.status_code != 200:
            raise RuntimeError(f'{r.status_code} {r.text[:300]}')
        j = r.json()
        if 'error' in j: raise RuntimeError(str(j['error'])[:300])
        ch, u = j['choices'][0], j.get('usage') or {}
        return {'content': ch['message'].get('content'), 'reasoning_trace': ch['message'].get('reasoning'),
                'finish_reason': ch.get('finish_reason'), 'prompt_tokens': u.get('prompt_tokens'),
                'completion_tokens': u.get('completion_tokens'), 'cost_usd': u.get('cost', 0.0),
                'cost_inr': (u.get('cost') or 0.0) * USD_TO_INR, 'served_by': j.get('provider')}
    raise ValueError(provider)
