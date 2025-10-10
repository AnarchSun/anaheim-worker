from openai import OpenAI
import json, traceback

from openai.resources.realtime.realtime import log

client = OpenAI()

def get_ts_patch_actions(prompt: str):
    """Ask the LLM to produce structured JSON patch actions for TypeScript fixes."""
    try:
        system_msg = {
            "role": "system",
            "content": (
                "You are an autonomous TypeScript repair assistant.\n"
                "Respond ONLY with a JSON array of patch actions, no markdown or prose.\n"
                "Each action must have fields:\n"
                " - action (string: e.g. 'add_import', 'create_function', 'insert_snippet')\n"
                " - file (string: relative TS file path)\n"
                " - symbol/module/function/param/type/package (optional strings)\n"
                " - snippet (string, optional code to insert)\n"
                " - insert_after/context_snippet (string, optional text anchor)\n"
                " - line (integer, optional line number)\n"
                "No explanation. Only return raw JSON array."
            ),
        }
        user_msg = {"role": "user", "content": prompt}

        # ✅ This fixes the typing warning: using OpenAI's message param objects
        messages = [
            {"role": "system", "content": system_msg["content"]},
            {"role": "user", "content": user_msg["content"]},
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content.strip()
        log(f"🧠 Raw LLM JSON output: {raw_output[:180]}...")

        # Safely parse
        data = json.loads(raw_output)
        if isinstance(data, dict) and "actions" in data:
            return data["actions"]
        elif isinstance(data, list):
            return data
        else:
            log("⚠️ Unexpected JSON structure, returning empty list.")
            return []

    except Exception as ex:
        log(f"💥 get_ts_patch_actions failed: {repr(ex)}\n{traceback.format_exc()}")
        return []
