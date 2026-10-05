# -*- coding: utf-8 -*-
"""Guard rails for the static browser build served by GitHub Pages.

The site/ tree is a second implementation of the app, so it needs its own
checks. These are the ones that would otherwise fail silently.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE = PROJECT_ROOT / 'site'
INDEX = SITE / 'index.html'
ARTICLES_JSON = SITE / 'data' / 'articles.json'
CONTRACT = PROJECT_ROOT / 'tests' / 'site' / 'run_contract.mjs'
APP_HARNESS = PROJECT_ROOT / 'tests' / 'site' / 'run_app.mjs'

sys.path.insert(0, str(PROJECT_ROOT))
from src import content  # noqa: E402
from src.categories import CATEGORY_ORDER  # noqa: E402
from tools.export_site_data import build_payload  # noqa: E402

requires_node = pytest.mark.skipif(
    shutil.which('node') is None, reason='Node is not installed'
)


def _site_files() -> list[str]:
    return [
        path.relative_to(SITE).as_posix()
        for path in SITE.rglob('*')
        if path.is_file()
    ]


def test_the_essentials_exist():
    for relative in [
        'index.html',
        'styles.css',
        'app.js',
        'lib/parser.js',
        'lib/reflection.js',
        'data/articles.json',
    ]:
        assert (SITE / relative).exists(), f'missing site/{relative}'


def test_index_references_only_files_that_exist():
    """A typo in a src/href is a 404 that no Python test would otherwise catch."""
    html = INDEX.read_text(encoding='utf-8')
    referenced = re.findall(r'(?:href|src)="([^"]+)"', html)
    present = set(_site_files())
    for target in referenced:
        if target.startswith(('http', 'data:', '#')):
            continue
        assert target in present, f'index.html references missing {target!r}'


def test_articles_json_matches_the_python_content_library():
    """The browser must show exactly what the Streamlit app shows."""
    on_disk = json.loads(ARTICLES_JSON.read_text(encoding='utf-8'))
    assert on_disk == build_payload()


def test_articles_json_carries_every_article_and_question():
    data = json.loads(ARTICLES_JSON.read_text(encoding='utf-8'))
    assert len(data['articles']) == len(content.ARTICLES)
    assert len(data['categories']) == len(CATEGORY_ORDER)
    for article in data['articles']:
        assert article['text'].strip()
        assert len(article['questions']) == 10
        for question in article['questions']:
            assert len(question['options']) == 4
            assert sorted(question['shuffleOrder']) == [0, 1, 2, 3]
            assert 0 <= question['sourceCorrectIndex'] < 4
            assert question['gist'].strip()


def test_shuffle_order_reproduces_the_python_lesson():
    """build_lesson() and the browser must place the answer identically."""
    from src.content import build_lesson

    data = json.loads(ARTICLES_JSON.read_text(encoding='utf-8'))
    for article in data['articles']:
        lesson = build_lesson(article['id'])
        for exported, built in zip(article['questions'], lesson.questions):
            assert exported['shuffleOrder'], (article['id'], exported['number'])
            shown = [exported['options'][i] for i in exported['shuffleOrder']]
            assert shown == list(built.options)
            assert shown[exported['shuffleOrder'].index(
                exported['sourceCorrectIndex']
            )] == built.correct_text


@requires_node
def test_javascript_parser_meets_the_same_contract_as_python():
    """Run the shipped parser.js under Node and assert its guarantees.

    The browser and Streamlit implementations are not bit-identical — they
    cannot be — but they must behave identically on the things that matter.
    """
    result = subprocess.run(
        ['node', str(CONTRACT)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=180,
    )
    assert result.returncode == 0, (
        f'contract failures:\n{result.stdout}\n{result.stderr}'
    )
    summary = json.loads(result.stdout)
    assert summary['articles'] == len(content.ARTICLES)
    assert summary['questions'] == 10 * len(content.ARTICLES)
    # 4 options per question, every one checked as a round trip.
    assert summary['verbatimChecked'] == 40 * len(content.ARTICLES)
    assert summary['verbatimWrong'] == 0
    assert summary['collapsed'] == 0
    assert summary['negativeAccepted'] == 0
    assert summary['failures'] == []


@requires_node
def test_the_shipped_app_js_runs_end_to_end():
    """Drive site/app.js under a minimal DOM stub, through all five lessons.

    There is no headless browser in CI, so this stands in for one. It catches
    the failure mode nothing else would: an element id typo or a mis-wired
    handler that leaves the page rendering but silently doing nothing.
    """
    result = subprocess.run(
        ['node', str(APP_HARNESS)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=180,
    )
    assert result.returncode == 0, (
        f'app harness failures:\n{result.stdout}\n{result.stderr}'
    )
    assert json.loads(result.stdout)['failures'] == []


def test_the_site_never_embeds_an_api_key():
    """A public URL cannot ship a credential; the browser build must be offline."""
    banned = re.compile(r'sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_')
    for path in SITE.rglob('*'):
        if path.is_file() and path.suffix in {'.js', '.html', '.css', '.json', '.md'}:
            found = banned.search(path.read_text(encoding='utf-8'))
            assert found is None, f'{path} looks like it contains a credential'


def test_the_site_does_not_call_any_remote_llm():
    """Everything runs on-device: no fetch to an API endpoint, no API key."""
    for name in ('app.js', 'lib/parser.js', 'lib/reflection.js'):
        source = (SITE / name).read_text(encoding='utf-8')
        assert 'api.deepseek.com' not in source
        assert 'openai' not in source.lower() or 'speechRecognition' in source
    app_source = (SITE / 'app.js').read_text(encoding='utf-8')
    fetches = re.findall(r"fetch\(['\"]([^'\"]+)", app_source)
    assert fetches == ['data/articles.json'], (
        f'the page should only fetch its own data, got {fetches}'
    )
