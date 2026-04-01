import argparse
import json
from collections import defaultdict

import pandas as pd


IMPORTANT_FIELDS = [
    "intent",
    "platform",
    "metrics",
    "features",
    "dimensions",
    "visualization",
]

SET_LIKE_FIELDS = {"metrics", "features", "dimensions"}


def safe_json_loads(value):
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, float) and pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        return None


def normalize_json(obj):
    if isinstance(obj, dict):
        return {k: normalize_json(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [normalize_json(x) for x in obj]
    return obj


def json_equal(a, b):
    return normalize_json(a) == normalize_json(b)


def to_normalized_set(value):
    if value is None:
        return set()

    if isinstance(value, list):
        result = set()
        for item in value:
            if isinstance(item, (dict, list)):
                result.add(
                    json.dumps(
                        normalize_json(item),
                        sort_keys=True,
                        ensure_ascii=False,
                    )
                )
            else:
                result.add(str(item).strip())
        return result

    return {str(value).strip()}


def compute_set_metrics(expected_value, predicted_value):
    expected_set = to_normalized_set(expected_value)
    predicted_set = to_normalized_set(predicted_value)

    tp = len(expected_set & predicted_set)
    fp = len(predicted_set - expected_set)
    fn = len(expected_set - predicted_set)

    overlap_precision = tp / len(predicted_set) if predicted_set else 0.0
    overlap_recall = tp / len(expected_set) if expected_set else 0.0
    overlap_f1 = (
        2 * overlap_precision * overlap_recall / (overlap_precision + overlap_recall)
        if (overlap_precision + overlap_recall) > 0
        else 0.0
    )

    exact_match = expected_set == predicted_set
    subset_match = expected_set.issubset(predicted_set)

    return {
        "expected_count": len(expected_set),
        "predicted_count": len(predicted_set),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "overlap_precision": overlap_precision,
        "overlap_recall": overlap_recall,
        "overlap_f1": overlap_f1,
        "exact_match": exact_match,
        "subset_match": subset_match,
    }


def compute_sample_level_match_scores(match_count, total_count):
    """
    For sample-level exact/subset match, each sample is one comparison.
    In this setup, accuracy / precision / recall / f1 collapse to the same rate.
    """
    rate = match_count / total_count if total_count else 0.0
    return {
        "count": match_count,
        "total": total_count,
        "accuracy": rate,
        "precision": rate,
        "recall": rate,
        "f1": rate,
    }


def compare_scalar_field(expected_value, predicted_value):
    return normalize_json(expected_value) == normalize_json(predicted_value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--predictions-file",
        type=str,
        required=True,
        help="CSV produced by run_model_eval.py",
    )
    parser.add_argument(
        "--report-file",
        type=str,
        default="evaluation_report.json",
        help="Where to save the summary report",
    )
    parser.add_argument(
        "--details-file",
        type=str,
        default="evaluation_details.csv",
        help="Where to save row-by-row comparison details",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.predictions_file)

    total = len(df)
    success_count = 0
    valid_prediction_json_count = 0
    full_exact_match_count = 0

    scalar_field_totals = defaultdict(int)
    scalar_field_correct = defaultdict(int)

    set_field_sample_count = defaultdict(int)

    # sample-level exact/subset counts
    set_field_exact_count = defaultdict(int)
    set_field_subset_count = defaultdict(int)

    # item-overlap sums
    set_field_overlap_precision_sum = defaultdict(float)
    set_field_overlap_recall_sum = defaultdict(float)
    set_field_overlap_f1_sum = defaultdict(float)

    detail_rows = []

    for _, row in df.iterrows():
        status = row.get("status")
        if status == "success":
            success_count += 1

        expected = safe_json_loads(row.get("expected_output"))
        predicted = safe_json_loads(row.get("prediction_json"))

        valid_prediction = predicted is not None
        if valid_prediction:
            valid_prediction_json_count += 1

        full_exact_match = False
        if isinstance(expected, dict) and isinstance(predicted, dict):
            full_exact_match = json_equal(expected, predicted)

        if full_exact_match:
            full_exact_match_count += 1

        detail = {
            "index": row.get("index"),
            "model": row.get("model"),
            "status": status,
            "valid_prediction_json": valid_prediction,
            "full_exact_match": full_exact_match,
            "input": row.get("input"),
            "expected_output": row.get("expected_output"),
            "prediction_json": row.get("prediction_json"),
        }

        for field in IMPORTANT_FIELDS:
            expected_has_field = isinstance(expected, dict) and field in expected
            expected_value = expected.get(field) if isinstance(expected, dict) else None
            predicted_value = predicted.get(field) if isinstance(predicted, dict) else None

            if not expected_has_field:
                detail[f"{field}_available_in_expected"] = False
                continue

            detail[f"{field}_available_in_expected"] = True

            if field in SET_LIKE_FIELDS:
                metrics = compute_set_metrics(expected_value, predicted_value)

                set_field_sample_count[field] += 1

                # sample-level match counts
                if metrics["exact_match"]:
                    set_field_exact_count[field] += 1
                if metrics["subset_match"]:
                    set_field_subset_count[field] += 1

                # item-overlap sums
                set_field_overlap_precision_sum[field] += metrics["overlap_precision"]
                set_field_overlap_recall_sum[field] += metrics["overlap_recall"]
                set_field_overlap_f1_sum[field] += metrics["overlap_f1"]

                detail[f"{field}_exact_match"] = metrics["exact_match"]
                detail[f"{field}_subset_match"] = metrics["subset_match"]

                detail[f"{field}_overlap_precision"] = metrics["overlap_precision"]
                detail[f"{field}_overlap_recall"] = metrics["overlap_recall"]
                detail[f"{field}_overlap_f1"] = metrics["overlap_f1"]

                detail[f"{field}_tp"] = metrics["tp"]
                detail[f"{field}_fp"] = metrics["fp"]
                detail[f"{field}_fn"] = metrics["fn"]
                detail[f"{field}_expected_count"] = metrics["expected_count"]
                detail[f"{field}_predicted_count"] = metrics["predicted_count"]

            else:
                is_correct = compare_scalar_field(expected_value, predicted_value)
                scalar_field_totals[field] += 1
                if is_correct:
                    scalar_field_correct[field] += 1

                detail[f"{field}_correct"] = is_correct

        detail_rows.append(detail)

    scalar_field_accuracy = {}
    for field in sorted(scalar_field_totals.keys()):
        total_count = scalar_field_totals[field]
        correct_count = scalar_field_correct[field]
        acc = correct_count / total_count if total_count else 0.0
        scalar_field_accuracy[field] = {
            "correct": correct_count,
            "total": total_count,
            "accuracy": acc,
            "precision": acc,
            "recall": acc,
            "f1": acc,
        }

    set_field_metrics_summary = {}
    for field in sorted(set_field_sample_count.keys()):
        n = set_field_sample_count[field]

        exact_scores = compute_sample_level_match_scores(set_field_exact_count[field], n)
        subset_scores = compute_sample_level_match_scores(set_field_subset_count[field], n)

        set_field_metrics_summary[field] = {
            "samples": n,
            "exact_match": exact_scores,
            "subset_match": subset_scores,
            "overlap_metrics": {
                "precision": set_field_overlap_precision_sum[field] / n if n else 0.0,
                "recall": set_field_overlap_recall_sum[field] / n if n else 0.0,
                "f1": set_field_overlap_f1_sum[field] / n if n else 0.0,
            },
        }

    full_exact_scores = compute_sample_level_match_scores(full_exact_match_count, total)

    report = {
        "total_samples": total,
        "success_rate": success_count / total if total else 0.0,
        "valid_prediction_json_rate": valid_prediction_json_count / total if total else 0.0,
        "full_output_exact_match": full_exact_scores,
        "scalar_field_metrics": scalar_field_accuracy,
        "set_field_metrics": set_field_metrics_summary,
    }

    with open(args.report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    details_df = pd.DataFrame(detail_rows)
    details_df.to_csv(args.details_file, index=False, encoding="utf-8-sig")

    print("\n=== Evaluation Summary ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSaved summary report to: {args.report_file}")
    print(f"Saved detailed results to: {args.details_file}")


if __name__ == "__main__":
    main()