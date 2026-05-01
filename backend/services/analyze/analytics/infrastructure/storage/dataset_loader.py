"""
Infrastructure – Storage Layer
===============================
Low-level CSV reading utilities that handle the quirks of the data files
(extra columns, encoding issues, etc.). No Django, no business logic here.
"""
from __future__ import annotations

import csv as csv_module
import logging
import re as _re
from io import StringIO

import pandas as pd

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Low-level CSV reader for analytics datasets.

    Handles the common case where data rows contain more fields than the header
    (an extra unnamed column was inserted). Uses a weighted heuristic to detect
    the best insertion position for the extra column so every real column maps
    to its correct header.
    """

    @staticmethod
    def read_csv_safe(file_obj) -> pd.DataFrame:
        """
        Read a CSV file-like object robustly.

        Detection strategy for exactly 1 extra data field:
        1. Check every possible insertion position.
        2. Score each position using heuristics (state column value, date
           column format, numeric columns, churn-sum relationship).
        3. Pick the highest-scoring position; fall back to appending at end.
        """
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        lines = content.strip().split("\n")
        if len(lines) < 2:
            return pd.read_csv(StringIO(content))

        header_fields = list(next(csv_module.reader(StringIO(lines[0]))))
        sample_rows = [
            list(next(csv_module.reader(StringIO(line))))
            for line in lines[1 : min(6, len(lines))]
        ]

        n_header = len(header_fields)
        n_data = len(sample_rows[0]) if sample_rows else n_header

        if n_data <= n_header:
            df = pd.read_csv(StringIO(content))
            # Drop any leading/trailing unnamed or empty-name columns
            cols_to_drop = [
                c for c in df.columns
                if str(c).startswith("Unnamed:") or str(c).strip() == ""
            ]
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
            return df

        extra_count = n_data - n_header

        if extra_count == 1:
            best_pos = DatasetLoader._detect_extra_col_position(header_fields, sample_rows)
            all_names = list(header_fields)
            all_names.insert(best_pos, "_extra_col_0")
            return pd.read_csv(StringIO(content), names=all_names, skiprows=1)

        # Multiple extra columns – append at end (safest generic default)
        extra_names = [f"_extra_col_{i}" for i in range(extra_count)]
        all_names = list(header_fields) + extra_names
        return pd.read_csv(StringIO(content), names=all_names, skiprows=1)

    @staticmethod
    def _detect_extra_col_position(header_fields: list[str], sample_rows: list[list[str]]) -> int:
        """
        Return the best insertion index for a single extra data column.

        Uses a weighted scoring system:
          • 'state' column should contain MR/PR state strings (+10 / -10)
          • 'Creation_Date' should look like a datetime (+5 / -5)
          • Numeric-name columns (#Commits, etc.) should be integers (+1 / -2)
          • extra_col == churn_deletions + initial_mr_size pattern (+8)
        """
        n_header = len(header_fields)
        n_data = n_header + 1
        valid_states = frozenset({"opened", "merged", "closed", "open", "locked"})

        def data_idx(hdr_i: int, insert_at: int) -> int:
            return hdr_i if hdr_i < insert_at else hdr_i + 1

        hdr_map = {name: i for i, name in enumerate(header_fields)}

        int_cols = [
            hdr_map[c]
            for c in (
                "#Discussions",
                "#Commits",
                "#UniqueCommiters",
                "nb_minor_author",
                "nb_major_author",
                "modified_files",
                "#people",
                "#reviewers",
                "#commiters",
                "#discussionners",
                "comments",
                "filetypes",
            )
            if c in hdr_map
        ]

        state_hi = hdr_map.get("state")
        date_hi = hdr_map.get("Creation_Date")
        churn_del_hi = hdr_map.get("churn_deletions")
        init_size_hi = hdr_map.get("initial_mr_size", hdr_map.get("initial_pr_size"))

        best_pos = n_header
        best_score = -999

        for insert_at in range(n_header + 1):
            score = 0
            for row in sample_rows:
                if len(row) < n_data:
                    continue

                if state_hi is not None:
                    di = data_idx(state_hi, insert_at)
                    if di < len(row) and row[di].strip() in valid_states:
                        score += 10
                    else:
                        score -= 10

                if date_hi is not None:
                    di = data_idx(date_hi, insert_at)
                    if di < len(row) and _re.match(r"\d{4}-\d{2}-\d{2}", row[di].strip()):
                        score += 5
                    else:
                        score -= 5

                for hi in int_cols:
                    di = data_idx(hi, insert_at)
                    if di < len(row):
                        try:
                            v = float(row[di])
                            if v == int(v):
                                score += 1
                            else:
                                score -= 2
                        except ValueError:
                            score -= 2

                if churn_del_hi is not None and init_size_hi is not None:
                    cd_i = data_idx(churn_del_hi, insert_at)
                    is_i = data_idx(init_size_hi, insert_at)
                    extra_val_i = insert_at
                    if extra_val_i < len(row) and cd_i < len(row) and is_i < len(row):
                        try:
                            ev = float(row[extra_val_i])
                            cv = float(row[cd_i])
                            iv = float(row[is_i])
                            if abs(ev - (cv + iv)) < 0.01:
                                score += 8
                        except ValueError:
                            pass

            if score > best_score:
                best_score = score
                best_pos = insert_at

        return best_pos
