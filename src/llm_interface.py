import os
import subprocess

LLM_CMD = os.getenv("LLM_CMD","gpt4all")

def ask_llm(prompt, timeout=60):
    # Simple call for local gpt4all CLI; adapt if you have another client
    try:
        cmd = [LLM_CMD, "--prompt", prompt]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip()
    except Exception as e:
        return f"LLM_ERROR: {e}"
