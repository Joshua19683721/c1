# -*- coding: utf-8 -*-
"""The library is Traditional Chinese, not just converted-by-accident.

The character list lives in src.zh so the authoring tool and this test agree on
what counts as a slip.
"""

from __future__ import annotations

import pytest

from src import content
from src.zh import SIMPLIFIED_ONLY


def _strings(article):
    yield 'title', article.title
    yield 'genre', article.genre
    yield 'text', article.text
    for question in article.questions:
        yield f'Q{question.number}.stem', question.stem
        yield f'Q{question.number}.hint', question.hint
        yield f'Q{question.number}.explanation', question.explanation
        yield f'Q{question.number}.gist', question.gist
        for index, option in enumerate(question.options, start=1):
            yield f'Q{question.number}.option{index}', option


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_article_is_traditional_chinese(article):
    hits = [
        f'{where}: {value[:30]}'
        for where, value in _strings(article)
        if any(char in value for char in SIMPLIFIED_ONLY)
    ]
    assert not hits, 'simplified characters found:\n  ' + '\n  '.join(hits)
