#!/usr/bin/env python
# -*- coding: utf-8 */
"""Export the content library to JSON for the static GitHub Pages build.

The static site runs entirely in the browser, so it needs the same article and
question data as the Streamlit app. Rather than maintaining two copies by hand,
this script derives site/data/articles.json from src/content.py.

Each question is exported in its **source** option order together with the
precomputed `shuffleOrder` array, so the browser reproduces the exact same
layout as build_lesson() without having to reimplement Python's Mersenne
Twister. One source of truth, identical output on both platforms.

Usage:
    python tools/export_site_data.py            # write the file
    python tools/export_site_data.py --check     # fail if it is out of date
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from random import Random

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import content  # noqa: E402

OUTPUT_PATH = PROJECT_ROOT / "site" / "data" / "articles.json"


def _shuffle_order(article_id: str, number: int) -> list[int]:
    """Reproduce the permutation build_lesson() applies, as a plain array.

    `_shuffled` builds order by shuffling [0,1,2,3], then maps
    new_options[k] = options[order[k]]. Exposing order directly lets the
    browser do the same thing without a PRNG.
    """
    order = list(range(content.OPTION_COUNT))
    Random(content.lesson_seed(article_id, number)).shuffle(order)
    return order


def build_payload() -> dict:
    articles = []
    for article in content.ARTICLES:
        questions = []
        for question in article.questions:
            questions.append(
                {
                    "number": question.number,
                    "skill": question.skill,
                    "stem": question.stem,
                    "options": list(question.options),
                    "sourceCorrectIndex": question.correct_index,
                    "shuffleOrder": _shuffle_order(article.id, question.number),
                    "hint": question.hint,
                    "gist": question.gist,
                }
            )
        articles.append(
            {
                "id": article.id,
                "title": article.title,
                "displayTitle": article.display_title,
                "author": article.author,
                "genre": article.genre,
                "text": article.text,
                "questions": questions,
            }
        )
    return {
        "generatedFrom": "src/content.py",
        "optionCount": content.OPTION_COUNT,
        "questionCount": content.TOTAL_QUESTIONS,
        "articles": articles,
    }


def render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the generated file is missing or stale",
    )
    args = parser.parse_args()

    text = render(build_payload())

    if args.check:
        if not OUTPUT_PATH.exists():
            print(f"missing: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        if OUTPUT_PATH.read_text(encoding="utf-8") != text:
            print(
                "stale: site/data/articles.json does not match src/content.py "
                "(run: python tools/export_site_data.py)",
                file=sys.stderr,
            )
            return 1
        print("site/data/articles.json is up to date")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
