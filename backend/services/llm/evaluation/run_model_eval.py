import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests


def call_openrouter_parser(
    base_url: str,
    user_message: str,
    model: str,
    timeout: int = 120,
) -> dict:
    url = f"{base_url.rstrip('/')}/openrouter"

    payload = {
        "user_message": user_message,
        "model": model,
    }

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        type=str,
        default="scenarios_llm_200.csv",
        help="CSV file containing columns: input, expected_output",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        required=True,
        help="CSV file where predictions will be saved",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://127.0.0.1:8004",
        help="Base URL of your FastAPI service",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="OpenRouter model name, e.g. openai/gpt-4o-mini",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Delay in seconds between requests",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    df = pd.read_csv(input_path)

    required_columns = {"input", "expected_output"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    records = []

    for idx, row in df.iterrows():
        user_message = str(row["input"])
        expected_output = row["expected_output"]

        print(f"[{idx + 1}/{len(df)}] Calling model: {args.model}")
        print(f"Prompt: {user_message}")

        status = "success"
        http_error = None
        raw_response = None
        parsed_result = None

        try:
            api_response = call_openrouter_parser(
                base_url=args.base_url,
                user_message=user_message,
                model=args.model,
            )

            raw_response = api_response
            parsed_result = api_response.get("result")

            print("-> Success")
            print(json.dumps(parsed_result, indent=2, ensure_ascii=False))

        except requests.HTTPError as exc:
            status = "http_error"
            http_error = str(exc)
            print(f"-> HTTP error: {exc}")

        except requests.RequestException as exc:
            status = "request_error"
            http_error = str(exc)
            print(f"-> Request error: {exc}")

        except Exception as exc:
            status = "unexpected_error"
            http_error = str(exc)
            print(f"-> Unexpected error: {exc}")

        records.append(
            {
                "index": idx,
                "model": args.model,
                "input": user_message,
                "expected_output": expected_output,
                "status": status,
                "error": http_error,
                "prediction_json": json.dumps(parsed_result, ensure_ascii=False)
                if parsed_result is not None
                else None,
                "raw_response_json": json.dumps(raw_response, ensure_ascii=False)
                if raw_response is not None
                else None,
            }
        )

        if args.sleep > 0:
            time.sleep(args.sleep)

    result_df = pd.DataFrame(records)
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\nSaved predictions to: {output_path}")


if __name__ == "__main__":
    main()

