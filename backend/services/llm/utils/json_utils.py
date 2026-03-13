import json
import re
from typing import Any, Dict


def extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extract the first valid JSON object from model output.

    This helps when the model returns extra text before/after the JSON.
    """
    text = text.strip()

    # First try direct parsing
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Parsed JSON is not an object.")
    except json.JSONDecodeError:
        pass

    # Fallback: extract first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")

    candidate = match.group(0)
    parsed = json.loads(candidate)

    if not isinstance(parsed, dict):
        raise ValueError("Parsed JSON is not an object.")

    return parsed
