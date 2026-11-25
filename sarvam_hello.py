import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()
key = os.environ.get("SARVAM_API_KEY")
if not key:
    raise SystemExit("SARVAM_API_KEY is not set. Add it to .env first.")

client = SarvamAI(api_subscription_key=key)
resp = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
)
print(resp.choices[0].message.content)
