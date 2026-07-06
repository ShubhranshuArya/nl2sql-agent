import os
import re
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_llm_client() -> AsyncOpenAI:
    """Returns a configured, model-agnostic LLM client.

    Reads LLM_API_KEY and optional LLM_BASE_URL from the environment so any
    LLM endpoint exposing a Chat Completions API (e.g. Amazon Bedrock, or other
    providers) works without code changes. LLM_BASE_URL selects the provider.
    """
    global _client
    if _client is None:
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL") or None  # None => provider default
        if not api_key:
            print("Warning: LLM_API_KEY not found in environment variables.")
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client

def get_model() -> str:
    """Returns the configured model id."""
    return os.getenv("LLM_MODEL", "gpt-4o")

def parse_json_response(content: str) -> dict:
    """Strip markdown fences / prose and parse the first JSON object."""
    if not content:
        return {}
    match = re.search(r"\{.*\}", content, re.DOTALL)
    raw = match.group(0) if match else content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
