#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Where the library stands against the daily-reading targets.

    python tools/progress.py

The agreed stage is 30 articles per category. A full year would be 365.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import content  # noqa: E402
from src.categories import CATEGORIES, CATEGORY_ORDER  # noqa: E402

TARGET = 30


def main() -> int:
    width = max(len(CATEGORIES[s].label) for s in CATEGORY_ORDER)
    total = 0
    print(f'{"":<{width}}  現在  目標({TARGET})    一年(365)')
    for slug in CATEGORY_ORDER:
        count = len(content.articles_in_category(slug))
        total += count
        gap = max(TARGET - count, 0)
        print(
            f'{CATEGORIES[slug].label:<{width}}  {count:>4}  '
            f'{("達成" if gap == 0 else "還缺 %d 篇" % gap):>10}  '
            f'{content.DAYS_IN_YEAR - count:>6}'
        )
    # A category that overshoots the target does not pay for one that is behind.
    gap = sum(max(TARGET - len(content.articles_in_category(s)), 0)
              for s in CATEGORY_ORDER)
    print(f'{"合計":<{width}}  {total:>4}  {gap:>10}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())