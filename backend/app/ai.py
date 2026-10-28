import httpx
from . import config


def _call_gemini(prompt: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent"
    )
    r = httpx.post(
        url,
        headers={"x-goog-api-key": config.GEMINI_API_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=config.AI_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_groq(prompt: str) -> str:
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        json={
            "model": config.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=config.AI_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# Providers are tried in this order. A provider with no key is skipped.
PROVIDERS = [
    ("gemini", lambda: config.GEMINI_API_KEY, _call_gemini),
    ("groq", lambda: config.GROQ_API_KEY, _call_groq),
]


def ask_ai(prompt: str):
    """Returns (text, provider_name). Returns (None, None) if every provider fails,
    so the caller can fall back to deterministic rules."""
    errors = {}
    for name, get_key, fn in PROVIDERS:
        if not get_key():
            errors[name] = "no key set"
            continue
        try:
            return fn(prompt), name
        except Exception as e:  # network, 429, bad key, bad response shape
            errors[name] = f"{type(e).__name__}: {e}"
    print("AI unavailable:", errors)
    return None, None


def check_providers():
    """Used by the health endpoint. Never exposes key values."""
    status = {}
    for name, get_key, fn in PROVIDERS:
        if not get_key():
            status[name] = "no key set"
            continue
        try:
            fn("Reply with the single word: ok")
            status[name] = "working"
        except httpx.HTTPStatusError as e:
            status[name] = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            status[name] = f"failing ({type(e).__name__})"
    return status