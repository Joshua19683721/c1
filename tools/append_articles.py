#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Append authored articles to a category module.

    python tools/append_articles.py src/categories/society.py defs.txt entries.txt

*defs.txt* holds the shared text/question definitions (_X_TEXT, _X_QUESTIONS);
*entries.txt* holds the matching article(...) calls. The definitions are spliced
in just above the ARTICLES tuple and the entries just inside its closing
bracket, which is where every category module expects them.

Kept as a real tool rather than a throwaway script: adding 30+ articles per
category is a batch operation, and the splice has to be identical every time.
"""

from __future__ import annotations

import argparse
import io
import sys

ANCHOR = 'ARTICLES = ('
#: Characters that only exist in simplified text; flagged so a slip is caught
#: before it reaches the library-wide test.
SIMPLIFIED_ONLY = '们个静现学书说语读写给应该认识这么为吗体对错进过还没点热爱双边万与专东丝严丧'


def _closing_index(source: str) -> int:
    if source.endswith('\n)\n'):
        return source.rindex('\n)\n')
    return source.rindex('\n)')


def append(target: str, defs_path: str, entries_path: str) -> int:
    source = io.open(target, encoding='utf-8').read()
    defs = io.open(defs_path, encoding='utf-8').read()
    entries = io.open(entries_path, encoding='utf-8').read()

    hits = sorted({ch for ch in SIMPLIFIED_ONLY if ch in defs or ch in entries})
    if hits:
        raise SystemExit(f'simplified characters in the new text: {"".join(hits)}')

    anchor = source.index(ANCHOR)
    source = source[:anchor] + defs.rstrip('\n') + '\n\n' + source[anchor:]
    closing = _closing_index(source)
    source = source[:closing] + '\n' + entries.rstrip('\n') + source[closing:]

    io.open(target, 'w', encoding='utf-8', newline='\n').write(source)
    return defs.count('_TEXT = (')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', help='category module, e.g. src/categories/fable.py')
    parser.add_argument('defs', help='file holding the _TEXT/_QUESTIONS definitions')
    parser.add_argument('entries', help='file holding the article(...) calls')
    args = parser.parse_args()
    count = append(args.target, args.defs, args.entries)
    print(f'inserted {count} article(s) into {args.target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
