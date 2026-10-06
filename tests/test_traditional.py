# -*- coding: utf-8 -*-
"""The library is Traditional Chinese, not just converted-by-accident.

The character list lives in src.zh so the authoring tool and this test agree on
what counts as a slip.
"""

from __future__ import annotations

import pathlib

import pytest

from src import content
from src.zh import SIMPLIFIED_ONLY

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Files that render the end-of-session reflection (閱讀思考拼圖 and the CoT
#: steps) or the article UI. The reflection is written by the model at runtime,
#: so its templates and the surrounding chrome have to be Traditional too.
REFLECTION_SURFACES = (
    'app.py',
    'src/cot.py',
    'src/ui.py',
    'src/prompts.py',
    'site/app.js',
    'site/index.html',
    'site/lib/reflection.js',
    'dsh_config/read_express_cot_pipelines_elem.yaml',
)


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


@pytest.mark.parametrize('relative', REFLECTION_SURFACES)
def test_reflection_surfaces_are_traditional(relative):
    path = PROJECT_ROOT / relative
    if not path.exists():  # pragma: no cover - the file is part of the repo
        pytest.skip(f'{relative} is missing')
    text = path.read_text(encoding='utf-8')
    hits = sorted({char for char in SIMPLIFIED_ONLY if char in text})
    assert not hits, f'{relative} contains simplified characters: {"".join(hits)}'
