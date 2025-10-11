# llm_interface.py
from anaheim_worker import log  # pour logging

def ask_llm(prompt: str) -> str:
    log(f"🤖 ask_llm called with prompt: {prompt[:100]}...")
    return "[]"
