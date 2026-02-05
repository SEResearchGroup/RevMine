import json
from datetime import date
from ollama import chat
from ollama._types import ResponseError

MODEL = "deepseek-r1"  # set to exactly what `ollama list` shows

SYSTEM_PROMPT_TEMPLATE = """
You are an assistant embedded in RevMine (a GitLab mining and analytics tool).
Your job is to read the user's message and produce a single JSON object that RevMine can execute.

Today is __TODAY__ (timezone America/Montreal).

You must decide intent: one of ["resolve_dates", "collect", "analyze", "clarify", "other"].

A) intent="resolve_dates"
If the user asks for a time window or date limits (e.g., "last two years", "from 2020 to 2022", "past 6 months"),
YOU MUST return start_date and end_date (ISO YYYY-MM-DD). Do NOT ask a clarification question.
Also include "interpretation" (short).

Defaults for ambiguous time windows:
- "last two years" / "past two years" / "two last years" => last 24 months ending today (inclusive).

Return fields for resolve_dates:
{
  "intent": "resolve_dates",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "interpretation": "..."
}

B) intent="collect"
If the user requests data collection, return:
- entity: one of ["merge_requests", "pull_requests", "commits", "issues", "pipelines", "comments"]
- start_date / end_date if present or inferable
- project: string or null
- filters: object (or empty object)

C) intent="analyze"
If the user requests analysis, return:
- metric: e.g., "commits_per_day", "mrs_per_day", "lead_time", "review_comments_per_mr"
- start_date / end_date if present or inferable
- group_by: e.g., "day", "week", "author", "project" or null
- filters: object (or empty object)

Clarify only if the user asks to collect/analyze but an essential parameter is missing AND cannot be inferred.
If the message is only about dates, use resolve_dates and never clarify.

Important rules:
- Do NOT invent project names, IDs, or computed results.
- Output JSON only. No extra text. No markdown.
"""

def revmine_parse(user_message: str) -> dict:
    today = date.today().isoformat()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("__TODAY__", today).strip()

    response = chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return json.loads(response.message.content.strip())

if __name__ == "__main__":
    user_message = input("User message: ")

    try:
        result = revmine_parse(user_message)
        print(json.dumps(result, indent=2))
    except json.JSONDecodeError:
        print("Model did not return valid JSON.")
    except ResponseError as e:
        print(f"Ollama error: {e}")
        print("Tip: set MODEL to the exact value from `ollama list` (e.g., deepseek-r1:7b).")
