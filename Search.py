#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a CSV summary of English words by first letter and last letter.

Output rows:
- pair: (a,a), (a,b), ..., (z,z) = 676 rows
- total_count: total words matching first/last letter
- len_3_count: number of 3-letter words
- len_4_count: number of 4-letter words
- len_5_count: number of 5-letter words
- len_6_count: number of 6-letter words
- len_7_count: number of 7-letter words
- len_8_count: number of 8-letter words
- len_9_count: number of 9-letter words
- len_10_plus_count: number of words with length >= 10

Recommended usage:

1. Prepare a plain text dictionary file, one word per line.
   Example:
     words_alpha.txt

2. Put the dictionary file in this same folder.

3. Run:
     python3 Search.py words_alpha.txt letter_pair_counts.csv

If you do not specify arguments, the script uses:
     input : words_alpha.txt
     output: letter_pair_counts.csv

Notes:
- Only alphabetic a-z words are counted.
- Words shorter than 3 letters are ignored.
- Duplicate words are removed.
- Proper nouns are not specially detected; use a lowercase/common-word dictionary if you want to exclude them.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple


DEFAULT_INPUT = "words_alpha.txt"
DEFAULT_OUTPUT = "letter_pair_counts.csv"
DEFAULT_LOW_COUNT_OUTPUT = "letter_pair_counts_total_le_10.csv"
LOW_COUNT_THRESHOLD = 10
LETTERS = "abcdefghijklmnopqrstuvwxyz"
MIN_WORD_LENGTH = 3
SCRIPT_VERSION = "letter_pair_counter_v1"


Pair = Tuple[str, str]
LengthBucketCounts = Dict[str, int]


def normalize_word(raw_word: str) -> str:
    """
    Normalize a dictionary entry.

    This keeps only simple English alphabet words.
    Examples:
    - "Apple" -> "apple"
    - "can't" -> ""      because apostrophes are excluded
    - "ice-cream" -> ""  because hyphens are excluded
    - "hello123" -> ""   because numbers are excluded
    """
    word = raw_word.strip().lower()

    # Remove comments that often appear in word-list files.
    # Example: "apple # noun" -> "apple"
    word = word.split("#", 1)[0].strip()

    if not word:
        return ""

    if not re.fullmatch(r"[a-z]+", word):
        return ""

    if len(word) < MIN_WORD_LENGTH:
        return ""

    return word


def load_words(dictionary_path: Path) -> Set[str]:
    """Load and normalize a word list from a text file."""
    if not dictionary_path.exists():
        raise FileNotFoundError(f"Dictionary file not found: {dictionary_path}")

    words: Set[str] = set()

    with dictionary_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            word = normalize_word(line)
            if word:
                words.add(word)

    if not words:
        raise ValueError(
            "No valid words were found. Make sure the dictionary file contains "
            "one English word per line."
        )

    return words


def make_empty_counts() -> LengthBucketCounts:
    """Create an empty count dictionary for one first/last-letter pair."""
    return {
        "total_count": 0,
        "len_3_count": 0,
        "len_4_count": 0,
        "len_5_count": 0,
        "len_6_count": 0,
        "len_7_count": 0,
        "len_8_count": 0,
        "len_9_count": 0,
        "len_10_plus_count": 0,
    }


def get_length_bucket(word: str) -> str:
    """Return the CSV count column name corresponding to the word length."""
    length = len(word)
    if length >= 10:
        return "len_10_plus_count"
    return f"len_{length}_count"


def count_words_by_pair(words: Iterable[str]) -> Dict[Pair, LengthBucketCounts]:
    """
    Count words for all 26 x 26 first/last-letter pairs.

    Returns a dictionary keyed by (first_letter, last_letter).
    Every pair exists in the output, even when the count is zero.
    """
    counts: Dict[Pair, LengthBucketCounts] = {
        (first, last): make_empty_counts()
        for first in LETTERS
        for last in LETTERS
    }

    for word in words:
        first = word[0]
        last = word[-1]
        pair = (first, last)

        if pair not in counts:
            # This should not happen after normalize_word(), but keep it safe.
            continue

        counts[pair]["total_count"] += 1
        bucket = get_length_bucket(word)
        if bucket in counts[pair]:
            counts[pair][bucket] += 1

    return counts


