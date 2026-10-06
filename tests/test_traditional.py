# -*- coding: utf-8 -*-
"""The library is Traditional Chinese, not just converted-by-accident.

Deliberately a narrow character list: characters like 台/臺 or 月台/月臺 are
Taiwan usage variants rather than simplified forms, so an OpenCC round-trip
would report false positives. These characters only exist in simplified text.
"""

from __future__ import annotations

import pytest

from src import content

#: Characters whose presence means the text is simplified, not a TW variant.
SIMPLIFIED_ONLY = '们个静现学书说语读写给应该认识这么为吗体对错进过还没点热爱双边万与专东丝严丧'


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
