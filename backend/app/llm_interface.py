import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Locate the .env file two directories up (from backend/app)
env_path = Path(__file__).resolve().parents[2] / '.env'
print(f"🔍 Loading .env from: {env_path}")

if not env_path.exists():
    raise FileNotFoundError(f"❌ .env file not found at {env_path}")

load_dotenv(dotenv_path=env_path)

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("❌ HF_TOKEN not found in .env file — please add it.")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

def generate_llm_response(prompt: str, model: str = "google/gemma-3-27b-it") -> str:
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"⚠️ LLM request failed: {e}")