def get_csv_fieldnames() -> list[str]:
    return [
        "pair",
        "total_count",
        "len_3_count",
        "len_4_count",
        "len_5_count",
        "len_6_count",
        "len_7_count",
        "len_8_count",
        "len_9_count",
        "len_10_plus_count",
    ]


def iter_count_rows(counts: Dict[Pair, LengthBucketCounts]) -> Iterable[dict[str, int | str]]:
    for first in LETTERS:
        for last in LETTERS:
            pair = (first, last)
            row: dict[str, int | str] = {"pair": f"({first},{last})"}
            row.update(counts[pair])
            yield row


def write_counts_csv(counts: Dict[Pair, LengthBucketCounts], output_path: Path) -> None:
    """Write 676 first/last-letter count rows to CSV."""
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_csv_fieldnames())
        writer.writeheader()
        writer.writerows(iter_count_rows(counts))


def write_low_count_pairs_csv(
    counts: Dict[Pair, LengthBucketCounts],
    output_path: Path,
    threshold: int = LOW_COUNT_THRESHOLD,
) -> int:
    """Write rows where total_count is less than or equal to threshold."""
    extracted_rows = [
        row for row in iter_count_rows(counts)
        if int(row["total_count"]) <= threshold
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_csv_fieldnames())
        writer.writeheader()
        writer.writerows(extracted_rows)

    return len(extracted_rows)


def print_summary(
    words: Set[str],
    counts: Dict[Pair, LengthBucketCounts],
    output_path: Path,
    low_count_output_path: Path,
    low_count_rows: int,
) -> None:
    """Print a short terminal summary after CSV creation."""
    nonzero_pairs = sum(1 for pair_counts in counts.values() if pair_counts["total_count"] > 0)

    top_pairs = sorted(
        counts.items(),
        key=lambda item: item[1]["total_count"],
        reverse=True,
    )[:10]

    print("=" * 72)
    print("Letter pair count CSV created")
    print("=" * 72)
    print(f"Unique valid words : {len(words):,}")
    print(f"Total pairs        : 676")
    print(f"Non-zero pairs     : {nonzero_pairs}")
    print(f"Output             : {output_path}")
    print(f"<= 10 output       : {low_count_output_path}")
    print(f"<= 10 rows         : {low_count_rows}")
    print("\nTop 10 pairs by total_count:")

    for (first, last), pair_counts in top_pairs:
        print(f"  ({first},{last}) : {pair_counts['total_count']:,}")


def create_letter_pair_count_csv(
    dictionary_path: Path,
    output_path: Path,
    low_count_output_path: Path,
) -> None:
    """Main conversion function."""
    words = load_words(dictionary_path)
    counts = count_words_by_pair(words)
    write_counts_csv(counts, output_path)
    low_count_rows = write_low_count_pairs_csv(counts, low_count_output_path)
    print_summary(words, counts, output_path, low_count_output_path, low_count_rows)


def main() -> None:
    print(f"Running Search.py mode: {SCRIPT_VERSION}")

    parser = argparse.ArgumentParser(
        description="Count dictionary words by first letter, last letter, and word length bucket."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=DEFAULT_INPUT,
        help=f"Input dictionary text file. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=DEFAULT_OUTPUT,
        help=f"Output CSV file. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "low_count_output",
        nargs="?",
        default=DEFAULT_LOW_COUNT_OUTPUT,
        help=f"Output CSV file for rows where total_count <= {LOW_COUNT_THRESHOLD}. Default: {DEFAULT_LOW_COUNT_OUTPUT}",
    )
    args = parser.parse_args()

    try:
        create_letter_pair_count_csv(Path(args.input), Path(args.output), Path(args.low_count_output))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
